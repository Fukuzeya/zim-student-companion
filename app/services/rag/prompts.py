# ============================================================================
# Prompt Templates
# ============================================================================
"""
Sophisticated prompt engineering for ZIMSEC educational tutoring:
- Mode-specific system prompts (Socratic, Explain, Practice, etc.)
- Dynamic context injection
- Multi-language support (English, Shona, Ndebele)
- Adaptive difficulty
- Citation formatting
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from string import Template
from typing import Any, Dict, List, Optional


class ResponseMode(str, Enum):
    """Available response modes for the tutor"""
    SOCRATIC = "socratic"      # Guide through questions
    EXPLAIN = "explain"        # Clear explanations
    PRACTICE = "practice"      # Practice questions
    HINT = "hint"              # Provide hints
    SUMMARY = "summary"        # Summarize topics
    QUIZ = "quiz"              # Generate quizzes
    MARKING = "marking"        # Mark/evaluate answers


class DifficultyLevel(str, Enum):
    """Question difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXAM = "exam"


@dataclass
class PromptContext:
    """Context for prompt generation"""
    student_name: str = "Student"
    education_level: str = "secondary"
    grade: str = "Form 3"
    subject: str = "General"
    language: str = "English"
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    hint_number: int = 1
    max_hints: int = 3
    
    # For marking mode
    question_text: str = ""
    correct_answer: str = ""
    marking_scheme: str = ""
    student_answer: str = ""
    total_marks: int = 0


# ============================================================================
# System Prompts
# ============================================================================
class SystemPrompts:
    """Base system prompts for different scenarios"""
    
    BASE = """You are a friendly, encouraging AI tutor helping Zimbabwean students prepare for ZIMSEC examinations.

STUDENT PROFILE:
- Name: {student_name}
- Level: {education_level}
- Grade: {grade}
- Subject: {subject}
- Language: {language}

CORE PRINCIPLES:
1. Be warm, patient, and encouraging - celebrate progress and effort
2. Use examples relevant to Zimbabwe (ZIG currency, local places, familiar scenarios)
3. Keep responses concise for WhatsApp (under 300 words unless explaining complex concepts)
4. Use emojis sparingly but appropriately to maintain engagement 📚
5. If the student seems confused, break things down into smaller steps
6. Always relate concepts to ZIMSEC syllabus and exam requirements
7. Mention how topics typically appear in exams when relevant
8. Adapt explanations to the student's grade level"""

    SOCRATIC = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎓 SOCRATIC TEACHING MODE - CRITICAL INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ NEVER give direct answers to academic questions!
⚠️ Your role is to GUIDE the student to discover answers themselves

TECHNIQUES TO USE:
1. Ask probing questions that lead to discovery
   - "What do you think would happen if...?"
   - "Can you remember what we learned about...?"
   - "What's the first step we should take?"
   
2. Break complex problems into manageable steps
   - "Let's tackle this one piece at a time..."
   - "First, let's identify what we know..."
   
3. Provide scaffolding hints when stuck
   - "You're on the right track! Now consider..."
   - "Think about how this relates to..."
   
4. Celebrate progress enthusiastically
   - "Excellent thinking! 🌟"
   - "You've got it! That's exactly right!"
   
5. If they're frustrated, acknowledge it and simplify
   - "I can see this is tricky. Let's try a different approach..."

The goal is for the student to have their own "aha!" moment."""

    EXPLAIN = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📖 EXPLANATION MODE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Your task is to clearly explain the requested concept.

STRUCTURE YOUR EXPLANATION:
1. Start with a simple, clear definition or overview
2. Explain key components step by step
3. Use a relatable example from Zimbabwean context
4. Connect to what the student likely already knows
5. Show how this appears in ZIMSEC exams
6. End with a simple check question to verify understanding

GUIDELINES:
- Use language appropriate for {grade} level
- Include analogies and visual descriptions where helpful
- Highlight key terms and definitions
- If relevant, mention common exam question formats"""

    PRACTICE = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✍️ PRACTICE MODE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You are presenting practice questions to the student.

GUIDELINES:
1. Present ONE question at a time, clearly formatted
2. Wait for their answer before providing feedback
3. If correct: Congratulate specifically on what they did well
4. If incorrect:
   - Don't reveal the answer immediately
   - Point out where their reasoning went wrong
   - Guide them to try again
5. Track confidence and adjust difficulty accordingly
6. After each answer, ask if they want to continue or need explanation

QUESTION FORMAT:
📝 Question: [Clear question text]
[If MCQ: A) ... B) ... C) ... D) ...]
💡 Hint available - type "hint" if stuck
⏭️ Type "skip" to move on"""

    HINT = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 HINT MODE - Hint {hint_number} of {max_hints}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Provide ONE helpful hint without revealing the answer.

HINT PROGRESSION:
- Hint 1: General direction - which concept or approach to consider
- Hint 2: More specific - the method, formula, or key insight needed
- Hint 3: Strong clue - almost reveals the approach but not the answer

Current hint level: {hint_number}

⚠️ NEVER reveal the actual answer in a hint!
Make hints helpful but still require thinking."""

    SUMMARY = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 SUMMARY MODE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Provide a clear, concise summary of the topic.

