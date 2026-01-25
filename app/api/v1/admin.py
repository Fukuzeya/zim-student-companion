# ============================================================================
# Admin API Endpoints - Part 1: Dashboard, Users, Students
# ============================================================================
"""
Comprehensive admin API endpoints for the EduBot application.
Provides full administrative control over users, content, analytics, and system.

All endpoints require admin authentication via the require_admin dependency.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import Integer
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID
from decimal import Decimal
import io

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User, UserRole
from app.schemas.admin import (UserUpdate, BulkUserAction)

# Import all services
from app.services.admin.dashboard_service import DashboardService
from app.services.admin.user_service import UserManagementService
from app.services.admin.system_service import SystemService, AuditAction


router = APIRouter(prefix="/admin", tags=["admin"])


# ============================================================================
# Admin Authentication Dependency
# ============================================================================
async def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Require admin role for endpoint access.
    
    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# ============================================================================
# Dashboard Endpoints
# ============================================================================
@router.get("/dashboard/stats")
async def get_dashboard_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all KPI card data for the admin dashboard.
    
    Returns real-time metrics including:
    - Total users with growth percentage
    - Active students today
    - Messages processed (24h)
    - Revenue this month
    - Active subscriptions
    - Conversion rate
    - Average session duration
    - Questions answered today
    """
    service = DashboardService(db)
    return await service.get_dashboard_stats()


