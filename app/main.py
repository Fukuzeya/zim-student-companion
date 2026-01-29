# ============================================================================
# FastAPI Application Entry Point
# ============================================================================
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time

from app.config import get_settings
from app.core.exceptions import ZSCException

# Import RAG components
from app.services.rag import (
    create_embedding_service,
    create_vector_store,
    create_rag_engine,
    Retriever,
    get_metrics_collector,
    RedisCacheAdapter,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

settings = get_settings()


# ============================================================================
# Application Lifespan Handler
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan - handles startup and shutdown.
    
    Startup:
    - Initialize database tables
    - Connect to Redis
    - Initialize RAG pipeline (embedding service, vector store, engine)
    
    Shutdown:
    - Close RAG engine connections
    - Dispose database engine
    - Close Redis connection
    """
    startup_start = time.time()
    logger.info("🚀 Starting Zim Student Companion...")
    
    # ==================== Import Models ====================
    # Import all models to register them with SQLAlchemy
    from app.models.user import User, Student, ParentStudentLink
    from app.models.curriculum import Subject, Topic, LearningObjective, Question
    from app.models.practice import PracticeSession, QuestionAttempt
    from app.models.gamification import (
        Achievement, StudentAchievement, StudentStreak,
        StudentTopicProgress, Competition, CompetitionParticipant
    )
    from app.models.payment import SubscriptionPlan, Payment
    from app.models.conversation import Conversation
    from app.models.document import UploadedDocument, DocumentProcessingLog
    
    # ==================== Initialize Database ====================
    from app.core.database import engine, Base
    
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables created/verified")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    
    # ==================== Initialize Redis ====================
    redis_client = None
    redis_cache = None
    
    try:
        from app.core.redis import redis_client as _redis_client
        redis_client = _redis_client
        await redis_client.ping()
        logger.info("✅ Redis connected")
        
        # Create Redis cache adapter for RAG pipeline
        redis_cache = RedisCacheAdapter(redis_client, prefix="rag")
        app.state.redis_cache = redis_cache
        
    except Exception as e:
        logger.warning(f"⚠️ Redis connection failed (will use in-memory cache): {e}")
        redis_cache = None
    
    # ==================== Initialize RAG Pipeline ====================
    try:
        logger.info("Initializing RAG pipeline...")
        
        # 1. Create embedding service with optional Redis cache
        embedding_service = create_embedding_service(
            settings,
            redis_cache=redis_cache
        )
        app.state.embedding_service = embedding_service
        logger.info("  ✓ Embedding service created")
        
        # 2. Create vector store with embedding service
        vector_store = create_vector_store(
            settings,
            embedding_service=embedding_service
        )
        app.state.vector_store = vector_store
        
        # Initialize collections
        await vector_store.initialize_collections()
        logger.info("  ✓ Vector store initialized")
        
        # 3. Create retriever
        retriever = Retriever(
            vector_store=vector_store,
            embedding_service=embedding_service,
            settings=settings
        )
        app.state.retriever = retriever
        logger.info("  ✓ Retriever created")
        
        # 4. Create RAG engine with all components
        rag_engine = create_rag_engine(
            settings,
            vector_store=vector_store,
            embedding_service=embedding_service
        )
        await rag_engine.initialize()
        app.state.rag_engine = rag_engine
        logger.info("  ✓ RAG engine initialized")
        
        logger.info("✅ RAG pipeline ready")
        
    except Exception as e:
        logger.error(f"❌ RAG pipeline initialization failed: {e}")
        # Set None values so app can still run (with limited functionality)
        app.state.embedding_service = None
        app.state.vector_store = None
        app.state.retriever = None
        app.state.rag_engine = None
        logger.warning("⚠️ Application running without RAG capabilities")
    
    # ==================== Startup Complete ====================
    startup_time = time.time() - startup_start
    logger.info(f"🎉 Application started successfully in {startup_time:.2f}s!")
    
    yield
    
    # ==================== Shutdown ====================
    logger.info("👋 Shutting down...")
    
    # Close RAG engine
    if hasattr(app.state, 'rag_engine') and app.state.rag_engine:
        try:
            await app.state.rag_engine.close()
            logger.info("  ✓ RAG engine closed")
        except Exception as e:
            logger.error(f"  ✗ Error closing RAG engine: {e}")
    
    # Close vector store
    if hasattr(app.state, 'vector_store') and app.state.vector_store:
        try:
            await app.state.vector_store.close()
            logger.info("  ✓ Vector store closed")
        except Exception as e:
            logger.error(f"  ✗ Error closing vector store: {e}")
    
    # Close database
    try:
        from app.core.database import engine
        await engine.dispose()
        logger.info("  ✓ Database connections closed")
    except Exception as e:
        logger.error(f"  ✗ Error closing database: {e}")
    
    # Close Redis
    if redis_client:
        try:
            await redis_client.close()
            logger.info("  ✓ Redis connection closed")
        except Exception as e:
            logger.error(f"  ✗ Error closing Redis: {e}")
    
    logger.info("👋 Shutdown complete")


# ============================================================================
# Create FastAPI Application
# ============================================================================
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered ZIMSEC/Cambridge study companion for Zimbabwean students",
    version="2.0.0",
    lifespan=lifespan,
    # This is the crucial addition:
    root_path="/api", 
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# ============================================================================
# Middleware
# ============================================================================
# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if hasattr(settings, 'CORS_ORIGINS') else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    """Add X-Process-Time header to all responses"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}"
    return response


# ============================================================================
# Exception Handlers
# ============================================================================
@app.exception_handler(ZSCException)
async def zsc_exception_handler(request: Request, exc: ZSCException):
    """Handle custom application exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": exc.error_code
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred",
            "error_code": "INTERNAL_ERROR"
        }
    )


# ============================================================================
# Health and Status Endpoints
# ============================================================================
@app.get("/", tags=["status"])
async def root():
    """Root endpoint - basic app info"""
    return {
        "app": settings.APP_NAME,
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", tags=["status"])
async def health_check(request: Request):
    """
    Comprehensive health check endpoint.
    
    Checks:
    - Database connectivity
    - Redis connectivity
    - RAG pipeline status
    - Recent metrics
    """
    health = {
        "status": "healthy",
        "timestamp": time.time(),
        "components": {}
    }
    
    # Check database
    try:
        from app.core.database import async_session_maker
        async with async_session_maker() as session:
            await session.execute("SELECT 1")
        health["components"]["database"] = {"status": "healthy"}
    except Exception as e:
        health["status"] = "degraded"
        health["components"]["database"] = {"status": "unhealthy", "error": str(e)}
    
    # Check Redis
    try:
        from app.core.redis import redis_client
        await redis_client.ping()
        health["components"]["redis"] = {"status": "healthy"}
    except Exception as e:
        health["components"]["redis"] = {"status": "unhealthy", "error": str(e)}
    
    # Check RAG engine
    if hasattr(request.app.state, 'rag_engine') and request.app.state.rag_engine:
        try:
            rag_health = await request.app.state.rag_engine.health_check()
            health["components"]["rag_engine"] = {
                "status": rag_health.get("status", "unknown"),
                "collections": len(rag_health.get("collections", {}))
            }
        except Exception as e:
            health["status"] = "degraded"
            health["components"]["rag_engine"] = {"status": "unhealthy", "error": str(e)}
    else:
        health["status"] = "degraded"
        health["components"]["rag_engine"] = {"status": "not_initialized"}
    
    # Check Vector Store
    if hasattr(request.app.state, 'vector_store') and request.app.state.vector_store:
        try:
            stats = await request.app.state.vector_store.get_stats()
            total_docs = sum(s.points_count for s in stats.values() if hasattr(s, 'points_count'))
            health["components"]["vector_store"] = {
                "status": "healthy",
                "collections": len(stats),
                "total_documents": total_docs
            }
        except Exception as e:
            health["components"]["vector_store"] = {"status": "error", "error": str(e)}
    else:
        health["components"]["vector_store"] = {"status": "not_initialized"}
    
    # Add recent metrics
    try:
        metrics = get_metrics_collector().get_stats(period_hours=1)
        health["metrics"] = {
            "queries_last_hour": metrics.get("query_count", 0),
            "error_rate": round(metrics.get("error_rate", 0), 4),
            "avg_latency_ms": round(metrics.get("latency", {}).get("avg_ms", 0), 2),
        }
    except Exception:
        health["metrics"] = {}
    
    return health


@app.get("/health/rag", tags=["status"])
async def rag_health_check(request: Request):
    """
    Detailed RAG pipeline health check.
    
    Returns detailed information about:
    - Embedding service status and cache stats
    - Vector store collections and document counts
    - Retriever configuration
    - Recent query metrics
    """
    if not hasattr(request.app.state, 'rag_engine') or not request.app.state.rag_engine:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "message": "RAG engine not initialized"}
        )
    
    result = {
        "status": "healthy",
        "components": {}
    }
    
    # RAG Engine health
    try:
        rag_health = await request.app.state.rag_engine.health_check()
        result["components"]["rag_engine"] = rag_health
    except Exception as e:
        result["status"] = "degraded"
        result["components"]["rag_engine"] = {"error": str(e)}
    
    # Embedding service stats
    if hasattr(request.app.state, 'embedding_service') and request.app.state.embedding_service:
        try:
            emb_stats = request.app.state.embedding_service.stats
            result["components"]["embedding_service"] = {
                "status": "healthy",
                "total_requests": emb_stats.get("total_requests", 0),
                "cache_hits": emb_stats.get("cache_hits", 0),
                "api_calls": emb_stats.get("api_calls", 0),
                "errors": emb_stats.get("errors", 0),
                "l1_cache": emb_stats.get("l1_cache", {})
            }
        except Exception as e:
            result["components"]["embedding_service"] = {"error": str(e)}
    
    # Vector store details
    if hasattr(request.app.state, 'vector_store') and request.app.state.vector_store:
        try:
            stats = await request.app.state.vector_store.get_stats()
            collections_info = {}
            for name, stat in stats.items():
                if hasattr(stat, 'points_count'):
                    collections_info[name] = {
                        "documents": stat.points_count,
                        "status": stat.status
                    }
            result["components"]["vector_store"] = {
                "status": "healthy",
                "collections": collections_info
            }
        except Exception as e:
            result["components"]["vector_store"] = {"error": str(e)}
    
    # Query metrics
    try:
        metrics = get_metrics_collector().get_stats(period_hours=24)
        result["metrics_24h"] = {
            "total_queries": metrics.get("query_count", 0),
            "error_rate": metrics.get("error_rate", 0),
            "avg_latency_ms": metrics.get("latency", {}).get("avg_ms", 0),
            "p95_latency_ms": metrics.get("latency", {}).get("p95_ms", 0),
            "avg_confidence": metrics.get("confidence", {}).get("avg", 0),
            "by_mode": metrics.get("by_mode", {}),
            "by_subject": metrics.get("by_subject", {}),
        }
    except Exception:
        result["metrics_24h"] = {}
    
    return result


# ============================================================================
# Include API Routers
# ============================================================================
try:
    from app.api.v1.router import api_router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    logger.info(f"✅ API router mounted at {settings.API_V1_PREFIX}")
except ImportError as e:
    logger.warning(f"⚠️ Could not import API router: {e}")

# Note: Webhook router is already included via api_router in router.py
# No need to include it separately here