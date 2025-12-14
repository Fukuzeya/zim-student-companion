# ============================================================================
# Paynow Zimbabwe Integration
# ============================================================================
from paynow import Paynow
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import uuid
import logging

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class PaynowStatus(str, Enum):
    CREATED = "created"
    SENT = "sent"
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    FAILED = "failed"
    REFUNDED = "refunded"
    AWAITING_DELIVERY = "awaiting delivery"
    DELIVERED = "delivered"

@dataclass
class PaynowResponse:
    """Standardized Paynow response"""
    success: bool
    status: str
    redirect_url: Optional[str] = None
    poll_url: Optional[str] = None
    error: Optional[str] = None
    reference: Optional[str] = None

class PaynowClient:
    """Client for Paynow Zimbabwe payment gateway"""
    
    def __init__(self):
        self.paynow = Paynow(
            settings.PAYNOW_INTEGRATION_ID,
            settings.PAYNOW_INTEGRATION_KEY,
            settings.PAYNOW_RESULT_URL,
            settings.PAYNOW_RETURN_URL
        )
    
    def create_payment(
        self,
        reference: str,
        email: str,
        items: Dict[str, float]
    ) -> Tuple[object, str]:
        """Create a new payment request"""
        payment = self.paynow.create_payment(reference, email)
        
        for item_name, amount in items.items():
            payment.add(item_name, amount)
        
        return payment, reference
    
    async def initiate_web_payment(
        self,
        amount: float,
        description: str,
        email: str,
        reference: str = None
    ) -> PaynowResponse:
        """Initiate a web-based payment (card, bank)"""
        try:
            if not reference:
                reference = f"ZSC-{uuid.uuid4().hex[:8].upper()}"
            
            payment, ref = self.create_payment(reference, email, {description: amount})
            response = self.paynow.send(payment)
            
            if response.success:
                return PaynowResponse(
                    success=True,
                    status="created",
                    redirect_url=response.redirect_url,
                    poll_url=response.poll_url,
                    reference=ref
                )
            else:
                return PaynowResponse(
                    success=False,
                    status="failed",
                    error=response.error
                )
        except Exception as e:
            logger.error(f"Paynow web payment error: {e}")
            return PaynowResponse(
                success=False,
                status="error",
                error=str(e)
            )
    
    async def initiate_mobile_payment(
        self,
        amount: float,
        description: str,
        email: str,
        phone: str,
        method: str = "ecocash",
        reference: str = None
    ) -> PaynowResponse:
        """Initiate mobile money payment (EcoCash, OneMoney, etc.)"""
        try:
            if not reference:
                reference = f"ZSC-{uuid.uuid4().hex[:8].upper()}"
            
            payment, ref = self.create_payment(reference, email, {description: amount})
            
            # Send to specific mobile money provider
            response = self.paynow.send_mobile(payment, phone, method)
            
            if response.success:
                return PaynowResponse(
                    success=True,
                    status="sent",
                    poll_url=response.poll_url,
                    reference=ref
                )
            else:
                return PaynowResponse(
                    success=False,
                    status="failed",
                    error=response.error
                )
        except Exception as e:
            logger.error(f"Paynow mobile payment error: {e}")
            return PaynowResponse(
                success=False,
                status="error",
                error=str(e)
            )
    
    async def check_payment_status(self, poll_url: str) -> PaynowResponse:
        """Check the status of a payment"""
        try:
            status = self.paynow.check_transaction_status(poll_url)
            
            return PaynowResponse(
                success=status.paid,
                status=status.status.lower(),
                reference=status.reference if hasattr(status, 'reference') else None
            )
        except Exception as e:
            logger.error(f"Paynow status check error: {e}")
            return PaynowResponse(
                success=False,
                status="error",
                error=str(e)
            )
