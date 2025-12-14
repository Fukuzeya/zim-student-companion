# ============================================================================
# Student Endpoints
# ============================================================================
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.api.deps import get_current_student
from app.models.user import Student, User, EducationLevel
from app.models.gamification import StudentStreak, StudentTopicProgress
from app.services.gamification.xp_system import XPSystem
from app.services.gamification.achievements import AchievementSystem
from app.services.gamification.leaderboards import LeaderboardService, LeaderboardType

router = APIRouter(prefix="/students", tags=["students"])

class StudentProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    school_name: Optional[str] = None
    district: Optional[str] = None
    province: Optional[str] = None
    grade: Optional[str] = None
    subjects: Optional[List[str]] = None
    preferred_language: Optional[str] = None
    daily_goal_minutes: Optional[int] = None

class StudentProfileResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    school_name: Optional[str]
    education_level: str
    grade: str
    subjects: List[str]
    total_xp: int
    level: int
    current_streak: int

@router.get("/me", response_model=StudentProfileResponse)
async def get_my_profile(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """Get current student's profile"""
    # Get streak
    result = await db.execute(
        select(StudentStreak).where(StudentStreak.student_id == student.id)
    )
    streak = result.scalar_one_or_none()
    
    return {
        "id": str(student.id),
        "first_name": student.first_name,
        "last_name": student.last_name or "",
        "school_name": student.school_name,
        "education_level": student.education_level.value,
        "grade": student.grade,
        "subjects": student.subjects or [],
        "total_xp": student.total_xp or 0,
        "level": student.level or 1,
        "current_streak": streak.current_streak if streak else 0
    }

@router.put("/me")
async def update_my_profile(
    updates: StudentProfileUpdate,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """Update current student's profile"""
    update_data = updates.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(student, field, value)
    
    await db.commit()
    return {"message": "Profile updated successfully"}

@router.get("/me/stats")
async def get_my_stats(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive stats for current student"""
    xp_system = XPSystem(db)
    stats = await xp_system.get_student_stats(student.id)
    
    # Get progress by topic
    result = await db.execute(
        select(StudentTopicProgress)
        .where(StudentTopicProgress.student_id == student.id)
        .order_by(StudentTopicProgress.mastery_level.desc())
    )
    progress = result.scalars().all()
    
    return {
        **stats,
        "topic_progress": [
            {
                "topic_id": str(p.topic_id),
                "mastery_level": float(p.mastery_level),
                "questions_attempted": p.questions_attempted,
                "questions_correct": p.questions_correct
            }
            for p in progress
        ]
    }

@router.get("/me/achievements")
async def get_my_achievements(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """Get student's achievements"""
    achievement_system = AchievementSystem(db)
    achievements = await achievement_system.get_student_achievements(student.id)
    return {"achievements": achievements}

@router.get("/me/rank")
async def get_my_rank(
    leaderboard_type: LeaderboardType = LeaderboardType.XP_ALL_TIME,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """Get student's rank on a leaderboard"""
    leaderboard_service = LeaderboardService(db)
    rank = await leaderboard_service.get_student_rank(student.id, leaderboard_type)
    return rank

@router.get("/leaderboard")
async def get_leaderboard(
    leaderboard_type: LeaderboardType = LeaderboardType.XP_ALL_TIME,
    education_level: Optional[str] = None,
    grade: Optional[str] = None,
    school: Optional[str] = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """Get leaderboard"""
    leaderboard_service = LeaderboardService(db)
    
    filters = {}
    if education_level:
        filters["education_level"] = education_level
    if grade:
        filters["grade"] = grade
    if school:
        filters["school_name"] = school
    
    results = await leaderboard_service.get_leaderboard(
        leaderboard_type, limit, filters if filters else None
    )
    
    return {"leaderboard": results, "type": leaderboard_type.value}

@router.post("/me/parent-code")
async def generate_parent_code(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """Generate a code for parent to link"""
    import random
    import string
    from app.models.user import ParentStudentLink
    
    # Generate 6-character code
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    # Create pending link
    link = ParentStudentLink(
        student_id=student.id,
        verification_code=code,
        verified=False
    )
    db.add(link)
    await db.commit()
    
    return {
        "code": code,
        "message": "Share this code with your parent. It expires in 24 hours.",
        "expires_in_hours": 24
    }
