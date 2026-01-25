# ============================================================================
# Payment Schemas - Production Grade
# ============================================================================
"""
Comprehensive payment and subscription schemas with validation.
Supports full payment lifecycle, refunds, reconciliation, and analytics.
"""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, date
from uuid import UUID
from enum import Enum
from decimal import Decimal
import re


# ============================================================================
# Enums
# ============================================================================
class PaymentMethodEnum(str, Enum):
    ECOCASH = "ecocash"
    ONEMONEY = "onemoney"
    INNBUCKS = "innbucks"
    TELECASH = "telecash"
    VISA = "visa"
    MASTERCARD = "mastercard"
    BANK = "bank"
    PAYPAL = "paypal"
    ZIPIT = "zipit"


class PaymentStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"
    EXPIRED = "expired"


class SubscriptionTierEnum(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    FAMILY = "family"
    SCHOOL = "school"


class SubscriptionStatusEnum(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    EXPIRING_SOON = "expiring_soon"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"
    PENDING = "pending"


class BillingCycleEnum(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class RefundTypeEnum(str, Enum):
    FULL = "full"
    PARTIAL = "partial"


class CurrencyEnum(str, Enum):
    USD = "USD"
    ZWL = "ZWL"


# ============================================================================
# Base Schemas
# ============================================================================
class MoneyAmount(BaseModel):
    """Standardized money representation"""
    amount: Decimal = Field(..., ge=0, description="Amount in currency units")
    currency: CurrencyEnum = Field(default=CurrencyEnum.USD)

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        if v < 0:
            raise ValueError("Amount cannot be negative")
        return round(v, 2)

    class Config:
        json_encoders = {Decimal: lambda v: float(v)}


# ============================================================================
# Subscription Plan Schemas
# ============================================================================
class PlanLimits(BaseModel):
    """Subscription plan usage limits"""
    daily_questions: int = Field(default=5, ge=0)
    max_subjects: int = Field(default=1, ge=0)
    max_practice_sessions: int = Field(default=5, ge=0)
    ai_explanations: bool = Field(default=False)
    priority_support: bool = Field(default=False)
    offline_access: bool = Field(default=False)
    parent_dashboard: bool = Field(default=False)
    progress_reports: bool = Field(default=False)
    advanced_analytics: bool = Field(default=False)


class SubscriptionPlanCreate(BaseModel):
    """Schema for creating a subscription plan"""
    name: str = Field(..., min_length=2, max_length=100)
    tier: SubscriptionTierEnum
    description: Optional[str] = Field(None, max_length=500)
    price_usd: Decimal = Field(..., ge=0)
    price_zwl: Optional[Decimal] = Field(None, ge=0)
    duration_days: int = Field(..., ge=1, le=365)
    features: List[str] = Field(default_factory=list)
    limits: Optional[PlanLimits] = None
    max_students: int = Field(default=1, ge=1)
    discount_percentage: int = Field(default=0, ge=0, le=100)
    is_popular: bool = Field(default=False)

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not re.match(r'^[a-zA-Z0-9\s\-]+$', v):
            raise ValueError("Plan name can only contain letters, numbers, spaces and hyphens")
        return v.strip()


class SubscriptionPlanUpdate(BaseModel):
    """Schema for updating a subscription plan"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price_usd: Optional[Decimal] = Field(None, ge=0)
    price_zwl: Optional[Decimal] = Field(None, ge=0)
    features: Optional[List[str]] = None
    limits: Optional[Dict[str, Any]] = None
    discount_percentage: Optional[int] = Field(None, ge=0, le=100)
    is_popular: Optional[bool] = None
    is_active: Optional[bool] = None


class SubscriptionPlanResponse(BaseModel):
    """Full subscription plan response"""
    id: UUID
    name: str
    tier: str
    description: Optional[str]
    price_usd: Decimal
    price_zwl: Optional[Decimal]
    duration_days: int
    features: List[str]
    limits: Dict[str, Any]
    max_students: int
    is_popular: bool
    is_active: bool
    discount_percentage: int
    subscriber_count: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SubscriptionPlanListResponse(BaseModel):
    """Paginated plan list response"""
    items: List[SubscriptionPlanResponse]
    total: int
    active_count: int
    popular_plan_id: Optional[UUID] = None


# ============================================================================
# Payment Schemas
# ============================================================================
class InitiatePaymentRequest(BaseModel):
    """Request to initiate a payment"""
    plan_id: UUID
    payment_method: PaymentMethodEnum
    phone: Optional[str] = Field(None, pattern=r'^\+263[0-9]{9}$')
    email: Optional[str] = Field(None, max_length=255)
    idempotency_key: Optional[str] = Field(None, min_length=16, max_length=64)

    @model_validator(mode='after')
    def validate_payment_details(self):
        mobile_methods = [
            PaymentMethodEnum.ECOCASH,
            PaymentMethodEnum.ONEMONEY,
            PaymentMethodEnum.INNBUCKS,
            PaymentMethodEnum.TELECASH
        ]
        if self.payment_method in mobile_methods and not self.phone:
            raise ValueError(f"Phone number is required for {self.payment_method.value} payments")
        return self


class PaymentResponse(BaseModel):
    """Standard payment response"""
    id: UUID
    user_id: UUID
    plan_id: UUID
    amount: Decimal
    currency: str
    status: PaymentStatusEnum
    payment_method: Optional[PaymentMethodEnum]
    payment_reference: Optional[str]
    external_reference: Optional[str]
    redirect_url: Optional[str]
    poll_url: Optional[str]
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime]
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaymentDetailResponse(BaseModel):
    """Detailed payment information for admin view"""
    id: UUID
    user_id: UUID
    user_phone: Optional[str]
    user_email: Optional[str]
    user_name: Optional[str]
    plan_id: UUID
    plan_name: Optional[str]
    plan_tier: Optional[str]
    amount: Decimal
    original_amount: Optional[Decimal] = None
    refunded_amount: Optional[Decimal] = None
    currency: str
    payment_method: Optional[str]
    payment_reference: Optional[str]
    external_reference: Optional[str]
    gateway_transaction_id: Optional[str] = None
    paynow_poll_url: Optional[str]
    status: PaymentStatusEnum
    error_message: Optional[str]
    failure_reason: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    payment_metadata: Optional[Dict[str, Any]]
    refund_history: Optional[List[Dict[str, Any]]] = None
    status_history: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class PaymentListResponse(BaseModel):
    """Paginated payment list response"""
    payments: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int
    total_pages: int
    summary: Optional[Dict[str, Any]] = None


class PaymentInitiationResponse(BaseModel):
    """Response after initiating a payment"""
    success: bool
    payment_id: Optional[UUID]
    reference: Optional[str]
    redirect_url: Optional[str]
    poll_url: Optional[str]
    message: str
    error: Optional[str] = None
    expires_at: Optional[datetime] = None


# ============================================================================
# Refund Schemas
# ============================================================================
class RefundRequest(BaseModel):
    """Request to process a refund"""
    reason: str = Field(..., min_length=10, max_length=500)
    refund_type: RefundTypeEnum = Field(default=RefundTypeEnum.FULL)
    partial_amount: Optional[Decimal] = Field(None, gt=0)
    notify_user: bool = Field(default=True)
    internal_notes: Optional[str] = Field(None, max_length=1000)

    @model_validator(mode='after')
    def validate_refund(self):
        if self.refund_type == RefundTypeEnum.PARTIAL and not self.partial_amount:
            raise ValueError("Partial amount is required for partial refunds")
        if self.refund_type == RefundTypeEnum.FULL and self.partial_amount:
            raise ValueError("Cannot specify partial amount for full refund")
        return self


class RefundResponse(BaseModel):
    """Response after processing a refund"""
    success: bool
    payment_id: UUID
    refund_amount: Decimal
    refund_reference: Optional[str] = None
    new_payment_status: PaymentStatusEnum
    message: str
    processed_at: datetime
    processed_by: Optional[UUID] = None


# ============================================================================
# Subscription Schemas
# ============================================================================
class SubscriptionResponse(BaseModel):
    """User subscription information"""
    user_id: UUID
    phone_number: Optional[str]
    email: Optional[str]
    user_name: Optional[str]
    tier: str
    plan_id: Optional[UUID] = None
    plan_name: Optional[str] = None
    status: SubscriptionStatusEnum
    expires_at: Optional[datetime]
    started_at: Optional[datetime] = None
    is_active: bool
    days_remaining: int
    auto_renew: bool = False
    next_billing_date: Optional[datetime] = None
    last_payment_id: Optional[UUID] = None
    last_payment_date: Optional[datetime] = None
    total_spent: Optional[Decimal] = None

    class Config:
        from_attributes = True


class SubscriptionListResponse(BaseModel):
    """Paginated subscription list"""
    subscriptions: List[SubscriptionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    summary: Optional[Dict[str, Any]] = None


class ModifySubscriptionRequest(BaseModel):
    """Request to modify a subscription"""
    new_tier: SubscriptionTierEnum
    expires_at: Optional[datetime] = None
    reason: str = Field(..., min_length=5, max_length=500)
    notify_user: bool = Field(default=True)

    @model_validator(mode='after')
    def validate_modification(self):
        if self.expires_at and self.expires_at <= datetime.utcnow():
            raise ValueError("Expiry date must be in the future")
        return self


class ModifySubscriptionResponse(BaseModel):
    """Response after modifying subscription"""
    success: bool
    user_id: UUID
    old_tier: str
    new_tier: str
    expires_at: Optional[datetime]
    message: str
    modified_at: datetime
    modified_by: Optional[UUID] = None


class SubscriptionStatusResponse(BaseModel):
    """Current subscription status for user"""
    tier: str
    is_active: bool
    expires_at: Optional[datetime]
    days_remaining: int
    features: List[str]
    limits: Dict[str, Any]
    usage: Optional[Dict[str, Any]] = None
    upgrade_options: Optional[List[Dict[str, Any]]] = None


# ============================================================================
# Payment Statistics Schemas
# ============================================================================
class RevenueByPlanItem(BaseModel):
    """Revenue breakdown by plan"""
    plan_id: UUID
    plan_name: str
    tier: str
    revenue: Decimal
    transaction_count: int
    percentage: float


class RevenueByMethodItem(BaseModel):
    """Revenue breakdown by payment method"""
    method: str
    revenue: Decimal
    transaction_count: int
    percentage: float
    success_rate: float


class RevenueTrendItem(BaseModel):
    """Daily revenue trend data"""
    date: date
    revenue: Decimal
    transaction_count: int
    new_subscriptions: int
    churned_subscriptions: int


class PaymentStatsResponse(BaseModel):
    """Comprehensive payment statistics"""
    # Key Metrics
    mrr: Decimal = Field(..., description="Monthly Recurring Revenue")
    arr: Decimal = Field(..., description="Annual Recurring Revenue")
    active_subscriptions: int
    total_subscribers: int

    # Health Metrics
    churn_rate: float = Field(..., description="Monthly churn rate percentage")
    ltv: Decimal = Field(..., description="Customer Lifetime Value")
    arpu: Decimal = Field(..., description="Average Revenue Per User")

    # Transaction Metrics
    total_revenue_30d: Decimal
    total_transactions_30d: int
    successful_transactions_30d: int
    failed_transactions_30d: int
    refunded_amount_30d: Decimal
    average_transaction_value: Decimal

    # Success Metrics
    payment_success_rate: float
    refund_rate: float
    dispute_rate: float

    # Breakdowns
    revenue_by_plan: List[RevenueByPlanItem]
    revenue_by_method: List[RevenueByMethodItem]
    revenue_trend: List[RevenueTrendItem]

    # Comparative Metrics
    mrr_growth: float = Field(..., description="MoM MRR growth percentage")
    subscriber_growth: float = Field(..., description="MoM subscriber growth percentage")

    # Period
    period_start: date
    period_end: date
    currency: str = "USD"

    class Config:
        json_encoders = {Decimal: lambda v: float(v)}


# ============================================================================
# Reconciliation Schemas
# ============================================================================
class ReconciliationItem(BaseModel):
    """Single reconciliation item"""
    payment_id: UUID
    external_reference: str
    expected_amount: Decimal
    actual_amount: Decimal
    status: str
    discrepancy: Optional[Decimal] = None
    notes: Optional[str] = None


class ReconciliationRequest(BaseModel):
    """Request to reconcile payments"""
    start_date: date
    end_date: date
    payment_method: Optional[PaymentMethodEnum] = None
    provider_report_data: Optional[str] = Field(None, description="Base64 encoded CSV/Excel data")


class ReconciliationResponse(BaseModel):
    """Reconciliation results"""
    total_payments: int
    matched: int
    unmatched: int
    discrepancies: int
    total_expected: Decimal
    total_actual: Decimal
    total_discrepancy: Decimal
    items: List[ReconciliationItem]
    reconciled_at: datetime
    reconciled_by: Optional[UUID] = None


# ============================================================================
# Export Schemas
# ============================================================================
class PaymentExportRequest(BaseModel):
    """Request to export payment data"""
    format: Literal["csv", "xlsx", "pdf"] = "csv"
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    status: Optional[List[PaymentStatusEnum]] = None
    payment_method: Optional[List[PaymentMethodEnum]] = None
    include_user_details: bool = True
    include_metadata: bool = False


class PaymentExportResponse(BaseModel):
    """Export response with download URL"""
    success: bool
    file_name: str
    file_url: Optional[str] = None
    file_size: Optional[int] = None
    record_count: int
    generated_at: datetime
    expires_at: Optional[datetime] = None


# ============================================================================
# Invoice Schemas
# ============================================================================
class InvoiceLineItem(BaseModel):
    """Single invoice line item"""
    description: str
    quantity: int = 1
    unit_price: Decimal
    total: Decimal
    tax_amount: Optional[Decimal] = None


class InvoiceRequest(BaseModel):
    """Request to generate an invoice"""
    payment_id: UUID
    include_tax: bool = False
    tax_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    custom_notes: Optional[str] = None


class InvoiceResponse(BaseModel):
    """Generated invoice details"""
    invoice_number: str
    payment_id: UUID
    user_id: UUID
    user_name: str
    user_email: Optional[str]
    billing_address: Optional[str] = None
    issue_date: date
    due_date: Optional[date] = None
    line_items: List[InvoiceLineItem]
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    currency: str
    status: str
    pdf_url: Optional[str] = None
    created_at: datetime


# ============================================================================
# Webhook Schemas
# ============================================================================
class PaynowWebhookPayload(BaseModel):
    """Paynow webhook payload"""
    reference: str
    paynowreference: str
    amount: Decimal
    status: str
    hash: str
    pollurl: Optional[str] = None


class WebhookEventResponse(BaseModel):
    """Response to webhook event"""
    received: bool
    payment_id: Optional[UUID] = None
    status_updated: bool
    message: str