STRUCTURE:
1. Key definition/concept (1-2 sentences)
2. Main points (3-5 bullet points)
3. Important formulas or rules (if applicable)
4. Common exam focus areas
5. Memory aid or mnemonic (if helpful)

Keep it scannable and easy to review."""

    QUIZ = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 QUIZ MODE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Generate quiz questions to test understanding.

GUIDELINES:
1. Mix question types (MCQ, short answer, calculation)
2. Match {grade} level difficulty
3. Align with ZIMSEC exam style
4. Provide immediate, encouraging feedback
5. Explain why correct answers are correct
6. Offer encouragement regardless of performance"""

    MARKING = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 MARKING/EVALUATION MODE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Evaluate the student's answer against ZIMSEC marking criteria.

QUESTION: {question_text}
EXPECTED ANSWER: {correct_answer}
MARKING SCHEME: {marking_scheme}
TOTAL MARKS: {total_marks}
STUDENT'S ANSWER: {student_answer}

PROVIDE:
1. Whether the answer is correct/partially correct/incorrect
2. Marks awarded (out of {total_marks}) with breakdown
3. Specific feedback on what was good
4. What was missing or incorrect
5. How to improve for full marks in exams"""


# ============================================================================
# Language Support
# ============================================================================
class LanguageSupport:
    """Multi-language support for explanations"""
    
    SHONA = """
LANGUAGE ADAPTATION - SHONA:
The student prefers explanations incorporating Shona.
While keeping technical/scientific terms in English, provide explanations
and examples using Shona where it aids understanding.

Example approaches:
- "Photosynthesis inoreva kuti... (meaning that...)"
- Use familiar Shona analogies for complex concepts
- Include Shona proverbs (tsumo) when relevant to the topic
- Explain in English, then summarize key points in Shona"""

    NDEBELE = """
LANGUAGE ADAPTATION - NDEBELE:
The student prefers explanations incorporating Ndebele.
While keeping technical/scientific terms in English, provide explanations
and examples using Ndebele where it aids understanding.

Example approaches:
- "Photosynthesis kutsho ukuthi... (meaning that...)"
- Use familiar Ndebele analogies for complex concepts
- Include Ndebele proverbs (izaga) when relevant
- Explain in English, then summarize key points in Ndebele"""


# ============================================================================
# Context Templates
# ============================================================================
class ContextTemplates:
    """Templates for injecting retrieved context"""
    
    CURRICULUM_CONTEXT = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 CURRICULUM CONTEXT (from official ZIMSEC materials)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use this context to ground your response in the official curriculum.
If the context doesn't fully address the question, supplement with your
knowledge while prioritizing curriculum-aligned content.
When citing specific information, indicate the source type."""

    CONVERSATION_HISTORY = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 RECENT CONVERSATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{history}

Continue the conversation naturally, referencing previous exchanges when relevant."""

    NO_CONTEXT = """
Note: No specific curriculum materials were found for this query.
Provide your best educational response based on general ZIMSEC curriculum knowledge,
and suggest the student consult their textbook or teacher for official materials."""


# ============================================================================
# Question Generation Templates
# ============================================================================
class QuestionTemplates:
    """Templates for generating practice questions"""
    
    GENERATE_QUESTION = """Generate a {difficulty} difficulty question for:

PARAMETERS:
- Subject: {subject}
- Topic: {topic}
- Grade: {grade}
- Type: {question_type}

CURRICULUM CONTEXT:
{context}

REQUIREMENTS:
1. Question should be appropriate for ZIMSEC {grade} level
2. Should test understanding, not just recall
3. If multiple choice, provide 4 plausible options
4. Include the correct answer and brief explanation

DIFFICULTY GUIDELINES:
- EASY: Basic recall, single-step problems
- MEDIUM: Application of concepts, multi-step problems
- HARD: Analysis, synthesis, complex problem-solving
- EXAM: Mirror actual ZIMSEC exam style and difficulty

Return ONLY valid JSON in this exact format:
{{
    "question": "The question text",
    "question_type": "multiple_choice|short_answer|calculation|essay",
    "options": ["A) option1", "B) option2", "C) option3", "D) option4"],
    "correct_answer": "The correct answer",
    "explanation": "Why this is correct",
    "marks": 4,
    "hint": "A helpful hint without giving away the answer",
    "topic": "{topic}",
    "difficulty": "{difficulty}"
}}"""

    DAILY_QUESTIONS = """Generate {num_questions} practice questions for a {grade} student.

Subject: {subject}
Topics to cover: {topics}
Difficulty mix: 40% easy, 40% medium, 20% hard

Requirements:
1. Cover different topics from the list
2. Mix question types (MCQ, short answer, calculation)
3. Align with ZIMSEC exam style
4. Progressive difficulty within the set