@router.get("/dashboard/charts")
async def get_dashboard_charts(
    days: int = Query(30, ge=7, le=90),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get chart data for dashboard visualizations.
    
    Returns data for:
    - User growth (line chart)
    - Revenue trend (area chart)
    - Subscription distribution (donut chart)
    - Active hours heatmap
    - Subject popularity (bar chart)
    - Daily active users (sparkline)
    """
    service = DashboardService(db)
    return await service.get_dashboard_charts(days=days)


@router.get("/dashboard/activity")
async def get_dashboard_activity(
    limit: int = Query(50, ge=10, le=200),
    offset: int = Query(0, ge=0),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent activity feed for dashboard.
    
    Includes:
    - New user registrations
    - Subscription upgrades
    - Competition completions
    - Support tickets
    - System alerts
    """
    service = DashboardService(db)
    return await service.get_activity_feed(limit=limit, offset=offset)


# ============================================================================
# User Management Endpoints
# ============================================================================
@router.get("/users")
async def list_users(
    role: Optional[str] = None,
    subscription_tier: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_verified: Optional[bool] = None,
    registration_date_from: Optional[date] = None,
    registration_date_to: Optional[date] = None,
    last_active_from: Optional[date] = None,
    last_active_to: Optional[date] = None,
    education_level: Optional[str] = None,
    province: Optional[str] = None,
    district: Optional[str] = None,
    school: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=100),
    sort_by: str = "created_at",
    sort_order: str = "desc",
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    List users with advanced filtering and pagination.
    
    Supports filtering by:
    - Role, subscription tier, verification status
    - Registration and activity date ranges
    - Education level, location (province/district)
    - School name
    - Global search across multiple fields
    """
    service = UserManagementService(db)
    filters = {
        "role": role,
        "subscription_tier": subscription_tier,
        "is_active": is_active,
        "is_verified": is_verified,
        "registration_date_from": registration_date_from,
        "registration_date_to": registration_date_to,
        "last_active_from": last_active_from,
        "last_active_to": last_active_to,
        "education_level": education_level,
        "province": province,
        "district": district,
        "school": school,
        "search": search
    }
    # Remove None values
    filters = {k: v for k, v in filters.items() if v is not None}
    
    return await service.list_users(
        filters=filters,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order
    )


@router.get("/users/{user_id}")
async def get_user_detail(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive user profile with statistics.
    
    Includes:
    - Full user and student information
    - Activity statistics
    - Payment history summary
    - Achievement counts
    """
    service = UserManagementService(db)
    result = await service.get_user_detail(user_id)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result


@router.put("/users/{user_id}")
async def update_user(
    user_id: UUID,
    updates: UserUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update user information"""
    service = UserManagementService(db)
    result = await service.update_user(user_id, updates.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Log the action
    system_service = SystemService(db)
    await system_service.log_action(
        admin_id=admin.id,
        admin_email=admin.email or "",
        action=AuditAction.UPDATE,
        resource_type="user",
        resource_id=user_id,
        details={"updated_fields": list(updates.model_dump(exclude_none=True).keys())}
    )
    
    return result


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete a user (soft delete - deactivates account)"""
    service = UserManagementService(db)
    result = await service.bulk_action([user_id], "deactivate")
    
    system_service = SystemService(db)
    await system_service.log_action(
        admin_id=admin.id,
        admin_email=admin.email or "",
        action=AuditAction.DELETE,
        resource_type="user",
        resource_id=user_id,
        details={}
    )
    
    return result


@router.post("/users/bulk-action")
async def bulk_user_action(
    action: BulkUserAction,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Perform bulk action on multiple users.
    
    Supported actions:
    - activate: Enable user accounts
    - deactivate: Disable user accounts
    - delete: Remove users
    - upgrade: Upgrade to basic subscription
    - downgrade: Downgrade to free tier
    """
    service = UserManagementService(db)
    return await service.bulk_action(action.user_ids, action.action)


@router.post("/users/{user_id}/impersonate")
async def impersonate_user(
    user_id: UUID,
    read_only: bool = True,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate impersonation token for debugging user issues.
    
    Creates a short-lived token to view the app as the specified user.
    Read-only mode prevents any modifications.
    """
    service = UserManagementService(db)
    result = await service.impersonate_user(admin.id, user_id, read_only)
    
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Log impersonation
    system_service = SystemService(db)
    await system_service.log_action(
        admin_id=admin.id,
        admin_email=admin.email or "",
        action=AuditAction.IMPERSONATE,
        resource_type="user",
        resource_id=user_id,
        details={"read_only": read_only}
    )
    
    return result


@router.get("/users/export")
async def export_users(
    format: str = Query("csv", regex="^(csv|json|excel)$"),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Export user data in specified format"""
    service = UserManagementService(db)
    data, filename = await service.export_users(format=format)
    
    content_types = {
        "csv": "text/csv",
        "json": "application/json",
        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    }
    
    return StreamingResponse(
        io.BytesIO(data),
        media_type=content_types[format],
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============================================================================
# Student Management Endpoints
# ============================================================================
@router.get("/students")
async def list_students(
    grade: Optional[str] = None,
    education_level: Optional[str] = None,
    school: Optional[str] = None,
    subscription_tier: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=100),
    sort_by: str = "created_at",
    sort_order: str = "desc",
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    List all students with comprehensive details and filtering.

    Returns student data including:
    - Full profile information (name, grade, school, etc.)
    - XP and level progression
    - Streak information
    - Question statistics
    - Subscription status
    """
    from sqlalchemy import select, func, or_, desc, asc
    from sqlalchemy.orm import selectinload
    from app.models.user import User as UserModel, Student
    from app.models.gamification import StudentStreak
    from app.models.practice import QuestionAttempt
    from datetime import datetime, timedelta

    # Build base query for students
    query = (
        select(Student, UserModel, StudentStreak)
        .join(UserModel, Student.user_id == UserModel.id)
        .outerjoin(StudentStreak, StudentStreak.student_id == Student.id)
        .where(UserModel.role == "student")
    )

    # Apply filters
    if grade:
        query = query.where(Student.grade == grade)
    if education_level:
        query = query.where(Student.education_level == education_level)
    if school:
        query = query.where(Student.school_name.ilike(f"%{school}%"))
    if subscription_tier:
        query = query.where(UserModel.subscription_tier == subscription_tier)
    if is_active is not None:
        query = query.where(UserModel.is_active == is_active)
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Student.first_name.ilike(search_term),
                Student.last_name.ilike(search_term),
                UserModel.email.ilike(search_term),
                UserModel.phone_number.ilike(search_term),
                Student.school_name.ilike(search_term)
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply sorting
    sort_column = Student.created_at
    if sort_by == "name":
        sort_column = Student.first_name
    elif sort_by == "xp":
        sort_column = Student.total_xp
    elif sort_by == "level":
        sort_column = Student.level
    elif sort_by == "last_active":
        sort_column = UserModel.last_active

    if sort_order == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    rows = result.all()

    # Get question statistics for all students in one query
    student_ids = [row[0].id for row in rows]

    # Get total questions answered per student
    questions_query = (
        select(
            QuestionAttempt.student_id,
            func.count(QuestionAttempt.id).label("total_questions"),
            func.sum(func.cast(QuestionAttempt.is_correct, Integer)).label("correct_count")
        )
        .where(QuestionAttempt.student_id.in_(student_ids))
        .group_by(QuestionAttempt.student_id)
    )
    questions_result = await db.execute(questions_query)
    questions_stats = {
        str(row.student_id): {
            "total_questions": row.total_questions,
            "correct_count": row.correct_count or 0
        }
        for row in questions_result.all()
    }

    # Format response
    students = []
    for student, user, streak in rows:
        student_id = str(student.id)
        q_stats = questions_stats.get(student_id, {"total_questions": 0, "correct_count": 0})
        accuracy = (q_stats["correct_count"] / q_stats["total_questions"] * 100) if q_stats["total_questions"] > 0 else 0

        students.append({
            "id": str(student.id),
            "user_id": str(user.id),
            "first_name": student.first_name,
            "last_name": student.last_name,
            "full_name": f"{student.first_name} {student.last_name}".strip(),
            "email": user.email,
            "phone_number": user.phone_number,
            "grade": student.grade,
            "education_level": student.education_level,
            "school_name": student.school_name,
            "district": student.district,
            "province": student.province,
            "subjects": student.subjects or [],
            "total_xp": student.total_xp,
            "level": student.level,
            "current_streak": streak.current_streak if streak else 0,
            "longest_streak": streak.longest_streak if streak else 0,
            "total_questions": q_stats["total_questions"],
            "correct_answers": q_stats["correct_count"],
            "accuracy": round(accuracy, 1),
            "subscription_tier": user.subscription_tier.value if hasattr(user.subscription_tier, 'value') else user.subscription_tier,
            "subscription_expires_at": user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_active": user.last_active.isoformat() if user.last_active else None
        })

    return {
        "items": students,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.get("/students/{student_id}")
async def get_student_detail(
    student_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed student profile with comprehensive statistics.

    Returns:
    - Full student profile information
    - User account details
    - Progress analytics (XP, level, streaks)
    - Question statistics and accuracy
    - Subject-by-subject performance
    - Recent sessions summary
    """
    from sqlalchemy import select, func
    from app.models.user import User as UserModel, Student
    from app.models.gamification import StudentStreak, StudentAchievement
    from app.models.practice import PracticeSession, QuestionAttempt
    from app.models.conversation import Conversation
    from app.models.payment import Payment
    from app.services.analytics.student_progress import StudentProgressAnalytics

    # Get student with user
    result = await db.execute(
        select(Student, UserModel, StudentStreak)
        .join(UserModel, Student.user_id == UserModel.id)
        .outerjoin(StudentStreak, StudentStreak.student_id == Student.id)
        .where(Student.id == student_id)
    )
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="Student not found")

    student, user, streak = row

    # Get total sessions count
    sessions_result = await db.execute(
        select(func.count(PracticeSession.id))
        .where(PracticeSession.student_id == student_id)
    )
    total_sessions = sessions_result.scalar() or 0

    # Get total questions answered
    questions_result = await db.execute(
        select(
            func.count(QuestionAttempt.id).label("total"),
            func.sum(func.cast(QuestionAttempt.is_correct, Integer)).label("correct")
        )
        .where(QuestionAttempt.student_id == student_id)
    )
    q_row = questions_result.first()
    total_questions = q_row.total or 0
    correct_answers = q_row.correct or 0

    # Get total study time (from completed sessions)
    time_result = await db.execute(
        select(func.sum(PracticeSession.time_spent_seconds))
        .where(PracticeSession.student_id == student_id)
        .where(PracticeSession.status == "completed")
    )
    total_time_seconds = time_result.scalar() or 0
    total_study_hours = round(total_time_seconds / 3600, 1)

    # Get achievements count
    achievements_result = await db.execute(
        select(func.count(StudentAchievement.id))
        .where(StudentAchievement.student_id == student_id)
    )
    achievements_count = achievements_result.scalar() or 0

    # Get conversations count
    convos_result = await db.execute(
        select(func.count(Conversation.id))
        .where(Conversation.student_id == student_id)
    )
    conversations_count = convos_result.scalar() or 0

    # Get comprehensive analytics
    analytics_service = StudentProgressAnalytics(db)
    analytics = await analytics_service.get_comprehensive_analytics(student_id)

    return {
        "id": str(student.id),
        "user_id": str(user.id),
        "first_name": student.first_name,
        "last_name": student.last_name,
        "full_name": f"{student.first_name} {student.last_name}".strip(),
        "email": user.email,
        "phone_number": user.phone_number,
        "grade": student.grade,
        "education_level": student.education_level,
        "school_name": student.school_name,
        "district": student.district,
        "province": student.province,
        "subjects": student.subjects or [],
        "preferred_language": student.preferred_language,
        "daily_goal_minutes": student.daily_goal_minutes,
        "total_xp": student.total_xp,
        "level": student.level,
        "subscription_tier": user.subscription_tier.value if hasattr(user.subscription_tier, 'value') else user.subscription_tier,
        "subscription_expires_at": user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_active": user.last_active.isoformat() if user.last_active else None,
        "statistics": {
            "current_streak": streak.current_streak if streak else 0,
            "longest_streak": streak.longest_streak if streak else 0,
            "total_active_days": streak.total_active_days if streak else 0,
            "total_sessions": total_sessions,
            "total_questions": total_questions,
            "correct_answers": correct_answers,
            "accuracy": round((correct_answers / total_questions * 100) if total_questions > 0 else 0, 1),
            "total_study_hours": total_study_hours,
            "achievements_count": achievements_count,
            "conversations_count": conversations_count
        },
        "analytics": analytics
    }


@router.get("/students/{student_id}/analytics")
async def get_student_analytics(
    student_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive analytics for a specific student"""
    from app.services.analytics.student_progress import StudentProgressAnalytics
    analytics = StudentProgressAnalytics(db)
    return await analytics.get_comprehensive_analytics(student_id)


@router.get("/students/{student_id}/sessions")
async def get_student_sessions(
    student_id: UUID,
    limit: int = Query(50, ge=10, le=200),
    offset: int = Query(0, ge=0),
    session_type: Optional[str] = None,
    status: Optional[str] = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get practice session history for a student with full details.

    Returns sessions with:
    - Session type and status
    - Subject and topic names
    - Performance metrics (questions, accuracy, XP)
    - Time spent
    """
    from sqlalchemy import select, func
    from sqlalchemy.orm import selectinload
    from app.models.practice import PracticeSession
    from app.models.curriculum import Subject, Topic

    # Build query with subject and topic joins
    query = (
        select(PracticeSession, Subject, Topic)
        .outerjoin(Subject, PracticeSession.subject_id == Subject.id)
        .outerjoin(Topic, PracticeSession.topic_id == Topic.id)
        .where(PracticeSession.student_id == student_id)
    )

    if session_type:
        query = query.where(PracticeSession.session_type == session_type)
    if status:
        query = query.where(PracticeSession.status == status)

    # Get total count
    count_query = (
        select(func.count(PracticeSession.id))
        .where(PracticeSession.student_id == student_id)
    )
    if session_type:
        count_query = count_query.where(PracticeSession.session_type == session_type)
    if status:
        count_query = count_query.where(PracticeSession.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply ordering and pagination
    query = query.order_by(PracticeSession.started_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    sessions = []
    for session, subject, topic in rows:
        # Calculate duration if session has ended
        duration_minutes = None
        if session.ended_at and session.started_at:
            duration_seconds = (session.ended_at - session.started_at).total_seconds()
            duration_minutes = round(duration_seconds / 60, 1)

        sessions.append({
            "id": str(session.id),
            "session_type": session.session_type,
            "subject_id": str(session.subject_id) if session.subject_id else None,
            "subject_name": subject.name if subject else None,
            "topic_id": str(session.topic_id) if session.topic_id else None,
            "topic_name": topic.name if topic else None,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "duration_minutes": duration_minutes,
            "total_questions": session.total_questions or 0,
            "correct_answers": session.correct_answers or 0,
            "score_percentage": float(session.score_percentage) if session.score_percentage else None,
            "total_marks_earned": float(session.total_marks_earned) if session.total_marks_earned else None,
            "total_marks_possible": float(session.total_marks_possible) if session.total_marks_possible else None,
            "time_spent_seconds": session.time_spent_seconds or 0,
            "difficulty_level": session.difficulty_level,
            "xp_earned": session.xp_earned or 0,
            "status": session.status
        })

    return {
        "sessions": sessions,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/students/stats/overview")
async def get_students_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get overview statistics for all students.

    Returns:
    - Total students count
    - Active today count
    - Premium students count
    - New students this week
    - Students by education level
    - Students by subscription tier
    """
    from sqlalchemy import select, func
    from app.models.user import User as UserModel, Student
    from datetime import datetime, timedelta

    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)

    # Total students
    total_result = await db.execute(
        select(func.count(Student.id))
    )
    total_students = total_result.scalar() or 0

    # Active today (students who were active today)
    active_today_result = await db.execute(
        select(func.count(Student.id))
        .join(UserModel, Student.user_id == UserModel.id)
        .where(func.date(UserModel.last_active) == today)
    )
    active_today = active_today_result.scalar() or 0

    # Premium students (basic, premium, family, school tiers)
    premium_result = await db.execute(
        select(func.count(Student.id))
        .join(UserModel, Student.user_id == UserModel.id)
        .where(UserModel.subscription_tier != "free")
    )
    premium_students = premium_result.scalar() or 0

    # New this week
    new_result = await db.execute(
        select(func.count(Student.id))
        .join(UserModel, Student.user_id == UserModel.id)
        .where(func.date(UserModel.created_at) >= week_ago)
    )
    new_this_week = new_result.scalar() or 0

    # By education level
    by_level_result = await db.execute(
        select(Student.education_level, func.count(Student.id))
        .group_by(Student.education_level)
    )
    by_education_level = {row[0]: row[1] for row in by_level_result.all()}

    # By subscription tier
    by_tier_result = await db.execute(
        select(UserModel.subscription_tier, func.count(Student.id))
        .join(Student, Student.user_id == UserModel.id)
        .group_by(UserModel.subscription_tier)
    )
    by_subscription = {
        (row[0].value if hasattr(row[0], 'value') else row[0]): row[1]
        for row in by_tier_result.all()
    }

    return {
        "total_students": total_students,
        "active_today": active_today,
        "premium_students": premium_students,
        "new_this_week": new_this_week,
        "by_education_level": by_education_level,
        "by_subscription_tier": by_subscription
    }


@router.get("/students/{student_id}/activity")
async def get_student_activity(
    student_id: UUID,
    limit: int = Query(20, ge=5, le=100),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent activity feed for a student.

    Returns a timeline of activities including:
    - Practice sessions started/completed
    - Achievements earned
    - Competition participations
    - Streak milestones
    """
    from sqlalchemy import select, union_all, literal
    from app.models.practice import PracticeSession
    from app.models.gamification import StudentAchievement, Achievement, CompetitionParticipant, Competition

    activities = []

    # Get recent sessions
    sessions_result = await db.execute(
        select(PracticeSession)
        .where(PracticeSession.student_id == student_id)
        .order_by(PracticeSession.started_at.desc())
        .limit(limit)
    )
    for session in sessions_result.scalars().all():
        if session.status == "completed":
            activities.append({
                "id": str(session.id),
                "type": "session_completed",
                "icon": "check_circle",
                "title": f"Completed {session.session_type.replace('_', ' ').title()} Session",
                "description": f"Answered {session.total_questions} questions with {session.correct_answers} correct ({round((session.correct_answers/session.total_questions*100) if session.total_questions else 0)}% accuracy). Earned {session.xp_earned} XP.",
                "timestamp": session.ended_at.isoformat() if session.ended_at else session.started_at.isoformat(),
                "metadata": {
                    "session_type": session.session_type,
                    "xp_earned": session.xp_earned,
                    "score": float(session.score_percentage) if session.score_percentage else None
                }
            })
        else:
            activities.append({
                "id": str(session.id),
                "type": "session_started",
                "icon": "play_circle",
                "title": f"Started {session.session_type.replace('_', ' ').title()} Session",
                "description": f"Session in progress" if session.status == "in_progress" else "Session abandoned",
                "timestamp": session.started_at.isoformat(),
                "metadata": {"session_type": session.session_type, "status": session.status}
            })

    # Get achievements
    achievements_result = await db.execute(
        select(StudentAchievement, Achievement)
        .join(Achievement, StudentAchievement.achievement_id == Achievement.id)
        .where(StudentAchievement.student_id == student_id)
        .order_by(StudentAchievement.earned_at.desc())
        .limit(limit)
    )
    for student_ach, achievement in achievements_result.all():
        activities.append({
            "id": str(student_ach.id),
            "type": "achievement",
            "icon": "emoji_events",
            "title": f"Earned Achievement: {achievement.name}",
            "description": achievement.description or "Achievement unlocked!",
            "timestamp": student_ach.earned_at.isoformat(),
            "metadata": {
                "achievement_name": achievement.name,
                "xp_reward": achievement.xp_reward
            }
        })

    # Get competition participations
    competitions_result = await db.execute(
        select(CompetitionParticipant, Competition)
        .join(Competition, CompetitionParticipant.competition_id == Competition.id)
        .where(CompetitionParticipant.student_id == student_id)
        .order_by(CompetitionParticipant.joined_at.desc())
        .limit(limit)
    )
    for participant, competition in competitions_result.all():
        if participant.status == "completed":
            activities.append({
                "id": str(participant.id),
                "type": "competition_completed",
                "icon": "leaderboard",
                "title": f"Completed Competition: {competition.name}",
                "description": f"Ranked #{participant.rank}" if participant.rank else "Participation completed",
                "timestamp": participant.completed_at.isoformat() if participant.completed_at else participant.joined_at.isoformat(),
                "metadata": {
                    "competition_name": competition.name,
                    "rank": participant.rank,
                    "score": float(participant.score) if participant.score else None
                }
            })
        else:
            activities.append({
                "id": str(participant.id),
                "type": "competition_joined",
                "icon": "flag",
                "title": f"Joined Competition: {competition.name}",
                "description": "Registered for competition",
                "timestamp": participant.joined_at.isoformat(),
                "metadata": {"competition_name": competition.name}
            })

    # Sort all activities by timestamp
    activities.sort(key=lambda x: x["timestamp"], reverse=True)

    return {
        "activities": activities[:limit],
        "total": len(activities)
    }


@router.get("/students/{student_id}/report")
async def generate_student_report(
    student_id: UUID,
    report_type: str = "comprehensive",
    format: str = "json",
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Generate downloadable student report"""
    from app.services.analytics.student_progress import StudentProgressAnalytics
    analytics = StudentProgressAnalytics(db)
    data = await analytics.get_comprehensive_analytics(student_id)

    if format == "json":
        return data
    # PDF generation would be implemented here
    return {"data": data, "format": format}

