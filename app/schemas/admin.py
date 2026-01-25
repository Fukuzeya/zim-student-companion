# ============================================================================
# Admin Schemas
# ============================================================================
"""
Pydantic schemas for admin dashboard, analytics, and management operations.
Provides request/response models for all admin API endpoints.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from uuid import UUID
from enum import Enum
from decimal import Decimal


# ============================================================================
# Enums
# ============================================================================
class AdminRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MODERATOR = "moderator"
    SUPPORT = "support"

class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    IMPERSONATE = "impersonate"
    EXPORT = "export"
    REFUND = "refund"
    BROADCAST = "broadcast"

class NotificationType(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ALERT = "alert"
    PROMOTION = "promotion"
    SYSTEM = "system"

class ReportFormat(str, Enum):
    PDF = "pdf"
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"

class TimeRange(str, Enum):
    TODAY = "today"
    YESTERDAY = "yesterday"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"
    THIS_YEAR = "this_year"
    CUSTOM = "custom"


# ============================================================================
# Dashboard Schemas
# ============================================================================
class KPICard(BaseModel):
    """Single KPI metric with trend data"""
    value: Any
    label: str
    change_percent: Optional[float] = None
    change_direction: Optional[str] = None  # up, down, stable
    period: str = "vs last period"

class DashboardStats(BaseModel):
    """Main dashboard statistics"""
    total_users: KPICard
    active_students_today: KPICard
    messages_24h: KPICard
    revenue_this_month: KPICard
    active_subscriptions: KPICard
    conversion_rate: KPICard
    avg_session_duration: KPICard
    questions_answered_today: KPICard

class ChartDataPoint(BaseModel):
    """Generic chart data point"""
    label: str
    value: float
    metadata: Optional[Dict[str, Any]] = None

class TimeSeriesPoint(BaseModel):
    """Time series data point"""
    timestamp: datetime
    value: float
    label: Optional[str] = None

class DashboardCharts(BaseModel):
    """Dashboard chart data"""
    user_growth: List[TimeSeriesPoint]
    revenue_trend: List[TimeSeriesPoint]
    subscription_distribution: List[ChartDataPoint]
    active_hours_heatmap: Dict[str, List[int]]  # day -> hourly counts
    subject_popularity: List[ChartDataPoint]
    daily_active_users: List[TimeSeriesPoint]

class ActivityFeedItem(BaseModel):
    """Single activity feed entry"""
    id: UUID
    type: str  # registration, upgrade, competition, ticket, alert
    title: str
    description: str
    user_id: Optional[UUID] = None
    user_name: Optional[str] = None
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

class DashboardActivity(BaseModel):
    """Recent activity feed"""
    items: List[ActivityFeedItem]
    total_count: int
    has_more: bool


# ============================================================================
# User Management Schemas
# ============================================================================
class UserFilter(BaseModel):
    """User list filtering options"""
    role: Optional[str] = None
    subscription_tier: Optional[str] = None
    registration_date_from: Optional[date] = None
    registration_date_to: Optional[date] = None
    last_active_from: Optional[date] = None
    last_active_to: Optional[date] = None
    education_level: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None
    school: Optional[str] = None
    is_verified: Optional[bool] = None
    is_active: Optional[bool] = None
    search: Optional[str] = None

class UserListItem(BaseModel):
    """User in list view"""
    id: UUID
    phone_number: str
    email: Optional[str]
    role: str
    subscription_tier: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_active: Optional[datetime]
    student_name: Optional[str] = None
    school: Optional[str] = None

class UserListResponse(BaseModel):
    """Paginated user list"""
    users: List[UserListItem]
    total: int
    page: int
    page_size: int
    total_pages: int

class UserDetail(BaseModel):
    """Complete user profile for admin view"""
    id: UUID
    phone_number: str
    whatsapp_id: Optional[str]
    email: Optional[str]
    role: str
    subscription_tier: str
    subscription_expires_at: Optional[datetime]
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_active: Optional[datetime]
    # Student details (if applicable)
    student: Optional[Dict[str, Any]] = None
    # Statistics
    total_sessions: int = 0
    total_questions_answered: int = 0
    total_payments: Decimal = Decimal("0")
    # Related data counts
    conversations_count: int = 0
    achievements_count: int = 0
    payments_count: int = 0

class UserUpdate(BaseModel):
    """Admin user update payload"""
    email: Optional[str] = None
    phone_number: Optional[str] = None
    role: Optional[str] = None
    subscription_tier: Optional[str] = None
    subscription_expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None

class BulkUserAction(BaseModel):
    """Bulk action on multiple users"""
    user_ids: List[UUID]
    action: str  # activate, deactivate, delete, upgrade, downgrade

class ImpersonateResponse(BaseModel):
    """Response for user impersonation"""
    access_token: str
    user_id: UUID
    expires_at: datetime
    read_only: bool = True


# ============================================================================
# Student Management Schemas
# ============================================================================
class StudentListItem(BaseModel):
    """Student in list view"""
    id: UUID
    user_id: UUID
    full_name: str
    grade: str
    education_level: str
    school_name: Optional[str]
    total_xp: int
    level: int
    current_streak: int
    subscription_tier: str
    last_active: Optional[datetime]

class StudentAnalytics(BaseModel):
    """Comprehensive student analytics"""
    overview: Dict[str, Any]
    activity: Dict[str, Any]
    performance: Dict[str, Any]
    subjects: List[Dict[str, Any]]
    trends: Dict[str, Any]
    predictions: Dict[str, Any]

class StudentSession(BaseModel):
    """Student practice session"""
    id: UUID
    session_type: str
    subject: Optional[str]
    topic: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]
    total_questions: int
    correct_answers: int
    score_percentage: Optional[float]
    xp_earned: int

class StudentReportRequest(BaseModel):
    """Request to generate student report"""
    report_type: str = "comprehensive"  # comprehensive, progress, performance
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    include_recommendations: bool = True
    format: ReportFormat = ReportFormat.PDF


# ============================================================================
# Conversation Management Schemas
# ============================================================================
class LiveConversation(BaseModel):
    """Active conversation for monitoring"""
    id: UUID
    student_id: UUID
    student_name: str
    subject: Optional[str]
    topic: Optional[str]
    started_at: datetime
    message_count: int
    last_message_at: datetime
    status: str  # active, idle, needs_attention
    sentiment: Optional[str]  # positive, neutral, negative

class ConversationMessage(BaseModel):
    """Single conversation message"""
    id: UUID
    role: str
    content: str
    context_type: Optional[str]
    tokens_used: Optional[int]
    response_time_ms: Optional[int]
    sources_used: int = 0
    created_at: datetime

class ConversationDetail(BaseModel):
    """Full conversation with messages"""
    id: UUID
    student_id: UUID
    student_name: str
    messages: List[ConversationMessage]
    total_messages: int
    total_tokens: int
    avg_response_time_ms: float
    subjects_discussed: List[str]
    started_at: datetime
    last_message_at: datetime

class InterventionRequest(BaseModel):
    """Admin intervention in conversation"""
    message: str
    intervention_type: str = "guidance"  # guidance, correction, escalation
    notify_student: bool = True

class ConversationPipeline(BaseModel):
    """Conversation processing pipeline stats"""
    pending: int
    processing: int
    completed_today: int
    failed_today: int
    avg_processing_time_ms: float
    queue_health: str  # healthy, degraded, critical


# ============================================================================
# Content Management Schemas
# ============================================================================

class EducationLevel(str, Enum):
    """Education levels in Zimbabwe"""
    PRIMARY = "primary"
    SECONDARY = "secondary"  # O-Level
    O_LEVEL = "o_level"
    A_LEVEL = "a_level"
    TERTIARY = "tertiary"


class SubjectSortField(str, Enum):
    """Fields available for sorting subjects"""
    NAME = "name"
    CODE = "code"
    CREATED_AT = "created_at"
    TOPIC_COUNT = "topic_count"
    QUESTION_COUNT = "question_count"
    EDUCATION_LEVEL = "education_level"


class SortOrder(str, Enum):
    """Sort order options"""
    ASC = "asc"
    DESC = "desc"


class SubjectCreate(BaseModel):
    """Create new subject with comprehensive validation"""
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Subject name (e.g., 'Mathematics', 'English Language')"
    )
    code: str = Field(
        ...,
        min_length=2,
        max_length=20,
        pattern=r"^[A-Z0-9\-]+$",
        description="Unique subject code (e.g., 'MATH-001', 'ENG-O-LEVEL')"
    )
    education_level: str = Field(
        ...,
        description="Education level: primary, secondary, o_level, a_level"
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Detailed description of the subject"
    )
    icon: Optional[str] = Field(
        None,
        max_length=50,
        description="Icon name or emoji for the subject"
    )
    color: Optional[str] = Field(
        None,
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Hex color code (e.g., '#3b82f6')"
    )

    @validator('code')
    def uppercase_code(cls, v):
        return v.upper() if v else v

    @validator('education_level')
    def validate_education_level(cls, v):
        valid_levels = ['primary', 'secondary', 'o_level', 'a_level', 'tertiary']
        if v.lower() not in valid_levels:
            raise ValueError(f"Education level must be one of: {', '.join(valid_levels)}")
        return v.lower()

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Mathematics",
                "code": "MATH-O-001",
                "education_level": "o_level",
                "description": "Core mathematics for O-Level students covering algebra, geometry, and statistics",
                "icon": "calculate",
                "color": "#3b82f6"
            }
        }


class SubjectUpdate(BaseModel):
    """Update subject with partial fields"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    code: Optional[str] = Field(None, min_length=2, max_length=20, pattern=r"^[A-Z0-9\-]+$")
    education_level: Optional[str] = None
    description: Optional[str] = Field(None, max_length=1000)
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    is_active: Optional[bool] = None

    @validator('code')
    def uppercase_code(cls, v):
        return v.upper() if v else v

    @validator('education_level')
    def validate_education_level(cls, v):
        if v is None:
            return v
        valid_levels = ['primary', 'secondary', 'o_level', 'a_level', 'tertiary']
        if v.lower() not in valid_levels:
            raise ValueError(f"Education level must be one of: {', '.join(valid_levels)}")
        return v.lower()


