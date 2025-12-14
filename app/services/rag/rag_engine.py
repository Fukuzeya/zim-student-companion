# ============================================================================
# Enhanced RAG Engine for Zim Student Companion
# Compatible with the Advanced Vector Store
# ============================================================================
from typing import List, Dict, Any, Optional, Tuple
import google.generativeai as genai
import logging
import json
import asyncio
from dataclasses import dataclass
from enum import Enum

from app.services.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)

# ============================================================================
# Enums and Data Classes
# ============================================================================
class ResponseMode(str, Enum):
    """Available response modes for the tutor"""
    SOCRATIC = "socratic"
    EXPLAIN = "explain"
    PRACTICE = "practice"
    HINT = "hint"
    SUMMARY = "summary"
    QUIZ = "quiz"

class DifficultyLevel(str, Enum):
    """Question difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

@dataclass
class RAGResponse:
    """Structured response from RAG engine"""
    response_text: str
    retrieved_docs: List[Dict[str, Any]]
    confidence_score: float
    mode_used: str
    context_used: bool

# ============================================================================
# RAG Engine Implementation
# ============================================================================
class RAGEngine:
    """Enhanced RAG engine for Zim Student Companion with advanced features"""
    
    def __init__(self, vector_store: VectorStore, settings):
        self.vector_store = vector_store
        self.settings = settings
        
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash')
        )
        
        # Configuration
        self._max_context_length = getattr(settings, 'MAX_CONTEXT_LENGTH', 8000)
        self._max_history_messages = getattr(settings, 'MAX_HISTORY_MESSAGES', 5)
        self._default_search_limit = getattr(settings, 'DEFAULT_SEARCH_LIMIT', 5)
        
        # Response mode configurations
        self._mode_configs = {
            ResponseMode.SOCRATIC: {
                "temperature": 0.7,
                "max_tokens": 800,
                "system_modifier": "Guide through questions, never give direct answers"
            },
            ResponseMode.EXPLAIN: {
                "temperature": 0.5,
                "max_tokens": 1200,
                "system_modifier": "Explain concepts clearly and thoroughly"
            },
            ResponseMode.PRACTICE: {
                "temperature": 0.6,
                "max_tokens": 600,
                "system_modifier": "Present practice questions and provide feedback"
            },
            ResponseMode.HINT: {
                "temperature": 0.6,
                "max_tokens": 400,
                "system_modifier": "Provide small, helpful hints without revealing answers"
            },
            ResponseMode.SUMMARY: {
                "temperature": 0.4,
                "max_tokens": 600,
                "system_modifier": "Summarize key points concisely"
            },
            ResponseMode.QUIZ: {
                "temperature": 0.7,
                "max_tokens": 800,
                "system_modifier": "Generate quiz questions to test understanding"
            }
        }
    
    # ==================== Main Query Method ====================
    
    async def query(
        self,
        question: str,
        student_context: Dict[str, Any],
        conversation_history: List[Dict[str, str]] = None,
        mode: str = "socratic"
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Main query method - retrieves context and generates response.
        
        Args:
            question: Student's question
            student_context: Info about the student (grade, subject, etc.)
            conversation_history: Previous messages in conversation
            mode: Response mode (socratic, explain, practice, hint, summary, quiz)
        
        Returns:
            Tuple of (response_text, retrieved_documents)
        """
        try:
            # Parse mode
            response_mode = ResponseMode(mode.lower()) if mode else ResponseMode.SOCRATIC
        except ValueError:
            response_mode = ResponseMode.SOCRATIC
            logger.warning(f"Invalid mode '{mode}', defaulting to socratic")
        
        # Step 1: Build search filters from student context
        filters = self._build_search_filters(student_context)
        
        # Step 2: Determine search strategy based on question type
        search_query = self._enhance_search_query(question, student_context)
        
        # Step 3: Retrieve relevant documents using hybrid search
        retrieved_docs = await self._retrieve_documents(
            query=search_query,
            filters=filters,
            limit=self._default_search_limit
        )
        
        # Step 4: Build context from retrieved documents
        context = self._build_context(retrieved_docs)
        
        # Step 5: Build the prompt based on mode
        prompt = self._build_prompt(
            question=question,
            context=context,
            student_context=student_context,
            conversation_history=conversation_history or [],
            mode=response_mode
        )
        
        # Step 6: Generate response with appropriate settings
        response = await self._generate_response(prompt, response_mode)
        
        # Step 7: Post-process response
        processed_response = self._post_process_response(response, response_mode)
        
        return processed_response, retrieved_docs
    
    async def query_with_metadata(
        self,
        question: str,
        student_context: Dict[str, Any],
        conversation_history: List[Dict[str, str]] = None,
        mode: str = "socratic"
    ) -> RAGResponse:
        """
        Query with full metadata response.
        """
        response_text, retrieved_docs = await self.query(
            question=question,
            student_context=student_context,
            conversation_history=conversation_history,
            mode=mode
        )
        
        # Calculate confidence based on retrieval scores
        confidence = self._calculate_confidence(retrieved_docs)
        
        return RAGResponse(
            response_text=response_text,
            retrieved_docs=retrieved_docs,
            confidence_score=confidence,
            mode_used=mode,
            context_used=len(retrieved_docs) > 0
        )
    
    # ==================== Document Retrieval ====================
    
    def _build_search_filters(self, student_context: Dict[str, Any]) -> Dict[str, Any]:
        """Build search filters from student context"""
        filters = {}
        
        # Map student context to filter fields
        field_mappings = {
            "education_level": "education_level",
            "grade": "grade",
            "current_subject": "subject",
            "subject": "subject"
        }
        
        for context_key, filter_key in field_mappings.items():
            value = student_context.get(context_key)
            if value and filter_key not in filters:
                filters[filter_key] = value
        
        return {k: v for k, v in filters.items() if v}
    
    def _enhance_search_query(self, question: str, student_context: Dict[str, Any]) -> str:
        """Enhance search query with context for better retrieval"""
        enhanced = question
        
        # Add subject context if available
        subject = student_context.get("current_subject") or student_context.get("subject")
        if subject and subject.lower() not in question.lower():
            enhanced = f"{subject}: {question}"
        
        return enhanced
    
    async def _retrieve_documents(
        self,
        query: str,
        filters: Dict[str, Any],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Retrieve documents using hybrid search with fallback"""
        try:
            # Try hybrid search first
            docs = await self.vector_store.hybrid_search(
                query=query,
                filters=filters if filters else None,
                limit=limit
            )
            
            # If no results with filters, try without
            if not docs and filters:
                logger.info("No filtered results, trying broader search")
                docs = await self.vector_store.hybrid_search(
                    query=query,
                    filters=None,
                    limit=limit
                )
            
            return docs
            
        except Exception as e:
            logger.error(f"Document retrieval failed: {e}")
            return []
    
    # ==================== Context Building ====================
    
    def _build_context(self, documents: List[Dict[str, Any]]) -> str:
        """Build context string from retrieved documents with smart truncation"""
        if not documents:
            return "No specific curriculum context available."
        
        context_parts = []
        total_length = 0
        
        for i, doc in enumerate(documents, 1):
            # Build source info
            source_info = self._format_source_info(doc, i)
            
            # Get content with length check
            content = doc.get("content", "")
            
            # Check if adding this would exceed limit
            entry = f"{source_info}\n{content}"
            if total_length + len(entry) > self._max_context_length:
                # Truncate content to fit
                remaining = self._max_context_length - total_length - len(source_info) - 50
                if remaining > 200:
                    content = content[:remaining] + "..."
                    entry = f"{source_info}\n{content}"
                else:
                    break
            
            context_parts.append(entry)
            total_length += len(entry)
        
        return "\n\n---\n\n".join(context_parts)
    
    def _format_source_info(self, doc: Dict[str, Any], index: int) -> str:
        """Format source information for context"""
        metadata = doc.get("metadata", {})
        
        parts = [f"[Source {index}"]
        
        if doc_type := metadata.get("document_type"):
            parts.append(f": {doc_type}")
        
        if subject := metadata.get("subject"):
            parts.append(f" - {subject}")
        
        if year := metadata.get("year"):
            parts.append(f" ({year})")
        
        if topic := metadata.get("topic"):
            parts.append(f" | Topic: {topic}")
        
        # Add relevance score if high
        score = doc.get("combined_score") or doc.get("score", 0)
        if score > 0.7:
            parts.append(" ⭐")
        
        parts.append("]")
        return "".join(parts)
    
    # ==================== Prompt Building ====================
    
    def _build_prompt(
        self,
        question: str,
        context: str,
        student_context: Dict[str, Any],
        conversation_history: List[Dict[str, str]],
        mode: ResponseMode
    ) -> str:
        """Build the complete prompt for generation"""
        
        # Base system instruction
        system_prompt = self._build_system_prompt(student_context, mode)
        
        # Mode-specific instructions
        mode_instructions = self._get_mode_instructions(mode)
        
        # Conversation context
        conv_context = self._format_conversation_history(conversation_history)
        
        # Assemble final prompt
        full_prompt = f"""{system_prompt}

{mode_instructions}

CURRICULUM CONTEXT (from ZIMSEC materials):
{context}

{conv_context}

Student's current message: {question}

Respond as the helpful ZIMSEC tutor:"""
        
        return full_prompt
    
    def _build_system_prompt(self, student_context: Dict[str, Any], mode: ResponseMode) -> str:
        """Build the system prompt with student context"""
        grade = student_context.get('grade', 'student')
        subject = student_context.get('current_subject', student_context.get('subject', 'their subjects'))
        name = student_context.get('first_name', 'Student')
        language = student_context.get('preferred_language', 'English')
        
        return f"""You are a friendly and encouraging AI tutor for Zimbabwean students, 
specializing in ZIMSEC curriculum. You're helping a {grade} student studying {subject}.

Student's name: {name}
Preferred language: {language}
Current mode: {mode.value.upper()}

IMPORTANT GUIDELINES:
1. Be warm, patient, and encouraging - use the student's name occasionally
2. Use examples relevant to Zimbabwe (ZWL currency, local places, Zimbabwean context)
3. Keep responses concise for WhatsApp (under 300 words unless explaining complex concepts)
4. Use emojis sparingly but appropriately 🎓
5. If the student seems confused, break things down further
6. Always encourage and celebrate progress
7. Relate concepts to real-world applications when possible"""
    
    def _get_mode_instructions(self, mode: ResponseMode) -> str:
        """Get specific instructions for each response mode"""
        instructions = {
            ResponseMode.SOCRATIC: """
SOCRATIC MODE - Guide through discovery! 🤔
- NEVER give direct answers
- Ask leading questions that help them think through the problem
- Break complex problems into smaller, manageable steps
- When they get stuck, provide gentle hints
- Celebrate their progress and "aha!" moments
- If they're close, encourage them to keep going
- Use phrases like "What do you think would happen if...?" or "Can you remember what we learned about...?"
""",
            ResponseMode.EXPLAIN: """
EXPLAIN MODE - Teach clearly! 📚
- Explain the concept step by step
- Use simple language appropriate for their grade level
- Include relevant examples from the ZIMSEC curriculum
- Connect to things they already know
- Use analogies from everyday Zimbabwean life
- End with a simple check question to verify understanding
""",
            ResponseMode.PRACTICE: """
PRACTICE MODE - Let's practice! ✍️
- Present the question clearly
- Wait for their answer before providing feedback
- If correct, congratulate warmly and explain why it's correct
- If incorrect, guide them toward the right approach without giving away the answer
- Encourage them to try again
- Track difficulty and adjust accordingly
""",
            ResponseMode.HINT: """
HINT MODE - Small nudges only! 💡
- Give ONE small hint at a time
- Don't reveal too much of the answer
- Connect to concepts they should already know
- Encourage them to try again with the hint
- Make hints progressively more helpful if they're still stuck
""",
            ResponseMode.SUMMARY: """
SUMMARY MODE - Key points only! 📝
- Provide a clear, concise summary
- Use bullet points for key concepts
- Highlight the most important takeaways
- Include memory aids or mnemonics if helpful
- Keep it brief and scannable
""",
            ResponseMode.QUIZ: """
QUIZ MODE - Test knowledge! 🎯
- Generate relevant questions based on the topic
- Mix question types (multiple choice, short answer)
- Provide immediate feedback on answers
- Explain why correct answers are correct
- Offer encouragement regardless of performance
"""
        }
        return instructions.get(mode, instructions[ResponseMode.SOCRATIC])
    
    def _format_conversation_history(self, history: List[Dict[str, str]]) -> str:
        """Format conversation history for context"""
        if not history:
            return ""
        
        # Take only recent messages
        recent = history[-self._max_history_messages:]
        
        formatted = "\nPrevious conversation:\n"
        for msg in recent:
            role = "Student" if msg.get("role") == "user" else "Tutor"
            content = msg.get("content", "")[:500]  # Truncate long messages
            formatted += f"{role}: {content}\n"
        
        return formatted
    
    # ==================== Response Generation ====================
    
    async def _generate_response(self, prompt: str, mode: ResponseMode) -> str:
        """Generate response using Gemini with mode-specific settings"""
        config = self._mode_configs.get(mode, self._mode_configs[ResponseMode.SOCRATIC])
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=config["temperature"],
                    top_p=0.9,
                    max_output_tokens=config["max_tokens"]
                ),
                safety_settings={
                    'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                    'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                    'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                    'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
                }
            )
            return response.text
            
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return self._get_fallback_response(mode)
    
    def _post_process_response(self, response: str, mode: ResponseMode) -> str:
        """Post-process the generated response"""
        if not response:
            return self._get_fallback_response(mode)
        
        # Clean up any artifacts
        response = response.strip()
        
        # Ensure response isn't too long for WhatsApp
        if len(response) > 1500 and mode != ResponseMode.EXPLAIN:
            # Try to find a good breaking point
            break_point = response.rfind('.', 0, 1400)
            if break_point > 1000:
                response = response[:break_point + 1]
                response += "\n\n(Let me know if you'd like me to continue! 😊)"
        
        return response
    
    def _get_fallback_response(self, mode: ResponseMode) -> str:
        """Get a fallback response when generation fails"""
        fallbacks = {
            ResponseMode.SOCRATIC: "I'm having a small hiccup right now 🙈 Could you try asking your question again? I'm here to help you think through it!",
            ResponseMode.EXPLAIN: "I'm experiencing a brief issue 🙏 Please try again, and I'll explain the concept clearly for you!",
            ResponseMode.PRACTICE: "Let me reset for a moment 🔄 Ask me again and we'll practice together!",
            ResponseMode.HINT: "Oops, let me try again 💡 What part are you stuck on?",
            ResponseMode.SUMMARY: "I need a moment to gather my thoughts 📝 Could you tell me what topic you'd like summarized?",
            ResponseMode.QUIZ: "Let me prepare a fresh quiz for you 🎯 What topic should we test?"
        }
        return fallbacks.get(mode, "I'm having trouble right now. Please try again in a moment. 🙏")
    
    # ==================== Confidence Calculation ====================
    
    def _calculate_confidence(self, docs: List[Dict[str, Any]]) -> float:
        """Calculate confidence score based on retrieval quality"""
        if not docs:
            return 0.3  # Low confidence without context
        
        # Use top scores
        scores = [doc.get("combined_score") or doc.get("score", 0) for doc in docs[:3]]
        
        if not scores:
            return 0.4
        
        avg_score = sum(scores) / len(scores)
        top_score = max(scores)
        
        # Weight toward top score
        confidence = (top_score * 0.6) + (avg_score * 0.4)
        
        # Boost if multiple good results
        if len([s for s in scores if s > 0.5]) >= 2:
            confidence = min(confidence + 0.1, 1.0)
        
        return round(confidence, 2)
    
    # ==================== Practice Question Generation ====================
    
    async def generate_practice_question(
        self,
        topic: str,
        difficulty: str,
        student_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a practice question based on topic and difficulty"""
        
        try:
            difficulty_level = DifficultyLevel(difficulty.lower())
        except ValueError:
            difficulty_level = DifficultyLevel.MEDIUM
        
        # Build filters
        filters = self._build_search_filters(student_context)
        
        # Search for relevant content
        subject = student_context.get('current_subject', student_context.get('subject', ''))
        search_query = f"{topic} {subject} questions exercises problems"
        
        docs = await self._retrieve_documents(
            query=search_query,
            filters=filters,
            limit=3
        )
        
        context = self._build_context(docs)
        grade = student_context.get('grade', 'Form 4')
        
        prompt = f"""Based on this ZIMSEC curriculum content, generate ONE {difficulty_level.value} 
practice question for a {grade} student on the topic of {topic}.

The question should:
- Be appropriate for ZIMSEC {grade} level
- Test understanding, not just memorization
- Be clear and unambiguous
- {"Be straightforward and test basic concepts" if difficulty_level == DifficultyLevel.EASY else ""}
- {"Require application of concepts" if difficulty_level == DifficultyLevel.MEDIUM else ""}
- {"Challenge deeper understanding and problem-solving" if difficulty_level == DifficultyLevel.HARD else ""}

Context from curriculum materials:
{context}

Generate a question in this exact JSON format (no markdown, just JSON):
{{
    "question": "The question text here",
    "question_type": "multiple_choice" or "short_answer",
    "options": ["A) option1", "B) option2", "C) option3", "D) option4"],
    "correct_answer": "The correct answer",
    "hint": "A helpful hint without giving away the answer",
    "explanation": "Why this is the correct answer",
    "topic": "{topic}",
    "difficulty": "{difficulty_level.value}"
}}

Return ONLY valid JSON, no other text or markdown."""

        response = await self._generate_response(prompt, ResponseMode.PRACTICE)
        
        # Parse JSON from response
        return self._parse_question_json(response, topic, difficulty_level.value)
    
    def _parse_question_json(self, response: str, topic: str, difficulty: str) -> Dict[str, Any]:
        """Parse and validate question JSON from response"""
        try:
            # Clean up response
            response = response.strip()
            
            # Remove markdown code blocks if present
            if response.startswith("```"):
                lines = response.split("\n")
                # Find content between ``` markers
                start_idx = 1 if lines[0].startswith("```") else 0
                end_idx = len(lines)
                for i in range(len(lines) - 1, -1, -1):
                    if lines[i].strip() == "```":
                        end_idx = i
                        break
                response = "\n".join(lines[start_idx:end_idx])
            
            # Try to parse JSON
            question_data = json.loads(response)
            
            # Validate required fields
            required = ["question", "correct_answer"]
            for field in required:
                if field not in question_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Add defaults for optional fields
            question_data.setdefault("question_type", "short_answer")
            question_data.setdefault("hint", "Think about the key concepts.")
            question_data.setdefault("explanation", "Review the topic material for more details.")
            question_data.setdefault("topic", topic)
            question_data.setdefault("difficulty", difficulty)
            
            return question_data
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse question JSON: {e}")
            # Return a default structure
            return {
                "question": response if len(response) < 500 else "Please try generating another question.",
                "question_type": "short_answer",
                "correct_answer": "Please check with your teacher.",
                "hint": "Think about the key concepts.",
                "explanation": "Review the topic material.",
                "topic": topic,
                "difficulty": difficulty,
                "parse_error": True
            }
    
    # ==================== Additional Helper Methods ====================
    
    async def get_topic_summary(
        self,
        topic: str,
        student_context: Dict[str, Any]
    ) -> str:
        """Get a summary of a specific topic"""
        response, _ = await self.query(
            question=f"Give me a summary of {topic}",
            student_context=student_context,
            mode="summary"
        )
        return response
    
    async def check_answer(
        self,
        question: str,
        student_answer: str,
        correct_answer: str,
        student_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check a student's answer and provide feedback"""
        name = student_context.get('first_name', 'there')
        
        prompt = f"""A student named {name} answered a question. Evaluate their answer and provide encouraging feedback.

Question: {question}
Student's Answer: {student_answer}
Correct Answer: {correct_answer}

Provide feedback in this JSON format:
{{
    "is_correct": true/false,
    "feedback": "Encouraging feedback message",
    "explanation": "Brief explanation of the correct answer",
    "encouragement": "A motivating message"
}}

Return only valid JSON."""

        response = await self._generate_response(prompt, ResponseMode.PRACTICE)
        
        try:
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            return json.loads(response)
        except:
            # Simple fallback comparison
            is_correct = student_answer.lower().strip() in correct_answer.lower()
            return {
                "is_correct": is_correct,
                "feedback": f"{'Great job! ✨' if is_correct else 'Not quite, but good try! 💪'}",
                "explanation": correct_answer,
                "encouragement": "Keep practicing!"
            }