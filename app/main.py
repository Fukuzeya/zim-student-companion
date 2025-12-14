# ============================================================================
# FastAPI Application Entry Point
# ============================================================================
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.config import get_settings
from app.core.exceptions import ZSCException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown"""
    logger.info("🚀 Starting Zim Student Companion...")
    
    from app.models.user import User, Student, ParentStudentLink
    from app.models.curriculum import Subject, Topic, LearningObjective, Question
    from app.models.practice import PracticeSession, QuestionAttempt
    from app.models.gamification import (
        Achievement, StudentAchievement, StudentStreak, 
        StudentTopicProgress, Competition, CompetitionParticipant
    )
    from app.models.payment import SubscriptionPlan, Payment
    from app.models.conversation import Conversation
    
    # Now import database components
    from app.core.database import engine, Base
    
    # Initialize database tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables created/verified")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    
    # Initialize Redis (optional - continue if fails)
    try:
        from app.core.redis import redis_client
        await redis_client.ping()
        logger.info("✅ Redis connected")
    except Exception as e:
        logger.warning(f"⚠️ Redis connection failed (non-critical): {e}")
    
    # Initialize Vector Store (optional - continue if fails)
    try:
        from app.services.rag.vector_store import VectorStore
        vector_store = VectorStore(settings)
        await vector_store.initialize_collections()
        app.state.vector_store = vector_store
        logger.info("✅ Vector store initialized")
    except Exception as e:
        logger.warning(f"⚠️ Vector store initialization failed (non-critical): {e}")
        app.state.vector_store = None
    
    logger.info("🎉 Application started successfully!")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down...")
    try:
        from app.core.database import engine
        await engine.dispose()
    except:
        pass

# Create FastAPI app - ALWAYS enable docs for now (remove condition)
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered ZIMSEC study companion for Zimbabwean students",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",      # Changed: Always available at /docs
    redoc_url="/redoc",    # Changed: Always available at /redoc
    openapi_url="/openapi.json"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handler
@app.exception_handler(ZSCException)
async def zsc_exception_handler(request: Request, exc: ZSCException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_code": exc.error_code}
    )

# Health Check - Root level
@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "app": settings.APP_NAME}

# Include API Router - import here to avoid circular imports
try:
    from app.api.v1.router import api_router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    logger.info(f"✅ API router mounted at {settings.API_V1_PREFIX}")
except ImportError as e:
    logger.warning(f"⚠️ Could not import API router: {e}")