class SubjectResponse(BaseModel):
    """Subject response with full details"""
    id: UUID
    name: str
    code: str
    education_level: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    is_active: bool
    topic_count: int = 0
    question_count: int = 0
    document_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SubjectListResponse(BaseModel):
    """Paginated subject list response"""
    subjects: List[SubjectResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class SubjectFilter(BaseModel):
    """Subject filtering options"""
    search: Optional[str] = Field(None, description="Search in name, code, description")
    education_level: Optional[str] = None
    is_active: Optional[bool] = None
    has_topics: Optional[bool] = Field(None, description="Filter subjects with/without topics")
    has_questions: Optional[bool] = Field(None, description="Filter subjects with/without questions")
    created_after: Optional[date] = None
    created_before: Optional[date] = None


class SubjectBulkAction(BaseModel):
    """Bulk action on multiple subjects"""
    subject_ids: List[UUID] = Field(..., min_items=1, max_items=100)
    action: str = Field(..., description="Action: activate, deactivate, delete")

    @validator('action')
    def validate_action(cls, v):
        valid_actions = ['activate', 'deactivate', 'delete']
        if v.lower() not in valid_actions:
            raise ValueError(f"Action must be one of: {', '.join(valid_actions)}")
        return v.lower()


class SubjectBulkActionResponse(BaseModel):
    """Response for bulk subject actions"""
    total_requested: int
    successful: int
    failed: int
    errors: List[Dict[str, str]] = []
    message: str


class SubjectStats(BaseModel):
    """Subject statistics"""
    total_subjects: int
    active_subjects: int
    inactive_subjects: int
    by_education_level: Dict[str, int]
    total_topics: int
    total_questions: int
    subjects_without_topics: int
    subjects_without_questions: int
    avg_topics_per_subject: float
    avg_questions_per_subject: float
    recently_created: int  # Last 30 days
    most_popular: List[Dict[str, Any]]  # By question count


class SubjectDetailResponse(BaseModel):
    """Detailed subject response with related data"""
    id: UUID
    name: str
    code: str
    education_level: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    is_active: bool
    topic_count: int = 0
    question_count: int = 0
    document_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
    # Additional details
    topics: List[Dict[str, Any]] = []
    coverage_percentage: float = 0.0
    difficulty_distribution: Dict[str, int] = {}
    recent_activity: List[Dict[str, Any]] = []


class SubjectExportFormat(str, Enum):
    """Export format options"""
    CSV = "csv"
    JSON = "json"
    EXCEL = "excel"


class SubjectExportRequest(BaseModel):
    """Subject export request"""
    format: SubjectExportFormat = SubjectExportFormat.CSV
    subject_ids: Optional[List[UUID]] = Field(None, description="Specific subjects to export, None = all")
    include_topics: bool = Field(False, description="Include related topics in export")
    include_questions: bool = Field(False, description="Include question counts per topic")


class SubjectExportResponse(BaseModel):
    """Subject export response"""
    filename: str
    file_size: int
    record_count: int
    download_url: str
    expires_at: datetime


class SubjectDependencyWarning(BaseModel):
    """Warning about subject dependencies before deletion"""
    subject_id: UUID
    subject_name: str
    topic_count: int
    question_count: int
    document_count: int
    active_students_count: int
    can_delete: bool
    warnings: List[str]


class TopicCreate(BaseModel):
    """Create new topic"""
    subject_id: UUID
    parent_topic_id: Optional[UUID] = None
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    grade: str
    syllabus_reference: Optional[str] = None
    order_index: int = 0
    estimated_hours: Optional[float] = None

class TopicUpdate(BaseModel):
    """Update topic"""
    name: Optional[str] = None
    description: Optional[str] = None
    syllabus_reference: Optional[str] = None
    order_index: Optional[int] = None
    estimated_hours: Optional[float] = None
    is_active: Optional[bool] = None

class QuestionCreate(BaseModel):
    """Create new question"""
    subject_id: UUID
    topic_id: Optional[UUID] = None
    question_text: str = Field(..., min_length=10)
    question_type: str
    options: Optional[List[str]] = None
    correct_answer: str
    marking_scheme: Optional[str] = None
    explanation: Optional[str] = None
    marks: int = Field(1, ge=1, le=100)
    difficulty: str = "medium"
    source: str = "admin"
    source_year: Optional[int] = None
    tags: Optional[List[str]] = None

class QuestionBulkUpload(BaseModel):
    """Bulk question upload response"""
    total_processed: int
    successful: int
    failed: int
    errors: List[Dict[str, str]]

class DocumentUploadResponse(BaseModel):
    """Document upload and processing response"""
    document_id: UUID
    filename: str
    file_size: int
    status: str  # processing, completed, failed
    chunks_created: int = 0
    processing_time_ms: Optional[int] = None
    error: Optional[str] = None

class RAGStats(BaseModel):
    """RAG system statistics"""
    total_documents: int
    total_chunks: int
    collections: Dict[str, int]  # collection_name -> chunk_count
    avg_chunk_size: float
    last_ingestion: Optional[datetime]
    vector_store_health: str


# ============================================================================
# Competition Management Schemas
# ============================================================================
class CompetitionCreate(BaseModel):
    """Create competition"""
    name: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    subject_id: Optional[UUID] = None
    education_level: Optional[str] = None
    grade: Optional[str] = None
    competition_type: str = "individual"
    start_date: datetime
    end_date: datetime
    max_participants: Optional[int] = None
    entry_fee: Decimal = Decimal("0")
    prizes: Optional[Dict[str, str]] = None
    rules: Optional[Dict[str, Any]] = None
    num_questions: int = Field(10, ge=5, le=100)
    time_limit_minutes: int = Field(30, ge=5, le=180)
    difficulty: str = "medium"

class CompetitionUpdate(BaseModel):
    """Update competition"""
    name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    max_participants: Optional[int] = None
    prizes: Optional[Dict[str, str]] = None
    rules: Optional[Dict[str, Any]] = None
    status: Optional[str] = None

class LeaderboardEntry(BaseModel):
    """Competition leaderboard entry"""
    rank: int
    student_id: UUID
    student_name: str
    school: Optional[str]
    score: float
    time_taken_seconds: Optional[int]
    questions_correct: int
    completed_at: Optional[datetime]

class CompetitionLive(BaseModel):
    """Live competition monitoring data"""
    competition_id: UUID
    name: str
    status: str
    time_remaining_seconds: int
    total_participants: int
    active_participants: int
    completed_participants: int
    leaderboard: List[LeaderboardEntry]
    anomalies: List[Dict[str, Any]]


# ============================================================================
# Payment & Subscription Schemas
# ============================================================================
class PaymentFilter(BaseModel):
    """Payment list filtering"""
    status: Optional[str] = None
    payment_method: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    user_id: Optional[UUID] = None

class PaymentListItem(BaseModel):
    """Payment in list view"""
    id: UUID
    user_id: UUID
    user_phone: str
    plan_name: str
    amount: Decimal
    currency: str
    payment_method: Optional[str]
    status: str
    created_at: datetime
    completed_at: Optional[datetime]

class PaymentStats(BaseModel):
    """Payment statistics"""
    mrr: Decimal  # Monthly Recurring Revenue
    arr: Decimal  # Annual Recurring Revenue
    churn_rate: float
    ltv: Decimal  # Lifetime Value
    revenue_by_plan: Dict[str, Decimal]
    payment_method_breakdown: Dict[str, int]
    failed_payments_count: int
    pending_payments_count: int

class RefundRequest(BaseModel):
    """Refund request payload"""
    reason: str = Field(..., min_length=10)
    partial_amount: Optional[Decimal] = None  # None = full refund

class PlanCreate(BaseModel):
    """Create subscription plan"""
    name: str
    tier: str
    description: Optional[str] = None
    price_usd: Decimal
    price_zwl: Optional[Decimal] = None
    duration_days: int
    features: List[str]
    limits: Dict[str, Any]
    max_students: int = 1
    discount_percentage: int = 0
    is_popular: bool = False


# ============================================================================
# Analytics Schemas
# ============================================================================
class AnalyticsRequest(BaseModel):
    """Analytics query parameters"""
    time_range: TimeRange = TimeRange.LAST_30_DAYS
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    group_by: Optional[str] = None  # day, week, month
    filters: Optional[Dict[str, Any]] = None

class EngagementAnalytics(BaseModel):
    """User engagement metrics"""
    dau: int  # Daily Active Users
    wau: int  # Weekly Active Users
    mau: int  # Monthly Active Users
    dau_wau_ratio: float
    avg_session_duration_minutes: float
    avg_messages_per_session: float
    feature_usage: Dict[str, int]
    retention_cohorts: Dict[str, List[float]]
    funnel_data: Dict[str, int]

class LearningAnalytics(BaseModel):
    """Learning metrics"""
    questions_answered: int
    accuracy_rate: float
    accuracy_trend: List[TimeSeriesPoint]
    time_by_subject: Dict[str, int]  # minutes
    difficulty_distribution: Dict[str, int]
    hint_usage_rate: float
    avg_time_per_question_seconds: float

class RevenueAnalytics(BaseModel):
    """Revenue metrics"""
    total_revenue: Decimal
    revenue_trend: List[TimeSeriesPoint]
    revenue_by_plan: Dict[str, Decimal]
    new_subscriptions: int
    churned_subscriptions: int
    upgrades: int
    downgrades: int
    conversion_funnel: Dict[str, int]

class CustomReportRequest(BaseModel):
    """Custom report generation request"""
    name: str
    description: Optional[str] = None
    metrics: List[str]
    dimensions: List[str]
    filters: Optional[Dict[str, Any]] = None
    time_range: TimeRange
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    format: ReportFormat = ReportFormat.PDF
    schedule: Optional[str] = None  # cron expression for scheduled reports


# ============================================================================
# Notification Schemas
# ============================================================================
class BroadcastRequest(BaseModel):
    """Broadcast notification request"""
    title: str = Field(..., min_length=3, max_length=100)
    message: str = Field(..., min_length=10, max_length=1000)
    type: NotificationType = NotificationType.INFO
    target_segment: Optional[Dict[str, Any]] = None  # Filtering criteria
    schedule_at: Optional[datetime] = None
    channels: List[str] = ["in_app"]  # in_app, whatsapp, email

class WhatsAppTemplate(BaseModel):
    """WhatsApp message template"""
    id: UUID
    name: str
    category: str
    language: str
    status: str  # approved, pending, rejected
    content: str
    variables: List[str]
    created_at: datetime
    last_used: Optional[datetime]
    usage_count: int


# ============================================================================
# Settings & System Schemas
# ============================================================================
class SystemSettings(BaseModel):
    """Application settings"""
    app_name: str
    app_tagline: Optional[str]
    contact_email: str
    contact_phone: str
    support_hours: str
    feature_flags: Dict[str, bool]
    maintenance_mode: bool = False
    maintenance_message: Optional[str] = None

class AdminCreate(BaseModel):
    """Create admin user"""
    email: str
    password: str = Field(..., min_length=8)
    phone_number: Optional[str] = None
    admin_role: AdminRole = AdminRole.ADMIN
    permissions: Optional[List[str]] = None

class AuditLogEntry(BaseModel):
    """Audit log entry"""
    id: UUID
    admin_id: UUID
    admin_email: str
    action: AuditAction
    resource_type: str
    resource_id: Optional[UUID]
    details: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]
    timestamp: datetime

class SystemHealth(BaseModel):
    """System health status"""
    status: str  # healthy, degraded, critical
    api_status: str
    database_status: str
    database_latency_ms: float
    redis_status: str
    redis_latency_ms: float
    queue_status: str
    queue_size: int
    vector_store_status: str
    external_services: Dict[str, str]
    uptime_seconds: int
    memory_usage_percent: float
    cpu_usage_percent: float
    error_rate_1h: float
    last_checked: datetime