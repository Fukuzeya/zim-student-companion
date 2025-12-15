# ============================================================================
# RAG Services - Public API
# ============================================================================
"""
ZIMSEC RAG (Retrieval-Augmented Generation) Pipeline

This module provides a production-ready RAG system for educational content
retrieval and AI-powered tutoring.

Main Components:
- RAGEngine: Main orchestrator for queries and response generation
- VectorStore: Qdrant-based vector storage with hybrid search
- Retriever: Multi-strategy document retrieval
- EmbeddingService: High-performance embedding generation
- DocumentProcessor: Intelligent document chunking

Quick Start:
    from app.services.rag import RAGEngine, create_rag_engine
    
    # Create engine with settings
    engine = create_rag_engine(settings)
    await engine.initialize()
    
    # Query
    response, docs = await engine.query(
        question="Explain photosynthesis",
        student_context={"grade": "Form 3", "subject": "Biology"},
        mode="explain"
    )

Available Modes:
- socratic: Guide through questions without direct answers
- explain: Clear, thorough explanations
- practice: Present practice questions
- hint: Provide progressive hints
- summary: Concise topic summaries
- quiz: Generate quiz questions
- marking: Evaluate student answers
"""
from app.services.rag.config import (
    RAGConfig,
    ChunkingStrategy,
    RetrievalStrategy,
    RerankingStrategy,
    get_rag_config,
    # Pre-configured profiles
    PROFILE_EXAM_PREP,
    PROFILE_QUICK_HELP,
    PROFILE_DEEP_EXPLANATION,
)

from app.services.rag.embeddings import (
    EmbeddingService,
    LRUCache,
    TokenBucketRateLimiter,
)

from app.services.rag.document_processor import (
    DocumentProcessor,
    DocumentChunk,
    ZIMSECDocument,
    ChunkingStrategyBase,
    SemanticChunker,
    HierarchicalChunker,
    QuestionAwareChunker,
)

from app.services.rag.vector_store import (
    VectorStore,
    SearchResult,
    IndexStats,
    SparseVectorizer,
)

from app.services.rag.retriever import (
    Retriever,
    RetrievalResult,
    StudentContext,
    QueryProcessor,
)

from app.services.rag.prompts import (
    ResponseMode,
    DifficultyLevel,
    PromptContext,
    PromptBuilder,
)

from app.services.rag.rag_engine import (
    RAGEngine,
    RAGResponse,
    GenerationSettings,
)

from app.services.rag.query_processor import (
    QueryProcessor,
    ProcessedQuery,
    QueryIntent,
    QueryComplexity,
    SubjectDetector,
    IntentDetector,
)

from app.services.rag.cache import (
    CacheBackend,
    RedisCacheAdapter,
    InMemoryCacheAdapter,
    ConversationCache,
    SessionStateCache,
    create_cache_adapter,
)

from app.services.rag.evaluation import (
    MetricsCollector,
    QueryMetrics,
    RetrievalEvaluation,
    ResponseQualityEvaluator,
    EvaluationTestSuite,
    get_metrics_collector,
    record_rag_query,
)


# ============================================================================
# Factory Functions
# ============================================================================
def create_embedding_service(settings, redis_cache=None) -> EmbeddingService:
    """
    Create an embedding service with optional Redis cache.
    
    Args:
        settings: Application settings with GEMINI_API_KEY
        redis_cache: Optional Redis cache backend
    
    Returns:
        Configured EmbeddingService instance
    """
    return EmbeddingService(
        api_key=settings.GEMINI_API_KEY,
        config=get_rag_config().embedding,
        redis_cache=redis_cache,
    )


def create_vector_store(
    settings,
    embedding_service: EmbeddingService = None
) -> VectorStore:
    """
    Create a vector store with optional embedding service.
    
    Args:
        settings: Application settings with Qdrant config
        embedding_service: Optional pre-configured embedding service
    
    Returns:
        Configured VectorStore instance
    """
    if embedding_service is None:
        embedding_service = create_embedding_service(settings)
    
    return VectorStore(
        settings=settings,
        embedding_service=embedding_service,
    )


def create_rag_engine(
    settings,
    config: RAGConfig = None,
    vector_store: VectorStore = None,
    embedding_service: EmbeddingService = None,
) -> RAGEngine:
    """
    Create a fully configured RAG engine.
    
    Args:
        settings: Application settings
        config: Optional RAG configuration override
        vector_store: Optional pre-configured vector store
        embedding_service: Optional pre-configured embedding service
    
    Returns:
        Configured RAGEngine instance (call initialize() before use)
    
    Example:
        engine = create_rag_engine(settings)
        await engine.initialize()
        
        response = await engine.query(
            question="What is the quadratic formula?",
            student_context={"grade": "Form 4", "subject": "Mathematics"},
            mode="explain"
        )
    """
    if embedding_service is None:
        embedding_service = create_embedding_service(settings)
    
    if vector_store is None:
        vector_store = create_vector_store(settings, embedding_service)
    
    return RAGEngine(
        settings=settings,
        config=config,
        vector_store=vector_store,
        embedding_service=embedding_service,
    )


async def create_and_initialize_rag_engine(settings, **kwargs) -> RAGEngine:
    """
    Create and initialize a RAG engine in one step.
    
    Convenience function for quick setup.
    """
    engine = create_rag_engine(settings, **kwargs)
    await engine.initialize()
    return engine


# ============================================================================
# Public API
# ============================================================================
__all__ = [
    # Main classes
    "RAGEngine",
    "RAGResponse",
    "VectorStore",
    "Retriever",
    "EmbeddingService",
    "DocumentProcessor",
    
    # Data classes
    "DocumentChunk",
    "ZIMSECDocument",
    "SearchResult",
    "RetrievalResult",
    "StudentContext",
    "PromptContext",
    "IndexStats",
    "ProcessedQuery",
    "QueryMetrics",
    
    # Enums
    "ResponseMode",
    "DifficultyLevel",
    "ChunkingStrategy",
    "RetrievalStrategy",
    "RerankingStrategy",
    "QueryIntent",
    "QueryComplexity",
    
    # Configuration
    "RAGConfig",
    "get_rag_config",
    "PROFILE_EXAM_PREP",
    "PROFILE_QUICK_HELP", 
    "PROFILE_DEEP_EXPLANATION",
    
    # Query Processing
    "QueryProcessor",
    "SubjectDetector",
    "IntentDetector",
    
    # Caching
    "CacheBackend",
    "RedisCacheAdapter",
    "InMemoryCacheAdapter",
    "ConversationCache",
    "SessionStateCache",
    "create_cache_adapter",
    
    # Evaluation & Metrics
    "MetricsCollector",
    "RetrievalEvaluation",
    "ResponseQualityEvaluator",
    "EvaluationTestSuite",
    "get_metrics_collector",
    "record_rag_query",
    
    # Builders
    "PromptBuilder",
    "GenerationSettings",
    
    # Factory functions
    "create_embedding_service",
    "create_vector_store",
    "create_rag_engine",
    "create_and_initialize_rag_engine",
]


# Version
__version__ = "2.0.0"