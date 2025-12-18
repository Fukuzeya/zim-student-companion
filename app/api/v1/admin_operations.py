# ============================================================================
# Admin API Endpoints - Part 3: Competitions, Payments, Analytics, System
# ============================================================================
"""
Competition management, payment processing, analytics, notifications, and system endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Form, WebSocket
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID
from decimal import Decimal
import io
import json

from app.core.database import get_db
from app.models.user import User
from app.api.v1.administration import require_admin
from app.services.admin.competition_service import CompetitionManagementService
from app.services.admin.payment_service import PaymentManagementService
from app.services.admin.analytics_service import AnalyticsService
from app.services.admin.notification_service import NotificationService
from app.services.admin.system_service import SystemService, AuditAction

router = APIRouter(prefix="/admin", tags=["admin-operations"])


# ============================================================================
# Competition Management Endpoints
# ============================================================================
@router.get("/competitions")
async def list_competitions(
    status: Optional[str] = None,
    subject_id: Optional[UUID] = None,
    education_level: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=10, le=50),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    List competitions with filtering.
    
    Status options: upcoming, active, completed, cancelled
    """
    service = CompetitionManagementService(db)
    return await service.list_competitions(
        status=status,
        subject_id=subject_id,
        education_level=education_level,
        page=page,
        page_size=page_size
    )


