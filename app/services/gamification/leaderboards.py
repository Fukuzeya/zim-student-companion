# ============================================================================
# Leaderboard System
# ============================================================================
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from uuid import UUID
from datetime import datetime, timedelta
from enum import Enum

from app.models.user import Student
from app.models.practice import PracticeSession, QuestionAttempt
from app.models.gamification import StudentStreak, CompetitionParticipant

class LeaderboardType(str, Enum):
    XP_ALL_TIME = "xp_all_time"
    XP_WEEKLY = "xp_weekly"
    XP_MONTHLY = "xp_monthly"
    STREAK = "streak"
    ACCURACY = "accuracy"
    QUESTIONS = "questions"
    SCHOOL = "school"
    DISTRICT = "district"

class LeaderboardService:
    """Manages leaderboards and rankings"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_leaderboard(
        self,
        leaderboard_type: LeaderboardType,
        limit: int = 20,
        filters: Dict = None
    ) -> List[Dict]:
        """Get leaderboard entries"""
        
        if leaderboard_type == LeaderboardType.XP_ALL_TIME:
            return await self._get_xp_leaderboard(limit, filters)
        elif leaderboard_type == LeaderboardType.STREAK:
            return await self._get_streak_leaderboard(limit, filters)
        elif leaderboard_type == LeaderboardType.ACCURACY:
            return await self._get_accuracy_leaderboard(limit, filters)
        elif leaderboard_type == LeaderboardType.QUESTIONS:
            return await self._get_questions_leaderboard(limit, filters)
        elif leaderboard_type == LeaderboardType.SCHOOL:
            return await self._get_school_leaderboard(limit, filters)
        
        return []
    
    async def _get_xp_leaderboard(self, limit: int, filters: Dict = None) -> List[Dict]:
        """Get XP-based leaderboard"""
        query = select(Student).order_by(desc(Student.total_xp)).limit(limit)
        
        if filters:
            if filters.get("education_level"):
                query = query.where(Student.education_level == filters["education_level"])
            if filters.get("grade"):
                query = query.where(Student.grade == filters["grade"])
            if filters.get("school_name"):
                query = query.where(Student.school_name == filters["school_name"])
        
        result = await self.db.execute(query)
        students = result.scalars().all()
        
        leaderboard = []
        for rank, student in enumerate(students, 1):
            leaderboard.append({
                "rank": rank,
                "student_id": str(student.id),
                "name": student.first_name,
                "school": student.school_name or "Unknown",
                "grade": student.grade,
                "score": student.total_xp,
                "level": student.level,
                "metric": "XP"
            })
        
        return leaderboard
    
    async def _get_streak_leaderboard(self, limit: int, filters: Dict = None) -> List[Dict]:
        """Get streak-based leaderboard"""
        query = (
            select(Student, StudentStreak)
            .join(StudentStreak, Student.id == StudentStreak.student_id)
            .order_by(desc(StudentStreak.current_streak))
            .limit(limit)
        )
        
        if filters:
            if filters.get("education_level"):
                query = query.where(Student.education_level == filters["education_level"])
        
        result = await self.db.execute(query)
        
        leaderboard = []
        for rank, (student, streak) in enumerate(result.all(), 1):
            leaderboard.append({
                "rank": rank,
                "student_id": str(student.id),
                "name": student.first_name,
                "school": student.school_name or "Unknown",
                "grade": student.grade,
                "score": streak.current_streak,
                "longest": streak.longest_streak,
                "metric": "Days"
            })
        
        return leaderboard
    
    async def _get_accuracy_leaderboard(self, limit: int, filters: Dict = None) -> List[Dict]:
        """Get accuracy-based leaderboard (min 50 questions)"""
        from sqlalchemy import Integer
        
        subquery = (
            select(
                QuestionAttempt.student_id,
                func.count(QuestionAttempt.id).label("total"),
                func.sum(QuestionAttempt.is_correct.cast(Integer)).label("correct")
            )
            .group_by(QuestionAttempt.student_id)
            .having(func.count(QuestionAttempt.id) >= 50)
            .subquery()
        )
        
        query = (
            select(
                Student,
                subquery.c.total,
                subquery.c.correct,
                (subquery.c.correct * 100.0 / subquery.c.total).label("accuracy")
            )
            .join(subquery, Student.id == subquery.c.student_id)
            .order_by(desc("accuracy"))
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        
        leaderboard = []
        for rank, row in enumerate(result.all(), 1):
            student = row[0]
            leaderboard.append({
                "rank": rank,
                "student_id": str(student.id),
                "name": student.first_name,
                "school": student.school_name or "Unknown",
                "grade": student.grade,
                "score": round(row.accuracy, 1),
                "total_questions": row.total,
                "metric": "%"
            })
        
        return leaderboard
    
    async def _get_questions_leaderboard(self, limit: int, filters: Dict = None) -> List[Dict]:
        """Get questions-answered leaderboard"""
        subquery = (
            select(
                QuestionAttempt.student_id,
                func.count(QuestionAttempt.id).label("total")
            )
            .group_by(QuestionAttempt.student_id)
            .subquery()
        )
        
        query = (
            select(Student, subquery.c.total)
            .join(subquery, Student.id == subquery.c.student_id)
            .order_by(desc(subquery.c.total))
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        
        leaderboard = []
        for rank, (student, total) in enumerate(result.all(), 1):
            leaderboard.append({
                "rank": rank,
                "student_id": str(student.id),
                "name": student.first_name,
                "school": student.school_name or "Unknown",
                "grade": student.grade,
                "score": total,
                "metric": "Questions"
            })
        
        return leaderboard
    
    async def _get_school_leaderboard(self, limit: int, filters: Dict = None) -> List[Dict]:
        """Get school-level aggregated leaderboard"""
        query = (
            select(
                Student.school_name,
                func.count(Student.id).label("student_count"),
                func.sum(Student.total_xp).label("total_xp"),
                func.avg(Student.total_xp).label("avg_xp")
            )
            .where(Student.school_name.isnot(None))
            .group_by(Student.school_name)
            .order_by(desc("total_xp"))
            .limit(limit)
        )
        
        if filters and filters.get("education_level"):
            query = query.where(Student.education_level == filters["education_level"])
        
        result = await self.db.execute(query)
        
        leaderboard = []
        for rank, row in enumerate(result.all(), 1):
            leaderboard.append({
                "rank": rank,
                "school": row.school_name,
                "student_count": row.student_count,
                "total_xp": row.total_xp,
                "average_xp": round(row.avg_xp, 0),
                "metric": "Total XP"
            })
        
        return leaderboard
    
    async def get_student_rank(
        self,
        student_id: UUID,
        leaderboard_type: LeaderboardType,
        filters: Dict = None
    ) -> Dict:
        """Get a specific student's rank"""
        # Get full leaderboard
        full_leaderboard = await self.get_leaderboard(
            leaderboard_type,
            limit=1000,  # Get more to find the student
            filters=filters
        )
        
        # Find student
        for entry in full_leaderboard:
            if entry["student_id"] == str(student_id):
                return {
                    "rank": entry["rank"],
                    "total_participants": len(full_leaderboard),
                    "score": entry["score"],
                    "percentile": round((1 - entry["rank"] / len(full_leaderboard)) * 100, 1)
                }
        
        return {
            "rank": None,
            "total_participants": len(full_leaderboard),
            "message": "Not enough activity to rank"
        }