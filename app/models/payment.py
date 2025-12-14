# ============================================================================
# Payment & Subscription Models
# ============================================================================
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy import Text, Numeric, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.core.database import Base
from app.models.user import SubscriptionTier

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"

class PaymentMethod(str, enum.Enum):
    ECOCASH = "ecocash"
    ONEMONEY = "onemoney"
    INNBUCKS = "innbucks"
    TELECASH = "telecash"
    VISA = "visa"
    MASTERCARD = "mastercard"
    BANK = "bank"
    PAYPAL = "paypal"

class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    tier = Column(Enum(SubscriptionTier), nullable=False)
    description = Column(Text)
    
    price_usd = Column(Numeric(10, 2), nullable=False)
    price_zwl = Column(Numeric(10, 2))
    
    duration_days = Column(Integer, nullable=False)  # 30 for monthly, 365 for yearly
    
    features = Column(JSON)  # List of features
    limits = Column(JSON)  # {"daily_questions": 50, "subjects": 3, etc.}
    
    max_students = Column(Integer, default=1)  # For family plans
    
    discount_percentage = Column(Integer, default=0)  # For yearly plans
    is_popular = Column(Boolean, default=False)  # UI flag
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    payments = relationship("Payment", back_populates="plan")
    
    def __repr__(self):
        return f"<SubscriptionPlan {self.name} (${self.price_usd})>"

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=False)
    
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), nullable=False, default="USD")
    
    payment_method = Column(Enum(PaymentMethod))
    payment_reference = Column(String(100))  # Our internal reference
    external_reference = Column(String(200))  # Payment provider reference
    
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    
    # Paynow specific
    paynow_poll_url = Column(String(500))
    paynow_redirect_url = Column(String(500))
    
    # Metadata
    payment_metadata = Column(JSON)  # Additional payment info
    error_message = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    user = relationship("User", back_populates="payments")
    plan = relationship("SubscriptionPlan", back_populates="payments")
    
    def __repr__(self):
        return f"<Payment {self.id} ({self.status.value})>"