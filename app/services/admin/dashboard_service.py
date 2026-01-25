# ============================================================================
# Admin Dashboard Service
# ============================================================================
"""
Service layer for admin dashboard operations.
Provides real-time KPIs, charts, and activity feeds for the admin panel.
"""
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case, Integer, Float
from datetime import datetime, timedelta, date
from uuid import UUID
from decimal import Decimal
import logging

from app.models.user import User, Student, UserRole, SubscriptionTier
from app.models.curriculum import Subject, Question
from app.models.practice import PracticeSession, QuestionAttempt
from app.models.payment import Payment, PaymentStatus
from app.models.conversation import Conversation
from app.models.gamification import Competition, CompetitionParticipant

logger = logging.getLogger(__name__)


class DashboardService:
    """
    Dashboard analytics and KPI service.
    
    Provides comprehensive metrics for the admin dashboard including:
    - Real-time KPI cards with trend analysis
    - Chart data for visualizations
    - Activity feeds for recent system events
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # =========================================================================
    # KPI Cards
    # =========================================================================
    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """
        Retrieve all KPI card data for the main dashboard.

        Returns:
            Dictionary containing all KPI metrics with trend data
        """
        try:
            now = datetime.utcnow()
            today = now.date()
            yesterday = today - timedelta(days=1)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_month_start = (month_start - timedelta(days=1)).replace(day=1)
            week_ago = today - timedelta(days=7)
            two_weeks_ago = today - timedelta(days=14)

            return {
                "total_users": await self._get_total_users_kpi(yesterday),
                "active_students_today": await self._get_active_students_kpi(today, yesterday),
                "messages_24h": await self._get_messages_kpi(now),
                "revenue_this_month": await self._get_revenue_kpi(month_start, last_month_start),
                "active_subscriptions": await self._get_subscriptions_kpi(),
                "conversion_rate": await self._get_conversion_rate_kpi(week_ago, two_weeks_ago),
                "avg_session_duration": await self._get_session_duration_kpi(week_ago),
                "questions_answered_today": await self._get_questions_kpi(today, yesterday),
            }
        except Exception as e:
            logger.error(f"Error fetching dashboard stats: {e}")
            raise
    
    async def _get_total_users_kpi(self, yesterday: date) -> Dict[str, Any]:
        """Calculate total users with growth percentage"""
        # Current total
        result = await self.db.execute(select(func.count(User.id)))
        total = result.scalar() or 0
        
        # Yesterday's total (users created before end of yesterday)
        result = await self.db.execute(
            select(func.count(User.id))
            .where(func.date(User.created_at) <= yesterday)
        )
        yesterday_total = result.scalar() or 0
        
        # Calculate change
        change = total - yesterday_total
        change_pct = (change / yesterday_total * 100) if yesterday_total > 0 else 0
        
        return {
            "value": total,
            "label": "Total Users",
            "change_percent": round(change_pct, 1),
            "change_direction": "up" if change > 0 else "down" if change < 0 else "stable",
            "period": "vs yesterday"
        }
    
    async def _get_active_students_kpi(self, today: date, yesterday: date) -> Dict[str, Any]:
        """Calculate active students today with comparison"""
        # Today's active
        result = await self.db.execute(
            select(func.count(User.id))
            .where(func.date(User.last_active) == today)
            .where(User.role == UserRole.STUDENT)
        )
        today_active = result.scalar() or 0
        
        # Yesterday's active
        result = await self.db.execute(
            select(func.count(User.id))
            .where(func.date(User.last_active) == yesterday)
            .where(User.role == UserRole.STUDENT)
        )
        yesterday_active = result.scalar() or 0
        
        change_pct = ((today_active - yesterday_active) / yesterday_active * 100) if yesterday_active > 0 else 0
        
        return {
            "value": today_active,
            "label": "Active Students Today",
            "change_percent": round(change_pct, 1),
            "change_direction": "up" if today_active > yesterday_active else "down" if today_active < yesterday_active else "stable",
            "period": "vs yesterday"
        }
    
    async def _get_messages_kpi(self, now: datetime) -> Dict[str, Any]:
        """Calculate messages processed in last 24 hours"""
        day_ago = now - timedelta(hours=24)
        two_days_ago = now - timedelta(hours=48)
        
        # Last 24h
        result = await self.db.execute(
            select(func.count(Conversation.id))
            .where(Conversation.created_at >= day_ago)
        )
        current = result.scalar() or 0
        
        # Previous 24h
        result = await self.db.execute(
            select(func.count(Conversation.id))
            .where(and_(
                Conversation.created_at >= two_days_ago,
                Conversation.created_at < day_ago
            ))
        )
        previous = result.scalar() or 0
        
        change_pct = ((current - previous) / previous * 100) if previous > 0 else 0
        
        return {
            "value": current,
            "label": "Messages (24h)",
            "change_percent": round(change_pct, 1),
            "change_direction": "up" if current > previous else "down" if current < previous else "stable",
            "period": "vs previous 24h"
        }
    
    async def _get_revenue_kpi(self, month_start: datetime, last_month_start: datetime) -> Dict[str, Any]:
        """Calculate revenue this month with comparison"""
        # This month
        result = await self.db.execute(
            select(func.sum(Payment.amount))
            .where(Payment.status == PaymentStatus.COMPLETED)
            .where(Payment.completed_at >= month_start)
        )
        current_revenue = result.scalar() or Decimal("0")
        
        # Last month (same period)
        days_into_month = (datetime.utcnow() - month_start).days + 1
        last_month_same_period = last_month_start + timedelta(days=days_into_month)
        
        result = await self.db.execute(
            select(func.sum(Payment.amount))
            .where(Payment.status == PaymentStatus.COMPLETED)
            .where(and_(
                Payment.completed_at >= last_month_start,
                Payment.completed_at < last_month_same_period
            ))
        )
        last_revenue = result.scalar() or Decimal("0")
        
        change_pct = float((current_revenue - last_revenue) / last_revenue * 100) if last_revenue > 0 else 0
        
        return {
            "value": float(current_revenue),
            "label": "Revenue This Month",
            "change_percent": round(change_pct, 1),
            "change_direction": "up" if current_revenue > last_revenue else "down" if current_revenue < last_revenue else "stable",
            "period": "vs last month",
            "currency": "USD"
        }
    
    async def _get_subscriptions_kpi(self) -> Dict[str, Any]:
        """Calculate active paid subscriptions"""
        now = datetime.utcnow()
        
        result = await self.db.execute(
            select(func.count(User.id))
            .where(User.subscription_tier != SubscriptionTier.FREE)
            .where(or_(
                User.subscription_expires_at.is_(None),
                User.subscription_expires_at > now
            ))
        )
        active_subs = result.scalar() or 0
        
        return {
            "value": active_subs,
            "label": "Active Subscriptions",
            "change_percent": None,
            "change_direction": None,
            "period": "current"
        }
    
    async def _get_conversion_rate_kpi(self, week_ago: date, two_weeks_ago: date) -> Dict[str, Any]:
        """Calculate free to paid conversion rate"""
        # Total free users
        result = await self.db.execute(
            select(func.count(User.id))
            .where(User.subscription_tier == SubscriptionTier.FREE)
        )
        free_users = result.scalar() or 0
        
        # Users who upgraded this week
        result = await self.db.execute(
            select(func.count(Payment.id))
            .where(Payment.status == PaymentStatus.COMPLETED)
            .where(func.date(Payment.completed_at) >= week_ago)
        )
        conversions = result.scalar() or 0
        
        # Calculate rate (simplified)
        total_users_result = await self.db.execute(select(func.count(User.id)))
        total_users = total_users_result.scalar() or 1
        
        conversion_rate = (conversions / total_users * 100) if total_users > 0 else 0
        
        return {
            "value": round(conversion_rate, 2),
            "label": "Conversion Rate",
            "change_percent": None,
            "change_direction": None,
            "period": "this week",
            "suffix": "%"
        }
    
    async def _get_session_duration_kpi(self, week_ago: date) -> Dict[str, Any]:
        """Calculate average session duration"""
        result = await self.db.execute(
            select(func.avg(PracticeSession.time_spent_seconds))
            .where(PracticeSession.status == "completed")
            .where(func.date(PracticeSession.started_at) >= week_ago)
        )
        avg_seconds = result.scalar() or 0
        avg_minutes = round(avg_seconds / 60, 1) if avg_seconds else 0
        
        return {
            "value": avg_minutes,
            "label": "Avg Session Duration",
            "change_percent": None,
            "change_direction": None,
            "period": "last 7 days",
            "suffix": "min"
        }
    
    async def _get_questions_kpi(self, today: date, yesterday: date) -> Dict[str, Any]:
        """Calculate questions answered today"""
        # Today
        result = await self.db.execute(
            select(func.count(QuestionAttempt.id))
            .where(func.date(QuestionAttempt.attempted_at) == today)
        )
        today_count = result.scalar() or 0
        
        # Yesterday
        result = await self.db.execute(
            select(func.count(QuestionAttempt.id))
            .where(func.date(QuestionAttempt.attempted_at) == yesterday)
        )
        yesterday_count = result.scalar() or 0
        
        change_pct = ((today_count - yesterday_count) / yesterday_count * 100) if yesterday_count > 0 else 0
        
        return {
            "value": today_count,
            "label": "Questions Answered Today",
            "change_percent": round(change_pct, 1),
            "change_direction": "up" if today_count > yesterday_count else "down" if today_count < yesterday_count else "stable",
            "period": "vs yesterday"
        }
    
    # =========================================================================
    # Chart Data
    # =========================================================================
    async def get_dashboard_charts(self, days: int = 30) -> Dict[str, Any]:
        """
        Retrieve all chart data for dashboard visualizations.

        Args:
            days: Number of days to include in time series data

        Returns:
            Dictionary containing data for all dashboard charts
        """
        try:
            start_date = date.today() - timedelta(days=days)

            return {
                "user_growth": await self._get_user_growth_chart(start_date),
                "revenue_trend": await self._get_revenue_trend_chart(start_date),
                "subscription_distribution": await self._get_subscription_distribution(),
                "active_hours_heatmap": await self._get_active_hours_heatmap(),
                "subject_popularity": await self._get_subject_popularity(),
                "daily_active_users": await self._get_dau_sparkline(start_date),
            }
        except Exception as e:
            logger.error(f"Error fetching dashboard charts: {e}")
            raise
    
    async def _get_user_growth_chart(self, start_date: date) -> List[Dict[str, Any]]:
        """Get daily user registration data with gap filling"""
        result = await self.db.execute(
            select(
                func.date(User.created_at).label("date"),
                func.count(User.id).label("count")
            )
            .where(func.date(User.created_at) >= start_date)
            .group_by(func.date(User.created_at))
            .order_by(func.date(User.created_at))
        )

        # Create a map of existing data
        data_map = {row.date: row.count for row in result.all()}

        # Fill gaps with zeros for continuous time series
        filled_data = []
        current = start_date
        today = date.today()
        while current <= today:
            filled_data.append({
                "timestamp": current.isoformat(),
                "value": data_map.get(current, 0),
                "label": "New Users"
            })
            current += timedelta(days=1)

        return filled_data
    
    async def _get_revenue_trend_chart(self, start_date: date) -> List[Dict[str, Any]]:
        """Get daily revenue data with gap filling"""
        result = await self.db.execute(
            select(
                func.date(Payment.completed_at).label("date"),
                func.sum(Payment.amount).label("amount")
            )
            .where(Payment.status == PaymentStatus.COMPLETED)
            .where(func.date(Payment.completed_at) >= start_date)
            .group_by(func.date(Payment.completed_at))
            .order_by(func.date(Payment.completed_at))
        )

        # Create a map of existing data
        data_map = {row.date: float(row.amount or 0) for row in result.all()}

        # Fill gaps with zeros for continuous time series
        filled_data = []
        current = start_date
        today = date.today()
        while current <= today:
            filled_data.append({
                "timestamp": current.isoformat(),
                "value": data_map.get(current, 0.0),
                "label": "Revenue"
            })
            current += timedelta(days=1)

        return filled_data
    
    async def _get_subscription_distribution(self) -> List[Dict[str, Any]]:
        """Get subscription tier distribution"""
        result = await self.db.execute(
            select(
                User.subscription_tier,
                func.count(User.id).label("count")
            )
            .group_by(User.subscription_tier)
        )
        
        return [
            {"label": row.subscription_tier.value, "value": row.count}
            for row in result.all()
        ]
    
    async def _get_active_hours_heatmap(self) -> Dict[str, List[int]]:
        """Get activity heatmap by day of week and hour"""
        result = await self.db.execute(
            select(
                func.extract('dow', QuestionAttempt.attempted_at).label("dow"),
                func.extract('hour', QuestionAttempt.attempted_at).label("hour"),
                func.count(QuestionAttempt.id).label("count")
            )
            .where(QuestionAttempt.attempted_at >= datetime.utcnow() - timedelta(days=30))
            .group_by(
                func.extract('dow', QuestionAttempt.attempted_at),
                func.extract('hour', QuestionAttempt.attempted_at)
            )
        )
        
        # Initialize heatmap with zeros
        days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        heatmap = {day: [0] * 24 for day in days}
        
        for row in result.all():
            day_idx = int(row.dow)
            hour = int(row.hour)
            heatmap[days[day_idx]][hour] = row.count
        
        return heatmap
    
    async def _get_subject_popularity(self) -> List[Dict[str, Any]]:
        """Get question attempts by subject"""
        result = await self.db.execute(
            select(
                Subject.name,
                func.count(QuestionAttempt.id).label("attempts")
            )
            .join(Question, QuestionAttempt.question_id == Question.id)
            .join(Subject, Question.subject_id == Subject.id)
            .where(QuestionAttempt.attempted_at >= datetime.utcnow() - timedelta(days=30))
            .group_by(Subject.name)
            .order_by(func.count(QuestionAttempt.id).desc())
            .limit(10)
        )
        
        return [
            {"label": row.name, "value": row.attempts}
            for row in result.all()
        ]
    
    async def _get_dau_sparkline(self, start_date: date) -> List[Dict[str, Any]]:
        """Get daily active users for sparkline with gap filling"""
        result = await self.db.execute(
            select(
                func.date(User.last_active).label("date"),
                func.count(User.id).label("count")
            )
            .where(func.date(User.last_active) >= start_date)
            .group_by(func.date(User.last_active))
            .order_by(func.date(User.last_active))
        )

        # Create a map of existing data
        data_map = {row.date: row.count for row in result.all()}

        # Fill gaps with zeros for continuous time series
        filled_data = []
        current = start_date
        today = date.today()
        while current <= today:
            filled_data.append({
                "timestamp": current.isoformat(),
                "value": data_map.get(current, 0)
            })
            current += timedelta(days=1)

        return filled_data
    
    # =========================================================================
    # Activity Feed
    # =========================================================================
    async def get_activity_feed(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """
        Retrieve recent activity feed for the dashboard.

        Args:
            limit: Maximum number of items to return
            offset: Pagination offset

        Returns:
            Dictionary with activity items and pagination info
        """
        try:
            activities = []

            # Get recent registrations
            registrations = await self._get_recent_registrations(limit=15)
            activities.extend(registrations)

            # Get recent subscription changes
            subscriptions = await self._get_recent_subscriptions(limit=15)
            activities.extend(subscriptions)

            # Get recent competition completions
            competitions = await self._get_recent_competition_completions(limit=10)
            activities.extend(competitions)

            # Sort by timestamp and paginate
            activities.sort(key=lambda x: x["timestamp"], reverse=True)
            total_count = len(activities)
            paginated = activities[offset:offset + limit]

            return {
                "items": paginated,
                "total_count": total_count,
                "has_more": total_count > offset + limit
            }
        except Exception as e:
            logger.error(f"Error fetching activity feed: {e}")
            raise
    
    async def _get_recent_registrations(self, limit: int) -> List[Dict[str, Any]]:
        """Get recent user registrations"""
        result = await self.db.execute(
            select(User, Student)
            .outerjoin(Student, User.id == Student.user_id)
            .order_by(User.created_at.desc())
            .limit(limit)
        )
        
        items = []
        for user, student in result.all():
            name = student.full_name if student else user.phone_number
            items.append({
                "id": str(user.id),
                "type": "registration",
                "title": "New User Registration",
                "description": f"{name} joined as {user.role.value}",
                "user_id": str(user.id),
                "user_name": name,
                "timestamp": user.created_at.isoformat(),
                "metadata": {"role": user.role.value}
            })
        
        return items
    
    async def _get_recent_subscriptions(self, limit: int) -> List[Dict[str, Any]]:
        """Get recent subscription upgrades"""
        result = await self.db.execute(
            select(Payment, User)
            .join(User, Payment.user_id == User.id)
            .where(Payment.status == PaymentStatus.COMPLETED)
            .order_by(Payment.completed_at.desc())
            .limit(limit)
        )
        
        items = []
        for payment, user in result.all():
            items.append({
                "id": str(payment.id),
                "type": "upgrade",
                "title": "Subscription Upgrade",
                "description": f"{user.phone_number} upgraded - ${payment.amount}",
                "user_id": str(user.id),
                "user_name": user.phone_number,
                "timestamp": payment.completed_at.isoformat() if payment.completed_at else payment.created_at.isoformat(),
                "metadata": {"amount": float(payment.amount), "currency": payment.currency}
            })
        
        return items
    
    async def _get_recent_competition_completions(self, limit: int) -> List[Dict[str, Any]]:
        """Get recent competition completions"""
        result = await self.db.execute(
            select(CompetitionParticipant, Competition, Student)
            .join(Competition, CompetitionParticipant.competition_id == Competition.id)
            .join(Student, CompetitionParticipant.student_id == Student.id)
            .where(CompetitionParticipant.status == "completed")
            .order_by(CompetitionParticipant.completed_at.desc())
            .limit(limit)
        )
        
        items = []
        for participant, competition, student in result.all():
            items.append({
                "id": str(participant.id),
                "type": "competition",
                "title": "Competition Completed",
                "description": f"{student.full_name} completed '{competition.name}' - Rank #{participant.rank or 'N/A'}",
                "user_id": str(student.user_id),
                "user_name": student.full_name,
                "timestamp": participant.completed_at.isoformat() if participant.completed_at else datetime.utcnow().isoformat(),
                "metadata": {
                    "competition_id": str(competition.id),
                    "score": float(participant.score or 0),
                    "rank": participant.rank
                }
            })
        
        return items