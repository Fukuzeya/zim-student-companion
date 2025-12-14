# ============================================================================
# Payment Schemas
# ============================================================================
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum
from decimal import Decimal

class PaymentMethodEnum(str, Enum):
    ECOCASH = "ecocash"
    ONEMONEY = "onemoney"
    INNBUCKS = "innbucks"
    TELECASH = "telecash"
    VISA = "visa"
    MASTERCARD = "mastercard"
    BANK = "bank"
    PAYPAL = "paypal"

class PaymentStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"

class SubscriptionPlanResponse(BaseModel):
    id: UUID
    name: str
    tier: str
    description: Optional[str]
    price_usd: Decimal
    price_zwl: Optional[Decimal]
    duration_days: int
    features: List[str]
    limits: Dict[str, Any]
    is_popular: bool
    discount_percentage: int
    
    class Config:
        from_attributes = True

class InitiatePaymentRequest(BaseModel):
    plan_id: UUID
    payment_method: PaymentMethodEnum
    phone: Optional[str] = None
    email: Optional[str] = None

class PaymentResponse(BaseModel):
    id: UUID
    amount: Decimal
    currency: str
    status: PaymentStatusEnum
    payment_method: Optional[PaymentMethodEnum]
    payment_reference: Optional[str]
    redirect_url: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class PaymentInitiationResponse(BaseModel):
    success: bool
    payment_id: Optional[UUID]
    reference: Optional[str]
    redirect_url: Optional[str]
    poll_url: Optional[str]
    message: str
    error: Optional[str] = None

class SubscriptionStatusResponse(BaseModel):
    tier: str
    is_active: bool
    expires_at: Optional[datetime]
    days_remaining: int
    features: List[str]
    limits: Dict[str, Any]