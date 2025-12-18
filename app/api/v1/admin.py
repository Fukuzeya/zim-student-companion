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
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=100),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all students with filtering"""
    service = UserManagementService(db)
    filters = {
        "role": "student",
        "education_level": education_level,
        "school": school
    }
    filters = {k: v for k, v in filters.items() if v is not None}
    return await service.list_users(filters=filters, page=page, page_size=page_size)


@router.get("/students/{student_id}")
async def get_student_detail(
    student_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed student profile"""
    # Use analytics service for comprehensive student data
    from app.services.analytics.student_progress import StudentProgressAnalytics
    analytics = StudentProgressAnalytics(db)
    return await analytics.get_comprehensive_analytics(student_id)


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
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get practice session history for a student"""
    from sqlalchemy import select
    from app.models.practice import PracticeSession
    
    result = await db.execute(
        select(PracticeSession)
        .where(PracticeSession.student_id == student_id)
        .order_by(PracticeSession.started_at.desc())
        .limit(limit)
    )
    sessions = result.scalars().all()
    
    return {
        "sessions": [
            {
                "id": str(s.id),
                "session_type": s.session_type,
                "started_at": s.started_at.isoformat(),
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                "total_questions": s.total_questions,
                "correct_answers": s.correct_answers,
                "score_percentage": float(s.score_percentage) if s.score_percentage else None,
                "xp_earned": s.xp_earned,
                "status": s.status
            }
            for s in sessions
        ]
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

