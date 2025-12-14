# ============================================================================
# XP & Leveling System
# ============================================================================
from typing import Dict, Tuple, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from uuid import UUID
from datetime import datetime

from app.models.user import Student
from app.models.gamification import StudentStreak

class XPSystem:
    """Manages XP awards and leveling"""
    
    # XP values for different actions
    XP_VALUES = {
        # Correct answers by difficulty
        "correct_easy": 5,
        "correct_medium": 10,
        "correct_hard": 20,
        
        # Bonuses
        "first_attempt_bonus": 5,
        "no_hints_bonus": 3,
        "speed_bonus": 5,  # Answer quickly
        
        # Session completion
        "session_complete": 25,
        "perfect_session": 50,  # All correct
        
        # Streaks
        "streak_7_days": 100,
        "streak_30_days": 500,
        "streak_100_days": 2000,
        
        # Competitions
        "competition_participate": 50,
        "competition_top_10": 200,
        "competition_top_3": 500,
        "competition_winner": 1000,
        
        # Special
        "help_another_student": 30,
        "complete_topic": 100,
        "first_question_of_day": 10,
    }
    
    # Level thresholds
    LEVELS = [
        (1, 0, "Curious Learner"),
        (2, 100, "Eager Student"),
        (3, 300, "Knowledge Seeker"),
        (4, 600, "Rising Scholar"),
        (5, 1000, "Dedicated Pupil"),
        (6, 1500, "Subject Explorer"),
        (7, 2200, "Academic Achiever"),
        (8, 3000, "Honor Student"),
        (9, 4000, "Distinguished Scholar"),
        (10, 5500, "Master Mind"),
        (11, 7500, "Academic Champion"),
        (12, 10000, "Wisdom Seeker"),
        (13, 13000, "Excellence Ambassador"),
        (14, 17000, "Future Leader"),
        (15, 22000, "ZIMSEC Legend"),
    ]
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def award_xp(
        self,
        student_id: UUID,
        action: str,
        difficulty: str = None,
        first_attempt: bool = False,
        bonus_multiplier: float = 1.0,
        **kwargs
    ) -> int:
        """Award XP for an action and handle level ups"""
        
        # Calculate base XP
        if action == "correct_answer" and difficulty:
            xp = self.XP_VALUES.get(f"correct_{difficulty}", 5)
        else:
            xp = self.XP_VALUES.get(action, 0)
        
        # Apply bonuses
        if first_attempt:
            xp += self.XP_VALUES["first_attempt_bonus"]
        
        if kwargs.get("no_hints"):
            xp += self.XP_VALUES["no_hints_bonus"]
        
        if kwargs.get("fast_answer"):
            xp += self.XP_VALUES["speed_bonus"]
        
        # Apply multiplier
        xp = int(xp * bonus_multiplier)
        
        if xp <= 0:
            return 0
        
        # Get student and update XP
        student = await self.db.get(Student, student_id)
        if not student:
            return 0
        
        old_xp = student.total_xp
        old_level = student.level
        
        student.total_xp = (student.total_xp or 0) + xp
        
        # Check for level up
        new_level = self._calculate_level(student.total_xp)
        if new_level > old_level:
            student.level = new_level
            # Could trigger level up notification here
        
        await self.db.commit()
        
        return xp
    
    def _calculate_level(self, total_xp: int) -> int:
        """Calculate level based on total XP"""
        current_level = 1
        for level, xp_required, _ in self.LEVELS:
            if total_xp >= xp_required:
                current_level = level
            else:
                break
        return current_level
    
    def get_level_info(self, total_xp: int) -> Dict:
        """Get detailed level information"""
        current_level = 1
        current_title = "Curious Learner"
        current_threshold = 0
        next_threshold = 100
        
        for i, (level, xp_required, title) in enumerate(self.LEVELS):
            if total_xp >= xp_required:
                current_level = level
                current_title = title
                current_threshold = xp_required
                if i + 1 < len(self.LEVELS):
                    next_threshold = self.LEVELS[i + 1][1]
                else:
                    next_threshold = xp_required  # Max level
            else:
                break
        
        xp_in_level = total_xp - current_threshold
        xp_for_next = next_threshold - current_threshold
        progress_percent = (xp_in_level / xp_for_next * 100) if xp_for_next > 0 else 100
        
        return {
            "level": current_level,
            "title": current_title,
            "total_xp": total_xp,
            "xp_in_level": xp_in_level,
            "xp_for_next_level": xp_for_next,
            "progress_percent": round(progress_percent, 1),
            "is_max_level": current_level >= 15
        }
    
    async def get_student_stats(self, student_id: UUID) -> Dict:
        """Get comprehensive XP and level stats for a student"""
        student = await self.db.get(Student, student_id)
        if not student:
            return {}
        
        level_info = self.get_level_info(student.total_xp)
        
        # Get streak info
        result = await self.db.execute(
            select(StudentStreak).where(StudentStreak.student_id == student_id)
        )
        streak = result.scalar_one_or_none()
        
        return {
            **level_info,
            "current_streak": streak.current_streak if streak else 0,
            "longest_streak": streak.longest_streak if streak else 0,
            "total_active_days": streak.total_active_days if streak else 0
        }