# ============================================================================
# Achievement System
# ============================================================================
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Integer, select
from uuid import UUID
from datetime import datetime, date

from app.models.gamification import Achievement, StudentAchievement, StudentStreak, StudentTopicProgress
from app.models.practice import PracticeSession, QuestionAttempt
from app.models.user import Student

class AchievementSystem:
    """Manages achievement checking and awarding"""
    
    # Achievement definitions
    ACHIEVEMENT_DEFINITIONS = [
        # Streak achievements
        {"name": "consistent", "type": "streak", "criteria": {"streak_days": 7}, "points": 50, "icon": "🔥"},
        {"name": "dedicated", "type": "streak", "criteria": {"streak_days": 30}, "points": 200, "icon": "💪"},
        {"name": "unstoppable", "type": "streak", "criteria": {"streak_days": 100}, "points": 1000, "icon": "⚡"},
        {"name": "legendary_learner", "type": "streak", "criteria": {"streak_days": 365}, "points": 5000, "icon": "👑"},
        
        # Mastery achievements
        {"name": "topic_master", "type": "mastery", "criteria": {"mastery_level": 90, "topic_count": 1}, "points": 100, "icon": "🎯"},
        {"name": "subject_expert", "type": "mastery", "criteria": {"mastery_level": 85, "subject_complete": True}, "points": 500, "icon": "📚"},
        {"name": "polymath", "type": "mastery", "criteria": {"subjects_mastered": 3, "mastery_level": 80}, "points": 1000, "icon": "🧠"},
        
        # Question achievements
        {"name": "first_steps", "type": "milestone", "criteria": {"questions_answered": 10}, "points": 20, "icon": "👶"},
        {"name": "getting_started", "type": "milestone", "criteria": {"questions_answered": 50}, "points": 50, "icon": "🚀"},
        {"name": "century", "type": "milestone", "criteria": {"questions_answered": 100}, "points": 100, "icon": "💯"},
        {"name": "question_machine", "type": "milestone", "criteria": {"questions_answered": 500}, "points": 300, "icon": "⚙️"},
        {"name": "thousand_club", "type": "milestone", "criteria": {"questions_answered": 1000}, "points": 500, "icon": "🏆"},
        
        # Accuracy achievements
        {"name": "sharp_shooter", "type": "accuracy", "criteria": {"accuracy": 90, "min_questions": 20}, "points": 100, "icon": "🎯"},
        {"name": "perfect_week", "type": "accuracy", "criteria": {"weekly_accuracy": 100, "min_questions": 10}, "points": 250, "icon": "✨"},
        
        # Competition achievements
        {"name": "competitor", "type": "competition", "criteria": {"competitions_joined": 1}, "points": 50, "icon": "🏅"},
        {"name": "top_10", "type": "competition", "criteria": {"top_10_finishes": 1}, "points": 150, "icon": "🔟"},
        {"name": "champion", "type": "competition", "criteria": {"wins": 1}, "points": 500, "icon": "🥇"},
        {"name": "serial_winner", "type": "competition", "criteria": {"wins": 5}, "points": 2000, "icon": "👑"},
        
        # Special achievements
        {"name": "early_bird", "type": "special", "criteria": {"practice_before_6am": True}, "points": 30, "icon": "🌅"},
        {"name": "night_owl", "type": "special", "criteria": {"practice_after_10pm": True}, "points": 30, "icon": "🦉"},
        {"name": "weekend_warrior", "type": "special", "criteria": {"weekend_streak": 4}, "points": 100, "icon": "⚔️"},
        {"name": "comeback_kid", "type": "special", "criteria": {"improvement": 20}, "points": 150, "icon": "📈"},
    ]
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def check_achievements(self, student_id: UUID) -> List[Achievement]:
        """Check and award any newly earned achievements"""
        newly_earned = []
        
        # Get student's current achievements
        result = await self.db.execute(
            select(StudentAchievement.achievement_id)
            .where(StudentAchievement.student_id == student_id)
        )
        earned_ids = {row[0] for row in result.all()}
        
        # Get all achievements
        result = await self.db.execute(select(Achievement).where(Achievement.is_active == True))
        all_achievements = result.scalars().all()
        
        # Check each unearned achievement
        for achievement in all_achievements:
            if achievement.id in earned_ids:
                continue
            
            if await self._check_criteria(student_id, achievement):
                # Award achievement
                student_achievement = StudentAchievement(
                    student_id=student_id,
                    achievement_id=achievement.id
                )
                self.db.add(student_achievement)
                newly_earned.append(achievement)
        
        if newly_earned:
            await self.db.commit()
        
        return newly_earned
    
    async def _check_criteria(self, student_id: UUID, achievement: Achievement) -> bool:
        """Check if student meets achievement criteria"""
        criteria = achievement.criteria or {}
        
        if achievement.achievement_type == "streak":
            return await self._check_streak_criteria(student_id, criteria)
        elif achievement.achievement_type == "mastery":
            return await self._check_mastery_criteria(student_id, criteria)
        elif achievement.achievement_type == "milestone":
            return await self._check_milestone_criteria(student_id, criteria)
        elif achievement.achievement_type == "accuracy":
            return await self._check_accuracy_criteria(student_id, criteria)
        elif achievement.achievement_type == "competition":
            return await self._check_competition_criteria(student_id, criteria)
        elif achievement.achievement_type == "special":
            return await self._check_special_criteria(student_id, criteria)
        
        return False
    
    async def _check_streak_criteria(self, student_id: UUID, criteria: Dict) -> bool:
        """Check streak-based achievement criteria"""
        result = await self.db.execute(
            select(StudentStreak).where(StudentStreak.student_id == student_id)
        )
        streak = result.scalar_one_or_none()
        
        if not streak:
            return False
        
        required_days = criteria.get("streak_days", 0)
        return streak.current_streak >= required_days or streak.longest_streak >= required_days
    
    async def _check_mastery_criteria(self, student_id: UUID, criteria: Dict) -> bool:
        """Check mastery-based achievement criteria"""
        required_level = criteria.get("mastery_level", 100)
        
        result = await self.db.execute(
            select(StudentTopicProgress)
            .where(StudentTopicProgress.student_id == student_id)
            .where(StudentTopicProgress.mastery_level >= required_level)
        )
        mastered_topics = result.scalars().all()
        
        if criteria.get("topic_count"):
            return len(mastered_topics) >= criteria["topic_count"]
        
        return len(mastered_topics) > 0
    
    async def _check_milestone_criteria(self, student_id: UUID, criteria: Dict) -> bool:
        """Check milestone-based achievement criteria"""
        from sqlalchemy import func
        
        result = await self.db.execute(
            select(func.count(QuestionAttempt.id))
            .where(QuestionAttempt.student_id == student_id)
        )
        total_questions = result.scalar() or 0
        
        return total_questions >= criteria.get("questions_answered", 0)
    
    async def _check_accuracy_criteria(self, student_id: UUID, criteria: Dict) -> bool:
        """Check accuracy-based achievement criteria"""
        from sqlalchemy import func
        
        result = await self.db.execute(
            select(
                func.count(QuestionAttempt.id).label("total"),
                func.sum(QuestionAttempt.is_correct.cast(Integer)).label("correct")
            )
            .where(QuestionAttempt.student_id == student_id)
        )
        row = result.one()
        
        if row.total < criteria.get("min_questions", 0):
            return False
        
        if row.total == 0:
            return False
        
        accuracy = (row.correct / row.total) * 100
        return accuracy >= criteria.get("accuracy", 100)
    
    async def _check_competition_criteria(self, student_id: UUID, criteria: Dict) -> bool:
        """Check competition-based achievement criteria"""
        from app.models.gamification import CompetitionParticipant
        from sqlalchemy import func
        
        if criteria.get("competitions_joined"):
            result = await self.db.execute(
                select(func.count(CompetitionParticipant.id))
                .where(CompetitionParticipant.student_id == student_id)
            )
            count = result.scalar() or 0
            return count >= criteria["competitions_joined"]
        
        if criteria.get("wins"):
            result = await self.db.execute(
                select(func.count(CompetitionParticipant.id))
                .where(CompetitionParticipant.student_id == student_id)
                .where(CompetitionParticipant.rank == 1)
            )
            wins = result.scalar() or 0
            return wins >= criteria["wins"]
        
        return False
    
    async def _check_special_criteria(self, student_id: UUID, criteria: Dict) -> bool:
        """Check special achievement criteria"""
        # These are typically checked at specific times
        return False
    
    async def get_student_achievements(self, student_id: UUID) -> List[Dict]:
        """Get all achievements for a student"""
        result = await self.db.execute(
            select(StudentAchievement, Achievement)
            .join(Achievement)
            .where(StudentAchievement.student_id == student_id)
            .order_by(StudentAchievement.earned_at.desc())
        )
        
        achievements = []
        for sa, ach in result.all():
            achievements.append({
                "name": ach.name,
                "description": ach.description,
                "icon": ach.icon,
                "points": ach.points,
                "earned_at": sa.earned_at.isoformat()
            })
        
        return achievements
