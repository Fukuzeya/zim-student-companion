# ============================================================================
# Adaptive Difficulty System
# ============================================================================
from typing import Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from datetime import datetime, timedelta
from enum import Enum

from app.models.practice import QuestionAttempt, PracticeSession
from app.models.gamification import StudentTopicProgress

class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class AdaptiveDifficultySystem:
    """Adaptive difficulty based on student performance"""
    
    # Thresholds for difficulty adjustment
    MASTERY_THRESHOLD_HIGH = 80  # Move to harder
    MASTERY_THRESHOLD_LOW = 40   # Move to easier
    
    # Recent performance window
    RECENT_ATTEMPTS_WINDOW = 10
    
    # Performance thresholds
    HIGH_PERFORMANCE = 0.85  # 85% correct
    LOW_PERFORMANCE = 0.50   # 50% correct
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_recommended_difficulty(
        self,
        student_id: UUID,
        topic_id: Optional[UUID] = None,
        subject_id: Optional[UUID] = None
    ) -> DifficultyLevel:
        """Get recommended difficulty for a student"""
        
        # Get recent performance
        recent_performance = await self._get_recent_performance(
            student_id, topic_id, subject_id
        )
        
        # Get topic mastery if available
        topic_mastery = None
        if topic_id:
            topic_mastery = await self._get_topic_mastery(student_id, topic_id)
        
        # Determine difficulty
        return self._calculate_difficulty(recent_performance, topic_mastery)
    
    async def _get_recent_performance(
        self,
        student_id: UUID,
        topic_id: Optional[UUID],
        subject_id: Optional[UUID]
    ) -> Dict:
        """Get recent performance metrics"""
        query = (
            select(QuestionAttempt)
            .where(QuestionAttempt.student_id == student_id)
            .order_by(QuestionAttempt.attempted_at.desc())
            .limit(self.RECENT_ATTEMPTS_WINDOW)
        )
        
        result = await self.db.execute(query)
        attempts = result.scalars().all()
        
        if not attempts:
            return {
                "accuracy": 0.5,  # Default to medium
                "count": 0,
                "avg_time": None,
                "trend": "stable"
            }
        
        correct = sum(1 for a in attempts if a.is_correct)
        accuracy = correct / len(attempts)
        
        # Calculate trend (improving/declining/stable)
        if len(attempts) >= 6:
            first_half = attempts[len(attempts)//2:]
            second_half = attempts[:len(attempts)//2]
            
            first_acc = sum(1 for a in first_half if a.is_correct) / len(first_half)
            second_acc = sum(1 for a in second_half if a.is_correct) / len(second_half)
            
            if second_acc - first_acc > 0.15:
                trend = "improving"
            elif first_acc - second_acc > 0.15:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        return {
            "accuracy": accuracy,
            "count": len(attempts),
            "trend": trend
        }
    
    async def _get_topic_mastery(
        self,
        student_id: UUID,
        topic_id: UUID
    ) -> Optional[float]:
        """Get mastery level for a specific topic"""
        result = await self.db.execute(
            select(StudentTopicProgress)
            .where(StudentTopicProgress.student_id == student_id)
            .where(StudentTopicProgress.topic_id == topic_id)
        )
        progress = result.scalar_one_or_none()
        
        if progress:
            return float(progress.mastery_level)
        return None
    
    def _calculate_difficulty(
        self,
        recent_performance: Dict,
        topic_mastery: Optional[float]
    ) -> DifficultyLevel:
        """Calculate recommended difficulty level"""
        accuracy = recent_performance["accuracy"]
        trend = recent_performance["trend"]
        count = recent_performance["count"]
        
        # Not enough data - start easy
        if count < 5:
            return DifficultyLevel.EASY
        
        # Factor in topic mastery if available
        if topic_mastery is not None:
            if topic_mastery >= self.MASTERY_THRESHOLD_HIGH:
                # High mastery - challenge them
                if accuracy >= self.HIGH_PERFORMANCE:
                    return DifficultyLevel.HARD
                return DifficultyLevel.MEDIUM
            elif topic_mastery <= self.MASTERY_THRESHOLD_LOW:
                # Low mastery - build confidence
                return DifficultyLevel.EASY
        
        # Performance-based difficulty
        if accuracy >= self.HIGH_PERFORMANCE:
            # Doing very well
            if trend == "improving":
                return DifficultyLevel.HARD
            return DifficultyLevel.MEDIUM
        
        elif accuracy <= self.LOW_PERFORMANCE:
            # Struggling
            if trend == "declining":
                return DifficultyLevel.EASY
            return DifficultyLevel.EASY
        
        else:
            # Middle ground
            if trend == "improving":
                return DifficultyLevel.MEDIUM
            elif trend == "declining":
                return DifficultyLevel.EASY
            return DifficultyLevel.MEDIUM
    
    async def update_after_attempt(
        self,
        student_id: UUID,
        topic_id: UUID,
        is_correct: bool,
        difficulty: str,
        time_taken_seconds: int
    ) -> Dict:
        """Update metrics after an attempt and return recommendations"""
        
        # Get current state
        current_diff = await self.get_recommended_difficulty(student_id, topic_id)
        
        # Simple feedback
        feedback = {
            "current_difficulty": current_diff.value,
            "adjustment": "none"
        }
        
        # Check if difficulty should change
        new_diff = await self.get_recommended_difficulty(student_id, topic_id)
        
        if new_diff != current_diff:
            feedback["adjustment"] = "up" if new_diff.value > current_diff.value else "down"
            feedback["message"] = self._get_adjustment_message(current_diff, new_diff)
        
        return feedback
    
    def _get_adjustment_message(
        self,
        old_diff: DifficultyLevel,
        new_diff: DifficultyLevel
    ) -> str:
        """Get message for difficulty adjustment"""
        if new_diff == DifficultyLevel.HARD:
            return "Great progress! Moving to harder questions to challenge you! 🚀"
        elif new_diff == DifficultyLevel.EASY:
            return "Let's build up your confidence with some easier questions first. 💪"
        else:
            return "Adjusting difficulty to match your current level. 📊"