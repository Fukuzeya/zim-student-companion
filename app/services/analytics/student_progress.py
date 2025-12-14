# ============================================================================
# Student Progress Analytics
# ============================================================================
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Integer, select, func
from uuid import UUID
from datetime import datetime, timedelta, date
from collections import defaultdict

from app.models.user import Student
from app.models.practice import PracticeSession, QuestionAttempt
from app.models.gamification import StudentTopicProgress, StudentStreak
from app.models.curriculum import Question, Subject, Topic

class StudentProgressAnalytics:
    """Analytics service for student progress"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_comprehensive_analytics(self, student_id: UUID) -> Dict:
        """Get comprehensive analytics for a student"""
        student = await self.db.get(Student, student_id)
        if not student:
            return {"error": "Student not found"}
        
        return {
            "overview": await self._get_overview(student),
            "activity": await self._get_activity_analytics(student_id),
            "performance": await self._get_performance_analytics(student_id),
            "subjects": await self._get_subject_analytics(student_id),
            "trends": await self._get_trend_analytics(student_id),
            "predictions": await self._get_predictions(student_id)
        }
    
    async def _get_overview(self, student: Student) -> Dict:
        """Get overview stats"""
        # Get total attempts
        result = await self.db.execute(
            select(func.count(QuestionAttempt.id))
            .where(QuestionAttempt.student_id == student.id)
        )
        total_attempts = result.scalar() or 0
        
        # Get correct count
        result = await self.db.execute(
            select(func.count(QuestionAttempt.id))
            .where(QuestionAttempt.student_id == student.id)
            .where(QuestionAttempt.is_correct == True)
        )
        correct_count = result.scalar() or 0
        
        # Get streak
        streak_result = await self.db.execute(
            select(StudentStreak).where(StudentStreak.student_id == student.id)
        )
        streak = streak_result.scalar_one_or_none()
        
        return {
            "total_xp": student.total_xp,
            "level": student.level,
            "total_questions": total_attempts,
            "correct_answers": correct_count,
            "accuracy": round((correct_count / total_attempts * 100) if total_attempts > 0 else 0, 1),
            "current_streak": streak.current_streak if streak else 0,
            "longest_streak": streak.longest_streak if streak else 0,
            "total_active_days": streak.total_active_days if streak else 0
        }
    
    async def _get_activity_analytics(self, student_id: UUID) -> Dict:
        """Get activity patterns"""
        # Get last 30 days of activity
        thirty_days_ago = date.today() - timedelta(days=30)
        
        result = await self.db.execute(
            select(
                func.date(QuestionAttempt.attempted_at).label("date"),
                func.count(QuestionAttempt.id).label("count")
            )
            .where(QuestionAttempt.student_id == student_id)
            .where(func.date(QuestionAttempt.attempted_at) >= thirty_days_ago)
            .group_by(func.date(QuestionAttempt.attempted_at))
        )
        
        daily_activity = {row.date.isoformat(): row.count for row in result.all()}
        
        # Get hour of day distribution
        result = await self.db.execute(
            select(
                func.extract('hour', QuestionAttempt.attempted_at).label("hour"),
                func.count(QuestionAttempt.id).label("count")
            )
            .where(QuestionAttempt.student_id == student_id)
            .group_by(func.extract('hour', QuestionAttempt.attempted_at))
        )
        
        hourly_distribution = {int(row.hour): row.count for row in result.all()}
        
        # Find peak hours
        peak_hour = max(hourly_distribution, key=hourly_distribution.get) if hourly_distribution else 0
        
        return {
            "daily_activity_30d": daily_activity,
            "hourly_distribution": hourly_distribution,
            "peak_study_hour": peak_hour,
            "most_active_day": max(daily_activity, key=daily_activity.get) if daily_activity else None
        }
    
    async def _get_performance_analytics(self, student_id: UUID) -> Dict:
        """Get performance analytics by difficulty"""
        result = await self.db.execute(
            select(QuestionAttempt, Question)
            .join(Question, QuestionAttempt.question_id == Question.id)
            .where(QuestionAttempt.student_id == student_id)
        )
        
        by_difficulty = defaultdict(lambda: {"attempted": 0, "correct": 0})
        
        for attempt, question in result.all():
            diff = question.difficulty or "medium"
            by_difficulty[diff]["attempted"] += 1
            if attempt.is_correct:
                by_difficulty[diff]["correct"] += 1
        
        performance = {}
        for diff, stats in by_difficulty.items():
            acc = (stats["correct"] / stats["attempted"] * 100) if stats["attempted"] > 0 else 0
            performance[diff] = {
                "attempted": stats["attempted"],
                "correct": stats["correct"],
                "accuracy": round(acc, 1)
            }
        
        return performance
    
    async def _get_subject_analytics(self, student_id: UUID) -> List[Dict]:
        """Get analytics by subject"""
        result = await self.db.execute(
            select(
                Subject.name,
                func.count(QuestionAttempt.id).label("attempted"),
                func.sum(QuestionAttempt.is_correct.cast(Integer)).label("correct")
            )
            .join(Question, QuestionAttempt.question_id == Question.id)
            .join(Subject, Question.subject_id == Subject.id)
            .where(QuestionAttempt.student_id == student_id)
            .group_by(Subject.name)
        )
        
        subjects = []
        for row in result.all():
            acc = (row.correct / row.attempted * 100) if row.attempted > 0 else 0
            subjects.append({
                "subject": row.name,
                "questions_attempted": row.attempted,
                "correct": row.correct or 0,
                "accuracy": round(acc, 1)
            })
        
        return sorted(subjects, key=lambda x: x["questions_attempted"], reverse=True)
    
    async def _get_trend_analytics(self, student_id: UUID) -> Dict:
        """Get performance trends over time"""
        # Weekly averages for last 8 weeks
        eight_weeks_ago = date.today() - timedelta(weeks=8)
        
        result = await self.db.execute(
            select(
                func.date_trunc('week', QuestionAttempt.attempted_at).label("week"),
                func.count(QuestionAttempt.id).label("total"),
                func.sum(QuestionAttempt.is_correct.cast(Integer)).label("correct")
            )
            .where(QuestionAttempt.student_id == student_id)
            .where(func.date(QuestionAttempt.attempted_at) >= eight_weeks_ago)
            .group_by(func.date_trunc('week', QuestionAttempt.attempted_at))
            .order_by(func.date_trunc('week', QuestionAttempt.attempted_at))
        )
        
        weekly_trends = []
        for row in result.all():
            acc = (row.correct / row.total * 100) if row.total > 0 else 0
            weekly_trends.append({
                "week": row.week.isoformat() if row.week else None,
                "questions": row.total,
                "accuracy": round(acc, 1)
            })
        
        # Calculate trend direction
        if len(weekly_trends) >= 2:
            recent_acc = weekly_trends[-1]["accuracy"]
            older_acc = weekly_trends[-2]["accuracy"]
            trend = "improving" if recent_acc > older_acc else "declining" if recent_acc < older_acc else "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "weekly_data": weekly_trends,
            "trend_direction": trend
        }
    
    async def _get_predictions(self, student_id: UUID) -> Dict:
        """Generate predictions and recommendations"""
        # Get topic progress
        result = await self.db.execute(
            select(StudentTopicProgress, Topic)
            .join(Topic, StudentTopicProgress.topic_id == Topic.id)
            .where(StudentTopicProgress.student_id == student_id)
        )
        
        topics_needing_review = []
        topics_for_advancement = []
        
        for progress, topic in result.all():
            mastery = float(progress.mastery_level)
            
            if mastery < 50:
                topics_needing_review.append({
                    "topic": topic.name,
                    "mastery": mastery,
                    "priority": "high" if mastery < 30 else "medium"
                })
            elif mastery >= 80:
                topics_for_advancement.append({
                    "topic": topic.name,
                    "mastery": mastery
                })
        
        # Exam readiness score (simplified)
        avg_mastery = sum(float(p[0].mastery_level) for p in result.all()) / len(result.all()) if result.all() else 0
        
        return {
            "exam_readiness_score": round(avg_mastery, 1),
            "topics_needing_review": sorted(topics_needing_review, key=lambda x: x["mastery"])[:5],
            "ready_for_advancement": topics_for_advancement[:3],
            "recommended_daily_goal": 10 if avg_mastery < 50 else 15 if avg_mastery < 70 else 20
        }