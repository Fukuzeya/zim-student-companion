# ============================================================================
# Admin Notification Service
# ============================================================================
"""
Service layer for notification and broadcast management.
Handles system notifications, broadcast messages, and WhatsApp template management.
"""
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from enum import Enum
from dataclasses import dataclass, field
import logging
import asyncio

from app.models.user import User, Student, SubscriptionTier, UserRole

logger = logging.getLogger(__name__)


# ============================================================================
# Notification Models (In-memory for now - use DB/Redis in production)
# ============================================================================
class NotificationType(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ALERT = "alert"
    PROMOTION = "promotion"
    SYSTEM = "system"

class NotificationChannel(str, Enum):
    IN_APP = "in_app"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    PUSH = "push"

class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    SCHEDULED = "scheduled"

@dataclass
class Notification:
    id: UUID
    title: str
    message: str
    type: NotificationType
    channels: List[NotificationChannel]
    target_segment: Optional[Dict[str, Any]]
    status: NotificationStatus
    created_by: UUID
    created_at: datetime
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    recipient_count: int = 0
    delivered_count: int = 0
    failed_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WhatsAppTemplate:
    id: UUID
    name: str
    category: str
    language: str
    status: str  # approved, pending, rejected
    content: str
    variables: List[str]
    created_at: datetime
    last_used: Optional[datetime] = None
    usage_count: int = 0


class NotificationService:
    """
    Notification and broadcast management service.
    
    Provides:
    - Broadcast message creation and sending
    - Segment targeting for notifications
    - Notification scheduling
    - WhatsApp template management
    - Delivery tracking and analytics
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        # In-memory storage (use Redis/DB in production)
        self._notifications: Dict[UUID, Notification] = {}
        self._whatsapp_templates: Dict[UUID, WhatsAppTemplate] = {}
        self._init_sample_templates()
    
    def _init_sample_templates(self):
        """Initialize sample WhatsApp templates"""
        templates = [
            WhatsAppTemplate(
                id=uuid4(),
                name="welcome_message",
                category="UTILITY",
                language="en",
                status="approved",
                content="Welcome to EduBot, {{1}}! 🎓 Start your learning journey today.",
                variables=["student_name"],
                created_at=datetime.utcnow() - timedelta(days=30),
                usage_count=150
            ),
            WhatsAppTemplate(
                id=uuid4(),
                name="daily_reminder",
                category="UTILITY",
                language="en",
                status="approved",
                content="Hi {{1}}! Don't forget to practice today. Your streak: {{2}} days 🔥",
                variables=["student_name", "streak_count"],
                created_at=datetime.utcnow() - timedelta(days=20),
                usage_count=500
            ),
            WhatsAppTemplate(
                id=uuid4(),
                name="competition_invite",
                category="MARKETING",
                language="en",
                status="approved",
                content="📣 {{1}} competition starts {{2}}! Join now and win prizes. Reply START to register.",
                variables=["competition_name", "start_date"],
                created_at=datetime.utcnow() - timedelta(days=10),
                usage_count=75
            ),
            WhatsAppTemplate(
                id=uuid4(),
                name="subscription_expiry",
                category="UTILITY",
                language="en",
                status="approved",
                content="Hi {{1}}, your {{2}} subscription expires in {{3}} days. Renew now to continue learning!",
                variables=["student_name", "plan_name", "days_remaining"],
                created_at=datetime.utcnow() - timedelta(days=15),
                usage_count=200
            ),
        ]
        for template in templates:
            self._whatsapp_templates[template.id] = template
    
    # =========================================================================
    # Broadcast Notifications
    # =========================================================================
    async def create_broadcast(
        self,
        title: str,
        message: str,
        notification_type: str,
        channels: List[str],
        created_by: UUID,
        target_segment: Optional[Dict[str, Any]] = None,
        schedule_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Create a broadcast notification.
        
        Args:
            title: Notification title
            message: Notification message
            notification_type: Type (info, warning, alert, promotion, system)
            channels: List of channels (in_app, whatsapp, email, push)
            created_by: Admin UUID
            target_segment: Targeting criteria for recipients
            schedule_at: Optional scheduled send time
            
        Returns:
            Created notification details
        """
        notification_id = uuid4()
        
        # Calculate recipient count based on segment
        recipient_count = await self._calculate_recipients(target_segment)
        
        notification = Notification(
            id=notification_id,
            title=title,
            message=message,
            type=NotificationType(notification_type),
            channels=[NotificationChannel(c) for c in channels],
            target_segment=target_segment,
            status=NotificationStatus.SCHEDULED if schedule_at else NotificationStatus.PENDING,
            created_by=created_by,
            created_at=datetime.utcnow(),
            scheduled_at=schedule_at,
            recipient_count=recipient_count
        )
        
        self._notifications[notification_id] = notification
        
        logger.info(
            f"Broadcast created: {notification_id} - '{title}' "
            f"targeting {recipient_count} recipients"
        )
        
        # If not scheduled, send immediately
        if not schedule_at:
            asyncio.create_task(self._send_notification(notification_id))
        
        return {
            "notification_id": str(notification_id),
            "title": title,
            "recipient_count": recipient_count,
            "status": notification.status.value,
            "scheduled_at": schedule_at.isoformat() if schedule_at else None,
            "message": "Broadcast created successfully"
        }
    
    async def _calculate_recipients(self, segment: Optional[Dict[str, Any]] = None) -> int:
        """Calculate number of recipients based on segment criteria"""
        query = select(func.count(User.id)).where(User.is_active == True)
        
        if segment:
            if segment.get("role"):
                query = query.where(User.role == UserRole(segment["role"]))
            
            if segment.get("subscription_tier"):
                query = query.where(User.subscription_tier == SubscriptionTier(segment["subscription_tier"]))
            
            if segment.get("education_level"):
                query = query.join(Student, User.id == Student.user_id)
                query = query.where(Student.education_level == segment["education_level"])
            
            if segment.get("grade"):
                if Student not in str(query):
                    query = query.join(Student, User.id == Student.user_id)
                query = query.where(Student.grade == segment["grade"])
            
            if segment.get("province"):
                if Student not in str(query):
                    query = query.join(Student, User.id == Student.user_id)
                query = query.where(Student.province == segment["province"])
        
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def _send_notification(self, notification_id: UUID) -> None:
        """
        Background task to send notification to all recipients.
        
        In production, this would integrate with:
        - WhatsApp Business API
        - Email service (SendGrid, SES, etc.)
        - Push notification service (FCM, APNs)
        """
        notification = self._notifications.get(notification_id)
        if not notification:
            return
        
        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.utcnow()
        
        # Get recipients based on segment
        recipients = await self._get_recipients(notification.target_segment)
        
        delivered = 0
        failed = 0
        
        for recipient in recipients:
            try:
                # In production, send via appropriate channels
                for channel in notification.channels:
                    if channel == NotificationChannel.WHATSAPP:
                        # await self._send_whatsapp(recipient, notification)
                        pass
                    elif channel == NotificationChannel.EMAIL:
                        # await self._send_email(recipient, notification)
                        pass
                    elif channel == NotificationChannel.IN_APP:
                        # Store in user's notification inbox
                        pass
                
                delivered += 1
            except Exception as e:
                logger.error(f"Failed to send to {recipient}: {e}")
                failed += 1
        
        notification.delivered_count = delivered
        notification.failed_count = failed
        notification.status = NotificationStatus.DELIVERED
        
        logger.info(
            f"Broadcast {notification_id} completed: "
            f"{delivered} delivered, {failed} failed"
        )
    
    async def _get_recipients(self, segment: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get list of recipients based on segment"""
        query = select(User).where(User.is_active == True)
        
        if segment:
            if segment.get("role"):
                query = query.where(User.role == UserRole(segment["role"]))
            if segment.get("subscription_tier"):
                query = query.where(User.subscription_tier == SubscriptionTier(segment["subscription_tier"]))
        
        result = await self.db.execute(query.limit(10000))  # Limit for safety
        users = result.scalars().all()
        
        return [
            {"id": str(u.id), "phone": u.phone_number, "email": u.email}
            for u in users
        ]
    
    # =========================================================================
    # Notification Listing
    # =========================================================================
    async def list_notifications(
        self,
        status: Optional[str] = None,
        notification_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """List broadcast notifications with filtering"""
        notifications = list(self._notifications.values())
        
        if status:
            notifications = [n for n in notifications if n.status.value == status]
        
        if notification_type:
            notifications = [n for n in notifications if n.type.value == notification_type]
        
        # Sort by created_at descending
        notifications.sort(key=lambda x: x.created_at, reverse=True)
        
        total = len(notifications)
        notifications = notifications[offset:offset + limit]
        
        return {
            "notifications": [
                {
                    "id": str(n.id),
                    "title": n.title,
                    "message": n.message[:100] + "..." if len(n.message) > 100 else n.message,
                    "type": n.type.value,
                    "channels": [c.value for c in n.channels],
                    "status": n.status.value,
                    "recipient_count": n.recipient_count,
                    "delivered_count": n.delivered_count,
                    "failed_count": n.failed_count,
                    "created_at": n.created_at.isoformat(),
                    "scheduled_at": n.scheduled_at.isoformat() if n.scheduled_at else None,
                    "sent_at": n.sent_at.isoformat() if n.sent_at else None
                }
                for n in notifications
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }
    
    async def get_notification_detail(self, notification_id: UUID) -> Optional[Dict[str, Any]]:
        """Get detailed notification information"""
        notification = self._notifications.get(notification_id)
        if not notification:
            return None
        
        return {
            "id": str(notification.id),
            "title": notification.title,
            "message": notification.message,
            "type": notification.type.value,
            "channels": [c.value for c in notification.channels],
            "target_segment": notification.target_segment,
            "status": notification.status.value,
            "recipient_count": notification.recipient_count,
            "delivered_count": notification.delivered_count,
            "failed_count": notification.failed_count,
            "created_by": str(notification.created_by),
            "created_at": notification.created_at.isoformat(),
            "scheduled_at": notification.scheduled_at.isoformat() if notification.scheduled_at else None,
            "sent_at": notification.sent_at.isoformat() if notification.sent_at else None,
            "metadata": notification.metadata
        }
    
    async def cancel_notification(self, notification_id: UUID) -> Dict[str, Any]:
        """Cancel a scheduled notification"""
        notification = self._notifications.get(notification_id)
        if not notification:
            return {"success": False, "error": "Notification not found"}
        
        if notification.status not in [NotificationStatus.PENDING, NotificationStatus.SCHEDULED]:
            return {"success": False, "error": "Can only cancel pending or scheduled notifications"}
        
        del self._notifications[notification_id]
        
        return {"success": True, "message": "Notification cancelled"}
    
    # =========================================================================
    # WhatsApp Templates
    # =========================================================================
    async def list_whatsapp_templates(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List WhatsApp message templates"""
        templates = list(self._whatsapp_templates.values())
        
        if status:
            templates = [t for t in templates if t.status == status]
        
        if category:
            templates = [t for t in templates if t.category == category]
        
        templates.sort(key=lambda x: x.usage_count, reverse=True)
        
        return [
            {
                "id": str(t.id),
                "name": t.name,
                "category": t.category,
                "language": t.language,
                "status": t.status,
                "content": t.content,
                "variables": t.variables,
                "created_at": t.created_at.isoformat(),
                "last_used": t.last_used.isoformat() if t.last_used else None,
                "usage_count": t.usage_count
            }
            for t in templates
        ]
    
    async def create_whatsapp_template(
        self,
        name: str,
        category: str,
        language: str,
        content: str,
        variables: List[str]
    ) -> Dict[str, Any]:
        """
        Create a new WhatsApp template.
        
        Note: In production, this would submit to WhatsApp Business API for approval.
        """
        template_id = uuid4()
        
        template = WhatsAppTemplate(
            id=template_id,
            name=name,
            category=category,
            language=language,
            status="pending",  # Requires WhatsApp approval
            content=content,
            variables=variables,
            created_at=datetime.utcnow()
        )
        
        self._whatsapp_templates[template_id] = template
        
        logger.info(f"WhatsApp template created: {name} (pending approval)")
        
        return {
            "id": str(template_id),
            "name": name,
            "status": "pending",
            "message": "Template created and submitted for approval"
        }
    
    async def get_template_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for WhatsApp templates"""
        templates = list(self._whatsapp_templates.values())
        
        total_usage = sum(t.usage_count for t in templates)
        by_category = {}
        by_status = {}
        
        for template in templates:
            by_category[template.category] = by_category.get(template.category, 0) + template.usage_count
            by_status[template.status] = by_status.get(template.status, 0) + 1
        
        return {
            "total_templates": len(templates),
            "total_usage": total_usage,
            "usage_by_category": by_category,
            "count_by_status": by_status,
            "most_used": [
                {"name": t.name, "usage": t.usage_count}
                for t in sorted(templates, key=lambda x: x.usage_count, reverse=True)[:5]
            ]
        }
    
    # =========================================================================
    # Segment Management
    # =========================================================================
    async def preview_segment(self, segment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preview how many users match a segment criteria.
        
        Used before sending broadcasts to verify targeting.
        """
        count = await self._calculate_recipients(segment)
        
        # Get sample of matching users
        query = select(User).where(User.is_active == True)
        
        if segment.get("role"):
            query = query.where(User.role == UserRole(segment["role"]))
        if segment.get("subscription_tier"):
            query = query.where(User.subscription_tier == SubscriptionTier(segment["subscription_tier"]))
        
        result = await self.db.execute(query.limit(5))
        sample_users = result.scalars().all()
        
        return {
            "matching_count": count,
            "segment_criteria": segment,
            "sample_users": [
                {
                    "id": str(u.id),
                    "phone": u.phone_number[:4] + "****" + u.phone_number[-2:],
                    "role": u.role.value,
                    "tier": u.subscription_tier.value
                }
                for u in sample_users
            ]
        }