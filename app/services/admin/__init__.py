# ============================================================================
# Admin Services Module
# ============================================================================
"""
Admin services module providing comprehensive administrative functionality.

Services:
- DashboardService: Real-time KPIs, charts, and activity feeds
- UserManagementService: User CRUD, filtering, bulk actions, impersonation
- ContentManagementService: Subjects, topics, questions, curriculum management
- DocumentUploadService: Document upload, processing, and RAG integration
- AnalyticsService: Engagement, learning, revenue, and custom analytics
- PaymentManagementService: Payments, refunds, subscription plans
- CompetitionManagementService: Competition CRUD, live monitoring, results
- NotificationService: Broadcast notifications, WhatsApp templates
- ConversationMonitoringService: Live conversations, intervention, pipeline
- SystemService: Settings, admin users, audit logging, health monitoring
"""

from app.services.admin.dashboard_service import DashboardService
from app.services.admin.user_service import UserManagementService
from app.services.admin.content_service import ContentManagementService
from app.services.admin.document_service import DocumentUploadService
from app.services.admin.analytics_service import AnalyticsService
from app.services.admin.payment_service import PaymentManagementService
from app.services.admin.competition_service import CompetitionManagementService
from app.services.admin.notification_service import NotificationService
from app.services.admin.conversation_service import ConversationMonitoringService
from app.services.admin.system_service import SystemService, AuditAction

__all__ = [
    # Core services
    "DashboardService",
    "UserManagementService",
    "ContentManagementService",
    "DocumentUploadService",
    "AnalyticsService",
    "PaymentManagementService",
    "CompetitionManagementService",
    "NotificationService",
    "ConversationMonitoringService",
    "SystemService",
    # Enums and utilities
    "AuditAction",
]