# ============================================================================
# Admin Endpoints
# ============================================================================
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User, Student, UserRole
from app.models.curriculum import Subject, Topic, Question
from app.models.payment import Payment, PaymentStatus
from app.models.practice import PracticeSession

router = APIRouter(prefix="/admin", tags=["admin"])

async def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Require admin role"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

class SubjectCreate(BaseModel):
    name: str
    code: str
    education_level: str
    description: Optional[str] = None

class TopicCreate(BaseModel):
    subject_id: UUID
    name: str
    description: Optional[str] = None
    grade: str
    syllabus_reference: Optional[str] = None
    order_index: int = 0

class QuestionCreate(BaseModel):
    subject_id: UUID
    topic_id: Optional[UUID] = None
    question_text: str
    question_type: str
    options: Optional[List[str]] = None
    correct_answer: str
    marking_scheme: Optional[str] = None
    marks: int = 1
    difficulty: str = "medium"
    source: str = "admin"
    source_year: Optional[int] = None

@router.get("/dashboard")
async def admin_dashboard(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get admin dashboard stats"""
    # Total users
    users_result = await db.execute(select(func.count(User.id)))
    total_users = users_result.scalar()
    
    # Total students
    students_result = await db.execute(select(func.count(Student.id)))
    total_students = students_result.scalar()
    
    # Active today
    today = datetime.utcnow().date()
    active_result = await db.execute(
        select(func.count(User.id))
        .where(func.date(User.last_active) == today)
    )
    active_today = active_result.scalar()
    
    # Revenue this month
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
    revenue_result = await db.execute(
        select(func.sum(Payment.amount))
        .where(Payment.status == PaymentStatus.COMPLETED)
        .where(Payment.completed_at >= month_start)
    )
    monthly_revenue = float(revenue_result.scalar() or 0)
    
    # Total questions
    questions_result = await db.execute(select(func.count(Question.id)))
    total_questions = questions_result.scalar()
    
    # Sessions today
    sessions_result = await db.execute(
        select(func.count(PracticeSession.id))
        .where(func.date(PracticeSession.started_at) == today)
    )
    sessions_today = sessions_result.scalar()
    
    return {
        "users": {
            "total": total_users,
            "students": total_students,
            "active_today": active_today
        },
        "revenue": {
            "this_month": monthly_revenue,
            "currency": "USD"
        },
        "content": {
            "total_questions": total_questions
        },
        "engagement": {
            "sessions_today": sessions_today
        }
    }

@router.post("/subjects")
async def create_subject(
    subject: SubjectCreate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create a new subject"""
    new_subject = Subject(
        name=subject.name,
        code=subject.code,
        education_level=subject.education_level,
        description=subject.description
    )
    db.add(new_subject)
    await db.commit()
    await db.refresh(new_subject)
    
    return {"id": str(new_subject.id), "message": "Subject created"}

@router.get("/subjects")
async def list_subjects(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all subjects"""
    result = await db.execute(select(Subject))
    subjects = result.scalars().all()
    
    return {
        "subjects": [
            {
                "id": str(s.id),
                "name": s.name,
                "code": s.code,
                "education_level": s.education_level,
                "is_active": s.is_active
            }
            for s in subjects
        ]
    }

@router.post("/topics")
async def create_topic(
    topic: TopicCreate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create a new topic"""
    new_topic = Topic(
        subject_id=topic.subject_id,
        name=topic.name,
        description=topic.description,
        grade=topic.grade,
        syllabus_reference=topic.syllabus_reference,
        order_index=topic.order_index
    )
    db.add(new_topic)
    await db.commit()
    
    return {"id": str(new_topic.id), "message": "Topic created"}

@router.post("/questions")
async def create_question(
    question: QuestionCreate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create a new question"""
    new_question = Question(
        subject_id=question.subject_id,
        topic_id=question.topic_id,
        question_text=question.question_text,
        question_type=question.question_type,
        options=question.options,
        correct_answer=question.correct_answer,
        marking_scheme=question.marking_scheme,
        marks=question.marks,
        difficulty=question.difficulty,
        source=question.source,
        source_year=question.source_year
    )
    db.add(new_question)
    await db.commit()
    
    return {"id": str(new_question.id), "message": "Question created"}

@router.post("/questions/bulk")
async def bulk_upload_questions(
    file: UploadFile = File(...),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Bulk upload questions from CSV/JSON"""
    import json
    
    content = await file.read()
    
    if file.filename.endswith('.json'):
        questions_data = json.loads(content)
    else:
        raise HTTPException(status_code=400, detail="Only JSON files supported")
    
    created = 0
    for q in questions_data:
        question = Question(
            subject_id=q.get("subject_id"),
            topic_id=q.get("topic_id"),
            question_text=q["question_text"],
            question_type=q.get("question_type", "short_answer"),
            options=q.get("options"),
            correct_answer=q["correct_answer"],
            marking_scheme=q.get("marking_scheme"),
            marks=q.get("marks", 1),
            difficulty=q.get("difficulty", "medium"),
            source=q.get("source", "bulk_upload"),
            source_year=q.get("source_year")
        )
        db.add(question)
        created += 1
    
    await db.commit()
    
    return {"message": f"Created {created} questions"}

@router.get("/users")
async def list_users(
    role: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List users with filtering"""
    query = select(User).offset(offset).limit(limit)
    
    if role:
        query = query.where(User.role == role)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return {
        "users": [
            {
                "id": str(u.id),
                "phone": u.phone_number,
                "email": u.email,
                "role": u.role.value,
                "subscription": u.subscription_tier.value,
                "created_at": u.created_at.isoformat(),
                "last_active": u.last_active.isoformat() if u.last_active else None
            }
            for u in users
        ]
    }