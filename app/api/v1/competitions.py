# ============================================================================
# Competition Endpoints
# ============================================================================
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.api.deps import get_current_student, require_subscription
from app.models.user import Student, SubscriptionTier
from app.models.gamification import Competition, CompetitionParticipant

router = APIRouter(prefix="/competitions", tags=["competitions"])

class CreateCompetitionRequest(BaseModel):
    name: str
    description: Optional[str] = None
    subject_id: Optional[UUID] = None
    education_level: Optional[str] = None
    grade: Optional[str] = None
    competition_type: str = "individual"
    start_date: datetime
    end_date: datetime
    num_questions: int = 10
    time_limit_minutes: int = 30
    difficulty: str = "medium"

@router.get("/")
async def list_competitions(
    status: Optional[str] = None,
    education_level: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List available competitions"""
    query = select(Competition).order_by(Competition.start_date.desc())
    
    if status:
        query = query.where(Competition.status == status)
    if education_level:
        query = query.where(Competition.education_level == education_level)
    
    result = await db.execute(query)
    competitions = result.scalars().all()
    
    competition_list = []
    for comp in competitions:
        # Get participant count
        count_result = await db.execute(
            select(func.count(CompetitionParticipant.id))
            .where(CompetitionParticipant.competition_id == comp.id)
        )
        participant_count = count_result.scalar() or 0
        
        competition_list.append({
            "id": str(comp.id),
            "name": comp.name,
            "description": comp.description,
            "type": comp.competition_type,
            "status": comp.status,
            "start_date": comp.start_date.isoformat(),
            "end_date": comp.end_date.isoformat(),
            "num_questions": comp.num_questions,
            "time_limit_minutes": comp.time_limit_minutes,
            "difficulty": comp.difficulty,
            "participants": participant_count,
            "prizes": comp.prizes
        })
    
    return {"competitions": competition_list}

@router.get("/{competition_id}")
async def get_competition(
    competition_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get competition details"""
    competition = await db.get(Competition, competition_id)
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found")
    
    # Get leaderboard
    result = await db.execute(
        select(CompetitionParticipant, Student)
        .join(Student, CompetitionParticipant.student_id == Student.id)
        .where(CompetitionParticipant.competition_id == competition_id)
        .where(CompetitionParticipant.status == "completed")
        .order_by(CompetitionParticipant.score.desc())
        .limit(20)
    )
    
    leaderboard = []
    for rank, (participant, student) in enumerate(result.all(), 1):
        leaderboard.append({
            "rank": rank,
            "name": student.first_name,
            "school": student.school_name,
            "score": float(participant.score),
            "time_taken": participant.time_taken_seconds
        })
    
    return {
        "id": str(competition.id),
        "name": competition.name,
        "description": competition.description,
        "rules": competition.rules,
        "prizes": competition.prizes,
        "leaderboard": leaderboard
    }

@router.post("/{competition_id}/join")
async def join_competition(
    competition_id: UUID,
    student: Student = Depends(get_current_student),
    _: None = Depends(require_subscription(SubscriptionTier.BASIC)),
    db: AsyncSession = Depends(get_db)
):
    """Join a competition"""
    competition = await db.get(Competition, competition_id)
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found")
    
    if competition.status != "upcoming" and competition.status != "active":
        raise HTTPException(status_code=400, detail="Competition is not open for registration")
    
    # Check if already registered
    result = await db.execute(
        select(CompetitionParticipant)
        .where(CompetitionParticipant.competition_id == competition_id)
        .where(CompetitionParticipant.student_id == student.id)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already registered for this competition")
    
    # Check max participants
    if competition.max_participants:
        count_result = await db.execute(
            select(func.count(CompetitionParticipant.id))
            .where(CompetitionParticipant.competition_id == competition_id)
        )
        if count_result.scalar() >= competition.max_participants:
            raise HTTPException(status_code=400, detail="Competition is full")
    
    # Register
    participant = CompetitionParticipant(
        competition_id=competition_id,
        student_id=student.id,
        status="registered"
    )
    db.add(participant)
    await db.commit()
    
    return {"message": "Successfully registered for competition"}

@router.post("/{competition_id}/start")
async def start_competition_attempt(
    competition_id: UUID,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """Start competition attempt"""
    # Verify registration
    result = await db.execute(
        select(CompetitionParticipant)
        .where(CompetitionParticipant.competition_id == competition_id)
        .where(CompetitionParticipant.student_id == student.id)
    )
    participant = result.scalar_one_or_none()
    
    if not participant:
        raise HTTPException(status_code=400, detail="Not registered for this competition")
    
    if participant.status == "completed":
        raise HTTPException(status_code=400, detail="Already completed this competition")
    
    competition = await db.get(Competition, competition_id)
    if competition.status != "active":
        raise HTTPException(status_code=400, detail="Competition is not active")
    
    # Update participant status
    participant.status = "in_progress"
    participant.started_at = datetime.utcnow()
    await db.commit()
    
    # Generate competition questions (would integrate with practice system)
    return {
        "message": "Competition started",
        "time_limit_minutes": competition.time_limit_minutes,
        "num_questions": competition.num_questions,
        "started_at": participant.started_at.isoformat()
    }

@router.get("/{competition_id}/leaderboard")
async def get_competition_leaderboard(
    competition_id: UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Get full competition leaderboard"""
    result = await db.execute(
        select(CompetitionParticipant, Student)
        .join(Student, CompetitionParticipant.student_id == Student.id)
        .where(CompetitionParticipant.competition_id == competition_id)
        .order_by(CompetitionParticipant.score.desc())
        .limit(limit)
    )
    
    leaderboard = []
    for rank, (participant, student) in enumerate(result.all(), 1):
        leaderboard.append({
            "rank": rank,
            "student_id": str(student.id),
            "name": student.first_name,
            "school": student.school_name or "Unknown",
            "grade": student.grade,
            "score": float(participant.score) if participant.score else 0,
            "questions_correct": participant.questions_correct,
            "time_taken_seconds": participant.time_taken_seconds,
            "status": participant.status
        })
    
    return {"leaderboard": leaderboard}