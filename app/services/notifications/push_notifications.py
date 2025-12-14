# ============================================================================
# Push Notification Service
# ============================================================================
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from datetime import datetime, time
import logging

from app.models.user import User, Student, ParentStudentLink
from app.services.whatsapp.client import WhatsAppClient

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for sending notifications via WhatsApp"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.wa_client = WhatsAppClient()
    
    async def send_daily_reminder(self, student_id: UUID) -> bool:
        """Send daily practice reminder to student"""
        student = await self.db.get(Student, student_id)
        if not student:
            return False
        
        user = await self.db.get(User, student.user_id)
        if not user:
            return False
        
        message = f"""🌅 Good morning, {student.first_name}!

Ready for today's practice? 📚

Your goals for today:
• Complete 5 practice questions
• Maintain your streak 🔥
• Learn something new!

Type *practice* to start, or ask me any question!
"""
        
        try:
            await self.wa_client.send_text(user.phone_number, message)
            return True
        except Exception as e:
            logger.error(f"Failed to send reminder: {e}")
            return False
    
    async def send_streak_warning(self, student_id: UUID) -> bool:
        """Warn student about losing streak"""
        student = await self.db.get(Student, student_id)
        user = await self.db.get(User, student.user_id)
        
        if not student or not user:
            return False
        
        from app.models.gamification import StudentStreak
        result = await self.db.execute(
            select(StudentStreak).where(StudentStreak.student_id == student_id)
        )
        streak = result.scalar_one_or_none()
        
        if not streak or streak.current_streak < 3:
            return False
        
        message = f"""⚠️ {student.first_name}, your {streak.current_streak}-day streak is at risk!

You haven't practiced today yet. Complete just one question to keep your streak alive! 🔥

Type *practice* now - it only takes 2 minutes!
"""
        
        try:
            await self.wa_client.send_text(user.phone_number, message)
            return True
        except Exception as e:
            logger.error(f"Failed to send streak warning: {e}")
            return False
    
    async def send_achievement_notification(
        self,
        student_id: UUID,
        achievement_name: str,
        achievement_icon: str,
        points: int
    ) -> bool:
        """Notify student of new achievement"""
        student = await self.db.get(Student, student_id)
        user = await self.db.get(User, student.user_id)
        
        if not student or not user:
            return False
        
        message = f"""🏆 *ACHIEVEMENT UNLOCKED!*

{achievement_icon} *{achievement_name}*

You earned +{points} XP!

Keep up the amazing work, {student.first_name}! 🌟

Type *achievements* to see all your badges.
"""
        
        try:
            await self.wa_client.send_text(user.phone_number, message)
            return True
        except Exception as e:
            logger.error(f"Failed to send achievement notification: {e}")
            return False
    
    async def send_parent_weekly_report(
        self,
        parent_user_id: UUID,
        student_id: UUID,
        report: Dict
    ) -> bool:
        """Send weekly report to parent"""
        parent = await self.db.get(User, parent_user_id)
        student = await self.db.get(Student, student_id)
        
        if not parent or not student:
            return False
        
        summary = report.get("summary", {})
        
        message = f"""📊 *Weekly Report for {student.first_name}*

📅 Week: {report.get('week_start')} to {report.get('week_end')}

📈 *Summary:*
• Questions: {summary.get('total_questions', 0)}
• Accuracy: {summary.get('accuracy_percentage', 0)}%
• Active Days: {summary.get('active_days', 0)}/7
• Streak: {summary.get('current_streak', 0)} days 🔥

💪 Strongest Area: {report.get('strongest_area', {}).get('topic', 'N/A')}
📚 Needs Practice: {report.get('needs_attention', {}).get('topic', 'N/A')}

Type *report {student.first_name}* for more details.
"""
        
        try:
            await self.wa_client.send_text(parent.phone_number, message)
            return True
        except Exception as e:
            logger.error(f"Failed to send parent report: {e}")
            return False
    
    async def send_competition_notification(
        self,
        student_ids: List[UUID],
        competition_name: str,
        start_time: datetime
    ) -> int:
        """Notify students about upcoming competition"""
        sent_count = 0
        
        message = f"""🏆 *Competition Alert!*

"{competition_name}" starts soon!

⏰ Start Time: {start_time.strftime('%H:%M on %d %B')}

Type *competitions* to register and compete for prizes!

Good luck! 🍀
"""
        
        for student_id in student_ids:
            student = await self.db.get(Student, student_id)
            if student:
                user = await self.db.get(User, student.user_id)
                if user:
                    try:
                        await self.wa_client.send_text(user.phone_number, message)
                        sent_count += 1
                    except:
                        pass
        
        return sent_count