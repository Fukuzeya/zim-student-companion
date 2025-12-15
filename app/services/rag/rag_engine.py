# ============================================================================
# RAG Engine
# ============================================================================
"""
Main RAG orchestrator that combines all components:
- Retrieval with multiple strategies
- Context building and compression
- Response generation with mode-specific behavior
- Caching and performance optimization
- Comprehensive observability
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import google.generativeai as genai

from app.services.rag.config import (
    RAGConfig, GenerationConfig, RetrievalStrategy, get_rag_config
)
from app.services.rag.embeddings import EmbeddingService
from app.services.rag.vector_store import VectorStore, SearchResult
from app.services.rag.retriever import Retriever, RetrievalResult, StudentContext
from app.services.rag.prompts import (
    ResponseMode, DifficultyLevel, PromptContext, PromptBuilder
)

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================
@dataclass
class RAGResponse:
    """Complete response from RAG pipeline"""
    response_text: str
    retrieved_docs: List[Dict[str, Any]]
    mode_used: str
    confidence_score: float
    
    # Timing metrics
    retrieval_time_ms: float = 0.0
    generation_time_ms: float = 0.0
    total_time_ms: float = 0.0
    
    # Metadata
    context_used: bool = True
    tokens_used: int = 0
    query_variations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "response": self.response_text,
            "documents": self.retrieved_docs,
            "mode": self.mode_used,
            "confidence": self.confidence_score,
            "timing": {
                "retrieval_ms": self.retrieval_time_ms,
                "generation_ms": self.generation_time_ms,
                "total_ms": self.total_time_ms,
            },
            "metadata": self.metadata,
        }


@dataclass
class GenerationSettings:
    """Settings for LLM generation"""
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    max_output_tokens: int = 1024
    
    @classmethod
    def for_mode(cls, mode: ResponseMode) -> "GenerationSettings":
        """Get optimized settings for each mode"""
        settings_map = {
            ResponseMode.SOCRATIC: cls(temperature=0.7, max_output_tokens=800),
            ResponseMode.EXPLAIN: cls(temperature=0.5, max_output_tokens=1200),
            ResponseMode.PRACTICE: cls(temperature=0.6, max_output_tokens=600),
            ResponseMode.HINT: cls(temperature=0.6, max_output_tokens=400),
            ResponseMode.SUMMARY: cls(temperature=0.4, max_output_tokens=600),
            ResponseMode.QUIZ: cls(temperature=0.7, max_output_tokens=800),
            ResponseMode.MARKING: cls(temperature=0.3, max_output_tokens=800),
        }
        return settings_map.get(mode, cls())


# ============================================================================
# Context Builder
# ============================================================================
class ContextBuilder:
    """Build and compress context from retrieved documents"""
    
    def __init__(self, max_context_tokens: int = 6000):
        self.max_tokens = max_context_tokens
    
    def build_context(
        self,
        documents: List[SearchResult],
        query: str,
        max_docs: int = 5
    ) -> str:
        """
        Build context string from retrieved documents.
        Prioritizes most relevant content within token limits.
        """
        if not documents:
            return ""
        
        context_parts = []
        total_tokens = 0
        
        for i, doc in enumerate(documents[:max_docs], 1):
            # Format source info
            source_info = self._format_source(doc, i)
            
            # Estimate tokens (rough: 1 token ≈ 4 chars)
            content = doc.content
            entry_tokens = len(f"{source_info}\n{content}") // 4
            
            # Check if we can fit this document
            if total_tokens + entry_tokens > self.max_tokens:
                # Try to fit truncated version
                remaining_tokens = self.max_tokens - total_tokens - len(source_info) // 4
                if remaining_tokens > 100:
                    max_chars = remaining_tokens * 4
                    content = content[:max_chars] + "..."
                else:
                    break
            
            context_parts.append(f"{source_info}\n{content}")
            total_tokens += entry_tokens
        
        return "\n\n---\n\n".join(context_parts)
    
    def _format_source(self, doc: SearchResult, index: int) -> str:
        """Format source attribution for a document"""
        meta = doc.metadata
        parts = [f"[Source {index}"]
        
        if doc_type := meta.get("document_type"):
            type_emoji = {
                "past_paper": "📝",
                "marking_scheme": "✅",
                "syllabus": "📋",
                "textbook": "📖",
                "teacher_notes": "📒",
            }.get(doc_type, "📄")
            parts.append(f": {type_emoji} {doc_type.replace('_', ' ').title()}")
        
        if subject := meta.get("subject"):
            parts.append(f" - {subject}")
        
        if year := meta.get("year"):
            parts.append(f" ({year})")
        
        if topic := meta.get("topic"):
            parts.append(f" | Topic: {topic}")
        
        # Quality indicator
        if doc.combined_score > 0.7:
            parts.append(" ⭐")
        
        parts.append("]")
        return "".join(parts)


# ============================================================================
# Main RAG Engine
# ============================================================================
class RAGEngine:
    """
    Production-ready RAG engine for ZIMSEC educational tutoring.
    
    Features:
    - Multiple response modes (Socratic, Explain, Practice, etc.)
    - Hybrid retrieval with fallback strategies
    - Adaptive response generation
    - Comprehensive caching and optimization
    - Full observability and metrics
    
    Usage:
        engine = RAGEngine(settings)
        await engine.initialize()
        
        response = await engine.query(
            question="Explain photosynthesis",
            student_context={"grade": "Form 3", "subject": "Biology"},
            mode="explain"
        )
    """
    
    def __init__(
        self,
        settings,
        config: Optional[RAGConfig] = None,
        vector_store: Optional[VectorStore] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        """
        Initialize RAG engine.
        
        Args:
            settings: Application settings
            config: Optional RAG configuration override
            vector_store: Optional pre-initialized vector store
            embedding_service: Optional pre-initialized embedding service
        """
        self.settings = settings
        self.config = config or get_rag_config()
        
        # Initialize components
        self._embedding_service = embedding_service or EmbeddingService(
            api_key=settings.GEMINI_API_KEY,
            config=self.config.embedding
        )
        
        self._vector_store = vector_store or VectorStore(
            settings=settings,
            embedding_service=self._embedding_service
        )
        
        self._retriever: Optional[Retriever] = None
        self._context_builder = ContextBuilder()
        
        # Initialize Gemini model
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._model = genai.GenerativeModel(self.config.generation.model)
        
        # Metrics
        self._stats = {
            "queries_processed": 0,
            "total_retrieval_time_ms": 0,
            "total_generation_time_ms": 0,
            "cache_hits": 0,
            "errors": 0,
        }
        
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize all components"""
        if self._initialized:
            return
        
        logger.info("Initializing RAG Engine...")
        
        # Initialize vector store collections
        await self._vector_store.initialize_collections()
        
        # Initialize retriever
        self._retriever = Retriever(
            vector_store=self._vector_store,
            embedding_service=self._embedding_service,
            settings=self.settings,
            config=self.config.retrieval
        )
        
        self._initialized = True
        logger.info("✓ RAG Engine initialized")
    
    # ==================== Main Query Method ====================
    
    async def query(
        self,
        question: str,
        student_context: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, str]]] = None,
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
        response = await self.query_with_metadata(
            question=question,
            student_context=student_context,
            conversation_history=conversation_history,
            mode=mode
        )
        
        return response.response_text, response.retrieved_docs
    
    async def query_with_metadata(
        self,
        question: str,
        student_context: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, str]]] = None,
        mode: str = "socratic"
    ) -> RAGResponse:
        """
        Query with full metadata response.
        
        Returns:
            RAGResponse with complete response data and metrics
        """
        if not self._initialized:
            await self.initialize()
        
        start_time = time.time()
        self._stats["queries_processed"] += 1
        
        # Parse response mode
        try:
            response_mode = ResponseMode(mode.lower())
        except ValueError:
            response_mode = ResponseMode.SOCRATIC
            logger.warning(f"Invalid mode '{mode}', defaulting to socratic")
        
        # Build student context object
        ctx = self._build_student_context(student_context)
        
        # Step 1: Retrieve relevant documents
        retrieval_start = time.time()
        retrieval_result = await self._retriever.retrieve_with_fallback(
            query=question,
            context=ctx
        )
        retrieval_time = (time.time() - retrieval_start) * 1000
        
        # Step 2: Build context from documents
        context_str = self._context_builder.build_context(
            documents=retrieval_result.documents,
            query=question
        )
        
        # Step 3: Build prompt
        prompt_context = self._build_prompt_context(student_context, response_mode)
        prompt = PromptBuilder.build(
            mode=response_mode,
            context=prompt_context,
            retrieved_context=context_str,
            conversation_history=conversation_history,
            query=question
        )
        
        # Step 4: Generate response
        generation_start = time.time()
        settings = GenerationSettings.for_mode(response_mode)
        response_text = await self._generate_response(prompt, settings)
        generation_time = (time.time() - generation_start) * 1000
        
        # Step 5: Post-process response
        response_text = self._post_process_response(response_text, response_mode)
        
        # Calculate metrics
        total_time = (time.time() - start_time) * 1000
        confidence = self._calculate_confidence(retrieval_result.documents)
        
        # Update stats
        self._stats["total_retrieval_time_ms"] += retrieval_time
        self._stats["total_generation_time_ms"] += generation_time
        
        return RAGResponse(
            response_text=response_text,
            retrieved_docs=[d.to_dict() for d in retrieval_result.documents],
            mode_used=response_mode.value,
            confidence_score=confidence,
            retrieval_time_ms=retrieval_time,
            generation_time_ms=generation_time,
            total_time_ms=total_time,
            context_used=len(retrieval_result.documents) > 0,
            query_variations=retrieval_result.query_variations,
            metadata={
                "strategy_used": retrieval_result.strategy_used,
                "total_candidates": retrieval_result.total_candidates,
                **retrieval_result.metadata
            }
        )
    
    # ==================== Practice Question Generation ====================
    
    async def generate_practice_question(
        self,
        topic: str,
        difficulty: str,
        student_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a practice question based on topic and difficulty.
        
        Args:
            topic: Topic for the question
            difficulty: Difficulty level (easy, medium, hard, exam)
            student_context: Student information
        
        Returns:
            Question dictionary with question, options, answer, etc.
        """
        if not self._initialized:
            await self.initialize()
        
        # Parse difficulty
        try:
            diff_level = DifficultyLevel(difficulty.lower())
        except ValueError:
            diff_level = DifficultyLevel.MEDIUM
        
        # Build context
        ctx = self._build_student_context(student_context)
        
        # Retrieve relevant content for question generation
        search_query = f"{topic} {ctx.subject or ''} questions examples"
        retrieval_result = await self._retriever.retrieve(
            query=search_query,
            context=ctx
        )
        
        context_str = self._context_builder.build_context(
            documents=retrieval_result.documents[:3],
            query=search_query
        )
        
        # Build question generation prompt
        prompt = PromptBuilder.build_question_prompt(
            subject=ctx.subject or student_context.get("subject", ""),
            topic=topic,
            grade=ctx.grade,
            difficulty=diff_level,
            question_type="mixed",
            context=context_str
        )
        
        # Generate question
        settings = GenerationSettings(temperature=0.7, max_output_tokens=800)
        response = await self._generate_response(prompt, settings)
        
        # Parse JSON response
        return self._parse_question_json(response, topic, diff_level.value)
    
    async def generate_daily_questions(
        self,
        student_context: Dict[str, Any],
        num_questions: int = 5
    ) -> List[Dict[str, Any]]:
        """Generate a set of daily practice questions"""
        questions = []
        topics = student_context.get("topics", [])
        
        if not topics:
            # Default topics based on subject
            subject = student_context.get("subject", "").lower()
            topics = self._get_default_topics(subject)
        
        difficulties = ["easy", "easy", "medium", "medium", "hard"]
        
        for i, diff in enumerate(difficulties[:num_questions]):
            topic = topics[i % len(topics)] if topics else "general"
            try:
                question = await self.generate_practice_question(
                    topic=topic,
                    difficulty=diff,
                    student_context=student_context
                )
                questions.append(question)
            except Exception as e:
                logger.error(f"Failed to generate question: {e}")
        
        return questions
    
    # ==================== Answer Checking ====================
    
    async def check_answer(
        self,
        question: str,
        student_answer: str,
        correct_answer: str,
        student_context: Dict[str, Any],
        marking_scheme: str = ""
    ) -> Dict[str, Any]:
        """
        Check a student's answer and provide feedback.
        
        Returns:
            Dict with is_correct, feedback, marks, explanation
        """
        name = student_context.get("first_name", "there")
        total_marks = student_context.get("marks", 4)
        
        prompt_ctx = PromptContext(
            student_name=name,
            question_text=question,
            correct_answer=correct_answer,
            marking_scheme=marking_scheme,
            student_answer=student_answer,
            total_marks=total_marks
        )
        
        prompt = PromptBuilder.build(
            mode=ResponseMode.MARKING,
            context=prompt_ctx,
            query=""
        )
        
        # Add JSON format request
        prompt += """

Respond with ONLY valid JSON in this format:
{
    "is_correct": true/false,
    "marks_earned": <number>,
    "feedback": "Specific feedback message",
    "explanation": "Why this is/isn't correct",
    "encouragement": "Motivating message"
}"""
        
        settings = GenerationSettings(temperature=0.3, max_output_tokens=500)
        response = await self._generate_response(prompt, settings)
        
        try:
            # Clean and parse JSON
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.warning(f"Failed to parse marking response: {e}")
        
        # Fallback
        is_correct = student_answer.lower().strip() in correct_answer.lower()
        return {
            "is_correct": is_correct,
            "marks_earned": total_marks if is_correct else 0,
            "feedback": "Great job! ✨" if is_correct else "Not quite, but good try! 💪",
            "explanation": correct_answer,
            "encouragement": "Keep practicing!"
        }
    
    # ==================== Topic Summary ====================
    
    async def get_topic_summary(
        self,
        topic: str,
        student_context: Dict[str, Any]
    ) -> str:
        """Get a concise summary of a topic"""
        response, _ = await self.query(
            question=f"Give me a clear, exam-focused summary of {topic}",
            student_context=student_context,
            mode="summary"
        )
        return response
    
    # ==================== Internal Methods ====================
    
    def _build_student_context(self, ctx: Dict[str, Any]) -> StudentContext:
        """Convert dict to StudentContext object"""
        return StudentContext(
            education_level=ctx.get("education_level", "secondary"),
            grade=ctx.get("grade", "Form 3"),
            subject=ctx.get("current_subject") or ctx.get("subject"),
            language=ctx.get("preferred_language", "English"),
            difficulty_preference=ctx.get("difficulty", "medium")
        )
    
    def _build_prompt_context(
        self,
        student_ctx: Dict[str, Any],
        mode: ResponseMode
    ) -> PromptContext:
        """Build PromptContext from student context"""
        return PromptContext(
            student_name=student_ctx.get("first_name", "Student"),
            education_level=student_ctx.get("education_level", "secondary"),
            grade=student_ctx.get("grade", "Form 3"),
            subject=student_ctx.get("current_subject") or student_ctx.get("subject", "General"),
            language=student_ctx.get("preferred_language", "English"),
        )
    
    async def _generate_response(
        self,
        prompt: str,
        settings: GenerationSettings
    ) -> str:
        """Generate response using Gemini"""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=settings.temperature,
                        top_p=settings.top_p,
                        top_k=settings.top_k,
                        max_output_tokens=settings.max_output_tokens
                    ),
                    safety_settings={
                        'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                        'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                        'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                        'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
                    }
                )
            )
            return response.text
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            self._stats["errors"] += 1
            return self._get_fallback_response()
    
    def _post_process_response(self, response: str, mode: ResponseMode) -> str:
        """Clean and format the response"""
        if not response:
            return self._get_fallback_response()
        
        response = response.strip()
        
        # Ensure response fits WhatsApp limits for most modes
        if mode != ResponseMode.EXPLAIN and len(response) > 1500:
            # Find a good breaking point
            break_point = response.rfind('.', 0, 1400)
            if break_point > 1000:
                response = response[:break_point + 1]
                response += "\n\n(Let me know if you'd like me to continue! 😊)"
        
        return response
    
    def _calculate_confidence(self, docs: List[SearchResult]) -> float:
        """Calculate confidence score based on retrieval quality"""
        if not docs:
            return 0.3
        
        scores = [d.combined_score for d in docs[:3]]
        if not scores:
            return 0.4
        
        avg_score = sum(scores) / len(scores)
        top_score = max(scores)
        
        confidence = (top_score * 0.6) + (avg_score * 0.4)
        
        # Boost if multiple good results
        good_results = len([s for s in scores if s > 0.5])
        if good_results >= 2:
            confidence = min(confidence + 0.1, 1.0)
        
        return round(confidence, 2)
    
    def _parse_question_json(
        self,
        response: str,
        topic: str,
        difficulty: str
    ) -> Dict[str, Any]:
        """Parse and validate question JSON from response"""
        try:
            # Remove markdown code blocks
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                start = 1 if lines[0].startswith("```") else 0
                end = len(lines)
                for i in range(len(lines) - 1, -1, -1):
                    if lines[i].strip() == "```":
                        end = i
                        break
                response = "\n".join(lines[start:end])
            
            question_data = json.loads(response)
            
            # Validate required fields
            if "question" not in question_data:
                raise ValueError("Missing question field")
            
            # Add defaults
            question_data.setdefault("question_type", "short_answer")
            question_data.setdefault("correct_answer", "")
            question_data.setdefault("hint", "Think about the key concepts.")
            question_data.setdefault("explanation", "Review the topic material.")
            question_data.setdefault("topic", topic)
            question_data.setdefault("difficulty", difficulty)
            question_data.setdefault("marks", 4)
            
            return question_data
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse question JSON: {e}")
            return {
                "question": response[:500] if len(response) < 500 else "Please try generating another question.",
                "question_type": "short_answer",
                "correct_answer": "",
                "hint": "Think about the key concepts.",
                "explanation": "Review the topic material.",
                "topic": topic,
                "difficulty": difficulty,
                "parse_error": True
            }
    
    def _get_default_topics(self, subject: str) -> List[str]:
        """Get default topics for a subject"""
        defaults = {
            "mathematics": ["algebra", "geometry", "trigonometry", "statistics"],
            "physics": ["mechanics", "electricity", "waves", "energy"],
            "chemistry": ["atoms", "reactions", "acids and bases", "organic chemistry"],
            "biology": ["cells", "photosynthesis", "genetics", "ecology"],
            "english": ["comprehension", "grammar", "essay writing", "vocabulary"],
        }
        return defaults.get(subject.lower(), ["general concepts"])
    
    def _get_fallback_response(self) -> str:
        """Get a friendly fallback response"""
        return (
            "I'm having a small hiccup right now 🙈 "
            "Could you try asking your question again? "
            "I'm here to help you learn!"
        )
    
    # ==================== Utility Methods ====================
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get engine statistics"""
        return {
            **self._stats,
            "embedding_stats": self._embedding_service.stats,
            "avg_retrieval_ms": (
                self._stats["total_retrieval_time_ms"] / 
                max(self._stats["queries_processed"], 1)
            ),
            "avg_generation_ms": (
                self._stats["total_generation_time_ms"] / 
                max(self._stats["queries_processed"], 1)
            ),
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        result = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {}
        }
        
        # Check vector store
        try:
            vs_health = await self._vector_store.health_check()
            result["components"]["vector_store"] = vs_health
        except Exception as e:
            result["status"] = "degraded"
            result["components"]["vector_store"] = {"status": "error", "error": str(e)}
        
        # Check LLM
        try:
            test_response = await self._generate_response(
                "Say 'OK'",
                GenerationSettings(temperature=0, max_output_tokens=10)
            )
            result["components"]["llm"] = {
                "status": "healthy" if test_response else "degraded"
            }
        except Exception as e:
            result["status"] = "degraded"
            result["components"]["llm"] = {"status": "error", "error": str(e)}
        
        result["stats"] = self.stats
        return result
    
    async def close(self) -> None:
        """Clean up resources"""
        if self._vector_store:
            await self._vector_store.close()
        logger.info("RAG Engine closed")