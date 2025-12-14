# ============================================================================
# Practice Session Management
# ============================================================================
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, date, timedelta
from uuid import UUID
import random

from app.models.practice import PracticeSession, QuestionAttempt
from app.models.curriculum import Question
from app.models.user import Student
from app.models.gamification import StudentTopicProgress, StudentStreak
from app.services.rag.rag_engine import RAGEngine
from app.services.gamification.xp_system import XPSystem

class FormattedQuestion:
    """Question formatted for WhatsApp display"""
    def __init__(self, question: Question, index: int, total: int):
        self.id = question.id
        self.question = question
        self.index = index
        self.total = total
    
    @property
    def formatted_text(self) -> str:
        q = self.question
        text = f"📝 *Question {self.index}/{self.total}*"
        
        if q.difficulty:
            diff_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}
            text += f" {diff_emoji.get(q.difficulty, '')} {q.difficulty.title()}"
        
        text += f"\n\n{q.question_text}"
        
        if q.question_type == "multiple_choice" and q.options:
            text += "\n\n"
            for i, opt in enumerate(q.options):
                letter = chr(65 + i)  # A, B, C, D
                text += f"{letter}) {opt}\n"
        
        text += "\n\n💡 Commands: 'hint' | 'skip' | 'quit'"
        
        if q.marks:
            text += f"\n📊 Marks: {q.marks}"
        
        return text

