# ============================================================================
# Subscription Management
# ============================================================================
from typing import Optional, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from uuid import UUID
from datetime import datetime, timedelta
import logging

from app.models.user import User, SubscriptionTier
from app.models.payment import Payment, SubscriptionPlan, PaymentStatus, PaymentMethod
from app.services.payments.paynow_client import PaynowClient, PaynowResponse
from app.services.whatsapp.client import WhatsAppClient

logger = logging.getLogger(__name__)

class SubscriptionManager:
    """Manages user subscriptions and payments"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.paynow = PaynowClient()
    
    async def get_available_plans(self, education_level: str = None) -> List[Dict]:
        """Get all available subscription plans"""
        query = select(SubscriptionPlan).where(SubscriptionPlan.is_active == True)
        result = await self.db.execute(query)
        plans = result.scalars().all()
        
        return [
            {
                "id": str(plan.id),
                "name": plan.name,
                "tier": plan.tier.value,
                "price_usd": float(plan.price_usd),
                "price_zwl": float(plan.price_zwl) if plan.price_zwl else None,
                "duration_days": plan.duration_days,
                "features": plan.features,
                "limits": plan.limits,
                "is_popular": plan.is_popular,
                "discount_percentage": plan.discount_percentage
            }
            for plan in plans
        ]
    
    async def initiate_subscription(
        self,
        user_id: UUID,
        plan_id: UUID,
        payment_method: PaymentMethod,
        phone: str = None,
        email: str = None
    ) -> Dict:
        """Initiate a subscription payment"""
        # Get plan
        plan = await self.db.get(SubscriptionPlan, plan_id)
        if not plan:
            return {"success": False, "error": "Plan not found"}
        
        # Get user
        user = await self.db.get(User, user_id)
        if not user:
            return {"success": False, "error": "User not found"}
        
        # Create payment record
        payment = Payment(
            user_id=user_id,
            plan_id=plan_id,
            amount=plan.price_usd,
            currency="USD",
            payment_method=payment_method,
            status=PaymentStatus.PENDING
        )
        self.db.add(payment)
        await self.db.flush()
        
        # Initiate payment with Paynow
        description = f"Zim Student Companion - {plan.name} Subscription"
        reference = f"ZSC-{str(payment.id)[:8].upper()}"
        payment.payment_reference = reference
        
        if payment_method in [PaymentMethod.ECOCASH, PaymentMethod.ONEMONEY, 
                             PaymentMethod.INNBUCKS, PaymentMethod.TELECASH]:
            # Mobile money payment
            response = await self.paynow.initiate_mobile_payment(
                amount=float(plan.price_usd),
                description=description,
                email=email or f"{phone}@zimstudent.com",
                phone=phone,
                method=payment_method.value,
                reference=reference
            )
        else:
            # Web payment (card/bank)
            response = await self.paynow.initiate_web_payment(
                amount=float(plan.price_usd),
                description=description,
                email=email or f"{user.phone_number}@zimstudent.com",
                reference=reference
            )
        
        if response.success:
            payment.paynow_poll_url = response.poll_url
            payment.status = PaymentStatus.PROCESSING
            await self.db.commit()
            
            return {
                "success": True,
                "payment_id": str(payment.id),
                "reference": reference,
                "redirect_url": response.redirect_url,
                "poll_url": response.poll_url,
                "message": "Payment initiated. Please complete the payment on your device."
            }
        else:
            payment.status = PaymentStatus.FAILED
            payment.error_message = response.error
            await self.db.commit()
            
            return {
                "success": False,
                "error": response.error or "Payment initiation failed"
            }
    
    async def check_payment_status(self, payment_id: UUID) -> Dict:
        """Check and update payment status"""
        payment = await self.db.get(Payment, payment_id)
        if not payment:
            return {"success": False, "error": "Payment not found"}
        
        if payment.status == PaymentStatus.COMPLETED:
            return {"success": True, "status": "completed", "message": "Payment already completed"}
        
        if not payment.paynow_poll_url:
            return {"success": False, "error": "No poll URL available"}
        
        # Check with Paynow
        response = await self.paynow.check_payment_status(payment.paynow_poll_url)
        
        if response.success and response.status == "paid":
            # Payment successful - activate subscription
            await self._activate_subscription(payment)
            return {
                "success": True,
                "status": "completed",
                "message": "Payment successful! Your subscription is now active."
            }
        elif response.status in ["cancelled", "failed"]:
            payment.status = PaymentStatus.FAILED
            await self.db.commit()
            return {
                "success": False,
                "status": response.status,
                "message": "Payment was not successful"
            }
        else:
            return {
                "success": False,
                "status": response.status,
                "message": "Payment is still pending"
            }
    
    async def _activate_subscription(self, payment: Payment) -> None:
        """Activate user subscription after successful payment"""
        plan = await self.db.get(SubscriptionPlan, payment.plan_id)
        user = await self.db.get(User, payment.user_id)
        
        # Update payment status
        payment.status = PaymentStatus.COMPLETED
        payment.completed_at = datetime.utcnow()
        
        # Calculate expiry
        current_expiry = user.subscription_expires_at
        if current_expiry and current_expiry > datetime.utcnow():
            # Extend existing subscription
            new_expiry = current_expiry + timedelta(days=plan.duration_days)
        else:
            # New subscription
            new_expiry = datetime.utcnow() + timedelta(days=plan.duration_days)
        
        # Update user subscription
        user.subscription_tier = plan.tier
        user.subscription_expires_at = new_expiry
        
        await self.db.commit()
        
        # Send confirmation via WhatsApp
        try:
            wa_client = WhatsAppClient()
            await wa_client.send_text(
                user.phone_number,
                f"🎉 *Payment Successful!*\n\n"
                f"Your {plan.name} subscription is now active!\n\n"
                f"📅 Valid until: {new_expiry.strftime('%d %B %Y')}\n"
                f"💎 Tier: {plan.tier.value.title()}\n\n"
                f"Enjoy unlimited learning! Type *menu* to get started."
            )
        except Exception as e:
            logger.error(f"Failed to send confirmation: {e}")
    
    async def handle_paynow_callback(self, data: Dict) -> bool:
        """Handle Paynow webhook callback"""
        try:
            reference = data.get("reference")
            status = data.get("status", "").lower()
            
            # Find payment by reference
            result = await self.db.execute(
                select(Payment).where(Payment.payment_reference == reference)
            )
            payment = result.scalar_one_or_none()
            
            if not payment:
                logger.warning(f"Payment not found for reference: {reference}")
                return False
            
            if status == "paid":
                await self._activate_subscription(payment)
                return True
            elif status in ["cancelled", "failed"]:
                payment.status = PaymentStatus.FAILED
                await self.db.commit()
                return True
            
            return True
        except Exception as e:
            logger.error(f"Paynow callback error: {e}")
            return False
    
    async def check_subscription_status(self, user_id: UUID) -> Dict:
        """Check user's current subscription status"""
        user = await self.db.get(User, user_id)
        if not user:
            return {"error": "User not found"}
        
        now = datetime.utcnow()
        is_active = (
            user.subscription_tier != SubscriptionTier.FREE and
            user.subscription_expires_at and
            user.subscription_expires_at > now
        )
        
        days_remaining = 0
        if user.subscription_expires_at and user.subscription_expires_at > now:
            days_remaining = (user.subscription_expires_at - now).days
        
        # Get plan details
        result = await self.db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.tier == user.subscription_tier)
        )
        plan = result.scalar_one_or_none()
        
        return {
            "tier": user.subscription_tier.value,
            "is_active": is_active,
            "expires_at": user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
            "days_remaining": days_remaining,
            "features": plan.features if plan else [],
            "limits": plan.limits if plan else {}
        }
    
    async def cancel_subscription(self, user_id: UUID) -> Dict:
        """Cancel user subscription (won't renew)"""
        user = await self.db.get(User, user_id)
        if not user:
            return {"success": False, "error": "User not found"}
        
        # Don't immediately downgrade - let it expire
        # Just mark for non-renewal (could add a field for this)
        
        return {
            "success": True,
            "message": f"Your subscription will remain active until {user.subscription_expires_at.strftime('%d %B %Y')} and will not renew."
        }
