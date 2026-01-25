# ============================================================================
# Admin Payment & Subscription Service - Production Grade
# ============================================================================
"""
Production-grade payment and subscription management service.
Includes comprehensive statistics, reconciliation, fraud detection, and audit logging.
"""
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, update, case, text
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta, date, timezone
from uuid import UUID, uuid4
from decimal import Decimal
import logging
import hashlib
import hmac
import csv
import io
from collections import defaultdict

from app.models.user import User, SubscriptionTier
from app.models.payment import Payment, PaymentStatus, PaymentMethod, SubscriptionPlan
from app.config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)


class PaymentManagementService:
    """
    Production-grade payment and subscription management service.

    Features:
    - Payment listing with advanced filtering
    - Comprehensive payment statistics (MRR, ARR, LTV, ARPU, churn)
    - Refund processing with audit trail
    - Subscription plan CRUD
    - Payment reconciliation
    - Fraud detection helpers
    - Export functionality
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._idempotency_cache: Dict[str, UUID] = {}

    # =========================================================================
    # Idempotency Key Management
    # =========================================================================
    async def check_idempotency_key(self, key: str, user_id: UUID) -> Optional[UUID]:
        """
        Check if an idempotency key has already been used.
        Returns existing payment_id if key exists, None otherwise.
        """
        cache_key = f"{user_id}:{key}"
        if cache_key in self._idempotency_cache:
            return self._idempotency_cache[cache_key]

        # Check database for existing payment with this idempotency key
        result = await self.db.execute(
            select(Payment.id)
            .where(
                and_(
                    Payment.user_id == user_id,
                    Payment.payment_metadata.op('->>')('idempotency_key') == key
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            self._idempotency_cache[cache_key] = existing
        return existing

    async def store_idempotency_key(self, key: str, user_id: UUID, payment_id: UUID):
        """Store idempotency key mapping"""
        self._idempotency_cache[f"{user_id}:{key}"] = payment_id

    # =========================================================================
    # Webhook Signature Verification
    # =========================================================================
    @staticmethod
    def verify_paynow_signature(
        payload: Dict[str, Any],
        received_hash: str,
        integration_key: str
    ) -> bool:
        """
        Verify Paynow webhook signature.

        Paynow uses HMAC-SHA512 for webhook signatures.
        """
        # Build string to hash (all values except 'hash' concatenated)
        values_to_hash = []
        for key in sorted(payload.keys()):
            if key.lower() != 'hash':
                values_to_hash.append(str(payload[key]))

        concat_string = ''.join(values_to_hash) + integration_key

        # Generate expected hash
        expected_hash = hashlib.sha512(concat_string.encode()).hexdigest().upper()

        # Compare securely
        return hmac.compare_digest(expected_hash, received_hash.upper())

    # =========================================================================
    # Payment Listing with Advanced Filtering
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
        search_query: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """
        List payments with comprehensive filtering and search.

        Returns paginated payment list with summary statistics.
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

        if search_query:
            search_pattern = f"%{search_query}%"
            conditions.append(or_(
                Payment.payment_reference.ilike(search_pattern),
                Payment.external_reference.ilike(search_pattern),
                Payment.user.has(User.email.ilike(search_pattern)),
                Payment.user.has(User.phone_number.ilike(search_pattern))
            ))

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        # Get total
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Sort
        sort_column = getattr(Payment, sort_by, Payment.created_at)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # Paginate
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(query)
        payments = result.scalars().all()

        # Build response
        payment_list = []
        for p in payments:
            payment_list.append(self._format_payment(p))

        # Calculate summary for current filter
        summary = await self._calculate_payment_summary(conditions)

        return {
            "payments": payment_list,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "summary": summary
        }

    def _format_payment(self, p: Payment) -> Dict[str, Any]:
        """Format payment for API response"""
        refund_info = p.payment_metadata.get("refund") if p.payment_metadata else None

        return {
            "id": str(p.id),
            "user_id": str(p.user_id),
            "user_phone": p.user.phone_number if p.user else None,
            "user_email": p.user.email if p.user else None,
            "user_name": self._get_user_display_name(p.user) if p.user else None,
            "plan_id": str(p.plan_id),
            "plan_name": p.plan.name if p.plan else None,
            "plan_tier": p.plan.tier.value if p.plan else None,
            "amount": float(p.amount),
            "original_amount": float(p.amount),
            "refunded_amount": float(refund_info.get("amount", 0)) if refund_info else 0,
            "currency": p.currency,
            "payment_method": p.payment_method.value if p.payment_method else None,
            "payment_reference": p.payment_reference,
            "external_reference": p.external_reference,
            "status": p.status.value,
            "error_message": p.error_message,
            "created_at": p.created_at.isoformat(),
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            "completed_at": p.completed_at.isoformat() if p.completed_at else None
        }

    def _get_user_display_name(self, user: User) -> str:
        """Get display name for user"""
        if user.email:
            return user.email.split('@')[0].title()
        if user.phone_number:
            return f"User {user.phone_number[-4:]}"
        return f"User {str(user.id)[:8]}"

    async def _calculate_payment_summary(self, conditions: List) -> Dict[str, Any]:
        """Calculate summary statistics for filtered payments"""
        # Total amount by status
        status_query = select(
            Payment.status,
            func.count(Payment.id).label("count"),
            func.sum(Payment.amount).label("total")
        ).group_by(Payment.status)

        if conditions:
            status_query = status_query.where(and_(*conditions))

        status_result = await self.db.execute(status_query)
        status_breakdown = {
            row.status.value: {"count": row.count, "total": float(row.total or 0)}
            for row in status_result.all()
        }

        return {
            "total_amount": sum(s["total"] for s in status_breakdown.values()),
            "by_status": status_breakdown
        }

    async def get_payment_detail(self, payment_id: UUID) -> Optional[Dict[str, Any]]:
        """Get comprehensive payment details including history"""
        result = await self.db.execute(
            select(Payment)
            .options(selectinload(Payment.user), selectinload(Payment.plan))
            .where(Payment.id == payment_id)
        )
        payment = result.scalar_one_or_none()

        if not payment:
            return None

        # Build status history from metadata
        status_history = []
        if payment.payment_metadata and "status_history" in payment.payment_metadata:
            status_history = payment.payment_metadata["status_history"]

        # Build refund history
        refund_history = []
        if payment.payment_metadata and "refunds" in payment.payment_metadata:
            refund_history = payment.payment_metadata["refunds"]
        elif payment.payment_metadata and "refund" in payment.payment_metadata:
            refund_history = [payment.payment_metadata["refund"]]

        return {
            "id": str(payment.id),
            "user_id": str(payment.user_id),
            "user_phone": payment.user.phone_number if payment.user else None,
            "user_email": payment.user.email if payment.user else None,
            "user_name": self._get_user_display_name(payment.user) if payment.user else None,
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
            "status_history": status_history,
            "refund_history": refund_history,
            "ip_address": payment.payment_metadata.get("ip_address") if payment.payment_metadata else None,
            "user_agent": payment.payment_metadata.get("user_agent") if payment.payment_metadata else None,
            "created_at": payment.created_at.isoformat(),
            "updated_at": payment.updated_at.isoformat() if payment.updated_at else None,
            "completed_at": payment.completed_at.isoformat() if payment.completed_at else None
        }

    # =========================================================================
    # Comprehensive Payment Statistics
    # =========================================================================
    async def get_payment_stats(
        self,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get comprehensive payment and subscription statistics.

        Includes:
        - MRR, ARR, LTV, ARPU
        - Churn rate
        - Revenue breakdowns
        - Trend data
        - Success rates
        """
        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=period_days)
        prev_period_start = period_start - timedelta(days=period_days)

        # Current period revenue
        current_revenue = await self._get_period_revenue(period_start, now)
        prev_revenue = await self._get_period_revenue(prev_period_start, period_start)

        # Active subscriptions
        active_subs = await self._count_active_subscriptions()
        prev_active_subs = await self._count_subscriptions_at_date(period_start)

        # Churned subscriptions
        churned = await self._count_churned_subscriptions(period_start, now)

        # Calculate metrics
        mrr = current_revenue
        arr = mrr * 12

        total_paid_start = prev_active_subs if prev_active_subs > 0 else 1
        churn_rate = (churned / total_paid_start * 100) if total_paid_start > 0 else 0

        # LTV calculation
        ltv = await self._calculate_ltv()

        # ARPU
        arpu = mrr / active_subs if active_subs > 0 else Decimal("0")

        # Transaction metrics
        tx_stats = await self._get_transaction_stats(period_start, now)

        # Revenue breakdowns
        revenue_by_plan = await self._get_revenue_by_plan(period_start, now)
        revenue_by_method = await self._get_revenue_by_method(period_start, now)

        # Trend data (daily)
        revenue_trend = await self._get_revenue_trend(period_start, now)

        # Growth metrics
        mrr_growth = ((current_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
        sub_growth = ((active_subs - prev_active_subs) / prev_active_subs * 100) if prev_active_subs > 0 else 0

        return {
            # Key Metrics
            "mrr": float(mrr),
            "arr": float(arr),
            "active_subscriptions": active_subs,
            "total_subscribers": await self._count_total_subscribers(),

            # Health Metrics
            "churn_rate": round(churn_rate, 2),
            "ltv": float(ltv),
            "arpu": float(arpu),

            # Transaction Metrics
            "total_revenue_30d": float(current_revenue),
            "total_transactions_30d": tx_stats["total"],
            "successful_transactions_30d": tx_stats["completed"],
            "failed_transactions_30d": tx_stats["failed"],
            "refunded_amount_30d": float(tx_stats["refunded_amount"]),
            "average_transaction_value": float(tx_stats["average"]),

            # Success Metrics
            "payment_success_rate": tx_stats["success_rate"],
            "refund_rate": tx_stats["refund_rate"],
            "dispute_rate": 0.0,  # Placeholder - needs dispute tracking

            # Breakdowns
            "revenue_by_plan": revenue_by_plan,
            "revenue_by_method": revenue_by_method,
            "revenue_trend": revenue_trend,

            # Growth
            "mrr_growth": round(mrr_growth, 2),
            "subscriber_growth": round(sub_growth, 2),

            # Period Info
            "period_start": period_start.date().isoformat(),
            "period_end": now.date().isoformat(),
            "currency": "USD"
        }

    async def _get_period_revenue(self, start: datetime, end: datetime) -> Decimal:
        """Get total revenue for a period"""
        result = await self.db.execute(
            select(func.sum(Payment.amount))
            .where(Payment.status == PaymentStatus.COMPLETED)
            .where(Payment.completed_at >= start)
            .where(Payment.completed_at < end)
        )
        return Decimal(str(result.scalar() or 0))

    async def _count_active_subscriptions(self) -> int:
        """Count currently active paid subscriptions"""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(func.count(User.id))
            .where(User.subscription_tier != SubscriptionTier.FREE)
            .where(or_(
                User.subscription_expires_at.is_(None),
                User.subscription_expires_at > now
            ))
        )
        return result.scalar() or 0

    async def _count_subscriptions_at_date(self, target_date: datetime) -> int:
        """Estimate subscription count at a past date"""
        # Count users with expiry after target date
        result = await self.db.execute(
            select(func.count(User.id))
            .where(User.subscription_tier != SubscriptionTier.FREE)
            .where(User.subscription_expires_at > target_date)
        )
        return result.scalar() or 0

    async def _count_churned_subscriptions(self, start: datetime, end: datetime) -> int:
        """Count subscriptions that expired in period"""
        result = await self.db.execute(
            select(func.count(User.id))
            .where(User.subscription_expires_at >= start)
            .where(User.subscription_expires_at < end)
        )
        return result.scalar() or 0

    async def _count_total_subscribers(self) -> int:
        """Count all users who have ever had a paid subscription"""
        result = await self.db.execute(
            select(func.count(func.distinct(Payment.user_id)))
            .where(Payment.status == PaymentStatus.COMPLETED)
        )
        return result.scalar() or 0

    async def _calculate_ltv(self) -> Decimal:
        """Calculate customer lifetime value"""
        # LTV = Average Revenue Per Customer / Churn Rate
        total_revenue_result = await self.db.execute(
            select(func.sum(Payment.amount))
            .where(Payment.status == PaymentStatus.COMPLETED)
        )
        total_revenue = Decimal(str(total_revenue_result.scalar() or 0))

        total_customers = await self._count_total_subscribers()

        if total_customers == 0:
            return Decimal("0")

        return total_revenue / total_customers

    async def _get_transaction_stats(self, start: datetime, end: datetime) -> Dict[str, Any]:
        """Get transaction statistics for period"""
        result = await self.db.execute(
            select(
                Payment.status,
                func.count(Payment.id).label("count"),
                func.sum(Payment.amount).label("total")
            )
            .where(Payment.created_at >= start)
            .where(Payment.created_at < end)
            .group_by(Payment.status)
        )

        stats = {row.status: {"count": row.count, "total": float(row.total or 0)}
                 for row in result.all()}

        total = sum(s["count"] for s in stats.values())
        completed = stats.get(PaymentStatus.COMPLETED, {"count": 0, "total": 0})
        failed = stats.get(PaymentStatus.FAILED, {"count": 0})
        refunded = stats.get(PaymentStatus.REFUNDED, {"count": 0, "total": 0})

        return {
            "total": total,
            "completed": completed["count"],
            "failed": failed["count"],
            "refunded_amount": Decimal(str(refunded["total"])),
            "average": Decimal(str(completed["total"] / completed["count"])) if completed["count"] > 0 else Decimal("0"),
            "success_rate": round(completed["count"] / total * 100, 2) if total > 0 else 0,
            "refund_rate": round(refunded["count"] / completed["count"] * 100, 2) if completed["count"] > 0 else 0
        }

    async def _get_revenue_by_plan(self, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        """Get revenue breakdown by subscription plan"""
        result = await self.db.execute(
            select(
                SubscriptionPlan.id,
                SubscriptionPlan.name,
                SubscriptionPlan.tier,
                func.sum(Payment.amount).label("revenue"),
                func.count(Payment.id).label("count")
            )
            .join(SubscriptionPlan, Payment.plan_id == SubscriptionPlan.id)
            .where(Payment.status == PaymentStatus.COMPLETED)
            .where(Payment.completed_at >= start)
            .where(Payment.completed_at < end)
            .group_by(SubscriptionPlan.id, SubscriptionPlan.name, SubscriptionPlan.tier)
            .order_by(func.sum(Payment.amount).desc())
        )

        rows = result.all()
        total_revenue = sum(float(row.revenue or 0) for row in rows)

        return [
            {
                "plan_id": str(row.id),
                "plan_name": row.name,
                "tier": row.tier.value,
                "revenue": float(row.revenue or 0),
                "transaction_count": row.count,
                "percentage": round(float(row.revenue or 0) / total_revenue * 100, 1) if total_revenue > 0 else 0
            }
            for row in rows
        ]

    async def _get_revenue_by_method(self, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        """Get revenue breakdown by payment method"""
        result = await self.db.execute(
            select(
                Payment.payment_method,
                func.sum(case(
                    (Payment.status == PaymentStatus.COMPLETED, Payment.amount),
                    else_=0
                )).label("revenue"),
                func.count(case(
                    (Payment.status == PaymentStatus.COMPLETED, 1)
                )).label("success_count"),
                func.count(Payment.id).label("total_count")
            )
            .where(Payment.created_at >= start)
            .where(Payment.created_at < end)
            .where(Payment.payment_method.isnot(None))
            .group_by(Payment.payment_method)
            .order_by(func.sum(Payment.amount).desc())
        )

        rows = result.all()
        total_revenue = sum(float(row.revenue or 0) for row in rows)

        return [
            {
                "method": row.payment_method.value if row.payment_method else "unknown",
                "revenue": float(row.revenue or 0),
                "transaction_count": row.success_count,
                "percentage": round(float(row.revenue or 0) / total_revenue * 100, 1) if total_revenue > 0 else 0,
                "success_rate": round(row.success_count / row.total_count * 100, 1) if row.total_count > 0 else 0
            }
            for row in rows
        ]

    async def _get_revenue_trend(self, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        """Get daily revenue trend"""
        result = await self.db.execute(
            select(
                func.date(Payment.completed_at).label("date"),
                func.sum(Payment.amount).label("revenue"),
                func.count(Payment.id).label("count")
            )
            .where(Payment.status == PaymentStatus.COMPLETED)
            .where(Payment.completed_at >= start)
            .where(Payment.completed_at < end)
            .group_by(func.date(Payment.completed_at))
            .order_by(func.date(Payment.completed_at))
        )

        return [
            {
                "date": str(row.date),
                "revenue": float(row.revenue or 0),
                "transaction_count": row.count,
                "new_subscriptions": 0,  # Placeholder
                "churned_subscriptions": 0  # Placeholder
            }
            for row in result.all()
        ]

    # =========================================================================
    # Refund Processing
    # =========================================================================
    async def process_refund(
        self,
        payment_id: UUID,
        reason: str,
        partial_amount: Optional[Decimal] = None,
        admin_id: Optional[UUID] = None,
        notify_user: bool = True,
        internal_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a refund for a payment with full audit trail.
        """
        # Get payment
        result = await self.db.execute(
            select(Payment).options(selectinload(Payment.user))
            .where(Payment.id == payment_id)
        )
        payment = result.scalar_one_or_none()

        if not payment:
            return {"success": False, "error": "Payment not found"}

        if payment.status not in [PaymentStatus.COMPLETED, PaymentStatus.PARTIALLY_REFUNDED]:
            return {"success": False, "error": f"Cannot refund payment with status: {payment.status.value}"}

        # Calculate refund amount
        already_refunded = Decimal("0")
        if payment.payment_metadata and "refunds" in payment.payment_metadata:
            already_refunded = sum(
                Decimal(str(r.get("amount", 0)))
                for r in payment.payment_metadata["refunds"]
            )

        max_refundable = payment.amount - already_refunded
        refund_amount = partial_amount if partial_amount else max_refundable

        if refund_amount > max_refundable:
            return {
                "success": False,
                "error": f"Refund amount ({refund_amount}) exceeds refundable amount ({max_refundable})"
            }

        if refund_amount <= 0:
            return {"success": False, "error": "Payment has already been fully refunded"}

        try:
            # Generate refund reference
            refund_reference = f"REF-{uuid4().hex[:8].upper()}"

            # Update payment metadata
            payment.payment_metadata = payment.payment_metadata or {}

            # Initialize refunds list if not exists
            if "refunds" not in payment.payment_metadata:
                payment.payment_metadata["refunds"] = []

            # Add refund record
            refund_record = {
                "reference": refund_reference,
                "amount": float(refund_amount),
                "reason": reason,
                "internal_notes": internal_notes,
                "processed_by": str(admin_id) if admin_id else None,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "notify_user": notify_user
            }
            payment.payment_metadata["refunds"].append(refund_record)

            # Add to status history
            if "status_history" not in payment.payment_metadata:
                payment.payment_metadata["status_history"] = []

            old_status = payment.status.value

            # Determine new status
            total_refunded = already_refunded + refund_amount
            if total_refunded >= payment.amount:
                payment.status = PaymentStatus.REFUNDED
            else:
                payment.status = PaymentStatus.PARTIALLY_REFUNDED

            payment.payment_metadata["status_history"].append({
                "from_status": old_status,
                "to_status": payment.status.value,
                "changed_at": datetime.now(timezone.utc).isoformat(),
                "changed_by": str(admin_id) if admin_id else None,
                "reason": f"Refund: {reason}"
            })

            # If full refund, downgrade user subscription
            if payment.status == PaymentStatus.REFUNDED and payment.user:
                payment.user.subscription_tier = SubscriptionTier.FREE
                payment.user.subscription_expires_at = None

            await self.db.commit()

            logger.info(
                f"Refund processed: Payment {payment_id}, Amount: {refund_amount}, "
                f"Reference: {refund_reference}, Admin: {admin_id}"
            )

            return {
                "success": True,
                "payment_id": str(payment_id),
                "refund_amount": float(refund_amount),
                "refund_reference": refund_reference,
                "new_payment_status": payment.status.value,
                "message": "Refund processed successfully",
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "processed_by": str(admin_id) if admin_id else None
            }

        except Exception as e:
            logger.error(f"Refund failed: {e}")
            await self.db.rollback()
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Subscription Plans
    # =========================================================================
    async def list_plans(
        self,
        include_inactive: bool = False
    ) -> Dict[str, Any]:
        """List all subscription plans with subscriber counts"""
        query = select(SubscriptionPlan)

        if not include_inactive:
            query = query.where(SubscriptionPlan.is_active == True)

        query = query.order_by(SubscriptionPlan.price_usd)

        result = await self.db.execute(query)
        plans = result.scalars().all()

        # Get subscriber counts per tier
        tier_counts = await self._get_tier_subscriber_counts()

        plan_list = []
        popular_plan_id = None
        active_count = 0

        for p in plans:
            if p.is_active:
                active_count += 1
            if p.is_popular:
                popular_plan_id = p.id

            plan_list.append({
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
                "subscriber_count": tier_counts.get(p.tier.value, 0),
                "created_at": p.created_at.isoformat() if p.created_at else None
            })

        return {
            "items": plan_list,
            "total": len(plan_list),
            "active_count": active_count,
            "popular_plan_id": str(popular_plan_id) if popular_plan_id else None
        }

    async def _get_tier_subscriber_counts(self) -> Dict[str, int]:
        """Get count of subscribers per tier"""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(
                User.subscription_tier,
                func.count(User.id).label("count")
            )
            .where(User.subscription_tier != SubscriptionTier.FREE)
            .where(or_(
                User.subscription_expires_at.is_(None),
                User.subscription_expires_at > now
            ))
            .group_by(User.subscription_tier)
        )
        return {row.subscription_tier.value: row.count for row in result.all()}

    async def create_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new subscription plan"""
        # Validate tier
        try:
            tier = SubscriptionTier(data["tier"])
        except ValueError:
            return {"success": False, "error": f"Invalid tier: {data['tier']}"}

        # Check for duplicate name
        existing = await self.db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.name == data["name"])
        )
        if existing.scalar_one_or_none():
            return {"success": False, "error": "A plan with this name already exists"}

        plan = SubscriptionPlan(
            name=data["name"],
            tier=tier,
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

        logger.info(f"Created subscription plan: {plan.name} ({plan.tier.value})")

        return {
            "success": True,
            "id": str(plan.id),
            "message": "Plan created successfully"
        }

    async def update_plan(
        self,
        plan_id: UUID,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update an existing subscription plan"""
        result = await self.db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
        )
        plan = result.scalar_one_or_none()

        if not plan:
            return None

        # Track changes for audit
        changes = []

        for field, value in updates.items():
            if value is not None and hasattr(plan, field):
                old_value = getattr(plan, field)

                if field == "tier":
                    value = SubscriptionTier(value)
                elif field in ["price_usd", "price_zwl"]:
                    value = Decimal(str(value))

                if old_value != value:
                    changes.append({"field": field, "old": str(old_value), "new": str(value)})
                    setattr(plan, field, value)

        await self.db.commit()

        logger.info(f"Updated subscription plan: {plan.name}, Changes: {changes}")

        return {
            "success": True,
            "id": str(plan.id),
            "message": "Plan updated successfully",
            "changes": changes
        }

    async def delete_plan(self, plan_id: UUID) -> Dict[str, Any]:
        """Soft delete a subscription plan"""
        result = await self.db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
        )
        plan = result.scalar_one_or_none()

        if not plan:
            return {"success": False, "error": "Plan not found"}

        # Check if plan has active subscribers
        tier_counts = await self._get_tier_subscriber_counts()
        if tier_counts.get(plan.tier.value, 0) > 0:
            return {
                "success": False,
                "error": f"Cannot delete plan with active subscribers ({tier_counts[plan.tier.value]} users)"
            }

        plan.is_active = False
        await self.db.commit()

        logger.info(f"Deactivated subscription plan: {plan.name}")

        return {"success": True, "message": "Plan deactivated successfully"}

    # =========================================================================
    # Subscription Management
    # =========================================================================
    async def list_subscriptions(
        self,
        tier: Optional[str] = None,
        status: Optional[str] = None,
        search_query: Optional[str] = None,
        sort_by: str = "expires_at",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """List user subscriptions with filtering"""
        now = datetime.now(timezone.utc)
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

        if search_query:
            search_pattern = f"%{search_query}%"
            conditions.append(or_(
                User.email.ilike(search_pattern),
                User.phone_number.ilike(search_pattern)
            ))

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        # Get total
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Sort
        if sort_by == "expires_at":
            sort_col = User.subscription_expires_at
        elif sort_by == "tier":
            sort_col = User.subscription_tier
        else:
            sort_col = User.subscription_expires_at

        if sort_order == "desc":
            query = query.order_by(sort_col.desc().nulls_last())
        else:
            query = query.order_by(sort_col.asc().nulls_last())

        # Paginate
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

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

            # Determine status
            if not is_active:
                sub_status = "expired"
            elif days_remaining <= 7:
                sub_status = "expiring_soon"
            else:
                sub_status = "active"

            subscriptions.append({
                "user_id": str(user.id),
                "phone_number": user.phone_number,
                "email": user.email,
                "user_name": self._get_user_display_name(user),
                "tier": user.subscription_tier.value,
                "status": sub_status,
                "expires_at": user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
                "is_active": is_active,
                "days_remaining": days_remaining,
                "auto_renew": False  # Placeholder - needs auto-renew implementation
            })

        # Calculate summary
        summary = await self._get_subscription_summary()

        return {
            "subscriptions": subscriptions,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "summary": summary
        }

    async def _get_subscription_summary(self) -> Dict[str, Any]:
        """Get subscription summary statistics"""
        now = datetime.now(timezone.utc)
        soon = now + timedelta(days=7)

        # Active count
        active = await self.db.execute(
            select(func.count(User.id))
            .where(User.subscription_tier != SubscriptionTier.FREE)
            .where(or_(
                User.subscription_expires_at.is_(None),
                User.subscription_expires_at > now
            ))
        )
        active_count = active.scalar() or 0

        # Expiring soon
        expiring = await self.db.execute(
            select(func.count(User.id))
            .where(User.subscription_tier != SubscriptionTier.FREE)
            .where(User.subscription_expires_at > now)
            .where(User.subscription_expires_at <= soon)
        )
        expiring_count = expiring.scalar() or 0

        # Expired
        expired = await self.db.execute(
            select(func.count(User.id))
            .where(User.subscription_tier != SubscriptionTier.FREE)
            .where(User.subscription_expires_at < now)
        )
        expired_count = expired.scalar() or 0

        # By tier
        tier_result = await self.db.execute(
            select(
                User.subscription_tier,
                func.count(User.id).label("count")
            )
            .where(User.subscription_tier != SubscriptionTier.FREE)
            .where(or_(
                User.subscription_expires_at.is_(None),
                User.subscription_expires_at > now
            ))
            .group_by(User.subscription_tier)
        )
        by_tier = {row.subscription_tier.value: row.count for row in tier_result.all()}

        return {
            "active": active_count,
            "expiring_soon": expiring_count,
            "expired": expired_count,
            "by_tier": by_tier
        }

    async def modify_subscription(
        self,
        user_id: UUID,
        new_tier: str,
        expires_at: Optional[datetime] = None,
        admin_id: Optional[UUID] = None,
        reason: Optional[str] = None,
        notify_user: bool = True
    ) -> Dict[str, Any]:
        """
        Manually modify a user's subscription with audit trail.
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            return {"success": False, "error": "User not found"}

        try:
            new_tier_enum = SubscriptionTier(new_tier)
        except ValueError:
            return {"success": False, "error": f"Invalid tier: {new_tier}"}

        old_tier = user.subscription_tier.value
        old_expires = user.subscription_expires_at

        user.subscription_tier = new_tier_enum

        if expires_at:
            user.subscription_expires_at = expires_at
        elif new_tier != "free":
            # Default to 30 days if no expiry specified
            user.subscription_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        else:
            user.subscription_expires_at = None

        await self.db.commit()

        logger.info(
            f"Subscription modified: User {user_id}, {old_tier} -> {new_tier}, "
            f"Expires: {user.subscription_expires_at}, Admin: {admin_id}, Reason: {reason}"
        )

        return {
            "success": True,
            "user_id": str(user_id),
            "old_tier": old_tier,
            "new_tier": new_tier,
            "old_expires_at": old_expires.isoformat() if old_expires else None,
            "expires_at": user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
            "message": "Subscription modified successfully",
            "modified_at": datetime.now(timezone.utc).isoformat(),
            "modified_by": str(admin_id) if admin_id else None
        }

    # =========================================================================
    # Payment Reconciliation
    # =========================================================================
    async def reconcile_payments(
        self,
        start_date: date,
        end_date: date,
        payment_method: Optional[str] = None,
        provider_data: Optional[List[Dict[str, Any]]] = None,
        admin_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Reconcile payments with provider data.

        Compares internal payment records with provider report data
        to identify discrepancies.
        """
        # Get internal payments
        conditions = [
            Payment.status == PaymentStatus.COMPLETED,
            func.date(Payment.completed_at) >= start_date,
            func.date(Payment.completed_at) <= end_date
        ]

        if payment_method:
            conditions.append(Payment.payment_method == PaymentMethod(payment_method))

        result = await self.db.execute(
            select(Payment).where(and_(*conditions))
        )
        internal_payments = {p.external_reference: p for p in result.scalars().all()}

        # Compare with provider data
        matched = []
        unmatched_internal = []
        unmatched_provider = []
        discrepancies = []

        total_expected = Decimal("0")
        total_actual = Decimal("0")

        if provider_data:
            provider_refs = {d.get("reference"): d for d in provider_data}

            for ref, payment in internal_payments.items():
                total_expected += payment.amount

                if ref in provider_refs:
                    provider_record = provider_refs[ref]
                    provider_amount = Decimal(str(provider_record.get("amount", 0)))
                    total_actual += provider_amount

                    if payment.amount != provider_amount:
                        discrepancies.append({
                            "payment_id": str(payment.id),
                            "external_reference": ref,
                            "expected_amount": float(payment.amount),
                            "actual_amount": float(provider_amount),
                            "discrepancy": float(payment.amount - provider_amount),
                            "status": "discrepancy"
                        })
                    else:
                        matched.append({
                            "payment_id": str(payment.id),
                            "external_reference": ref,
                            "expected_amount": float(payment.amount),
                            "actual_amount": float(provider_amount),
                            "status": "matched"
                        })
                else:
                    unmatched_internal.append({
                        "payment_id": str(payment.id),
                        "external_reference": ref,
                        "expected_amount": float(payment.amount),
                        "actual_amount": 0,
                        "status": "missing_in_provider"
                    })

            # Check for provider records not in our system
            for ref, record in provider_refs.items():
                if ref not in internal_payments:
                    unmatched_provider.append({
                        "external_reference": ref,
                        "actual_amount": float(record.get("amount", 0)),
                        "status": "missing_in_system"
                    })
        else:
            # No provider data, just list internal payments
            for ref, payment in internal_payments.items():
                total_expected += payment.amount
                matched.append({
                    "payment_id": str(payment.id),
                    "external_reference": ref,
                    "expected_amount": float(payment.amount),
                    "actual_amount": None,
                    "status": "pending_verification"
                })

        all_items = matched + unmatched_internal + unmatched_provider + discrepancies

        return {
            "total_payments": len(internal_payments),
            "matched": len(matched),
            "unmatched": len(unmatched_internal) + len(unmatched_provider),
            "discrepancies": len(discrepancies),
            "total_expected": float(total_expected),
            "total_actual": float(total_actual),
            "total_discrepancy": float(total_expected - total_actual),
            "items": all_items,
            "reconciled_at": datetime.now(timezone.utc).isoformat(),
            "reconciled_by": str(admin_id) if admin_id else None
        }

    # =========================================================================
    # Export Functionality
    # =========================================================================
    async def export_payments(
        self,
        format: str = "csv",
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        status: Optional[List[str]] = None,
        payment_method: Optional[List[str]] = None,
        include_user_details: bool = True
    ) -> Dict[str, Any]:
        """
        Export payments to CSV format.
        """
        conditions = []

        if date_from:
            conditions.append(func.date(Payment.created_at) >= date_from)
        if date_to:
            conditions.append(func.date(Payment.created_at) <= date_to)
        if status:
            conditions.append(Payment.status.in_([PaymentStatus(s) for s in status]))
        if payment_method:
            conditions.append(Payment.payment_method.in_([PaymentMethod(m) for m in payment_method]))

        query = select(Payment).options(
            selectinload(Payment.user),
            selectinload(Payment.plan)
        )

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(Payment.created_at.desc())

        result = await self.db.execute(query)
        payments = result.scalars().all()

        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        headers = [
            "Payment ID", "Reference", "External Reference",
            "Amount", "Currency", "Status", "Payment Method",
            "Plan Name", "Created At", "Completed At"
        ]
        if include_user_details:
            headers.extend(["User Email", "User Phone"])

        writer.writerow(headers)

        # Data rows
        for p in payments:
            row = [
                str(p.id),
                p.payment_reference or "",
                p.external_reference or "",
                float(p.amount),
                p.currency,
                p.status.value,
                p.payment_method.value if p.payment_method else "",
                p.plan.name if p.plan else "",
                p.created_at.isoformat(),
                p.completed_at.isoformat() if p.completed_at else ""
            ]
            if include_user_details:
                row.extend([
                    p.user.email if p.user else "",
                    p.user.phone_number if p.user else ""
                ])
            writer.writerow(row)

        csv_data = output.getvalue()
        output.close()

        file_name = f"payments_export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"

        return {
            "success": True,
            "file_name": file_name,
            "data": csv_data,
            "record_count": len(payments),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    # =========================================================================
    # Fraud Detection Helpers
    # =========================================================================
    async def check_payment_velocity(
        self,
        user_id: UUID,
        time_window_minutes: int = 60,
        max_attempts: int = 5
    ) -> Dict[str, Any]:
        """
        Check if user has exceeded payment velocity limits.

        Used to detect potential fraud or abuse.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=time_window_minutes)

        result = await self.db.execute(
            select(func.count(Payment.id))
            .where(Payment.user_id == user_id)
            .where(Payment.created_at >= cutoff)
        )
        attempt_count = result.scalar() or 0

        is_exceeded = attempt_count >= max_attempts

        if is_exceeded:
            logger.warning(
                f"Payment velocity exceeded: User {user_id}, "
                f"Attempts: {attempt_count} in {time_window_minutes} minutes"
            )

        return {
            "user_id": str(user_id),
            "attempts_in_window": attempt_count,
            "window_minutes": time_window_minutes,
            "max_allowed": max_attempts,
            "is_exceeded": is_exceeded,
            "checked_at": datetime.now(timezone.utc).isoformat()
        }

    async def get_user_payment_patterns(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get payment patterns for a user for fraud analysis.
        """
        result = await self.db.execute(
            select(Payment)
            .where(Payment.user_id == user_id)
            .order_by(Payment.created_at.desc())
            .limit(20)
        )
        payments = result.scalars().all()

        if not payments:
            return {"user_id": str(user_id), "has_history": False}

        methods_used = set()
        status_counts = defaultdict(int)
        amounts = []

        for p in payments:
            if p.payment_method:
                methods_used.add(p.payment_method.value)
            status_counts[p.status.value] += 1
            amounts.append(float(p.amount))

        return {
            "user_id": str(user_id),
            "has_history": True,
            "total_payments": len(payments),
            "methods_used": list(methods_used),
            "status_breakdown": dict(status_counts),
            "average_amount": sum(amounts) / len(amounts) if amounts else 0,
            "max_amount": max(amounts) if amounts else 0,
            "min_amount": min(amounts) if amounts else 0,
            "failure_rate": status_counts.get("failed", 0) / len(payments) * 100 if payments else 0
        }
