# ============================================================================
# Intelligent Question Selection
# ============================================================================
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from uuid import UUID
from datetime import datetime, timedelta
import random

from app.models.curriculum import Question, Topic, Subject
from app.models.practice import QuestionAttempt
from app.models.gamification import StudentTopicProgress

class QuestionSelector:
    """Intelligent question selection based on student performance and spaced repetition"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def select_questions(
        self,
        student_id: UUID,
        num_questions: int,
        subject_id: Optional[UUID] = None,
        topic_id: Optional[UUID] = None,
        difficulty: Optional[str] = None,
        exclude_recent: bool = True,
        session_type: str = "daily_practice"
    ) -> List[Question]:
        """Select optimal questions for a student"""
        
        # Get student's progress data
        progress_map = await self._get_student_progress(student_id)
        
        # Get recently attempted questions to avoid
        recent_question_ids = []
        if exclude_recent:
            recent_question_ids = await self._get_recent_questions(student_id, days=3)
        
        # Build question pool
        questions = await self._build_question_pool(
            subject_id=subject_id,
            topic_id=topic_id,
            difficulty=difficulty,
            exclude_ids=recent_question_ids
        )
        
        if not questions:
            # Fallback: include recently attempted if no questions available
            questions = await self._build_question_pool(
                subject_id=subject_id,
                topic_id=topic_id,
                difficulty=difficulty,
                exclude_ids=[]
            )
        
        if not questions:
            return []
        
        # Score and rank questions
        scored_questions = []
        for question in questions:
            score = self._calculate_question_score(
                question=question,
                progress_map=progress_map,
                session_type=session_type
            )
            scored_questions.append((question, score))
        
        # Sort by score (higher is better)
        scored_questions.sort(key=lambda x: x[1], reverse=True)
        
        # Select with some randomization to avoid predictability
        selected = self._weighted_selection(scored_questions, num_questions)
        
        # Ensure difficulty distribution for practice sessions
        if session_type == "daily_practice" and not difficulty:
            selected = self._balance_difficulty(selected, num_questions)
        
        return selected
    
    async def _get_student_progress(self, student_id: UUID) -> Dict[str, Dict]:
        """Get student's progress for all topics"""
        result = await self.db.execute(
            select(StudentTopicProgress)
            .where(StudentTopicProgress.student_id == student_id)
        )
        progress_list = result.scalars().all()
        
        return {
            str(p.topic_id): {
                "mastery": float(p.mastery_level),
                "attempts": p.questions_attempted,
                "correct": p.questions_correct,
                "last_practiced": p.last_practiced,
                "next_review": p.next_review_date
            }
            for p in progress_list
        }
    
    async def _get_recent_questions(self, student_id: UUID, days: int = 3) -> List[UUID]:
        """Get questions attempted in the last N days"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        result = await self.db.execute(
            select(QuestionAttempt.question_id)
            .where(QuestionAttempt.student_id == student_id)
            .where(QuestionAttempt.attempted_at >= cutoff)
            .distinct()
        )
        
        return [row[0] for row in result.all()]
    
    async def _build_question_pool(
        self,
        subject_id: Optional[UUID],
        topic_id: Optional[UUID],
        difficulty: Optional[str],
        exclude_ids: List[UUID]
    ) -> List[Question]:
        """Build pool of candidate questions"""
        query = select(Question).where(Question.is_active == True)
        
        if subject_id:
            query = query.where(Question.subject_id == subject_id)
        
        if topic_id:
            query = query.where(Question.topic_id == topic_id)
        
        if difficulty:
            query = query.where(Question.difficulty == difficulty)
        
        if exclude_ids:
            query = query.where(~Question.id.in_(exclude_ids))
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    def _calculate_question_score(
        self,
        question: Question,
        progress_map: Dict[str, Dict],
        session_type: str
    ) -> float:
        """Calculate selection score for a question"""
        score = 50.0  # Base score
        
        topic_id = str(question.topic_id) if question.topic_id else None
        
        if topic_id and topic_id in progress_map:
            progress = progress_map[topic_id]
            mastery = progress["mastery"]
            
            # Prioritize topics with lower mastery (need more practice)
            if mastery < 40:
                score += 30  # High priority
            elif mastery < 70:
                score += 20  # Medium priority
            else:
                score += 5   # Low priority (already mastered)
            
            # Spaced repetition: boost if due for review
            if progress["next_review"]:
                from datetime import date
                if progress["next_review"] <= date.today():
                    score += 25  # Due for review
            
            # Recency: slight penalty for very recently practiced topics
            if progress["last_practiced"]:
                days_since = (datetime.utcnow() - progress["last_practiced"]).days
                if days_since < 1:
                    score -= 10
        else:
            # New topic - moderate priority
            score += 15
        
        # Question-level factors
        if question.times_attempted:
            success_rate = (question.times_correct or 0) / question.times_attempted
            # Prefer questions with moderate success rate (challenging but achievable)
            if 0.4 <= success_rate <= 0.7:
                score += 10
        else:
            # New questions get a boost
            score += 5
        
        # Source bonus (past papers are valuable)
        if question.source == "past_paper":
            score += 15
        
        return score
    
    def _weighted_selection(
        self,
        scored_questions: List[tuple],
        num_questions: int
    ) -> List[Question]:
        """Select questions with weighted randomization"""
        if len(scored_questions) <= num_questions:
            return [q for q, _ in scored_questions]
        
        # Use scores as weights for random selection
        questions = [q for q, _ in scored_questions]
        scores = [s for _, s in scored_questions]
        
        # Normalize scores to probabilities
        total = sum(scores)
        if total == 0:
            weights = [1.0] * len(scores)
        else:
            weights = [s / total for s in scores]
        
        # Weighted random selection without replacement
        selected = []
        available_indices = list(range(len(questions)))
        
        for _ in range(min(num_questions, len(questions))):
            if not available_indices:
                break
            
            current_weights = [weights[i] for i in available_indices]
            weight_sum = sum(current_weights)
            if weight_sum > 0:
                current_weights = [w / weight_sum for w in current_weights]
            else:
                current_weights = [1.0 / len(current_weights)] * len(current_weights)
            
            chosen_idx = random.choices(available_indices, weights=current_weights, k=1)[0]
            selected.append(questions[chosen_idx])
            available_indices.remove(chosen_idx)
        
        return selected
    
    def _balance_difficulty(
        self,
        questions: List[Question],
        target_count: int
    ) -> List[Question]:
        """Balance difficulty distribution: 40% easy, 40% medium, 20% hard"""
        if len(questions) <= target_count:
            return questions
        
        by_difficulty = {"easy": [], "medium": [], "hard": []}
        for q in questions:
            diff = q.difficulty or "medium"
            by_difficulty[diff].append(q)
        
        # Target distribution
        targets = {
            "easy": int(target_count * 0.4),
            "medium": int(target_count * 0.4),
            "hard": int(target_count * 0.2)
        }
        
        balanced = []
        for diff, target in targets.items():
            available = by_difficulty[diff]
            balanced.extend(available[:target])
        
        # Fill remaining with any questions
        remaining = target_count - len(balanced)
        all_remaining = [q for q in questions if q not in balanced]
        balanced.extend(all_remaining[:remaining])
        
        random.shuffle(balanced)
        return balanced[:target_count]