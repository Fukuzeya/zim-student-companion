# ============================================================================
# Daily Scheduled Tasks
# ============================================================================
from celery import shared_task
from datetime import datetime, date, timedelta
from typing import List
import asyncio
import logging

logger = logging.getLogger(__name__)

def run_async(coro):
    """Helper to run async functions in Celery tasks"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

@shared_task(name="app.tasks.daily_tasks.send_morning_reminders")
def send_morning_reminders():
    """Send morning practice reminders to active students"""
    async def _send_reminders():
        from app.core.database import async_session_maker
        from app.services.notifications.push_notifications import NotificationService
        from app.models.user import Student, User
        from app.models.gamification import StudentStreak
        from sqlalchemy import select
        
        async with async_session_maker() as db:
            # Get active students who have practiced in the last 7 days
            week_ago = date.today() - timedelta(days=7)
            
            result = await db.execute(
                select(Student)
                .join(StudentStreak, Student.id == StudentStreak.student_id)
                .where(StudentStreak.last_activity_date >= week_ago)
            )
            students = result.scalars().all()
            
            notification_service = NotificationService(db)
            sent_count = 0
            
            for student in students:
                try:
                    success = await notification_service.send_daily_reminder(student.id)
                    if success:
                        sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to send reminder to {student.id}: {e}")
            
            logger.info(f"Sent {sent_count} morning reminders")
            return sent_count
    
    return run_async(_send_reminders())

@shared_task(name="app.tasks.daily_tasks.send_streak_warnings")
def send_streak_warnings():
    """Send warnings to students about to lose their streak"""
    async def _send_warnings():
        from app.core.database import async_session_maker
        from app.services.notifications.push_notifications import NotificationService
        from app.models.gamification import StudentStreak
        from sqlalchemy import select
        
        async with async_session_maker() as db:
            today = date.today()
            
            # Find students with streaks >= 3 who haven't practiced today
            result = await db.execute(
                select(StudentStreak)
                .where(StudentStreak.current_streak >= 3)
                .where(StudentStreak.last_activity_date < today)
            )
            at_risk = result.scalars().all()
            
            notification_service = NotificationService(db)
            sent_count = 0
            
            for streak in at_risk:
                try:
                    success = await notification_service.send_streak_warning(streak.student_id)
                    if success:
                        sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to send streak warning: {e}")
            
            logger.info(f"Sent {sent_count} streak warnings")
            return sent_count
    
    return run_async(_send_warnings())

@shared_task(name="app.tasks.daily_tasks.generate_daily_questions")
def generate_daily_questions():
    """Pre-generate daily practice questions for popular topics"""
    async def _generate():
        from app.core.database import async_session_maker
        from app.models.curriculum import Subject, Topic, Question
        from app.services.rag.rag_engine import RAGEngine
        from app.services.rag.vector_store import VectorStore
        from app.config import get_settings
        from sqlalchemy import select, func
        
        settings = get_settings()
        
        async with async_session_maker() as db:
            # Get topics that need more questions
            result = await db.execute(
                select(Topic)
                .join(Subject, Topic.subject_id == Subject.id)
                .where(Subject.is_active == True)
                .limit(20)
            )
            topics = result.scalars().all()
            
            vector_store = VectorStore(settings)
            rag_engine = RAGEngine(vector_store, settings)
            
            generated_count = 0
            
            for topic in topics:
                # Check existing question count
                count_result = await db.execute(
                    select(func.count(Question.id))
                    .where(Question.topic_id == topic.id)
                )
                existing_count = count_result.scalar() or 0
                
                # Generate if we have fewer than 50 questions
                if existing_count < 50:
                    try:
                        for difficulty in ["easy", "medium", "hard"]:
                            # Generate 2 questions per difficulty
                            for _ in range(2):
                                q_data = await rag_engine.generate_practice_question(
                                    topic_id=str(topic.id),
                                    difficulty=difficulty,
                                    student_context={
                                        "education_level": "secondary",
                                        "grade": topic.grade,
                                        "current_subject": topic.subject.name if topic.subject else None
                                    }
                                )
                                
                                question = Question(
                                    topic_id=topic.id,
                                    subject_id=topic.subject_id,
                                    question_text=q_data.get("question", ""),
                                    question_type=q_data.get("question_type", "short_answer"),
                                    options=q_data.get("options"),
                                    correct_answer=q_data.get("correct_answer", ""),
                                    explanation=q_data.get("explanation"),
                                    difficulty=difficulty,
                                    marks=q_data.get("marks", 1),
                                    source="generated"
                                )
                                db.add(question)
                                generated_count += 1
                        
                        await db.commit()
                    except Exception as e:
                        logger.error(f"Failed to generate questions for topic {topic.id}: {e}")
            
            logger.info(f"Generated {generated_count} new questions")
            return generated_count
    
    return run_async(_generate())

@shared_task(name="app.tasks.daily_tasks.check_expiring_subscriptions")
def check_expiring_subscriptions():
    """Notify users about expiring subscriptions"""
    async def _check():
        from app.core.database import async_session_maker
        from app.models.user import User, SubscriptionTier
        from app.services.whatsapp.client import WhatsAppClient
        from sqlalchemy import select, and_
        
        async with async_session_maker() as db:
            # Users expiring in 3 days
            three_days = datetime.utcnow() + timedelta(days=3)
            one_day = datetime.utcnow() + timedelta(days=1)
            
            result = await db.execute(
                select(User)
                .where(User.subscription_tier != SubscriptionTier.FREE)
                .where(User.subscription_expires_at.between(datetime.utcnow(), three_days))
            )
            expiring_users = result.scalars().all()
            
            wa_client = WhatsAppClient()
            notified = 0
            
            for user in expiring_users:
                days_left = (user.subscription_expires_at - datetime.utcnow()).days
                
                try:
                    await wa_client.send_text(
                        user.phone_number,
                        f"⏰ Your {user.subscription_tier.value.title()} subscription expires in {days_left} day(s)!\n\n"
                        f"Renew now to continue unlimited learning.\n\n"
                        f"Type *renew* to extend your subscription."
                    )
                    notified += 1
                except Exception as e:
                    logger.error(f"Failed to notify user {user.id}: {e}")
            
            logger.info(f"Notified {notified} users about expiring subscriptions")
            return notified
    
    return run_async(_check())

@shared_task(name="app.tasks.daily_tasks.update_competition_rankings")
def update_competition_rankings():
    """Update rankings for active competitions"""
    async def _update():
        from app.core.database import async_session_maker
        from app.models.gamification import Competition, CompetitionParticipant
        from sqlalchemy import select, update
        
        async with async_session_maker() as db:
            # Get active competitions
            result = await db.execute(
                select(Competition).where(Competition.status == "active")
            )
            competitions = result.scalars().all()
            
            for competition in competitions:
                # Get participants ordered by score
                result = await db.execute(
                    select(CompetitionParticipant)
                    .where(CompetitionParticipant.competition_id == competition.id)
                    .order_by(CompetitionParticipant.score.desc())
                )
                participants = result.scalars().all()
                
                # Update ranks
                for rank, participant in enumerate(participants, 1):
                    participant.rank = rank
                
                await db.commit()
            
            logger.info(f"Updated rankings for {len(competitions)} competitions")
            return len(competitions)
    
    return run_async(_update())

@shared_task(name="app.tasks.daily_tasks.check_pending_achievements")
def check_pending_achievements():
    """Check and award pending achievements for active students"""
    async def _check():
        from app.core.database import async_session_maker
        from app.models.user import Student
        from app.models.gamification import StudentStreak
        from app.services.gamification.achievements import AchievementSystem
        from app.services.notifications.push_notifications import NotificationService
        from sqlalchemy import select
        
        async with async_session_maker() as db:
            # Get students active in last hour
            hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            result = await db.execute(
                select(Student)
                .join(StudentStreak, Student.id == StudentStreak.student_id)
                .where(StudentStreak.last_activity_date == date.today())
            )
            active_students = result.scalars().all()
            
            achievement_system = AchievementSystem(db)
            notification_service = NotificationService(db)
            
            total_awarded = 0
            
            for student in active_students:
                try:
                    new_achievements = await achievement_system.check_achievements(student.id)
                    
                    for achievement in new_achievements:
                        await notification_service.send_achievement_notification(
                            student_id=student.id,
                            achievement_name=achievement.name,
                            achievement_icon=achievement.icon or "🏆",
                            points=achievement.points
                        )
                        total_awarded += 1
                except Exception as e:
                    logger.error(f"Failed to check achievements for {student.id}: {e}")
            
            logger.info(f"Awarded {total_awarded} new achievements")
            return total_awarded
    
    return run_async(_check())