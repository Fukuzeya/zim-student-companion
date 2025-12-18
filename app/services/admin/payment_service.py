# ============================================================================
# Admin Payment & Subscription Service
# ============================================================================
"""
Service layer for payment and subscription management.
Handles payment listing, refunds, subscription plans, and payment provider integration.
"""
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta, date
from uuid import UUID
from decimal import Decimal
import logging

from app.models.user import User, SubscriptionTier
from app.models.payment import Payment, PaymentStatus, PaymentMethod, SubscriptionPlan

logger = logging.getLogger(__name__)


class PaymentManagementService:
    """
    Payment and subscription management service.
    
    Provides:
    - Payment listing with filtering
    - Payment statistics and reporting
    - Refund processing
    - Subscription plan management
    - Payment provider reconciliation
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # =========================================================================
    # Payment Listing
    # =========================================================================
    async def list_payments(
        self,
        status: Optional[str] = None,
        payment_method: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        min_amount: Optional[Decimal] = None,
        max_amount: Optional[Decimal] = None,
        user_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """
        List payments with comprehensive filtering.
        
        Returns:
            Paginated payment list with user details
        """
        query = select(Payment).options(
            selectinload(Payment.user),
            selectinload(Payment.plan)
        )
        count_query = select(func.count(Payment.id))
        
        conditions = []
        
        if status:
            conditions.append(Payment.status == PaymentStatus(status))
        
        if payment_method:
            conditions.append(Payment.payment_method == PaymentMethod(payment_method))
        
        if date_from:
            conditions.append(func.date(Payment.created_at) >= date_from)
        
        if date_to:
            conditions.append(func.date(Payment.created_at) <= date_to)
        
        if min_amount is not None:
            conditions.append(Payment.amount >= min_amount)
        
        if max_amount is not None:
            conditions.append(Payment.amount <= max_amount)
        
        if user_id:
            conditions.append(Payment.user_id == user_id)
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        # Get total
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Paginate and sort
        offset = (page - 1) * page_size
        query = query.order_by(Payment.created_at.desc()).offset(offset).limit(page_size)
        
        result = await self.db.execute(query)
        payments = result.scalars().all()
        
        payment_list = []
        for p in payments:
            payment_list.append({
                "id": str(p.id),
                "user_id": str(p.user_id),
                "user_phone": p.user.phone_number if p.user else None,
                "user_email": p.user.email if p.user else None,
                "plan_id": str(p.plan_id),
                "plan_name": p.plan.name if p.plan else None,
                "amount": float(p.amount),
                "currency": p.currency,
                "payment_method": p.payment_method.value if p.payment_method else None,
                "payment_reference": p.payment_reference,
                "external_reference": p.external_reference,
                "status": p.status.value,
                "error_message": p.error_message,
                "created_at": p.created_at.isoformat(),
                "completed_at": p.completed_at.isoformat() if p.completed_at else None
            })
        
        return {
            "payments": payment_list,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    
    async def get_payment_detail(self, payment_id: UUID) -> Optional[Dict[str, Any]]:
        """Get detailed payment information"""
        result = await self.db.execute(
            select(Payment)
            .options(selectinload(Payment.user), selectinload(Payment.plan))
            .where(Payment.id == payment_id)
        )
        payment = result.scalar_one_or_none()
        
        if not payment:
            return None
        
        return {
            "id": str(payment.id),
            "user_id": str(payment.user_id),
            "user_phone": payment.user.phone_number if payment.user else None,
            "user_email": payment.user.email if payment.user else None,
            "plan_id": str(payment.plan_id),
            "plan_name": payment.plan.name if payment.plan else None,
            "plan_tier": payment.plan.tier.value if payment.plan else None,
            "amount": float(payment.amount),
            "currency": payment.currency,
            "payment_method": payment.payment_method.value if payment.payment_method else None,
            "payment_reference": payment.payment_reference,
            "external_reference": payment.external_reference,
            "paynow_poll_url": payment.paynow_poll_url,
            "status": payment.status.value,
            "error_message": payment.error_message,
            "payment_metadata": payment.payment_metadata,
            "created_at": payment.created_at.isoformat(),
            "updated_at": payment.updated_at.isoformat() if payment.updated_at else None,
            "completed_at": payment.completed_at.isoformat() if payment.completed_at else None
        }
    
    # =========================================================================
    # Payment Statistics
    # =========================================================================
    async def get_payment_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive payment statistics.
        
        Returns:
            MRR, ARR, churn rate, LTV, revenue breakdowns
        """
        now = datetime.utcnow()
        month_ago = now - timedelta(days=30)
        
        # MRR - Monthly Recurring Revenue
        mrr_result = await self.db.execute(
            select(func.sum(Payment.amount))
            .where(Payment.status == PaymentStatus.COMPLETED)
            .where(Payment.completed_at >= month_ago)
        )
        mrr = Decimal(str(mrr_result.scalar() or 0))
        
        # ARR
        arr = mrr * 12
        
        # Active subscriptions count
        active_subs_result = await self.db.execute(
            select(func.count(User.id))
            .where(User.subscription_tier != SubscriptionTier.FREE)
            .where(or_(
                User.subscription_expires_at.is_(None),
                User.subscription_expires_at > now
            ))
        )
        active_subscriptions = active_subs_result.scalar() or 0
        
        # Churned this month (subscriptions that expired)
        churned_result = await self.db.execute(
            select(func.count(User.id))
            .where(User.subscription_expires_at >= month_ago)
            .where(User.subscription_expires_at < now)
        )
        churned = churned_result.scalar() or 0
        
        # Churn rate
        total_paid_start = active_subscriptions + churned
        churn_rate = (churned / total_paid_start * 100) if total_paid_start > 0 else 0
        
        # LTV (simplified)
        total_revenue_result = await self.db.execute(
            select(func.sum(Payment.amount))
            .where(Payment.status == PaymentStatus.COMPLETED)
        )
        total_revenue = Decimal(str(total_revenue_result.scalar() or 0))
        
        total_customers_result = await self.db.execute(
            select(func.count(func.distinct(Payment.user_id)))
            .where(Payment.status == PaymentStatus.COMPLETED)
        )
        total_customers = total_customers_result.scalar() or 1
        
        ltv = total_revenue / total_customers if total_customers > 0 else Decimal("0")
        
        # Revenue by plan
        plan_revenue_result = await self.db.execute(
            select(SubscriptionPlan.name, func.sum(Payment.amount))
            .join(SubscriptionPlan, Payment.plan_id == SubscriptionPlan.id)
            .where(Payment.status == PaymentStatus.COMPLETED)
            .where(Payment.completed_at >= month_ago)
            .group_by(SubscriptionPlan.name)
        )
        revenue_by_plan = {row[0]: float(row[1] or 0) for row in plan_revenue_result.all()}
        
        # Payment method breakdown
        method_result = await self.db.execute(
            select(Payment.payment_method, func.count(Payment.id))
            .where(Payment.status == PaymentStatus.COMPLETED)
            .where(Payment.completed_at >= month_ago)
            .group_by(Payment.payment_method)
        )
        payment_method_breakdown = {
            (row[0].value if row[0] else "unknown"): row[1]
            for row in method_result.all()
        }
        
        # Failed and pending payments
        failed_result = await self.db.execute(
            select(func.count(Payment.id))
            .where(Payment.status == PaymentStatus.FAILED)
            .where(Payment.created_at >= month_ago)
        )
        failed_count = failed_result.scalar() or 0
        
        pending_result = await self.db.execute(
            select(func.count(Payment.id))
            .where(Payment.status == PaymentStatus.PENDING)
        )
        pending_count = pending_result.scalar() or 0
        
        return {
            "mrr": float(mrr),
            "arr": float(arr),
            "active_subscriptions": active_subscriptions,
            "churn_rate": round(churn_rate, 2),
            "ltv": float(ltv),
            "revenue_by_plan": revenue_by_plan,
            "payment_method_breakdown": payment_method_breakdown,
            "failed_payments_count": failed_count,
            "pending_payments_count": pending_count,
            "currency": "USD"
        }
    
    # =========================================================================
    # Refund Processing
    # =========================================================================
    async def process_refund(
        self,
        payment_id: UUID,
        reason: str,
        partial_amount: Optional[Decimal] = None,
        admin_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Process a refund for a payment.
        
        Args:
            payment_id: Payment to refund
            reason: Reason for refund
            partial_amount: Amount for partial refund (None = full refund)
            admin_id: Admin processing the refund
            
        Returns:
            Refund result
        """
        # Get payment
        result = await self.db.execute(
            select(Payment).options(selectinload(Payment.user))
            .where(Payment.id == payment_id)
        )
        payment = result.scalar_one_or_none()
        
        if not payment:
            return {"success": False, "error": "Payment not found"}
        
        if payment.status != PaymentStatus.COMPLETED:
            return {"success": False, "error": "Can only refund completed payments"}
        
        refund_amount = partial_amount if partial_amount else payment.amount
        
        if refund_amount > payment.amount:
            return {"success": False, "error": "Refund amount exceeds payment amount"}
        
        # In production, this would call the payment provider's refund API
        # For now, we'll just update the status
        
        try:
            # Update payment status
            payment.status = PaymentStatus.REFUNDED
            payment.payment_metadata = payment.payment_metadata or {}
            payment.payment_metadata["refund"] = {
                "amount": float(refund_amount),
                "reason": reason,
                "processed_by": str(admin_id) if admin_id else None,
                "processed_at": datetime.utcnow().isoformat()
            }
            
            # If full refund, downgrade user subscription
            if refund_amount == payment.amount and payment.user:
                payment.user.subscription_tier = SubscriptionTier.FREE
                payment.user.subscription_expires_at = None
            
            await self.db.commit()
            
            logger.info(f"Refund processed: Payment {payment_id}, Amount: {refund_amount}")
            
            return {
                "success": True,
                "payment_id": str(payment_id),
                "refund_amount": float(refund_amount),
                "message": "Refund processed successfully"
            }
            
        except Exception as e:
            logger.error(f"Refund failed: {e}")
            await self.db.rollback()
            return {"success": False, "error": str(e)}
    
    # =========================================================================
    # Subscription Plans
    # =========================================================================
    async def list_plans(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """List all subscription plans"""
        query = select(SubscriptionPlan)
        
        if not include_inactive:
            query = query.where(SubscriptionPlan.is_active == True)
        
        query = query.order_by(SubscriptionPlan.price_usd)
        
        result = await self.db.execute(query)
        plans = result.scalars().all()
        
        return [
            {
                "id": str(p.id),
                "name": p.name,
                "tier": p.tier.value,
                "description": p.description,
                "price_usd": float(p.price_usd),
                "price_zwl": float(p.price_zwl) if p.price_zwl else None,
                "duration_days": p.duration_days,
                "features": p.features,
                "limits": p.limits,
                "max_students": p.max_students,
                "discount_percentage": p.discount_percentage,
                "is_popular": p.is_popular,
                "is_active": p.is_active,
                "created_at": p.created_at.isoformat()
            }
            for p in plans
        ]
    
    async def create_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new subscription plan"""
        plan = SubscriptionPlan(
            name=data["name"],
            tier=SubscriptionTier(data["tier"]),
            description=data.get("description"),
            price_usd=Decimal(str(data["price_usd"])),
            price_zwl=Decimal(str(data["price_zwl"])) if data.get("price_zwl") else None,
            duration_days=data["duration_days"],
            features=data.get("features", []),
            limits=data.get("limits", {}),
            max_students=data.get("max_students", 1),
            discount_percentage=data.get("discount_percentage", 0),
            is_popular=data.get("is_popular", False)
        )
        
        self.db.add(plan)
        await self.db.commit()
        await self.db.refresh(plan)
        
        logger.info(f"Created subscription plan: {plan.name}")
        
        return {"id": str(plan.id), "message": "Plan created successfully"}
    
    async def update_plan(self, plan_id: UUID, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing subscription plan"""
        result = await self.db.execute(select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id))
        plan = result.scalar_one_or_none()
        
        if not plan:
            return None
        
        for field, value in updates.items():
            if value is not None and hasattr(plan, field):
                if field == "tier":
                    value = SubscriptionTier(value)
                elif field in ["price_usd", "price_zwl"]:
                    value = Decimal(str(value))
                setattr(plan, field, value)
        
        await self.db.commit()
        return {"id": str(plan.id), "message": "Plan updated successfully"}
    
    async def delete_plan(self, plan_id: UUID) -> bool:
        """Soft delete a subscription plan"""
        result = await self.db.execute(
            update(SubscriptionPlan)
            .where(SubscriptionPlan.id == plan_id)
            .values(is_active=False)
        )
        await self.db.commit()
        return result.rowcount > 0
    
    # =========================================================================
    # Subscription Management
    # =========================================================================
    async def list_subscriptions(
        self,
        tier: Optional[str] = None,
        status: Optional[str] = None,  # active, expired, expiring_soon
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """List user subscriptions with filtering"""
        now = datetime.utcnow()
        soon = now + timedelta(days=7)
        
        query = select(User).where(User.subscription_tier != SubscriptionTier.FREE)
        count_query = select(func.count(User.id)).where(User.subscription_tier != SubscriptionTier.FREE)
        
        conditions = []
        
        if tier:
            conditions.append(User.subscription_tier == SubscriptionTier(tier))
        
        if status == "active":
            conditions.append(or_(
                User.subscription_expires_at.is_(None),
                User.subscription_expires_at > now
            ))
        elif status == "expired":
            conditions.append(User.subscription_expires_at < now)
        elif status == "expiring_soon":
            conditions.append(and_(
                User.subscription_expires_at > now,
                User.subscription_expires_at <= soon
            ))
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        # Get total
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Paginate
        offset = (page - 1) * page_size
        query = query.order_by(User.subscription_expires_at).offset(offset).limit(page_size)
        
        result = await self.db.execute(query)
        users = result.scalars().all()
        
        subscriptions = []
        for user in users:
            is_active = (
                user.subscription_expires_at is None or
                user.subscription_expires_at > now
            )
            days_remaining = 0
            if user.subscription_expires_at:
                days_remaining = max(0, (user.subscription_expires_at - now).days)
            
            subscriptions.append({
                "user_id": str(user.id),
                "phone_number": user.phone_number,
                "email": user.email,
                "tier": user.subscription_tier.value,
                "expires_at": user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
                "is_active": is_active,
                "days_remaining": days_remaining
            })
        
        return {
            "subscriptions": subscriptions,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    
    async def modify_subscription(
        self,
        user_id: UUID,
        new_tier: str,
        expires_at: Optional[datetime] = None,
        admin_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Manually modify a user's subscription.
        
        Used for customer service, promotions, etc.
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return {"success": False, "error": "User not found"}
        
        old_tier = user.subscription_tier.value
        user.subscription_tier = SubscriptionTier(new_tier)
        
        if expires_at:
            user.subscription_expires_at = expires_at
        elif new_tier != "free":
            # Default to 30 days if no expiry specified
            user.subscription_expires_at = datetime.utcnow() + timedelta(days=30)
        else:
            user.subscription_expires_at = None
        
        await self.db.commit()
        
        logger.info(
            f"Subscription modified: User {user_id}, {old_tier} -> {new_tier}, "
            f"by admin {admin_id}"
        )
        
        return {
            "success": True,
            "user_id": str(user_id),
            "old_tier": old_tier,
            "new_tier": new_tier,
            "expires_at": user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
            "message": "Subscription modified successfully"
        }