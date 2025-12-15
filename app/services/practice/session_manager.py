# ============================================================================
# Practice Session Management Service
# ============================================================================
"""
Manages practice sessions, question flow, and answer evaluation.

Key improvements:
- Full integration with advanced RAG pipeline
- AI-powered answer evaluation using RAG engine
- Better hint generation with progressive hints
- Metrics recording for session analytics
- Enhanced question generation with topic context
"""
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, date, timedelta
from uuid import UUID
import random
import logging

from app.models.practice import PracticeSession, QuestionAttempt
from app.models.curriculum import Question, Subject, Topic
from app.models.user import Student
from app.models.gamification import StudentTopicProgress, StudentStreak

# Import from updated RAG pipeline
from app.services.rag import (
    RAGEngine,
    RAGResponse,
    ResponseMode,
    DifficultyLevel,
    record_rag_query,
    get_metrics_collector,
)
from app.services.gamification.xp_system import XPSystem

logger = logging.getLogger(__name__)


# ============================================================================
# Formatted Question Display
# ============================================================================
class FormattedQuestion:
    """Question formatted for WhatsApp display"""
    
    def __init__(self, question: Question, index: int, total: int):
        self.id = question.id
        self.question = question
        self.index = index
        self.total = total
    
    @property
    def formatted_text(self) -> str:
        """Generate WhatsApp-friendly question text"""
        q = self.question
        
        # Header with question number and difficulty
        text = f"📝 *Question {self.index}/{self.total}*"
        
        if q.difficulty:
            diff_emoji = {
                "easy": "🟢",
                "medium": "🟡", 
                "hard": "🔴",
                "exam": "⭐"
            }
            text += f" {diff_emoji.get(q.difficulty, '')} {q.difficulty.title()}"
        
        # Question text
        text += f"\n\n{q.question_text}"
        
        # Options for MCQ
        if q.question_type == "multiple_choice" and q.options:
            text += "\n\n"
            for i, opt in enumerate(q.options):
                letter = chr(65 + i)  # A, B, C, D
                text += f"{letter}) {opt}\n"
        
        # Commands reminder
        text += "\n\n💡 Commands: 'hint' | 'skip' | 'quit'"
        
        # Marks if available
        if q.marks:
            text += f"\n📊 Marks: {q.marks}"
        
        return text
    
    @property
    def short_text(self) -> str:
        """Short version without commands for follow-up"""
        q = self.question
        text = q.question_text
        
        if q.question_type == "multiple_choice" and q.options:
            text += "\n"
            for i, opt in enumerate(q.options):
                text += f"\n{chr(65 + i)}) {opt}"
        
        return text


# ============================================================================
# Session Statistics
# ============================================================================
class SessionStats:
    """Track session statistics"""
    
    def __init__(self):
        self.questions_attempted = 0
        self.correct_answers = 0
        self.total_marks_earned = 0
        self.total_marks_possible = 0
        self.total_xp_earned = 0
        self.hints_used = 0
        self.skipped = 0
        self.time_spent_seconds = 0
    
    @property
    def accuracy(self) -> float:
        if self.questions_attempted == 0:
            return 0.0
        return (self.correct_answers / self.questions_attempted) * 100
    
    @property
    def score_percentage(self) -> float:
        if self.total_marks_possible == 0:
            return 0.0
        return (self.total_marks_earned / self.total_marks_possible) * 100


