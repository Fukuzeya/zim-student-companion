# ============================================================================
# API Dependencies
# ============================================================================
from typing import Optional, AsyncGenerator
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import logging

from app.core.database import get_db
from app.core.security import get_current_user, get_current_active_user
from app.core.redis import cache
from app.core.exceptions import RateLimitExceeded, SubscriptionRequired
from app.models.user import User, Student, SubscriptionTier
from app.config import get_settings

# Import from RAG pipeline
from app.services.rag import (
    RAGEngine,
    VectorStore,
    EmbeddingService,
    Retriever,
    MetricsCollector,
    get_metrics_collector,
)

settings = get_settings()
security = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


# ============================================================================
# RAG Pipeline Dependencies
# ============================================================================
async def get_embedding_service(request: Request) -> EmbeddingService:
    """
    Get embedding service from app state.
    
    The embedding service is initialized once at startup and stored
    in app.state for reuse across requests.
    """
    if not hasattr(request.app.state, 'embedding_service'):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding service not initialized"
        )
    return request.app.state.embedding_service


async def get_vector_store(request: Request) -> VectorStore:
    """
    Get vector store from app state.
    
    The vector store is initialized once at startup with proper
    collection setup and stored in app.state.
    """
    if not hasattr(request.app.state, 'vector_store'):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector store not initialized"
        )
    return request.app.state.vector_store


async def get_rag_engine(request: Request) -> RAGEngine:
    """
    Get RAG engine from app state.
    
    The RAG engine is initialized once at startup with all components
    (embedding service, vector store, retriever) and stored in app.state.
    
    Usage:
        @router.post("/query")
        async def query_rag(
            question: str,
            rag: RAGEngine = Depends(get_rag_engine)
        ):
            response, docs = await rag.query(
                question=question,
                student_context={...},
                mode="explain"
            )
    """
    if not hasattr(request.app.state, 'rag_engine'):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG engine not initialized"
        )
    return request.app.state.rag_engine


async def get_retriever(request: Request) -> Retriever:
    """
    Get retriever from app state for direct retrieval operations.
    
    Useful for advanced use cases where you need retrieval
    without generation.
    """
    if not hasattr(request.app.state, 'retriever'):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Retriever not initialized"
        )
    return request.app.state.retriever


def get_metrics() -> MetricsCollector:
    """
    Get metrics collector for recording RAG metrics.
    
    Usage:
        @router.post("/query")
        async def query(
            metrics: MetricsCollector = Depends(get_metrics)
        ):
            metrics.record_query(...)
    """
    return get_metrics_collector()


# ============================================================================
# Student Dependencies
# ============================================================================
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


# ============================================================================
# Rate Limiting Dependencies
# ============================================================================
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


# ============================================================================
# Subscription Dependencies
# ============================================================================
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