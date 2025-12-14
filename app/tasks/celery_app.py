# ============================================================================
# Celery Application Configuration
# ============================================================================
from celery import Celery
from celery.schedules import crontab
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "zim_student_companion",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.daily_tasks",
        "app.tasks.report_tasks",
        "app.tasks.cleanup_tasks"
    ]
)

# Celery Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Harare",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

# Beat Schedule (Periodic Tasks)
celery_app.conf.beat_schedule = {
    # Daily morning reminders (6 AM Zimbabwe time)
    "daily-morning-reminders": {
        "task": "app.tasks.daily_tasks.send_morning_reminders",
        "schedule": crontab(hour=6, minute=0),
    },
    
    # Daily streak warnings (8 PM Zimbabwe time)
    "daily-streak-warnings": {
        "task": "app.tasks.daily_tasks.send_streak_warnings",
        "schedule": crontab(hour=20, minute=0),
    },
    
    # Generate daily questions (midnight)
    "generate-daily-questions": {
        "task": "app.tasks.daily_tasks.generate_daily_questions",
        "schedule": crontab(hour=0, minute=30),
    },
    
    # Weekly parent reports (Sunday 6 PM)
    "weekly-parent-reports": {
        "task": "app.tasks.report_tasks.send_weekly_parent_reports",
        "schedule": crontab(hour=18, minute=0, day_of_week=0),
    },
    
    # Check expiring subscriptions (daily at noon)
    "check-expiring-subscriptions": {
        "task": "app.tasks.daily_tasks.check_expiring_subscriptions",
        "schedule": crontab(hour=12, minute=0),
    },
    
    # Update competition rankings (every hour)
    "update-competition-rankings": {
        "task": "app.tasks.daily_tasks.update_competition_rankings",
        "schedule": crontab(minute=5),
    },
    
    # Cleanup old data (weekly, Sunday 2 AM)
    "weekly-cleanup": {
        "task": "app.tasks.cleanup_tasks.cleanup_old_data",
        "schedule": crontab(hour=2, minute=0, day_of_week=0),
    },
    
    # Check achievements (every 30 minutes)
    "check-achievements": {
        "task": "app.tasks.daily_tasks.check_pending_achievements",
        "schedule": crontab(minute="*/30"),
    },
}
