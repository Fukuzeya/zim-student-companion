# ============================================================================
# API Dependencies
# ============================================================================
from typing import Optional, AsyncGenerator
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user, get_current_active_user
from app.core.redis import cache
from app.core.exceptions import RateLimitExceeded, SubscriptionRequired
from app.models.user import User, Student, SubscriptionTier
from app.services.rag.vector_store import VectorStore
from app.services.rag.rag_engine import RAGEngine
from app.config import get_settings

settings = get_settings()
security = HTTPBearer(auto_error=False)

async def get_vector_store(request: Request) -> VectorStore:
    """Get vector store from app state"""
    return request.app.state.vector_store

async def get_rag_engine(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> RAGEngine:
    """Get RAG engine instance"""
    vector_store = request.app.state.vector_store
    return RAGEngine(vector_store, settings)

async def get_current_student(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Student:
    """Get current student (user must be a student)"""
    from sqlalchemy import select
    
    if current_user.role.value != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is for students only"
        )
    
    result = await db.execute(
        select(Student).where(Student.user_id == current_user.id)
    )
    student = result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found"
        )
    
    return student

async def check_rate_limit(
    current_user: User = Depends(get_current_active_user)
) -> int:
    """Check and enforce rate limits based on subscription tier"""
    tier = current_user.subscription_tier.value
    
    limits = {
        "free": settings.FREE_DAILY_QUESTIONS,
        "basic": settings.BASIC_DAILY_QUESTIONS,
        "premium": settings.PREMIUM_DAILY_QUESTIONS,
        "family": settings.PREMIUM_DAILY_QUESTIONS,
        "school": 10000
    }
    
    limit = limits.get(tier, settings.FREE_DAILY_QUESTIONS)
    rate_key = f"rate_limit:{current_user.id}:daily"
    
    allowed, remaining = await cache.check_rate_limit(rate_key, limit, window=86400)
    
    if not allowed:
        raise RateLimitExceeded()
    
    return remaining

def require_subscription(min_tier: SubscriptionTier):
    """Dependency to require minimum subscription tier"""
    tier_levels = {
        SubscriptionTier.FREE: 0,
        SubscriptionTier.BASIC: 1,
        SubscriptionTier.PREMIUM: 2,
        SubscriptionTier.FAMILY: 2,
        SubscriptionTier.SCHOOL: 3
    }
    
    async def check_subscription(
        current_user: User = Depends(get_current_active_user)
    ):
        user_level = tier_levels.get(current_user.subscription_tier, 0)
        required_level = tier_levels.get(min_tier, 0)
        
        if user_level < required_level:
            raise SubscriptionRequired(min_tier.value)
        
        return current_user
    
    return check_subscription