# ============================================================================
# Practice Session Manager
# ============================================================================
class PracticeSessionManager:
    """
    Manages practice sessions with full RAG integration.
    
    Features:
    - Adaptive difficulty based on performance
    - AI-powered answer evaluation
    - Progressive hint system
    - Question generation when database is empty
    - Comprehensive session statistics
    """
    
    def __init__(self, db: AsyncSession, rag_engine: RAGEngine):
        self.db = db
        self.rag = rag_engine
        self.xp_system = XPSystem(db)
        self._metrics = get_metrics_collector()
    
    # ==================== Session Lifecycle ====================
    
    async def start_session(
        self,
        student_id: UUID,
        subject_id: Optional[UUID] = None,
        topic_id: Optional[UUID] = None,
        topic_name: Optional[str] = None,
        session_type: str = "daily_practice",
        num_questions: int = 5,
        difficulty: Optional[str] = None
    ) -> Tuple[PracticeSession, FormattedQuestion]:
        """
        Start a new practice session.
        
        Args:
            student_id: Student's UUID
            subject_id: Optional subject filter
            topic_id: Optional topic filter
            topic_name: Topic name (used for AI generation)
            session_type: Type of session (daily_practice, topic_review, exam_prep)
            num_questions: Number of questions
            difficulty: Override difficulty (auto-determined if None)
        
        Returns:
            Tuple of (PracticeSession, FormattedQuestion)
        """
        # Get student for context
        student = await self.db.get(Student, student_id)
        if not student:
            raise ValueError("Student not found")
        
        # Determine difficulty adaptively if not specified
        if not difficulty:
            difficulty = await self._determine_adaptive_difficulty(
                student_id, topic_id
            )
        
        # Get topic name if not provided
        if topic_id and not topic_name:
            topic = await self.db.get(Topic, topic_id)
            if topic:
                topic_name = topic.name
        
        # Create session
        session = PracticeSession(
            student_id=student_id,
            subject_id=subject_id,
            topic_id=topic_id,
            session_type=session_type,
            difficulty_level=difficulty,
            total_questions=num_questions,
            status="in_progress",
            started_at=datetime.utcnow()
        )
        self.db.add(session)
        await self.db.flush()
        
        logger.info(
            f"Started session {session.id} for student {student_id}: "
            f"{num_questions} questions, difficulty={difficulty}"
        )
        
        # Get first question
        question = await self._get_next_question(
            session=session,
            student=student,
            topic_name=topic_name,
            exclude_ids=[]
        )
        
        formatted = FormattedQuestion(question, 1, num_questions)
        
        await self.db.commit()
        return session, formatted
    
    async def evaluate_answer(
        self,
        session_id: UUID,
        question_id: UUID,
        student_answer: str,
        student_id: UUID,
        hints_used: int = 0
    ) -> Dict[str, Any]:
        """
        Evaluate student's answer with AI assistance.
        
        Returns:
            Dict with: is_correct, feedback, marks_earned, xp_earned, 
                      next_question, progress
        """
        # Get session, question, and student
        session = await self.db.get(PracticeSession, session_id)
        question = await self.db.get(Question, question_id)
        student = await self.db.get(Student, student_id)
        
        if not all([session, question, student]):
            return {"error": "Session, question, or student not found"}
        
        # Evaluate the answer
        is_correct, marks_earned, feedback = await self._evaluate_answer(
            question=question,
            student_answer=student_answer,
            student=student,
            hints_used=hints_used
        )
        
        marks_possible = question.marks or 1
        
        # Record attempt
        attempt = QuestionAttempt(
            session_id=session_id,
            student_id=student_id,
            question_id=question_id,
            student_answer=student_answer,
            is_correct=is_correct,
            marks_earned=marks_earned,
            marks_possible=marks_possible,
            hints_used=hints_used,
            ai_feedback=feedback,
            answered_at=datetime.utcnow()
        )
        self.db.add(attempt)
        
        # Update session stats
        session.correct_answers = (session.correct_answers or 0) + (1 if is_correct else 0)
        session.total_marks_earned = (session.total_marks_earned or 0) + marks_earned
        
        # Update question stats
        question.times_attempted = (question.times_attempted or 0) + 1
        if is_correct:
            question.times_correct = (question.times_correct or 0) + 1
        
        # Award XP
        xp_earned = 0
        if is_correct:
            xp_earned = await self.xp_system.award_xp(
                student_id=student_id,
                action="correct_answer",
                difficulty=question.difficulty,
                first_attempt=(hints_used == 0)
            )
        
        # Update topic progress
        if question.topic_id:
            await self._update_topic_progress(
                student_id=student_id,
                topic_id=question.topic_id,
                is_correct=is_correct
            )
        
        await self.db.commit()
        
        # Get next question
        attempted_ids = await self._get_attempted_question_ids(session_id)
        next_question = None
        
        current_count = len(attempted_ids)
        if current_count < session.total_questions:
            # Get topic name for generation
            topic_name = None
            if question.topic_id:
                topic = await self.db.get(Topic, question.topic_id)
                topic_name = topic.name if topic else None
            
            next_q = await self._get_next_question(
                session=session,
                student=student,
                topic_name=topic_name,
                exclude_ids=attempted_ids
            )
            if next_q:
                next_question = FormattedQuestion(
                    next_q, current_count + 1, session.total_questions
                )
        
        # Build response feedback message
        response_text = self._build_feedback_message(
            is_correct=is_correct,
            feedback=feedback,
            xp_earned=xp_earned,
            correct_answer=question.correct_answer,
            explanation=question.marking_scheme
        )
        
        return {
            "is_correct": is_correct,
            "feedback": response_text,
            "marks_earned": marks_earned,
            "marks_possible": marks_possible,
            "xp_earned": xp_earned,
            "next_question": next_question,
            "progress": f"{current_count}/{session.total_questions}",
            "session_correct": session.correct_answers,
        }
    
    async def get_hint(
        self,
        question_id: UUID,
        hint_number: int,
        student_id: Optional[UUID] = None
    ) -> str:
        """
        Get progressive hint for question using RAG.
        
        Args:
            question_id: Question to get hint for
            hint_number: Which hint (0, 1, 2)
            student_id: Optional student for context
        
        Returns:
            Hint text
        """
        question = await self.db.get(Question, question_id)
        if not question:
            return "Sorry, I couldn't find that question."
        
        # Build context
        student_context = {"education_level": "secondary", "grade": "Form 3"}
        if student_id:
            student = await self.db.get(Student, student_id)
            if student:
                student_context = {
                    "first_name": student.first_name,
                    "education_level": student.education_level.value,
                    "grade": student.grade,
                    "hint_number": hint_number + 1,
                    "max_hints": 3,
                }
        
        # Build hint prompt based on level
        hint_levels = {
            0: "general direction - which concept or approach to think about",
            1: "more specific - the method, formula, or key insight needed",
            2: "strong clue - almost reveals the approach but not the answer"
        }
        hint_level = hint_levels.get(hint_number, hint_levels[2])
        
        hint_prompt = f"""Provide hint #{hint_number + 1} for this question.

Question: {question.question_text}

Hint level required: {hint_level}

Important:
- Do NOT reveal the answer
- Be encouraging and helpful
- Keep it concise (1-2 sentences)
- Make the student think

Generate ONLY the hint text."""
        
        # Use RAG engine with hint mode
        response, _ = await self.rag.query(
            question=hint_prompt,
            student_context=student_context,
            mode="hint"
        )
        
        # Clean up response
        hint = response.strip()
        
        # Fallback if response is too long or reveals answer
        if len(hint) > 300 or question.correct_answer.lower() in hint.lower():
            fallback_hints = [
                "Think about the key concept involved in this question.",
                "Consider what formula or method applies here.",
                "You're close! Focus on the main relationship between the variables."
            ]
            hint = fallback_hints[min(hint_number, 2)]
        
        return hint
    
    async def skip_question(
        self,
        session_id: UUID,
        question_id: UUID
    ) -> Optional[FormattedQuestion]:
        """Skip current question and get next"""
        session = await self.db.get(PracticeSession, session_id)
        if not session:
            return None
        
        student = await self.db.get(Student, session.student_id)
        
        # Mark question as skipped in attempts
        skip_attempt = QuestionAttempt(
            session_id=session_id,
            student_id=session.student_id,
            question_id=question_id,
            student_answer="[SKIPPED]",
            is_correct=False,
            marks_earned=0,
            marks_possible=0,
            hints_used=0,
            answered_at=datetime.utcnow()
        )
        self.db.add(skip_attempt)
        
        # Get attempted questions
        attempted_ids = await self._get_attempted_question_ids(session_id)
        attempted_ids.append(question_id)
        
        current_count = len(attempted_ids)
        if current_count >= session.total_questions:
            await self.db.commit()
            return None
        
        # Get topic name
        topic_name = None
        if session.topic_id:
            topic = await self.db.get(Topic, session.topic_id)
            topic_name = topic.name if topic else None
        
        next_q = await self._get_next_question(
            session=session,
            student=student,
            topic_name=topic_name,
            exclude_ids=attempted_ids
        )
        
        await self.db.commit()
        
        if next_q:
            return FormattedQuestion(next_q, current_count + 1, session.total_questions)
        
        return None
    
    async def end_session(
        self,
        session_id: UUID,
        student_id: UUID
    ) -> str:
        """End practice session and generate summary"""
        session = await self.db.get(PracticeSession, session_id)
        if not session:
            return "Session not found."
        
        student = await self.db.get(Student, student_id)
        
        # Calculate final statistics
        stats = await self._calculate_session_stats(session_id)
        
        # Update session
        session.ended_at = datetime.utcnow()
        session.score_percentage = stats.score_percentage
        session.status = "completed"
        
        # Calculate time spent
        if session.started_at:
            duration = (session.ended_at - session.started_at).total_seconds()
            session.time_spent_seconds = int(duration)
        
        # Update streak
        streak_bonus = await self._update_streak(student_id)
        
        # Award completion bonus
        bonus_multiplier = 1.0
        if stats.accuracy >= 90:
            bonus_multiplier = 2.0
        elif stats.accuracy >= 80:
            bonus_multiplier = 1.5
        elif stats.accuracy >= 70:
            bonus_multiplier = 1.2
        
        completion_xp = await self.xp_system.award_xp(
            student_id=student_id,
            action="session_complete",
            bonus_multiplier=bonus_multiplier
        )
        
        await self.db.commit()
        
        # Generate summary
        summary = self._generate_session_summary(
            student_name=student.first_name if student else "Student",
            stats=stats,
            completion_xp=completion_xp,
            streak_bonus=streak_bonus,
            duration_seconds=session.time_spent_seconds or 0
        )
        
        logger.info(
            f"Session {session_id} completed: {stats.correct_answers}/{stats.questions_attempted} "
            f"({stats.accuracy:.1f}%), XP earned: {completion_xp}"
        )
        
        return summary
    
    # ==================== Answer Evaluation ====================
    
    async def _evaluate_answer(
        self,
        question: Question,
        student_answer: str,
        student: Student,
        hints_used: int
    ) -> Tuple[bool, float, str]:
        """
        Comprehensive answer evaluation with AI assistance.
        
        Returns:
            Tuple of (is_correct, marks_earned, feedback)
        """
        correct_answer = question.correct_answer.strip()
        student_answer_clean = student_answer.strip()
        marks_possible = question.marks or 1
        
        # Quick check for exact match
        if self._exact_match(student_answer_clean, correct_answer):
            marks = self._calculate_marks(marks_possible, hints_used, is_correct=True)
            return True, marks, "Perfect! That's exactly right."
        
        # MCQ handling
        if question.question_type == "multiple_choice":
            is_correct, feedback = self._evaluate_mcq(
                question, student_answer_clean
            )
            marks = self._calculate_marks(marks_possible, hints_used, is_correct)
            return is_correct, marks, feedback
        
        # Numerical answer handling
        if question.question_type == "calculation":
            is_correct, feedback = self._evaluate_numerical(
                question, student_answer_clean
            )
            marks = self._calculate_marks(marks_possible, hints_used, is_correct)
            return is_correct, marks, feedback
        
        # Fuzzy match for short answers
        if self._fuzzy_match(student_answer_clean, correct_answer, threshold=0.85):
            marks = self._calculate_marks(marks_possible, hints_used, is_correct=True)
            return True, marks, "Correct! Your answer captures the key points."
        
        # Use AI for nuanced evaluation
        return await self._ai_evaluate_answer(
            question=question,
            student_answer=student_answer_clean,
            student=student,
            hints_used=hints_used
        )
    
    def _exact_match(self, answer1: str, answer2: str) -> bool:
        """Check for exact match (case insensitive)"""
        return answer1.lower() == answer2.lower()
    
    def _evaluate_mcq(
        self,
        question: Question,
        student_answer: str
    ) -> Tuple[bool, str]:
        """Evaluate multiple choice answer"""
        correct = question.correct_answer.lower().strip()
        answer = student_answer.lower().strip()
        
        # Handle letter answers (A, B, C, D)
        if len(answer) == 1 and answer.isalpha():
            index = ord(answer) - ord('a')
            if question.options and 0 <= index < len(question.options):
                answer = question.options[index].lower()
        
        is_correct = answer == correct or correct in answer or answer in correct
        
        if is_correct:
            return True, "Correct!"
        else:
            return False, f"Not quite. Review the options carefully."
    
    def _evaluate_numerical(
        self,
        question: Question,
        student_answer: str
    ) -> Tuple[bool, str]:
        """Evaluate numerical/calculation answer"""
        import re
        
        # Extract numbers
        def extract_number(text: str) -> Optional[float]:
            cleaned = re.sub(r'[a-zA-Z°%$£€,\s]', '', text)
            try:
                return float(cleaned)
            except ValueError:
                numbers = re.findall(r'-?\d+\.?\d*', text)
                if numbers:
                    return float(numbers[0])
                return None
        
        student_num = extract_number(student_answer)
        correct_num = extract_number(question.correct_answer)
        
        if student_num is None:
            return False, "Please provide a numerical answer."
        
        if correct_num is None:
            # Fall back to string comparison
            return False, "Could not evaluate numerical answer."
        
        # Check with 1% tolerance
        tolerance = 0.01
        if correct_num == 0:
            is_correct = abs(student_num) < 0.0001
        else:
            relative_error = abs(student_num - correct_num) / abs(correct_num)
            is_correct = relative_error <= tolerance
        
        if is_correct:
            return True, "Correct calculation!"
        elif correct_num != 0 and abs(student_num - correct_num) / abs(correct_num) <= 0.1:
            return False, f"Close! Your answer {student_num} is approximately correct, but not precise enough."
        else:
            return False, "Check your calculation steps."
    
    def _fuzzy_match(
        self,
        answer1: str,
        answer2: str,
        threshold: float = 0.8
    ) -> bool:
        """Fuzzy matching for text answers"""
        import re
        
        # Normalize
        clean1 = re.sub(r'[^\w\s]', '', answer1.lower()).strip()
        clean2 = re.sub(r'[^\w\s]', '', answer2.lower()).strip()
        
        if clean1 == clean2:
            return True
        
        # Containment check
        if clean1 in clean2 or clean2 in clean1:
            return True
        
        # Word overlap
        words1 = set(clean1.split())
        words2 = set(clean2.split())
        
        if not words1 or not words2:
            return False
        
        overlap = len(words1 & words2) / max(len(words1), len(words2))
        return overlap >= threshold
    
    async def _ai_evaluate_answer(
        self,
        question: Question,
        student_answer: str,
        student: Student,
        hints_used: int
    ) -> Tuple[bool, float, str]:
        """Use RAG engine for AI-powered answer evaluation"""
        marks_possible = question.marks or 1
        
        try:
            student_context = {
                "first_name": student.first_name,
                "grade": student.grade,
                "marks": marks_possible,
            }
            
            result = await self.rag.check_answer(
                question=question.question_text,
                student_answer=student_answer,
                correct_answer=question.correct_answer,
                student_context=student_context,
                marking_scheme=question.marking_scheme or ""
            )
            
            is_correct = result.get("is_correct", False)
            feedback = result.get("feedback", "Please review the correct answer.")
            
            # Calculate marks based on AI evaluation
            if is_correct:
                marks = self._calculate_marks(marks_possible, hints_used, True)
            else:
                # Partial credit for close answers
                marks_earned = result.get("marks_earned", 0)
                marks = min(marks_earned, marks_possible * 0.5)
            
            return is_correct, marks, feedback
            
        except Exception as e:
            logger.error(f"AI evaluation failed: {e}")
            # Fallback to simple comparison
            return False, 0.0, "Please review the correct answer."
    
    def _calculate_marks(
        self,
        marks_possible: float,
        hints_used: int,
        is_correct: bool
    ) -> float:
        """Calculate marks with hint penalty"""
        if not is_correct:
            return 0.0
        
        # Reduce marks for hints (but minimum 50%)
        hint_penalty = hints_used * 0.15
        multiplier = max(1.0 - hint_penalty, 0.5)
        
        return marks_possible * multiplier
    
    # ==================== Question Selection ====================
    
    async def _get_next_question(
        self,
        session: PracticeSession,
        student: Student,
        topic_name: Optional[str],
        exclude_ids: List[UUID]
    ) -> Question:
        """Get next question from DB or generate with AI"""
        # Try to get from database first
        question = await self._get_question_from_db(
            subject_id=session.subject_id,
            topic_id=session.topic_id,
            difficulty=session.difficulty_level,
            exclude_ids=exclude_ids
        )
        
        if question:
            return question
        
        # Generate with AI if no questions available
        logger.info(f"No questions in DB, generating with AI for topic: {topic_name}")
        return await self._generate_question_with_ai(
            student=student,
            session=session,
            topic_name=topic_name
        )
    
    async def _get_question_from_db(
        self,
        subject_id: Optional[UUID],
        topic_id: Optional[UUID],
        difficulty: str,
        exclude_ids: List[UUID]
    ) -> Optional[Question]:
        """Query database for next question"""
        query = select(Question)
        
        if subject_id:
            query = query.where(Question.subject_id == subject_id)
        if topic_id:
            query = query.where(Question.topic_id == topic_id)
        if difficulty:
            # Allow adjacent difficulties too
            difficulties = [difficulty]
            if difficulty == "medium":
                difficulties.extend(["easy", "hard"])
            elif difficulty == "easy":
                difficulties.append("medium")
            elif difficulty == "hard":
                difficulties.append("medium")
            query = query.where(Question.difficulty.in_(difficulties))
        
        if exclude_ids:
            query = query.where(~Question.id.in_(exclude_ids))
        
        # Prefer less attempted questions (spaced repetition effect)
        query = query.order_by(
            Question.times_attempted.asc().nullsfirst()
        ).limit(10)
        
        result = await self.db.execute(query)
        questions = result.scalars().all()
        
        if questions:
            # Random selection from top candidates
            return random.choice(questions)
        
        return None
    
    async def _generate_question_with_ai(
        self,
        student: Student,
        session: PracticeSession,
        topic_name: Optional[str]
    ) -> Question:
        """Generate a question using RAG engine"""
        # Build context
        student_context = {
            "first_name": student.first_name,
            "education_level": student.education_level.value,
            "grade": student.grade,
            "current_subject": student.subjects[0] if student.subjects else "General"
        }
        
        # Get topic name if we have topic_id
        if not topic_name and session.topic_id:
            topic = await self.db.get(Topic, session.topic_id)
            topic_name = topic.name if topic else "general concepts"
        
        topic_name = topic_name or "general concepts"
        
        # Generate question
        generated = await self.rag.generate_practice_question(
            topic=topic_name,
            difficulty=session.difficulty_level or "medium",
            student_context=student_context
        )
        
        # Create question in database
        question = Question(
            subject_id=session.subject_id,
            topic_id=session.topic_id,
            question_text=generated.get("question", "Practice question"),
            question_type=generated.get("question_type", "short_answer"),
            options=generated.get("options"),
            correct_answer=generated.get("correct_answer", ""),
            marking_scheme=generated.get("explanation", ""),
            difficulty=session.difficulty_level or "medium",
            marks=generated.get("marks", 4),
            source="ai_generated",
            created_at=datetime.utcnow()
        )
        
        self.db.add(question)
        await self.db.flush()
        
        return question
    
    # ==================== Difficulty & Progress ====================
    
    async def _determine_adaptive_difficulty(
        self,
        student_id: UUID,
        topic_id: Optional[UUID]
    ) -> str:
        """Determine difficulty based on student's past performance"""
        # Check topic progress if available
        if topic_id:
            result = await self.db.execute(
                select(StudentTopicProgress)
                .where(StudentTopicProgress.student_id == student_id)
                .where(StudentTopicProgress.topic_id == topic_id)
            )
            progress = result.scalar_one_or_none()
            
            if progress and progress.questions_attempted >= 5:
                mastery = float(progress.mastery_level or 0)
                if mastery >= 85:
                    return "hard"
                elif mastery >= 60:
                    return "medium"
                return "easy"
        
        # Check recent session performance
        result = await self.db.execute(
            select(PracticeSession)
            .where(PracticeSession.student_id == student_id)
            .where(PracticeSession.status == "completed")
            .order_by(PracticeSession.ended_at.desc())
            .limit(5)
        )
        recent_sessions = result.scalars().all()
        
        if recent_sessions:
            avg_score = sum(s.score_percentage or 0 for s in recent_sessions) / len(recent_sessions)
            if avg_score >= 80:
                return "hard"
            elif avg_score >= 50:
                return "medium"
        
        return "easy"
    
    async def _update_topic_progress(
        self,
        student_id: UUID,
        topic_id: UUID,
        is_correct: bool
    ) -> None:
        """Update student's progress for a topic"""
        result = await self.db.execute(
            select(StudentTopicProgress)
            .where(StudentTopicProgress.student_id == student_id)
            .where(StudentTopicProgress.topic_id == topic_id)
        )
        progress = result.scalar_one_or_none()
        
        if not progress:
            progress = StudentTopicProgress(
                student_id=student_id,
                topic_id=topic_id,
                questions_attempted=0,
                questions_correct=0,
                mastery_level=0
            )
            self.db.add(progress)
        
        progress.questions_attempted = (progress.questions_attempted or 0) + 1
        if is_correct:
            progress.questions_correct = (progress.questions_correct or 0) + 1
        
        # Calculate mastery level (weighted recent performance)
        if progress.questions_attempted > 0:
            progress.mastery_level = (
                progress.questions_correct / progress.questions_attempted
            ) * 100
        
        progress.last_practiced = datetime.utcnow()
        
        # Spaced repetition scheduling
        if progress.mastery_level >= 90:
            days_until_review = 14
        elif progress.mastery_level >= 70:
            days_until_review = 7
        elif progress.mastery_level >= 50:
            days_until_review = 3
        else:
            days_until_review = 1
        
        progress.next_review_date = date.today() + timedelta(days=days_until_review)
    
    async def _update_streak(self, student_id: UUID) -> int:
        """Update student's daily streak, returns bonus XP if milestone"""
        result = await self.db.execute(
            select(StudentStreak).where(StudentStreak.student_id == student_id)
        )
        streak = result.scalar_one_or_none()
        
        today = date.today()
        streak_bonus = 0
        
        if not streak:
            streak = StudentStreak(
                student_id=student_id,
                current_streak=1,
                longest_streak=1,
                last_activity_date=today,
                total_active_days=1
            )
            self.db.add(streak)
            return 0
        
        if streak.last_activity_date == today:
            return 0  # Already counted today
        
        if streak.last_activity_date == today - timedelta(days=1):
            # Consecutive day - extend streak
            streak.current_streak += 1
            
            # Check for milestone bonuses
            if streak.current_streak in [7, 14, 30, 50, 100]:
                streak_bonus = streak.current_streak * 10
            
            if streak.current_streak > streak.longest_streak:
                streak.longest_streak = streak.current_streak
        else:
            # Streak broken
            streak.current_streak = 1
        
        streak.last_activity_date = today
        streak.total_active_days = (streak.total_active_days or 0) + 1
        
        return streak_bonus
    
    # ==================== Statistics & Summaries ====================
    
    async def _calculate_session_stats(self, session_id: UUID) -> SessionStats:
        """Calculate comprehensive session statistics"""
        stats = SessionStats()
        
        result = await self.db.execute(
            select(QuestionAttempt)
            .where(QuestionAttempt.session_id == session_id)
            .where(QuestionAttempt.student_answer != "[SKIPPED]")
        )
        attempts = result.scalars().all()
        
        for attempt in attempts:
            stats.questions_attempted += 1
            if attempt.is_correct:
                stats.correct_answers += 1
            stats.total_marks_earned += attempt.marks_earned or 0
            stats.total_marks_possible += attempt.marks_possible or 0
            stats.hints_used += attempt.hints_used or 0
        
        # Count skipped
        skip_result = await self.db.execute(
            select(func.count(QuestionAttempt.id))
            .where(QuestionAttempt.session_id == session_id)
            .where(QuestionAttempt.student_answer == "[SKIPPED]")
        )
        stats.skipped = skip_result.scalar() or 0
        
        return stats
    
    async def _get_attempted_question_ids(self, session_id: UUID) -> List[UUID]:
        """Get list of question IDs already attempted in session"""
        result = await self.db.execute(
            select(QuestionAttempt.question_id)
            .where(QuestionAttempt.session_id == session_id)
        )
        return [row[0] for row in result.all()]
    
    async def _get_attempted_count(self, session_id: UUID) -> int:
        """Get count of attempted questions"""
        result = await self.db.execute(
            select(func.count(QuestionAttempt.id))
            .where(QuestionAttempt.session_id == session_id)
        )
        return result.scalar() or 0
    
    def _build_feedback_message(
        self,
        is_correct: bool,
        feedback: str,
        xp_earned: int,
        correct_answer: str,
        explanation: Optional[str]
    ) -> str:
        """Build user-friendly feedback message"""
        if is_correct:
            emoji = random.choice(["🎉", "✅", "🌟", "👏", "💪", "🔥", "⭐"])
            message = f"{emoji} *Correct!*\n\n{feedback}"
            if xp_earned:
                message += f"\n\n+{xp_earned} XP earned! 🎮"
        else:
            message = f"❌ *Not quite right.*\n\n{feedback}"
            message += f"\n\n📖 *Correct answer:* {correct_answer}"
            if explanation:
                # Truncate long explanations
                exp = explanation[:300] + "..." if len(explanation) > 300 else explanation
                message += f"\n\n💡 *Explanation:* {exp}"
        
        return message
    
    def _generate_session_summary(
        self,
        student_name: str,
        stats: SessionStats,
        completion_xp: int,
        streak_bonus: int,
        duration_seconds: int
    ) -> str:
        """Generate end-of-session summary"""
        # Performance tier
        if stats.accuracy >= 90:
            emoji = "🏆"
            tier = "Outstanding!"
            message = "You're mastering this material!"
        elif stats.accuracy >= 80:
            emoji = "🌟"
            tier = "Excellent!"
            message = "Great work, keep it up!"
        elif stats.accuracy >= 70:
            emoji = "✨"
            tier = "Good job!"
            message = "Solid performance!"
        elif stats.accuracy >= 50:
            emoji = "👍"
            tier = "Nice effort!"
            message = "Practice makes perfect."
        else:
            emoji = "💪"
            tier = "Keep going!"
            message = "Every attempt helps you learn."
        
        # Format duration
        if duration_seconds > 0:
            minutes = duration_seconds // 60
            seconds = duration_seconds % 60
            time_str = f"{minutes}m {seconds}s" if minutes else f"{seconds}s"
        else:
            time_str = "N/A"
        
        # Build summary
        summary = f"""
{emoji} *Practice Session Complete!*

Hey {student_name}, here are your results:

━━━━━━━━━━━━━━━━━━━━━
📊 *Results*
━━━━━━━━━━━━━━━━━━━━━
✅ Correct: {stats.correct_answers}/{stats.questions_attempted}
📈 Accuracy: {stats.accuracy:.0f}%
⏱️ Time: {time_str}
💡 Hints used: {stats.hints_used}

━━━━━━━━━━━━━━━━━━━━━
🎮 *Rewards*
━━━━━━━━━━━━━━━━━━━━━
🌟 XP Earned: +{completion_xp}"""
        
        if streak_bonus > 0:
            summary += f"\n🔥 Streak Bonus: +{streak_bonus}"
        
        summary += f"""

*{tier}* {message}

━━━━━━━━━━━━━━━━━━━━━
What's next?
• Type *practice* for more questions
• Type *progress* to see your stats
• Or ask me anything! 📚
"""
        
        return summary