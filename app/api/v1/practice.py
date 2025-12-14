# ============================================================================
# Practice Session Endpoints
# ============================================================================
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID

from app.core.database import get_db
from app.api.deps import get_current_student, check_rate_limit, get_rag_engine
from app.models.user import Student
from app.models.practice import PracticeSession, QuestionAttempt
from app.services.practice.session_manager import PracticeSessionManager
from app.services.rag.rag_engine import RAGEngine

router = APIRouter(prefix="/practice", tags=["practice"])

class StartSessionRequest(BaseModel):
    subject_id: Optional[UUID] = None
    topic_id: Optional[UUID] = None
    session_type: str = "daily_practice"
    num_questions: int = 5
    difficulty: Optional[str] = None

class SubmitAnswerRequest(BaseModel):
    question_id: UUID
    answer: str

@router.post("/start")
async def start_practice_session(
    request: StartSessionRequest,
    student: Student = Depends(get_current_student),
    remaining: int = Depends(check_rate_limit),
    rag_engine: RAGEngine = Depends(get_rag_engine),
    db: AsyncSession = Depends(get_db)
):
    """Start a new practice session"""
    session_manager = PracticeSessionManager(db, rag_engine)
    
    session, first_question = await session_manager.start_session(
        student_id=student.id,
        subject_id=request.subject_id,
        topic_id=request.topic_id,
        session_type=request.session_type,
        num_questions=min(request.num_questions, remaining),
        difficulty=request.difficulty
    )
    
    return {
        "session_id": str(session.id),
        "total_questions": session.total_questions,
        "difficulty": session.difficulty_level,
        "question": {
            "id": str(first_question.id),
            "text": first_question.formatted_text,
            "index": first_question.index,
            "total": first_question.total
        },
        "remaining_daily": remaining - 1
    }

@router.post("/sessions/{session_id}/answer")
async def submit_answer(
    session_id: UUID,
    request: SubmitAnswerRequest,
    student: Student = Depends(get_current_student),
    rag_engine: RAGEngine = Depends(get_rag_engine),
    db: AsyncSession = Depends(get_db)
):
    """Submit an answer for current question"""
    session_manager = PracticeSessionManager(db, rag_engine)
    
    # Get hint count from Redis
    from app.core.redis import cache
    hints_used = int(await cache.get(f"hints:{session_id}:{request.question_id}") or 0)
    
    result = await session_manager.evaluate_answer(
        session_id=session_id,
        question_id=request.question_id,
        student_answer=request.answer,
        student_id=student.id,
        hints_used=hints_used
    )
    
    response = {
        "is_correct": result["is_correct"],
        "feedback": result["feedback"],
        "xp_earned": result.get("xp_earned", 0),
        "progress": result.get("progress")
    }
    
    if result.get("next_question"):
        nq = result["next_question"]
        response["next_question"] = {
            "id": str(nq.id),
            "text": nq.formatted_text,
            "index": nq.index,
            "total": nq.total
        }
    else:
        response["session_complete"] = True
    
    return response

@router.post("/sessions/{session_id}/hint")
async def get_hint(
    session_id: UUID,
    question_id: UUID,
    student: Student = Depends(get_current_student),
    rag_engine: RAGEngine = Depends(get_rag_engine),
    db: AsyncSession = Depends(get_db)
):
    """Get a hint for current question"""
    from app.core.redis import cache
    
    # Track hints used
    hint_key = f"hints:{session_id}:{question_id}"
    hints_used = int(await cache.get(hint_key) or 0)
    
    if hints_used >= 3:
        raise HTTPException(status_code=400, detail="Maximum hints reached")
    
    session_manager = PracticeSessionManager(db, rag_engine)
    hint = await session_manager.get_hint(question_id, hints_used)
    
    # Increment hint count
    await cache.set(hint_key, str(hints_used + 1), ttl=3600)
    
    return {
        "hint": hint,
        "hint_number": hints_used + 1,
        "hints_remaining": 2 - hints_used
    }

@router.post("/sessions/{session_id}/end")
async def end_session(
    session_id: UUID,
    student: Student = Depends(get_current_student),
    rag_engine: RAGEngine = Depends(get_rag_engine),
    db: AsyncSession = Depends(get_db)
):
    """End practice session early"""
    session_manager = PracticeSessionManager(db, rag_engine)
    summary = await session_manager.end_session(session_id, student.id)
    return {"summary": summary}

@router.get("/sessions/history")
async def get_session_history(
    limit: int = 10,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """Get practice session history"""
    result = await db.execute(
        select(PracticeSession)
        .where(PracticeSession.student_id == student.id)
        .order_by(PracticeSession.started_at.desc())
        .limit(limit)
    )
    sessions = result.scalars().all()
    
    return {
        "sessions": [
            {
                "id": str(s.id),
                "type": s.session_type,
                "started_at": s.started_at.isoformat(),
                "status": s.status,
                "score": float(s.score_percentage) if s.score_percentage else None,
                "questions": s.total_questions,
                "correct": s.correct_answers
            }
            for s in sessions
        ]
    }

@router.post("/ask")
async def ask_question(
    question: str,
    subject: Optional[str] = None,
    student: Student = Depends(get_current_student),
    remaining: int = Depends(check_rate_limit),
    rag_engine: RAGEngine = Depends(get_rag_engine),
    db: AsyncSession = Depends(get_db)
):
    """Ask a question using RAG"""
    student_context = {
        "first_name": student.first_name,
        "education_level": student.education_level.value,
        "grade": student.grade,
        "current_subject": subject or (student.subjects[0] if student.subjects else None),
        "preferred_language": student.preferred_language
    }
    
    response, sources = await rag_engine.query(
        question=question,
        student_context=student_context,
        mode="socratic"
    )
    
    return {
        "response": response,
        "sources_used": len(sources),
        "remaining_questions": remaining - 1
    }