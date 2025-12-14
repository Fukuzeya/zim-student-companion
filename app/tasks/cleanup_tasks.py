# ============================================================================
# Data Cleanup Tasks
# ============================================================================
from celery import shared_task
from datetime import datetime, timedelta
import logging

from app.tasks.daily_tasks import run_async

logger = logging.getLogger(__name__)

@shared_task(name="app.tasks.cleanup_tasks.cleanup_old_data")
def cleanup_old_data():
    """Clean up old conversation history and expired data"""
    async def _cleanup():
        from app.core.database import async_session_maker
        from app.models.conversation import Conversation
        from app.models.user import ParentStudentLink
        from sqlalchemy import delete
        
        async with async_session_maker() as db:
            deleted_counts = {}
            
            # Delete conversations older than 90 days
            ninety_days_ago = datetime.utcnow() - timedelta(days=90)
            
            result = await db.execute(
                delete(Conversation)
                .where(Conversation.created_at < ninety_days_ago)
            )
            deleted_counts["old_conversations"] = result.rowcount
            
            # Delete unverified parent links older than 24 hours
            one_day_ago = datetime.utcnow() - timedelta(hours=24)
            
            result = await db.execute(
                delete(ParentStudentLink)
                .where(ParentStudentLink.verified == False)
                .where(ParentStudentLink.created_at < one_day_ago)
            )
            deleted_counts["expired_parent_links"] = result.rowcount
            
            await db.commit()
            
            logger.info(f"Cleanup completed: {deleted_counts}")
            return deleted_counts
    
    return run_async(_cleanup())

@shared_task(name="app.tasks.cleanup_tasks.cleanup_redis_cache")
def cleanup_redis_cache():
    """Clean up expired Redis cache entries"""
    async def _cleanup():
        from app.core.redis import redis_client
        
        # Redis handles expiration automatically, but we can clean up 
        # patterns that might have accumulated
        patterns = [
            "flow_state:*",  # Old conversation states
            "otp:*",         # Old OTPs
            "hints:*",       # Old hint counters
        ]
        
        deleted = 0
        for pattern in patterns:
            cursor = 0
            while True:
                cursor, keys = await redis_client.scan(cursor, match=pattern, count=100)
                if keys:
                    # Check TTL and delete if no TTL (orphaned keys)
                    for key in keys:
                        ttl = await redis_client.ttl(key)
                        if ttl == -1:  # No expiration set
                            await redis_client.delete(key)
                            deleted += 1
                if cursor == 0:
                    break
        
        logger.info(f"Redis cleanup: deleted {deleted} orphaned keys")
        return deleted
    
    return run_async(_cleanup())

@shared_task(name="app.tasks.cleanup_tasks.archive_old_sessions")
def archive_old_sessions():
    """Archive old practice sessions (move to archive table or mark archived)"""
    async def _archive():
        from app.core.database import async_session_maker
        from app.models.practice import PracticeSession
        from sqlalchemy import update
        
        async with async_session_maker() as db:
            # Mark sessions older than 6 months as archived
            six_months_ago = datetime.utcnow() - timedelta(days=180)
            
            result = await db.execute(
                update(PracticeSession)
                .where(PracticeSession.started_at < six_months_ago)
                .where(PracticeSession.status != "archived")
                .values(status="archived")
            )
            
            await db.commit()
            
            logger.info(f"Archived {result.rowcount} old sessions")
            return result.rowcount
    
    return run_async(_archive())