class PracticeSessionManager:
    """Manages practice sessions and question flow"""
    
    def __init__(self, db: AsyncSession, rag_engine: RAGEngine):
        self.db = db
        self.rag = rag_engine
        self.xp_system = XPSystem(db)
    
    async def start_session(
        self,
        student_id: UUID,
        subject_id: Optional[UUID] = None,
        topic_id: Optional[UUID] = None,
        session_type: str = "daily_practice",
        num_questions: int = 5,
        difficulty: Optional[str] = None
    ) -> tuple[PracticeSession, FormattedQuestion]:
        """Start a new practice session"""
        
        # Determine difficulty if not specified (adaptive)
        if not difficulty:
            difficulty = await self._determine_difficulty(student_id, topic_id)
        
        # Create session
        session = PracticeSession(
            student_id=student_id,
            subject_id=subject_id,
            topic_id=topic_id,
            session_type=session_type,
            difficulty_level=difficulty,
            total_questions=num_questions,
            status="in_progress"
        )
        self.db.add(session)
        await self.db.flush()
        
        # Get first question
        question = await self._get_next_question(
            session_id=session.id,
            student_id=student_id,
            subject_id=subject_id,
            topic_id=topic_id,
            difficulty=difficulty,
            exclude_ids=[]
        )
        
        if not question:
            # Generate question using AI if none available
            question = await self._generate_question(
                student_id=student_id,
                subject_id=subject_id,
                topic_id=topic_id,
                difficulty=difficulty
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
        """Evaluate student's answer and provide feedback"""
        
        # Get session and question
        session = await self.db.get(PracticeSession, session_id)
        question = await self.db.get(Question, question_id)
        
        if not session or not question:
            return {"error": "Session or question not found"}
        
        # Evaluate the answer
        is_correct, feedback = await self._check_answer(
            question, student_answer, hints_used
        )
        
        # Calculate marks
        marks_possible = question.marks or 1
        if is_correct:
            # Reduce marks for hints used
            marks_earned = max(marks_possible - (hints_used * 0.5), marks_possible * 0.5)
        else:
            marks_earned = 0
        
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
            ai_feedback=feedback
        )
        self.db.add(attempt)
        
        # Update session stats
        session.correct_answers = (session.correct_answers or 0) + (1 if is_correct else 0)
        
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
            next_q = await self._get_next_question(
                session_id=session_id,
                student_id=student_id,
                subject_id=session.subject_id,
                topic_id=session.topic_id,
                difficulty=session.difficulty_level,
                exclude_ids=attempted_ids
            )
            if next_q:
                next_question = FormattedQuestion(
                    next_q, current_count + 1, session.total_questions
                )
        
        # Build response feedback
        if is_correct:
            emoji = random.choice(["🎉", "✅", "🌟", "👏", "💪", "🔥"])
            response_text = f"{emoji} *Correct!*\n\n{feedback}"
            if xp_earned:
                response_text += f"\n\n+{xp_earned} XP earned!"
        else:
            response_text = f"❌ Not quite right.\n\n{feedback}"
            response_text += f"\n\n📖 The correct answer was: {question.correct_answer}"
        
        return {
            "is_correct": is_correct,
            "feedback": response_text,
            "marks_earned": marks_earned,
            "xp_earned": xp_earned,
            "next_question": next_question,
            "progress": f"{current_count}/{session.total_questions}"
        }
    
    async def get_hint(self, question_id: UUID, hint_number: int) -> str:
        """Get a hint for the current question"""
        question = await self.db.get(Question, question_id)
        
        if not question:
            return "Sorry, I couldn't find that question."
        
        # Use RAG to generate contextual hint
        student_context = {"education_level": "secondary", "grade": "Form 3"}
        
        hint_prompt = f"""Generate hint #{hint_number + 1} for this question.
        
Question: {question.question_text}
Correct Answer: {question.correct_answer}

Previous hints given: {hint_number}

Rules:
- Hint 1: Give a general direction/concept to think about
- Hint 2: Point to the specific method or approach
- Hint 3: Give a strong clue without revealing the answer

Generate ONLY the hint text, be concise."""
        
        response, _ = await self.rag.query(
            question=hint_prompt,
            student_context=student_context,
            mode="hint"
        )
        
        return response
    
    async def skip_question(
        self,
        session_id: UUID,
        question_id: UUID
    ) -> Optional[FormattedQuestion]:
        """Skip current question and get next"""
        session = await self.db.get(PracticeSession, session_id)
        
        if not session:
            return None
        
        attempted_ids = await self._get_attempted_question_ids(session_id)
        attempted_ids.append(question_id)  # Mark as "attempted" (skipped)
        
        current_count = len(attempted_ids)
        if current_count >= session.total_questions:
            return None
        
        next_q = await self._get_next_question(
            session_id=session_id,
            student_id=session.student_id,
            subject_id=session.subject_id,
            topic_id=session.topic_id,
            difficulty=session.difficulty_level,
            exclude_ids=attempted_ids
        )
        
        if next_q:
            return FormattedQuestion(next_q, current_count + 1, session.total_questions)
        
        return None
    
    async def end_session(self, session_id: UUID, student_id: UUID) -> str:
        """End practice session and generate summary"""
        session = await self.db.get(PracticeSession, session_id)
        
        if not session:
            return "Session not found."
        
        # Calculate score
        attempted_count = await self._get_attempted_count(session_id)
        correct = session.correct_answers or 0
        
        if attempted_count > 0:
            score_pct = (correct / attempted_count) * 100
        else:
            score_pct = 0
        
        # Update session
        session.ended_at = datetime.utcnow()
        session.score_percentage = score_pct
        session.status = "completed"
        
        # Update streak
        await self._update_streak(student_id)
        
        # Award completion bonus
        completion_xp = await self.xp_system.award_xp(
            student_id=student_id,
            action="session_complete",
            bonus_multiplier=1.5 if score_pct >= 80 else 1.0
        )
        
        await self.db.commit()
        
        # Generate summary
        if score_pct >= 90:
            emoji = "🏆"
            message = "Outstanding performance!"
        elif score_pct >= 70:
            emoji = "🌟"
            message = "Great work! Keep it up!"
        elif score_pct >= 50:
            emoji = "👍"
            message = "Good effort! Practice makes perfect."
        else:
            emoji = "💪"
            message = "Don't give up! Every attempt helps you learn."
        
        summary = f"""
{emoji} *Practice Session Complete!*

📊 *Your Results:*
━━━━━━━━━━━━━━━
✅ Correct: {correct}/{attempted_count}
📈 Score: {score_pct:.0f}%
🎯 XP Earned: +{completion_xp}

{message}

Type *practice* to start another session!
Type *progress* to see your overall stats.
"""
        return summary
    
    async def _check_answer(
        self,
        question: Question,
        student_answer: str,
        hints_used: int
    ) -> tuple[bool, str]:
        """Check if answer is correct and generate feedback"""
        correct_answer = question.correct_answer.strip().lower()
        student_answer = student_answer.strip().lower()
        
        # Handle multiple choice
        if question.question_type == "multiple_choice":
            # Accept both letter and full answer
            if len(student_answer) == 1 and student_answer.isalpha():
                index = ord(student_answer) - ord('a')
                if 0 <= index < len(question.options):
                    student_answer = question.options[index].lower()
            
            is_correct = student_answer == correct_answer or \
                         student_answer in correct_answer
        else:
            # For other types, use fuzzy matching or AI evaluation
            is_correct = self._fuzzy_match(student_answer, correct_answer)
            
            if not is_correct:
                # Use AI for more nuanced evaluation
                is_correct = await self._ai_evaluate(
                    question.question_text,
                    correct_answer,
                    student_answer
                )
        
        # Generate feedback
        if is_correct:
            feedback = question.marking_scheme or "Well done! Your understanding is correct."
        else:
            feedback = f"Review the concept and try again. "
            if question.marking_scheme:
                feedback += f"Key points: {question.marking_scheme[:200]}"
        
        return is_correct, feedback
    
    def _fuzzy_match(self, answer1: str, answer2: str, threshold: float = 0.8) -> bool:
        """Simple fuzzy matching for answers"""
        # Remove common punctuation and extra spaces
        import re
        clean1 = re.sub(r'[^\w\s]', '', answer1).strip()
        clean2 = re.sub(r'[^\w\s]', '', answer2).strip()
        
        if clean1 == clean2:
            return True
        
        # Check if one contains the other
        if clean1 in clean2 or clean2 in clean1:
            return True
        
        # Check word overlap
        words1 = set(clean1.split())
        words2 = set(clean2.split())
        
        if not words1 or not words2:
            return False
        
        overlap = len(words1 & words2) / max(len(words1), len(words2))
        return overlap >= threshold
    
    async def _ai_evaluate(
        self,
        question: str,
        correct: str,
        student_answer: str
    ) -> bool:
        """Use AI to evaluate answer correctness"""
        # This would call Gemini for nuanced evaluation
        # For now, return False to be safe
        return False
    
    async def _determine_difficulty(
        self,
        student_id: UUID,
        topic_id: Optional[UUID]
    ) -> str:
        """Determine appropriate difficulty based on student performance"""
        if topic_id:
            result = await self.db.execute(
                select(StudentTopicProgress)
                .where(StudentTopicProgress.student_id == student_id)
                .where(StudentTopicProgress.topic_id == topic_id)
            )
            progress = result.scalar_one_or_none()
            
            if progress:
                mastery = float(progress.mastery_level)
                if mastery >= 80:
                    return "hard"
                elif mastery >= 50:
                    return "medium"
        
        return "easy"
    
    async def _get_next_question(
        self,
        session_id: UUID,
        student_id: UUID,
        subject_id: Optional[UUID],
        topic_id: Optional[UUID],
        difficulty: str,
        exclude_ids: List[UUID]
    ) -> Optional[Question]:
        """Get next question for the session"""
        query = select(Question)
        
        if subject_id:
            query = query.where(Question.subject_id == subject_id)
        if topic_id:
            query = query.where(Question.topic_id == topic_id)
        if difficulty:
            query = query.where(Question.difficulty == difficulty)
        if exclude_ids:
            query = query.where(~Question.id.in_(exclude_ids))
        
        # Order by least attempted first
        query = query.order_by(Question.times_attempted.asc())
        query = query.limit(10)
        
        result = await self.db.execute(query)
        questions = result.scalars().all()
        
        if questions:
            return random.choice(questions)
        
        return None
    
    async def _generate_question(
        self,
        student_id: UUID,
        subject_id: Optional[UUID],
        topic_id: Optional[UUID],
        difficulty: str
    ) -> Question:
        """Generate a question using AI when database is empty"""
        # Get student context
        student = await self.db.get(Student, student_id)
        
        student_context = {
            "education_level": student.education_level.value,
            "grade": student.grade,
            "current_subject": student.subjects[0] if student.subjects else "General"
        }
        
        generated = await self.rag.generate_practice_question(
            topic_id=str(topic_id) if topic_id else None,
            difficulty=difficulty,
            student_context=student_context
        )
        
        # Create question in database
        question = Question(
            subject_id=subject_id,
            topic_id=topic_id,
            question_text=generated.get("question", "Practice question"),
            question_type=generated.get("question_type", "short_answer"),
            options=generated.get("options"),
            correct_answer=generated.get("correct_answer", ""),
            marking_scheme=generated.get("explanation", ""),
            difficulty=difficulty,
            source="generated"
        )
        
        self.db.add(question)
        await self.db.flush()
        
        return question
    
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
                topic_id=topic_id
            )
            self.db.add(progress)
        
        progress.questions_attempted = (progress.questions_attempted or 0) + 1
        if is_correct:
            progress.questions_correct = (progress.questions_correct or 0) + 1
        
        # Calculate mastery level
        if progress.questions_attempted > 0:
            progress.mastery_level = (
                progress.questions_correct / progress.questions_attempted
            ) * 100
        
        progress.last_practiced = datetime.utcnow()
        
        # Calculate next review date (spaced repetition)
        if progress.mastery_level >= 90:
            days_until_review = 14
        elif progress.mastery_level >= 70:
            days_until_review = 7
        elif progress.mastery_level >= 50:
            days_until_review = 3
        else:
            days_until_review = 1
        
        progress.next_review_date = date.today() + timedelta(days=days_until_review)
    
    async def _update_streak(self, student_id: UUID) -> None:
        """Update student's daily streak"""
        result = await self.db.execute(
            select(StudentStreak).where(StudentStreak.student_id == student_id)
        )
        streak = result.scalar_one_or_none()
        
        today = date.today()
        
        if not streak:
            streak = StudentStreak(
                student_id=student_id,
                current_streak=1,
                longest_streak=1,
                last_activity_date=today,
                total_active_days=1
            )
            self.db.add(streak)
            return
        
        if streak.last_activity_date == today:
            return  # Already counted today
        
        if streak.last_activity_date == today - timedelta(days=1):
            # Consecutive day
            streak.current_streak += 1
            if streak.current_streak > streak.longest_streak:
                streak.longest_streak = streak.current_streak
        else:
            # Streak broken
            streak.current_streak = 1
        
        streak.last_activity_date = today
        streak.total_active_days += 1