@router.post("/competitions")
async def create_competition(
    name: str = Form(...),
    start_date: datetime = Form(...),
    end_date: datetime = Form(...),
    description: Optional[str] = Form(None),
    subject_id: Optional[UUID] = Form(None),
    education_level: Optional[str] = Form(None),
    grade: Optional[str] = Form(None),
    competition_type: str = Form("individual"),
    max_participants: Optional[int] = Form(None),
    entry_fee: float = Form(0),
    prizes: Optional[str] = Form(None),  # JSON string
    rules: Optional[str] = Form(None),  # JSON string
    num_questions: int = Form(10),
    time_limit_minutes: int = Form(30),
    difficulty: str = Form("medium"),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create a new competition"""
    service = CompetitionManagementService(db)
    data = {
        "name": name,
        "description": description,
        "subject_id": subject_id,
        "education_level": education_level,
        "grade": grade,
        "competition_type": competition_type,
        "start_date": start_date,
        "end_date": end_date,
        "max_participants": max_participants,
        "entry_fee": entry_fee,
        "prizes": json.loads(prizes) if prizes else None,
        "rules": json.loads(rules) if rules else None,
        "num_questions": num_questions,
        "time_limit_minutes": time_limit_minutes,
        "difficulty": difficulty
    }
    return await service.create_competition(data, admin.id)


@router.get("/competitions/{competition_id}")
async def get_competition_detail(
    competition_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed competition information"""
    service = CompetitionManagementService(db)
    result = await service.get_competition_detail(competition_id)
    if not result:
        raise HTTPException(status_code=404, detail="Competition not found")
    return result


@router.put("/competitions/{competition_id}")
async def update_competition(
    competition_id: UUID,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    start_date: Optional[datetime] = Form(None),
    end_date: Optional[datetime] = Form(None),
    max_participants: Optional[int] = Form(None),
    prizes: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update competition details"""
    service = CompetitionManagementService(db)
    updates = {k: v for k, v in {
        "name": name,
        "description": description,
        "start_date": start_date,
        "end_date": end_date,
        "max_participants": max_participants,
        "prizes": json.loads(prizes) if prizes else None,
        "status": status
    }.items() if v is not None}
    
    result = await service.update_competition(competition_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="Competition not found")
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/competitions/{competition_id}")
async def delete_competition(
    competition_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete or cancel a competition"""
    service = CompetitionManagementService(db)
    return await service.delete_competition(competition_id)


@router.get("/competitions/{competition_id}/leaderboard")
async def get_competition_leaderboard(
    competition_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=100),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get competition leaderboard"""
    service = CompetitionManagementService(db)
    return await service.get_leaderboard(
        competition_id=competition_id,
        page=page,
        page_size=page_size
    )


@router.get("/competitions/{competition_id}/live")
async def get_live_competition_data(
    competition_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get real-time competition monitoring data.
    
    Includes:
    - Live leaderboard
    - Participant progress
    - Anomaly detection
    """
    service = CompetitionManagementService(db)
    result = await service.get_live_competition_data(competition_id)
    if not result:
        raise HTTPException(status_code=404, detail="Competition not found")
    return result


@router.post("/competitions/{competition_id}/finalize")
async def finalize_competition(
    competition_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Finalize competition results and distribute prizes"""
    service = CompetitionManagementService(db)
    return await service.finalize_competition(competition_id)


@router.post("/competitions/{competition_id}/disqualify/{student_id}")
async def disqualify_participant(
    competition_id: UUID,
    student_id: UUID,
    reason: str = Form(...),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Disqualify a participant from competition"""
    service = CompetitionManagementService(db)
    return await service.disqualify_participant(
        competition_id=competition_id,
        student_id=student_id,
        reason=reason,
        admin_id=admin.id
    )


@router.get("/competitions/{competition_id}/export")
async def export_competition_results(
    competition_id: UUID,
    format: str = Query("csv", regex="^(csv|json)$"),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Export competition results"""
    service = CompetitionManagementService(db)
    result = await service.export_results(competition_id, format)
    
    if format == "csv":
        return StreamingResponse(
            io.StringIO(result["data"]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={result['filename']}"}
        )
    return result


# ============================================================================
# Payment Management Endpoints
# ============================================================================
@router.get("/payments")
async def list_payments(
    status: Optional[str] = None,
    payment_method: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    user_id: Optional[UUID] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=100),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List payments with comprehensive filtering"""
    service = PaymentManagementService(db)
    return await service.list_payments(
        status=status,
        payment_method=payment_method,
        date_from=date_from,
        date_to=date_to,
        min_amount=Decimal(str(min_amount)) if min_amount else None,
        max_amount=Decimal(str(max_amount)) if max_amount else None,
        user_id=user_id,
        page=page,
        page_size=page_size
    )


@router.get("/payments/stats")
async def get_payment_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get payment statistics.
    
    Returns:
    - MRR, ARR
    - Churn rate, LTV
    - Revenue by plan
    - Payment method breakdown
    """
    service = PaymentManagementService(db)
    return await service.get_payment_stats()


@router.get("/payments/{payment_id}")
async def get_payment_detail(
    payment_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed payment information"""
    service = PaymentManagementService(db)
    result = await service.get_payment_detail(payment_id)
    if not result:
        raise HTTPException(status_code=404, detail="Payment not found")
    return result


@router.post("/payments/{payment_id}/refund")
async def process_refund(
    payment_id: UUID,
    reason: str = Form(...),
    partial_amount: Optional[float] = Form(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Process a refund for a payment.
    
    Leave partial_amount empty for full refund.
    """
    service = PaymentManagementService(db)
    result = await service.process_refund(
        payment_id=payment_id,
        reason=reason,
        partial_amount=Decimal(str(partial_amount)) if partial_amount else None,
        admin_id=admin.id
    )
    
    if result.get("success"):
        # Log the refund
        system_service = SystemService(db)
        await system_service.log_action(
            admin_id=admin.id,
            admin_email=admin.email or "",
            action=AuditAction.REFUND,
            resource_type="payment",
            resource_id=payment_id,
            details={"reason": reason, "amount": partial_amount}
        )
    
    return result


# ============================================================================
# Subscription Plan Endpoints
# ============================================================================
@router.get("/subscriptions")
async def list_subscriptions(
    tier: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=100),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List user subscriptions"""
    service = PaymentManagementService(db)
    return await service.list_subscriptions(
        tier=tier,
        status=status,
        page=page,
        page_size=page_size
    )


@router.get("/plans")
async def list_plans(
    include_inactive: bool = False,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all subscription plans"""
    service = PaymentManagementService(db)
    return await service.list_plans(include_inactive=include_inactive)


@router.post("/plans")
async def create_plan(
    name: str = Form(...),
    tier: str = Form(...),
    price_usd: float = Form(...),
    duration_days: int = Form(...),
    description: Optional[str] = Form(None),
    price_zwl: Optional[float] = Form(None),
    features: str = Form("[]"),  # JSON array
    limits: str = Form("{}"),  # JSON object
    max_students: int = Form(1),
    discount_percentage: int = Form(0),
    is_popular: bool = Form(False),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create a new subscription plan"""
    service = PaymentManagementService(db)
    data = {
        "name": name,
        "tier": tier,
        "description": description,
        "price_usd": price_usd,
        "price_zwl": price_zwl,
        "duration_days": duration_days,
        "features": json.loads(features),
        "limits": json.loads(limits),
        "max_students": max_students,
        "discount_percentage": discount_percentage,
        "is_popular": is_popular
    }
    return await service.create_plan(data)


@router.put("/plans/{plan_id}")
async def update_plan(
    plan_id: UUID,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    price_usd: Optional[float] = Form(None),
    features: Optional[str] = Form(None),
    is_active: Optional[bool] = Form(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update a subscription plan"""
    service = PaymentManagementService(db)
    updates = {k: v for k, v in {
        "name": name,
        "description": description,
        "price_usd": price_usd,
        "features": json.loads(features) if features else None,
        "is_active": is_active
    }.items() if v is not None}
    
    result = await service.update_plan(plan_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="Plan not found")
    return result


@router.post("/subscriptions/{user_id}/modify")
async def modify_subscription(
    user_id: UUID,
    new_tier: str = Form(...),
    expires_at: Optional[datetime] = Form(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Manually modify a user's subscription"""
    service = PaymentManagementService(db)
    return await service.modify_subscription(
        user_id=user_id,
        new_tier=new_tier,
        expires_at=expires_at,
        admin_id=admin.id
    )


# ============================================================================
# Analytics Endpoints
# ============================================================================
@router.get("/analytics/engagement")
async def get_engagement_analytics(
    time_range: str = Query("last_30_days"),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get engagement analytics.
    
    Returns DAU/WAU/MAU, retention cohorts, feature usage, funnel data.
    """
    service = AnalyticsService(db)
    return await service.get_engagement_analytics(
        time_range=time_range,
        date_from=date_from,
        date_to=date_to
    )


@router.get("/analytics/learning")
async def get_learning_analytics(
    time_range: str = Query("last_30_days"),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    subject_id: Optional[UUID] = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get learning analytics.
    
    Returns question stats, accuracy trends, time distribution, difficulty analysis.
    """
    service = AnalyticsService(db)
    return await service.get_learning_analytics(
        time_range=time_range,
        date_from=date_from,
        date_to=date_to,
        subject_id=subject_id
    )


@router.get("/analytics/revenue")
async def get_revenue_analytics(
    time_range: str = Query("last_30_days"),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get revenue analytics.
    
    Returns MRR/ARR, churn, LTV, revenue trends and breakdowns.
    """
    service = AnalyticsService(db)
    return await service.get_revenue_analytics(
        time_range=time_range,
        date_from=date_from,
        date_to=date_to
    )


@router.post("/analytics/custom")
async def generate_custom_analytics(
    metrics: List[str] = Form(...),
    dimensions: List[str] = Form([]),
    time_range: str = Form("last_30_days"),
    date_from: Optional[date] = Form(None),
    date_to: Optional[date] = Form(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate custom analytics report.
    
    Available metrics: total_users, active_users, total_revenue,
                      questions_answered, average_accuracy, new_signups
    
    Available dimensions: by_subject, by_grade, by_subscription, by_province
    """
    service = AnalyticsService(db)
    return await service.generate_custom_report(
        metrics=metrics,
        dimensions=dimensions,
        time_range=time_range,
        date_from=date_from,
        date_to=date_to
    )


@router.post("/reports/generate")
async def generate_report(
    report_type: str = Form(...),
    format: str = Form("pdf"),
    time_range: str = Form("last_30_days"),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Generate downloadable report"""
    # Would generate PDF/Excel reports
    return {
        "message": "Report generation started",
        "report_type": report_type,
        "format": format,
        "status": "processing"
    }


# ============================================================================
# Notification Endpoints
# ============================================================================
@router.get("/notifications")
async def list_notifications(
    status: Optional[str] = None,
    notification_type: Optional[str] = None,
    limit: int = Query(50, ge=10, le=200),
    offset: int = Query(0, ge=0),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List broadcast notifications"""
    service = NotificationService(db)
    return await service.list_notifications(
        status=status,
        notification_type=notification_type,
        limit=limit,
        offset=offset
    )


@router.post("/notifications/broadcast")
async def create_broadcast(
    title: str = Form(...),
    message: str = Form(...),
    notification_type: str = Form("info"),
    channels: str = Form("in_app"),  # Comma-separated
    target_segment: Optional[str] = Form(None),  # JSON
    schedule_at: Optional[datetime] = Form(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create and send broadcast notification.
    
    Channels: in_app, whatsapp, email, push
    
    Target segment example:
    {"role": "student", "subscription_tier": "premium", "grade": "Form 4"}
    """
    service = NotificationService(db)
    
    result = await service.create_broadcast(
        title=title,
        message=message,
        notification_type=notification_type,
        channels=channels.split(","),
        created_by=admin.id,
        target_segment=json.loads(target_segment) if target_segment else None,
        schedule_at=schedule_at
    )
    
    # Log the broadcast
    system_service = SystemService(db)
    await system_service.log_action(
        admin_id=admin.id,
        admin_email=admin.email or "",
        action=AuditAction.BROADCAST,
        resource_type="notification",
        resource_id=None,
        details={"title": title, "recipients": result.get("recipient_count", 0)}
    )
    
    return result


@router.post("/notifications/preview-segment")
async def preview_segment(
    segment: str = Form(...),  # JSON
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Preview how many users match a segment"""
    service = NotificationService(db)
    return await service.preview_segment(json.loads(segment))


@router.delete("/notifications/{notification_id}")
async def cancel_notification(
    notification_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a scheduled notification"""
    service = NotificationService(db)
    return await service.cancel_notification(notification_id)


@router.get("/whatsapp/templates")
async def list_whatsapp_templates(
    status: Optional[str] = None,
    category: Optional[str] = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List WhatsApp message templates"""
    service = NotificationService(db)
    return await service.list_whatsapp_templates(status=status, category=category)


@router.get("/whatsapp/templates/stats")
async def get_whatsapp_template_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get WhatsApp template usage statistics"""
    service = NotificationService(db)
    return await service.get_template_usage_stats()


# ============================================================================
# System Settings Endpoints
# ============================================================================
@router.get("/settings")
async def get_settings(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get current system settings"""
    service = SystemService(db)
    return await service.get_settings()


@router.put("/settings")
async def update_settings(
    app_name: Optional[str] = Form(None),
    contact_email: Optional[str] = Form(None),
    contact_phone: Optional[str] = Form(None),
    support_hours: Optional[str] = Form(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update system settings"""
    service = SystemService(db)
    updates = {k: v for k, v in {
        "app_name": app_name,
        "contact_email": contact_email,
        "contact_phone": contact_phone,
        "support_hours": support_hours
    }.items() if v is not None}
    
    return await service.update_settings(updates, admin.id)


@router.post("/settings/feature-flag")
async def toggle_feature_flag(
    flag_name: str = Form(...),
    enabled: bool = Form(...),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Toggle a feature flag"""
    service = SystemService(db)
    return await service.toggle_feature_flag(flag_name, enabled, admin.id)


@router.post("/settings/maintenance")
async def set_maintenance_mode(
    enabled: bool = Form(...),
    message: Optional[str] = Form(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Enable or disable maintenance mode"""
    service = SystemService(db)
    return await service.set_maintenance_mode(enabled, message, admin.id)


# ============================================================================
# Admin User Management Endpoints
# ============================================================================
@router.get("/admins")
async def list_admins(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all admin users"""
    service = SystemService(db)
    return await service.list_admins()


@router.post("/admins")
async def create_admin(
    email: str = Form(...),
    password: str = Form(...),
    phone_number: Optional[str] = Form(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create a new admin user"""
    service = SystemService(db)
    return await service.create_admin(
        email=email,
        password=password,
        phone_number=phone_number,
        created_by=admin.id
    )


@router.put("/admins/{admin_id}")
async def update_admin(
    admin_id: UUID,
    email: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    is_active: Optional[bool] = Form(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update an admin user"""
    service = SystemService(db)
    updates = {k: v for k, v in {
        "email": email,
        "password": password,
        "is_active": is_active
    }.items() if v is not None}
    
    result = await service.update_admin(admin_id, updates, admin.id)
    if not result:
        raise HTTPException(status_code=404, detail="Admin not found")
    return result


@router.delete("/admins/{admin_id}")
async def deactivate_admin(
    admin_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate an admin user"""
    service = SystemService(db)
    return await service.deactivate_admin(admin_id, admin.id)


# ============================================================================
# Audit Log Endpoints
# ============================================================================
@router.get("/audit-log")
async def get_audit_log(
    admin_id: Optional[UUID] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = Query(100, ge=10, le=500),
    offset: int = Query(0, ge=0),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get audit log entries.
    
    Filterable by admin, action type, resource type, and date range.
    """
    service = SystemService(db)
    return await service.get_audit_log(
        admin_id=admin_id,
        action=action,
        resource_type=resource_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset
    )


# ============================================================================
# System Health Endpoints
# ============================================================================
@router.get("/system/health")
async def get_system_health(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive system health status.
    
    Checks database, Redis, external services, and system resources.
    """
    service = SystemService(db)
    return await service.get_system_health()


@router.get("/system/errors")
async def get_error_logs(
    level: str = Query("ERROR"),
    limit: int = Query(100, ge=10, le=500),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get recent error logs"""
    service = SystemService(db)
    return await service.get_error_logs(level=level, limit=limit)