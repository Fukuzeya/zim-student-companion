# ============================================================================
# Parent Report Service
# ============================================================================
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Integer, select, func
from uuid import UUID
from datetime import datetime, timedelta, date
from decimal import Decimal

from app.models.user import Student, ParentStudentLink
from app.models.practice import PracticeSession, QuestionAttempt
from app.models.gamification import StudentStreak, StudentTopicProgress
from app.models.curriculum import Topic, Subject

class ParentReportService:
    """Generate reports for parents about their children's progress"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_report(
        self,
        student_id: UUID,
        report_type: str = "weekly"
    ) -> Dict:
        """Generate a comprehensive report"""
        student = await self.db.get(Student, student_id)
        if not student:
            return {"error": "Student not found"}
        
        if report_type == "daily":
            return await self._generate_daily_report(student)
        elif report_type == "weekly":
            return await self._generate_weekly_report(student)
        elif report_type == "monthly":
            return await self._generate_monthly_report(student)
        else:
            return {"error": "Invalid report type"}
    
    async def _generate_daily_report(self, student: Student) -> Dict:
        """Generate daily activity report"""
        today = date.today()
        
        # Get today's sessions
        result = await self.db.execute(
            select(PracticeSession)
            .where(PracticeSession.student_id == student.id)
            .where(func.date(PracticeSession.started_at) == today)
        )
        sessions = result.scalars().all()
        
        total_questions = sum(s.total_questions or 0 for s in sessions)
        correct_answers = sum(s.correct_answers or 0 for s in sessions)
        time_spent = sum(s.time_spent_seconds or 0 for s in sessions)
        
        # Get streak
        streak_result = await self.db.execute(
            select(StudentStreak).where(StudentStreak.student_id == student.id)
        )
        streak = streak_result.scalar_one_or_none()
        
        accuracy = (correct_answers / total_questions * 100) if total_questions > 0 else 0
        
        return {
            "report_type": "daily",
            "date": today.isoformat(),
            "student": {
                "name": student.first_name,
                "grade": student.grade
            },
            "summary": {
                "questions_attempted": total_questions,
                "correct_answers": correct_answers,
                "accuracy_percentage": round(accuracy, 1),
                "time_spent_minutes": time_spent // 60,
                "sessions_completed": len(sessions),
                "current_streak": streak.current_streak if streak else 0
            },
            "status": self._get_performance_status(accuracy, total_questions),
            "message": self._generate_daily_message(accuracy, total_questions, streak)
        }
    
    async def _generate_weekly_report(self, student: Student) -> Dict:
        """Generate weekly progress report"""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        
        # Get this week's attempts
        result = await self.db.execute(
            select(QuestionAttempt)
            .where(QuestionAttempt.student_id == student.id)
            .where(func.date(QuestionAttempt.attempted_at) >= week_start)
        )
        attempts = result.scalars().all()
        
        total_questions = len(attempts)
        correct_answers = sum(1 for a in attempts if a.is_correct)
        accuracy = (correct_answers / total_questions * 100) if total_questions > 0 else 0
        
        # Get subject breakdown
        from app.models.curriculum import Question
        subject_stats = {}
        for attempt in attempts:
            question = await self.db.get(Question, attempt.question_id)
            if question and question.subject_id:
                subj_id = str(question.subject_id)
                if subj_id not in subject_stats:
                    subject_stats[subj_id] = {"attempted": 0, "correct": 0}
                subject_stats[subj_id]["attempted"] += 1
                if attempt.is_correct:
                    subject_stats[subj_id]["correct"] += 1
        
        # Get topic progress
        progress_result = await self.db.execute(
            select(StudentTopicProgress, Topic)
            .join(Topic, StudentTopicProgress.topic_id == Topic.id)
            .where(StudentTopicProgress.student_id == student.id)
            .order_by(StudentTopicProgress.mastery_level.desc())
        )
        progress_data = progress_result.all()
        
        strongest = progress_data[0] if progress_data else None
        weakest = progress_data[-1] if len(progress_data) > 1 else None
        
        # Get streak info
        streak_result = await self.db.execute(
            select(StudentStreak).where(StudentStreak.student_id == student.id)
        )
        streak = streak_result.scalar_one_or_none()
        
        # Calculate daily breakdown
        daily_stats = {}
        for attempt in attempts:
            day = attempt.attempted_at.date().isoformat()
            if day not in daily_stats:
                daily_stats[day] = {"attempted": 0, "correct": 0}
            daily_stats[day]["attempted"] += 1
            if attempt.is_correct:
                daily_stats[day]["correct"] += 1
        
        return {
            "report_type": "weekly",
            "week_start": week_start.isoformat(),
            "week_end": today.isoformat(),
            "student": {
                "name": student.first_name,
                "grade": student.grade,
                "level": student.level,
                "total_xp": student.total_xp
            },
            "summary": {
                "total_questions": total_questions,
                "correct_answers": correct_answers,
                "accuracy_percentage": round(accuracy, 1),
                "active_days": len(daily_stats),
                "current_streak": streak.current_streak if streak else 0,
                "longest_streak": streak.longest_streak if streak else 0
            },
            "daily_breakdown": daily_stats,
            "strongest_area": {
                "topic": strongest[1].name if strongest else None,
                "mastery": float(strongest[0].mastery_level) if strongest else None
            },
            "needs_attention": {
                "topic": weakest[1].name if weakest else None,
                "mastery": float(weakest[0].mastery_level) if weakest else None
            },
            "recommendations": self._generate_recommendations(accuracy, total_questions, streak),
            "comparison": {
                "vs_last_week": await self._calculate_weekly_change(student.id, week_start)
            }
        }
    
    async def _generate_monthly_report(self, student: Student) -> Dict:
        """Generate monthly comprehensive report"""
        today = date.today()
        month_start = today.replace(day=1)
        
        # Similar structure to weekly but for the month
        # Get attempts for the month
        result = await self.db.execute(
            select(func.count(QuestionAttempt.id).label("total"),
                   func.sum(QuestionAttempt.is_correct.cast(Integer)).label("correct"))
            .where(QuestionAttempt.student_id == student.id)
            .where(func.date(QuestionAttempt.attempted_at) >= month_start)
        )
        stats = result.one()
        
        total = stats.total or 0
        correct = stats.correct or 0
        accuracy = (correct / total * 100) if total > 0 else 0
        
        return {
            "report_type": "monthly",
            "month": month_start.strftime("%B %Y"),
            "student": {
                "name": student.first_name,
                "grade": student.grade,
                "level": student.level,
                "total_xp": student.total_xp
            },
            "summary": {
                "total_questions": total,
                "correct_answers": correct,
                "accuracy_percentage": round(accuracy, 1)
            },
            "achievements_this_month": await self._get_monthly_achievements(student.id, month_start),
            "growth": await self._calculate_monthly_growth(student.id)
        }
    
    def _get_performance_status(self, accuracy: float, questions: int) -> str:
        """Get performance status emoji and text"""
        if questions == 0:
            return "⚠️ No activity today"
        elif accuracy >= 90:
            return "🌟 Excellent!"
        elif accuracy >= 70:
            return "👍 Good progress"
        elif accuracy >= 50:
            return "📈 Keep practicing"
        else:
            return "💪 Needs more practice"
    
    def _generate_daily_message(self, accuracy: float, questions: int, streak) -> str:
        """Generate personalized daily message"""
        if questions == 0:
            return "No practice today. Encourage your child to practice for at least 15 minutes!"
        
        streak_days = streak.current_streak if streak else 0
        
        if accuracy >= 80:
            msg = f"Great day! Answered {questions} questions with {accuracy:.0f}% accuracy."
        else:
            msg = f"Practiced {questions} questions today. More practice will help improve!"
        
        if streak_days >= 7:
            msg += f" 🔥 Amazing {streak_days}-day streak!"
        elif streak_days >= 3:
            msg += f" Keep the {streak_days}-day streak going!"
        
        return msg
    
    def _generate_recommendations(
        self,
        accuracy: float,
        questions: int,
        streak
    ) -> List[str]:
        """Generate personalized recommendations"""
        recommendations = []
        
        if questions < 5:
            recommendations.append("Encourage more daily practice - aim for at least 10 questions per day")
        
        if accuracy < 60:
            recommendations.append("Focus on reviewing weak topics before moving to new ones")
        
        if streak and streak.current_streak == 0:
            recommendations.append("Help maintain a daily practice streak for better retention")
        
        if accuracy >= 80 and questions >= 10:
            recommendations.append("Great progress! Consider increasing difficulty or exploring new topics")
        
        return recommendations
    
    async def _calculate_weekly_change(self, student_id: UUID, current_week_start: date) -> Dict:
        """Calculate change vs previous week"""
        prev_week_start = current_week_start - timedelta(days=7)
        prev_week_end = current_week_start - timedelta(days=1)
        
        # Previous week stats
        result = await self.db.execute(
            select(func.count(QuestionAttempt.id))
            .where(QuestionAttempt.student_id == student_id)
            .where(func.date(QuestionAttempt.attempted_at) >= prev_week_start)
            .where(func.date(QuestionAttempt.attempted_at) <= prev_week_end)
        )
        prev_count = result.scalar() or 0
        
        # Current week stats
        result = await self.db.execute(
            select(func.count(QuestionAttempt.id))
            .where(QuestionAttempt.student_id == student_id)
            .where(func.date(QuestionAttempt.attempted_at) >= current_week_start)
        )
        current_count = result.scalar() or 0
        
        if prev_count > 0:
            change = ((current_count - prev_count) / prev_count) * 100
        else:
            change = 100 if current_count > 0 else 0
        
        return {
            "previous_week_questions": prev_count,
            "current_week_questions": current_count,
            "change_percentage": round(change, 1)
        }
    
    async def _get_monthly_achievements(self, student_id: UUID, month_start: date) -> List[str]:
        """Get achievements earned this month"""
        from app.models.gamification import StudentAchievement, Achievement
        
        result = await self.db.execute(
            select(Achievement.name)
            .join(StudentAchievement, Achievement.id == StudentAchievement.achievement_id)
            .where(StudentAchievement.student_id == student_id)
            .where(func.date(StudentAchievement.earned_at) >= month_start)
        )
        
        return [row[0] for row in result.all()]
    
    async def _calculate_monthly_growth(self, student_id: UUID) -> Dict:
        """Calculate XP and level growth"""
        # This would compare start vs end of month
        return {"xp_gained": 0, "levels_gained": 0}