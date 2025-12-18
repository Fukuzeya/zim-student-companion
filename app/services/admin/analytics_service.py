# ============================================================================
# Admin Analytics Service
# ============================================================================
"""
Service layer for comprehensive analytics and reporting.
Provides engagement, learning, revenue, and custom analytics capabilities.
"""
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case, Integer, Float, cast
from datetime import datetime, timedelta, date
from uuid import UUID
from decimal import Decimal
from collections import defaultdict
import logging
import json
import io
import csv

from app.models.user import User, Student, UserRole, SubscriptionTier
from app.models.curriculum import Subject, Topic, Question
from app.models.practice import PracticeSession, QuestionAttempt
from app.models.payment import Payment, PaymentStatus, SubscriptionPlan
from app.models.conversation import Conversation
from app.models.gamification import StudentStreak, StudentTopicProgress

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Comprehensive analytics service for admin dashboard.
    
    Provides:
    - Engagement metrics (DAU, WAU, MAU, retention)
    - Learning analytics (performance, progress, patterns)
    - Revenue analytics (MRR, churn, LTV)
    - Custom report generation
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # =========================================================================
    # Time Range Helpers
    # =========================================================================
    def _parse_time_range(
        self,
        time_range: str,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> Tuple[datetime, datetime]:
        """
        Parse time range string into start/end datetimes.
        
        Args:
            time_range: Predefined range (today, last_7_days, etc.) or 'custom'
            date_from: Custom start date
            date_to: Custom end date
            
        Returns:
            Tuple of (start_datetime, end_datetime)
        """
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        ranges = {
            "today": (today, now),
            "yesterday": (today - timedelta(days=1), today),
            "last_7_days": (today - timedelta(days=7), now),
            "last_30_days": (today - timedelta(days=30), now),
            "this_month": (today.replace(day=1), now),
            "last_month": (
                (today.replace(day=1) - timedelta(days=1)).replace(day=1),
                today.replace(day=1)
            ),
            "this_year": (today.replace(month=1, day=1), now),
        }
        
        if time_range == "custom" and date_from and date_to:
            return (
                datetime.combine(date_from, datetime.min.time()),
                datetime.combine(date_to, datetime.max.time())
            )
        
        return ranges.get(time_range, ranges["last_30_days"])
    
    # =========================================================================
    # Engagement Analytics
    # =========================================================================
    async def get_engagement_analytics(
        self,
        time_range: str = "last_30_days",
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive engagement metrics.
        
        Returns:
            DAU/WAU/MAU, session metrics, feature usage, retention cohorts
        """
        start_dt, end_dt = self._parse_time_range(time_range, date_from, date_to)
        today = datetime.utcnow().date()
        
        # DAU - Daily Active Users (today)
        dau_result = await self.db.execute(
            select(func.count(func.distinct(User.id)))
            .where(func.date(User.last_active) == today)
        )
        dau = dau_result.scalar() or 0
        
        # WAU - Weekly Active Users
        week_ago = today - timedelta(days=7)
        wau_result = await self.db.execute(
            select(func.count(func.distinct(User.id)))
            .where(func.date(User.last_active) >= week_ago)
        )
        wau = wau_result.scalar() or 0
        
        # MAU - Monthly Active Users
        month_ago = today - timedelta(days=30)
        mau_result = await self.db.execute(
            select(func.count(func.distinct(User.id)))
            .where(func.date(User.last_active) >= month_ago)
        )
        mau = mau_result.scalar() or 0
        
        # DAU/WAU ratio (stickiness)
        dau_wau_ratio = (dau / wau) if wau > 0 else 0
        
        # Average session duration
        session_result = await self.db.execute(
            select(func.avg(PracticeSession.time_spent_seconds))
            .where(PracticeSession.started_at >= start_dt)
            .where(PracticeSession.status == "completed")
        )
        avg_session_seconds = session_result.scalar() or 0
        avg_session_minutes = round(avg_session_seconds / 60, 2)
        
        # Messages per session
        messages_result = await self.db.execute(
            select(func.count(Conversation.id))
            .where(Conversation.created_at >= start_dt)
        )
        total_messages = messages_result.scalar() or 0
        
        sessions_result = await self.db.execute(
            select(func.count(PracticeSession.id))
            .where(PracticeSession.started_at >= start_dt)
        )
        total_sessions = sessions_result.scalar() or 1
        
        avg_messages_per_session = round(total_messages / total_sessions, 2)
        
        # Feature usage (by session type)
        feature_usage = await self._get_feature_usage(start_dt, end_dt)
        
        # Retention cohorts
        retention_cohorts = await self._calculate_retention_cohorts()
        
        # Conversion funnel
        funnel_data = await self._get_conversion_funnel(start_dt, end_dt)
        
        return {
            "dau": dau,
            "wau": wau,
            "mau": mau,
            "dau_wau_ratio": round(dau_wau_ratio, 3),
            "avg_session_duration_minutes": avg_session_minutes,
            "avg_messages_per_session": avg_messages_per_session,
            "feature_usage": feature_usage,
            "retention_cohorts": retention_cohorts,
            "funnel_data": funnel_data,
            "period": {
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat()
            }
        }
    
    async def _get_feature_usage(self, start_dt: datetime, end_dt: datetime) -> Dict[str, int]:
        """Get usage counts by feature/session type"""
        result = await self.db.execute(
            select(PracticeSession.session_type, func.count(PracticeSession.id))
            .where(PracticeSession.started_at >= start_dt)
            .where(PracticeSession.started_at <= end_dt)
            .group_by(PracticeSession.session_type)
        )
        return {row[0]: row[1] for row in result.all()}
    
    async def _calculate_retention_cohorts(self) -> Dict[str, List[float]]:
        """
        Calculate weekly retention cohorts.
        
        Returns:
            Dictionary with cohort week as key and retention percentages as values
        """
        cohorts = {}
        today = datetime.utcnow().date()
        
        # Calculate for last 8 weeks
        for week_offset in range(8):
            cohort_start = today - timedelta(weeks=week_offset + 1)
            cohort_end = today - timedelta(weeks=week_offset)
            
            # Users who joined in this week
            cohort_users_result = await self.db.execute(
                select(User.id)
                .where(func.date(User.created_at) >= cohort_start)
                .where(func.date(User.created_at) < cohort_end)
            )
            cohort_users = [row[0] for row in cohort_users_result.all()]
            cohort_size = len(cohort_users)
            
            if cohort_size == 0:
                continue
            
            # Calculate retention for subsequent weeks
            retention = []
            for retention_week in range(min(week_offset + 1, 4)):
                retention_start = cohort_end + timedelta(weeks=retention_week)
                retention_end = retention_start + timedelta(weeks=1)
                
                retained_result = await self.db.execute(
                    select(func.count(func.distinct(User.id)))
                    .where(User.id.in_(cohort_users))
                    .where(func.date(User.last_active) >= retention_start)
                    .where(func.date(User.last_active) < retention_end)
                )
                retained = retained_result.scalar() or 0
                retention.append(round((retained / cohort_size) * 100, 1))
            
            cohorts[f"Week {week_offset + 1}"] = retention
        
        return cohorts
    
    async def _get_conversion_funnel(self, start_dt: datetime, end_dt: datetime) -> Dict[str, int]:
        """Get conversion funnel data"""
        # Total signups
        signups_result = await self.db.execute(
            select(func.count(User.id))
            .where(User.created_at >= start_dt)
            .where(User.created_at <= end_dt)
        )
        signups = signups_result.scalar() or 0
        
        # Completed profile (have student record)
        profile_result = await self.db.execute(
            select(func.count(Student.id))
            .join(User, Student.user_id == User.id)
            .where(User.created_at >= start_dt)
            .where(User.created_at <= end_dt)
        )
        completed_profile = profile_result.scalar() or 0
        
        # First session
        first_session_result = await self.db.execute(
            select(func.count(func.distinct(PracticeSession.student_id)))
            .join(Student, PracticeSession.student_id == Student.id)
            .join(User, Student.user_id == User.id)
            .where(User.created_at >= start_dt)
            .where(User.created_at <= end_dt)
        )
        first_session = first_session_result.scalar() or 0
        
        # Converted to paid
        paid_result = await self.db.execute(
            select(func.count(func.distinct(Payment.user_id)))
            .join(User, Payment.user_id == User.id)
            .where(User.created_at >= start_dt)
            .where(User.created_at <= end_dt)
            .where(Payment.status == PaymentStatus.COMPLETED)
        )
        converted = paid_result.scalar() or 0
        
        return {
            "signups": signups,
            "completed_profile": completed_profile,
            "first_session": first_session,
            "converted_to_paid": converted
        }
    
    # =========================================================================
    # Learning Analytics
    # =========================================================================
    async def get_learning_analytics(
        self,
        time_range: str = "last_30_days",
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        subject_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive learning metrics.
        
        Returns:
            Questions answered, accuracy, time distribution, difficulty analysis
        """
        start_dt, end_dt = self._parse_time_range(time_range, date_from, date_to)
        
        # Base query conditions
        base_conditions = [
            QuestionAttempt.attempted_at >= start_dt,
            QuestionAttempt.attempted_at <= end_dt
        ]
        
        if subject_id:
            base_conditions.append(Question.subject_id == subject_id)
        
        # Total questions answered
        questions_result = await self.db.execute(
            select(func.count(QuestionAttempt.id))
            .join(Question, QuestionAttempt.question_id == Question.id)
            .where(and_(*base_conditions))
        )
        questions_answered = questions_result.scalar() or 0
        
        # Correct answers
        correct_result = await self.db.execute(
            select(func.count(QuestionAttempt.id))
            .join(Question, QuestionAttempt.question_id == Question.id)
            .where(and_(*base_conditions))
            .where(QuestionAttempt.is_correct == True)
        )
        correct_answers = correct_result.scalar() or 0
        
        accuracy_rate = (correct_answers / questions_answered * 100) if questions_answered > 0 else 0
        
        # Accuracy trend (daily)
        accuracy_trend = await self._get_accuracy_trend(start_dt, end_dt, subject_id)
        
        # Time by subject
        time_by_subject = await self._get_time_by_subject(start_dt, end_dt)
        
        # Difficulty distribution
        difficulty_dist = await self._get_difficulty_distribution(start_dt, end_dt, subject_id)
        
        # Hint usage
        hints_result = await self.db.execute(
            select(
                func.sum(QuestionAttempt.hints_used),
                func.count(QuestionAttempt.id)
            )
            .where(QuestionAttempt.attempted_at >= start_dt)
            .where(QuestionAttempt.attempted_at <= end_dt)
        )
        hints_row = hints_result.one()
        total_hints = hints_row[0] or 0
        total_attempts = hints_row[1] or 1
        hint_usage_rate = round((total_hints / total_attempts) * 100, 2)
        
        # Average time per question
        avg_time_result = await self.db.execute(
            select(func.avg(QuestionAttempt.time_spent_seconds))
            .where(QuestionAttempt.attempted_at >= start_dt)
            .where(QuestionAttempt.attempted_at <= end_dt)
        )
        avg_time_per_question = round(avg_time_result.scalar() or 0, 1)
        
        return {
            "questions_answered": questions_answered,
            "correct_answers": correct_answers,
            "accuracy_rate": round(accuracy_rate, 2),
            "accuracy_trend": accuracy_trend,
            "time_by_subject": time_by_subject,
            "difficulty_distribution": difficulty_dist,
            "hint_usage_rate": hint_usage_rate,
            "avg_time_per_question_seconds": avg_time_per_question,
            "period": {
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat()
            }
        }
    
    async def _get_accuracy_trend(
        self,
        start_dt: datetime,
        end_dt: datetime,
        subject_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get daily accuracy trend"""
        query = select(
            func.date(QuestionAttempt.attempted_at).label("date"),
            func.count(QuestionAttempt.id).label("total"),
            func.sum(case((QuestionAttempt.is_correct == True, 1), else_=0)).label("correct")
        ).where(
            QuestionAttempt.attempted_at >= start_dt,
            QuestionAttempt.attempted_at <= end_dt
        ).group_by(
            func.date(QuestionAttempt.attempted_at)
        ).order_by(
            func.date(QuestionAttempt.attempted_at)
        )
        
        if subject_id:
            query = query.join(Question, QuestionAttempt.question_id == Question.id)
            query = query.where(Question.subject_id == subject_id)
        
        result = await self.db.execute(query)
        
        return [
            {
                "timestamp": row.date.isoformat(),
                "value": round((row.correct / row.total * 100) if row.total > 0 else 0, 1),
                "label": "Accuracy %"
            }
            for row in result.all()
        ]
    
    async def _get_time_by_subject(self, start_dt: datetime, end_dt: datetime) -> Dict[str, int]:
        """Get total study time by subject (in minutes)"""
        result = await self.db.execute(
            select(
                Subject.name,
                func.sum(PracticeSession.time_spent_seconds).label("total_seconds")
            )
            .join(PracticeSession, PracticeSession.subject_id == Subject.id)
            .where(PracticeSession.started_at >= start_dt)
            .where(PracticeSession.started_at <= end_dt)
            .group_by(Subject.name)
        )
        
        return {
            row.name: round((row.total_seconds or 0) / 60)
            for row in result.all()
        }
    
    async def _get_difficulty_distribution(
        self,
        start_dt: datetime,
        end_dt: datetime,
        subject_id: Optional[UUID] = None
    ) -> Dict[str, int]:
        """Get question attempts by difficulty level"""
        query = select(
            Question.difficulty,
            func.count(QuestionAttempt.id).label("count")
        ).join(
            Question, QuestionAttempt.question_id == Question.id
        ).where(
            QuestionAttempt.attempted_at >= start_dt,
            QuestionAttempt.attempted_at <= end_dt
        ).group_by(Question.difficulty)
        
        if subject_id:
            query = query.where(Question.subject_id == subject_id)
        
        result = await self.db.execute(query)
        return {row.difficulty or "unknown": row.count for row in result.all()}
    
    # =========================================================================
    # Revenue Analytics
    # =========================================================================
    async def get_revenue_analytics(
        self,
        time_range: str = "last_30_days",
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive revenue metrics.
        
        Returns:
            MRR, ARR, churn, LTV, revenue breakdown
        """
        start_dt, end_dt = self._parse_time_range(time_range, date_from, date_to)
        now = datetime.utcnow()
        
        # Total revenue in period
        revenue_result = await self.db.execute(
            select(func.sum(Payment.amount))
            .where(Payment.status == PaymentStatus.COMPLETED)
            .where(Payment.completed_at >= start_dt)
            .where(Payment.completed_at <= end_dt)
        )
        total_revenue = Decimal(str(revenue_result.scalar() or 0))
        
        # MRR - Monthly Recurring Revenue (last 30 days)
        month_ago = now - timedelta(days=30)
        mrr_result = await self.db.execute(
            select(func.sum(Payment.amount))
            .where(Payment.status == PaymentStatus.COMPLETED)
            .where(Payment.completed_at >= month_ago)
        )
        mrr = Decimal(str(mrr_result.scalar() or 0))
        
        # ARR - Annual Recurring Revenue (projected)
        arr = mrr * 12
        
        # Revenue trend
        revenue_trend = await self._get_revenue_trend(start_dt, end_dt)
        
        # Revenue by plan
        revenue_by_plan = await self._get_revenue_by_plan(start_dt, end_dt)
        
        # New subscriptions in period
        new_subs_result = await self.db.execute(
            select(func.count(Payment.id))
            .where(Payment.status == PaymentStatus.COMPLETED)
            .where(Payment.completed_at >= start_dt)
            .where(Payment.completed_at <= end_dt)
        )
        new_subscriptions = new_subs_result.scalar() or 0
        
        # Churn calculation (simplified - users whose subscription expired)
        churned_result = await self.db.execute(
            select(func.count(User.id))
            .where(User.subscription_tier != SubscriptionTier.FREE)
            .where(User.subscription_expires_at < now)
            .where(User.subscription_expires_at >= start_dt)
        )
        churned = churned_result.scalar() or 0
        
        # Active paid users at start of period
        active_start_result = await self.db.execute(
            select(func.count(User.id))
            .where(User.subscription_tier != SubscriptionTier.FREE)
            .where(or_(
                User.subscription_expires_at.is_(None),
                User.subscription_expires_at >= start_dt
            ))
        )
        active_at_start = active_start_result.scalar() or 1
        
        churn_rate = round((churned / active_at_start) * 100, 2) if active_at_start > 0 else 0
        
        # LTV - Lifetime Value (simplified: ARPU / churn rate)
        total_paid_users_result = await self.db.execute(
            select(func.count(func.distinct(Payment.user_id)))
            .where(Payment.status == PaymentStatus.COMPLETED)
        )
        total_paid_users = total_paid_users_result.scalar() or 1
        
        total_revenue_all_time_result = await self.db.execute(
            select(func.sum(Payment.amount))
            .where(Payment.status == PaymentStatus.COMPLETED)
        )
        total_revenue_all = Decimal(str(total_revenue_all_time_result.scalar() or 0))
        
        arpu = total_revenue_all / total_paid_users if total_paid_users > 0 else Decimal("0")
        ltv = arpu * Decimal("12") if churn_rate > 0 else arpu  # Simplified LTV
        
        # Conversion funnel
        conversion_funnel = await self._get_conversion_funnel(start_dt, end_dt)
        
        return {
            "total_revenue": float(total_revenue),
            "mrr": float(mrr),
            "arr": float(arr),
            "churn_rate": churn_rate,
            "ltv": float(ltv),
            "revenue_trend": revenue_trend,
            "revenue_by_plan": {k: float(v) for k, v in revenue_by_plan.items()},
            "new_subscriptions": new_subscriptions,
            "churned_subscriptions": churned,
            "upgrades": 0,  # Would need upgrade tracking
            "downgrades": 0,  # Would need downgrade tracking
            "conversion_funnel": conversion_funnel,
            "currency": "USD",
            "period": {
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat()
            }
        }
    
    async def _get_revenue_trend(self, start_dt: datetime, end_dt: datetime) -> List[Dict[str, Any]]:
        """Get daily revenue trend"""
        result = await self.db.execute(
            select(
                func.date(Payment.completed_at).label("date"),
                func.sum(Payment.amount).label("amount")
            )
            .where(Payment.status == PaymentStatus.COMPLETED)
            .where(Payment.completed_at >= start_dt)
            .where(Payment.completed_at <= end_dt)
            .group_by(func.date(Payment.completed_at))
            .order_by(func.date(Payment.completed_at))
        )
        
        return [
            {
                "timestamp": row.date.isoformat(),
                "value": float(row.amount or 0),
                "label": "Revenue"
            }
            for row in result.all()
        ]
    
    async def _get_revenue_by_plan(self, start_dt: datetime, end_dt: datetime) -> Dict[str, Decimal]:
        """Get revenue breakdown by subscription plan"""
        result = await self.db.execute(
            select(
                SubscriptionPlan.name,
                func.sum(Payment.amount).label("total")
            )
            .join(SubscriptionPlan, Payment.plan_id == SubscriptionPlan.id)
            .where(Payment.status == PaymentStatus.COMPLETED)
            .where(Payment.completed_at >= start_dt)
            .where(Payment.completed_at <= end_dt)
            .group_by(SubscriptionPlan.name)
        )
        
        return {row.name: Decimal(str(row.total or 0)) for row in result.all()}
    
    # =========================================================================
    # Custom Reports
    # =========================================================================
    async def generate_custom_report(
        self,
        metrics: List[str],
        dimensions: List[str],
        time_range: str = "last_30_days",
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        filters: Optional[Dict[str, Any]] = None,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        Generate a custom analytics report.
        
        Args:
            metrics: List of metrics to include
            dimensions: List of dimensions to group by
            time_range: Time range for the report
            date_from: Custom start date
            date_to: Custom end date
            filters: Additional filters
            format: Output format (json, csv)
            
        Returns:
            Generated report data
        """
        start_dt, end_dt = self._parse_time_range(time_range, date_from, date_to)
        
        report_data = {
            "generated_at": datetime.utcnow().isoformat(),
            "period": {"start": start_dt.isoformat(), "end": end_dt.isoformat()},
            "metrics": {},
            "dimensions": {}
        }
        
        # Gather requested metrics
        metric_functions = {
            "total_users": self._metric_total_users,
            "active_users": self._metric_active_users,
            "total_revenue": self._metric_total_revenue,
            "questions_answered": self._metric_questions_answered,
            "average_accuracy": self._metric_average_accuracy,
            "new_signups": self._metric_new_signups,
        }
        
        for metric in metrics:
            if metric in metric_functions:
                report_data["metrics"][metric] = await metric_functions[metric](start_dt, end_dt)
        
        # Gather dimension breakdowns
        dimension_functions = {
            "by_subject": self._dimension_by_subject,
            "by_grade": self._dimension_by_grade,
            "by_subscription": self._dimension_by_subscription,
            "by_province": self._dimension_by_province,
        }
        
        for dimension in dimensions:
            if dimension in dimension_functions:
                report_data["dimensions"][dimension] = await dimension_functions[dimension](start_dt, end_dt)
        
        return report_data
    
    # Metric functions
    async def _metric_total_users(self, start_dt: datetime, end_dt: datetime) -> int:
        result = await self.db.execute(select(func.count(User.id)))
        return result.scalar() or 0
    
    async def _metric_active_users(self, start_dt: datetime, end_dt: datetime) -> int:
        result = await self.db.execute(
            select(func.count(User.id))
            .where(User.last_active >= start_dt)
            .where(User.last_active <= end_dt)
        )
        return result.scalar() or 0
    
    async def _metric_total_revenue(self, start_dt: datetime, end_dt: datetime) -> float:
        result = await self.db.execute(
            select(func.sum(Payment.amount))
            .where(Payment.status == PaymentStatus.COMPLETED)
            .where(Payment.completed_at >= start_dt)
            .where(Payment.completed_at <= end_dt)
        )
        return float(result.scalar() or 0)
    
    async def _metric_questions_answered(self, start_dt: datetime, end_dt: datetime) -> int:
        result = await self.db.execute(
            select(func.count(QuestionAttempt.id))
            .where(QuestionAttempt.attempted_at >= start_dt)
            .where(QuestionAttempt.attempted_at <= end_dt)
        )
        return result.scalar() or 0
    
    async def _metric_average_accuracy(self, start_dt: datetime, end_dt: datetime) -> float:
        result = await self.db.execute(
            select(
                func.count(QuestionAttempt.id).label("total"),
                func.sum(case((QuestionAttempt.is_correct == True, 1), else_=0)).label("correct")
            )
            .where(QuestionAttempt.attempted_at >= start_dt)
            .where(QuestionAttempt.attempted_at <= end_dt)
        )
        row = result.one()
        if row.total and row.total > 0:
            return round((row.correct / row.total) * 100, 2)
        return 0.0
    
    async def _metric_new_signups(self, start_dt: datetime, end_dt: datetime) -> int:
        result = await self.db.execute(
            select(func.count(User.id))
            .where(User.created_at >= start_dt)
            .where(User.created_at <= end_dt)
        )
        return result.scalar() or 0
    
    # Dimension functions
    async def _dimension_by_subject(self, start_dt: datetime, end_dt: datetime) -> Dict[str, int]:
        result = await self.db.execute(
            select(Subject.name, func.count(QuestionAttempt.id))
            .join(Question, QuestionAttempt.question_id == Question.id)
            .join(Subject, Question.subject_id == Subject.id)
            .where(QuestionAttempt.attempted_at >= start_dt)
            .where(QuestionAttempt.attempted_at <= end_dt)
            .group_by(Subject.name)
        )
        return {row[0]: row[1] for row in result.all()}
    
    async def _dimension_by_grade(self, start_dt: datetime, end_dt: datetime) -> Dict[str, int]:
        result = await self.db.execute(
            select(Student.grade, func.count(func.distinct(Student.id)))
            .join(User, Student.user_id == User.id)
            .where(User.last_active >= start_dt)
            .where(User.last_active <= end_dt)
            .group_by(Student.grade)
        )
        return {row[0]: row[1] for row in result.all()}
    
    async def _dimension_by_subscription(self, start_dt: datetime, end_dt: datetime) -> Dict[str, int]:
        result = await self.db.execute(
            select(User.subscription_tier, func.count(User.id))
            .group_by(User.subscription_tier)
        )
        return {row[0].value: row[1] for row in result.all()}
    
    async def _dimension_by_province(self, start_dt: datetime, end_dt: datetime) -> Dict[str, int]:
        result = await self.db.execute(
            select(Student.province, func.count(Student.id))
            .where(Student.province.isnot(None))
            .group_by(Student.province)
        )
        return {row[0]: row[1] for row in result.all()}