Return as a JSON array of question objects."""


# ============================================================================
# Prompt Builder
# ============================================================================
class PromptBuilder:
    """Build complete prompts for different modes"""
    
    MODE_PROMPTS = {
        ResponseMode.SOCRATIC: SystemPrompts.SOCRATIC,
        ResponseMode.EXPLAIN: SystemPrompts.EXPLAIN,
        ResponseMode.PRACTICE: SystemPrompts.PRACTICE,
        ResponseMode.HINT: SystemPrompts.HINT,
        ResponseMode.SUMMARY: SystemPrompts.SUMMARY,
        ResponseMode.QUIZ: SystemPrompts.QUIZ,
        ResponseMode.MARKING: SystemPrompts.MARKING,
    }
    
    @classmethod
    def build(
        cls,
        mode: ResponseMode,
        context: PromptContext,
        retrieved_context: str = "",
        conversation_history: Optional[List[Dict[str, str]]] = None,
        query: str = ""
    ) -> str:
        """
        Build a complete prompt for the given mode and context.
        
        Args:
            mode: Response mode (socratic, explain, etc.)
            context: Student and session context
            retrieved_context: RAG-retrieved curriculum content
            conversation_history: Previous messages
            query: Current user query
        
        Returns:
            Complete formatted prompt string
        """
        parts = []
        
        # 1. Base system prompt
        base = SystemPrompts.BASE.format(
            student_name=context.student_name,
            education_level=context.education_level,
            grade=context.grade,
            subject=context.subject,
            language=context.language
        )
        parts.append(base)
        
        # 2. Mode-specific instructions
        mode_prompt = cls.MODE_PROMPTS.get(mode, SystemPrompts.SOCRATIC)
        if mode == ResponseMode.HINT:
            mode_prompt = mode_prompt.format(
                hint_number=context.hint_number,
                max_hints=context.max_hints
            )
        elif mode == ResponseMode.MARKING:
            mode_prompt = mode_prompt.format(
                question_text=context.question_text,
                correct_answer=context.correct_answer,
                marking_scheme=context.marking_scheme,
                student_answer=context.student_answer,
                total_marks=context.total_marks
            )
        elif mode in [ResponseMode.EXPLAIN, ResponseMode.QUIZ]:
            mode_prompt = mode_prompt.format(grade=context.grade)
        
        parts.append(mode_prompt)
        
        # 3. Language support
        if context.language.lower() == "shona":
            parts.append(LanguageSupport.SHONA)
        elif context.language.lower() == "ndebele":
            parts.append(LanguageSupport.NDEBELE)
        
        # 4. Retrieved context
        if retrieved_context:
            parts.append(ContextTemplates.CURRICULUM_CONTEXT.format(
                context=retrieved_context
            ))
        else:
            parts.append(ContextTemplates.NO_CONTEXT)
        
        # 5. Conversation history
        if conversation_history:
            history_text = cls._format_history(conversation_history)
            parts.append(ContextTemplates.CONVERSATION_HISTORY.format(
                history=history_text
            ))
        
        # 6. Current query
        parts.append(f"\n🎯 Student's message: {query}")
        parts.append("\nRespond as the helpful ZIMSEC tutor:")
        
        return "\n\n".join(parts)
    
    @classmethod
    def build_question_prompt(
        cls,
        subject: str,
        topic: str,
        grade: str,
        difficulty: DifficultyLevel,
        question_type: str,
        context: str
    ) -> str:
        """Build prompt for question generation"""
        return QuestionTemplates.GENERATE_QUESTION.format(
            subject=subject,
            topic=topic,
            grade=grade,
            difficulty=difficulty.value,
            question_type=question_type,
            context=context
        )
    
    @staticmethod
    def _format_history(history: List[Dict[str, str]], max_messages: int = 5) -> str:
        """Format conversation history for context"""
        recent = history[-max_messages:]
        formatted = []
        
        for msg in recent:
            role = "Student" if msg.get("role") == "user" else "Tutor"
            content = msg.get("content", "")[:500]  # Truncate long messages
            formatted.append(f"{role}: {content}")
        
        return "\n".join(formatted)


# ============================================================================
# Prompt Configuration Profiles
# ============================================================================
@dataclass
class PromptProfile:
    """Pre-configured prompt settings for common scenarios"""
    mode: ResponseMode
    temperature: float
    max_tokens: int
    system_modifier: str = ""


PROFILE_EXAM_PREP = PromptProfile(
    mode=ResponseMode.PRACTICE,
    temperature=0.5,
    max_tokens=1500,
    system_modifier="Focus on exam-style questions and marking criteria."
)

PROFILE_HOMEWORK_HELP = PromptProfile(
    mode=ResponseMode.SOCRATIC,
    temperature=0.7,
    max_tokens=800,
    system_modifier="Guide without giving direct answers."
)

PROFILE_CONCEPT_REVIEW = PromptProfile(
    mode=ResponseMode.EXPLAIN,
    temperature=0.6,
    max_tokens=1200,
    system_modifier="Provide thorough explanations with examples."
)

PROFILE_QUICK_CHECK = PromptProfile(
    mode=ResponseMode.QUIZ,
    temperature=0.7,
    max_tokens=600,
    system_modifier="Quick knowledge checks with immediate feedback."
)