# ============================================================================
# RAG System Configuration
# ============================================================================
"""
Centralized configuration for the RAG pipeline with environment-based settings,
validation, and sensible defaults optimized for ZIMSEC educational content.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from functools import lru_cache
import os


class ChunkingStrategy(str, Enum):
    """Available document chunking strategies"""
    FIXED_SIZE = "fixed_size"           # Simple token-based chunks
    SEMANTIC = "semantic"               # Sentence-boundary aware
    HIERARCHICAL = "hierarchical"       # Parent-child chunk relationships
    SLIDING_WINDOW = "sliding_window"   # Overlapping windows with context
    QUESTION_AWARE = "question_aware"   # Optimized for Q&A extraction


class RetrievalStrategy(str, Enum):
    """Retrieval strategies for document search"""
    DENSE_ONLY = "dense_only"           # Pure vector similarity
    SPARSE_ONLY = "sparse_only"         # BM25/keyword-based
    HYBRID = "hybrid"                   # Combined dense + sparse
    MULTI_QUERY = "multi_query"         # Query expansion + fusion
    HYDE = "hyde"                       # Hypothetical Document Embeddings


class RerankingStrategy(str, Enum):
    """Reranking strategies for result refinement"""
    NONE = "none"
    CROSS_ENCODER = "cross_encoder"     # Neural reranking
    LLM_RERANK = "llm_rerank"           # LLM-based relevance scoring
    RECIPROCAL_RANK = "reciprocal_rank" # RRF fusion


@dataclass(frozen=True)
class EmbeddingConfig:
    """Immutable embedding configuration"""
    model: str = "text-embedding-004"
    dimension: int = 768
    batch_size: int = 64
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # Task-specific embedding types for Gemini
    document_task: str = "retrieval_document"
    query_task: str = "retrieval_query"
    
    # Caching configuration
    cache_enabled: bool = True
    cache_ttl_seconds: int = 86400 * 7  # 7 days
    cache_prefix: str = "emb:v1"


@dataclass(frozen=True)
class ChunkingConfig:
    """Document chunking configuration"""
    strategy: ChunkingStrategy = ChunkingStrategy.HIERARCHICAL
    
    # Token-based settings
    chunk_size: int = 512
    chunk_overlap: int = 64
    min_chunk_size: int = 100
    max_chunk_size: int = 1500
    
    # Hierarchical chunking
    parent_chunk_size: int = 1500
    child_chunk_size: int = 384
    
    # Sliding window
    window_size: int = 3  # sentences
    stride: int = 2
    
    # Content separators (priority order)
    separators: tuple = (
        "\n\n\n",   # Section breaks
        "\n\n",     # Paragraph breaks
        "\n",       # Line breaks
        ". ",       # Sentence ends
        "? ",       # Questions
        "! ",       # Exclamations
        "; ",       # Semicolons
        ", ",       # Clauses
        " ",        # Words
    )


@dataclass(frozen=True)
class RetrievalConfig:
    """Retrieval and search configuration"""
    strategy: RetrievalStrategy = RetrievalStrategy.HYBRID
    
    # Result limits
    top_k: int = 10
    final_k: int = 5  # After reranking
    min_score_threshold: float = 0.35
    
    # Hybrid search weights
    dense_weight: float = 0.7
    sparse_weight: float = 0.3
    
    # Multi-query settings
    num_query_variations: int = 3
    include_original_query: bool = True
    
    # HyDE settings
    hyde_enabled: bool = False
    hyde_num_generations: int = 1
    
    # Reranking
    reranking_strategy: RerankingStrategy = RerankingStrategy.RECIPROCAL_RANK
    rerank_top_k: int = 20


@dataclass(frozen=True)
class GenerationConfig:
    """LLM generation configuration"""
    model: str = "gemini-2.0-flash-exp"
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    max_output_tokens: int = 1024
    
    # Response constraints
    max_response_words: int = 300  # For WhatsApp
    include_citations: bool = False
    
    # Socratic mode defaults
    socratic_enabled: bool = True
    max_hints: int = 3
    
    # Safety settings
    block_none_safety: bool = True


@dataclass(frozen=True)
class CollectionConfig:
    """Qdrant collection configuration"""
    # Collection names mapping
    syllabi: str = "zimsec_syllabi"
    past_papers: str = "zimsec_past_papers"
    marking_schemes: str = "zimsec_marking_schemes"
    teacher_notes: str = "teacher_notes"
    textbooks: str = "textbooks"
    
    # HNSW index parameters
    hnsw_m: int = 16
    hnsw_ef_construct: int = 128
    hnsw_ef_search: int = 64
    
    # Optimizer settings
    indexing_threshold: int = 20000
    memmap_threshold: int = 50000
    
    @property
    def all_collections(self) -> Dict[str, str]:
        return {
            "syllabi": self.syllabi,
            "past_papers": self.past_papers,
            "marking_schemes": self.marking_schemes,
            "teacher_notes": self.teacher_notes,
            "textbooks": self.textbooks,
        }


@dataclass(frozen=True)
class DocumentTypeWeights:
    """Relevance weights by document type for scoring"""
    syllabus: float = 1.3
    past_paper: float = 1.5      # Highest priority for exam prep
    marking_scheme: float = 1.4
    textbook: float = 1.0
    teacher_notes: float = 0.9
    
    def get_weight(self, doc_type: str) -> float:
        return getattr(self, doc_type.lower().replace(" ", "_"), 1.0)


@dataclass
class RAGConfig:
    """
    Master RAG configuration combining all sub-configurations.
    Designed for easy environment-based overrides.
    """
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    collections: CollectionConfig = field(default_factory=CollectionConfig)
    doc_weights: DocumentTypeWeights = field(default_factory=DocumentTypeWeights)
    
    # Observability
    enable_telemetry: bool = True
    log_queries: bool = True
    log_retrievals: bool = True
    
    # Performance
    max_concurrent_embeddings: int = 10
    embedding_timeout: float = 30.0
    search_timeout: float = 10.0
    
    @classmethod
    def from_env(cls) -> "RAGConfig":
        """Create configuration from environment variables"""
        return cls(
            embedding=EmbeddingConfig(
                model=os.getenv("EMBEDDING_MODEL", "text-embedding-004"),
                dimension=int(os.getenv("EMBEDDING_DIMENSION", "768")),
                batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", "64")),
            ),
            retrieval=RetrievalConfig(
                strategy=RetrievalStrategy(
                    os.getenv("RETRIEVAL_STRATEGY", "hybrid")
                ),
                top_k=int(os.getenv("RETRIEVAL_TOP_K", "10")),
            ),
            generation=GenerationConfig(
                model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp"),
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            ),
        )


@lru_cache(maxsize=1)
def get_rag_config() -> RAGConfig:
    """Get singleton RAG configuration instance"""
    return RAGConfig.from_env()


# Pre-configured profiles for different use cases
PROFILE_EXAM_PREP = RAGConfig(
    retrieval=RetrievalConfig(
        strategy=RetrievalStrategy.HYBRID,
        top_k=15,
        final_k=7,
        min_score_threshold=0.4,
    ),
    generation=GenerationConfig(
        temperature=0.5,  # More focused
        max_output_tokens=1500,
    ),
)

PROFILE_QUICK_HELP = RAGConfig(
    retrieval=RetrievalConfig(
        strategy=RetrievalStrategy.DENSE_ONLY,
        top_k=5,
        final_k=3,
    ),
    generation=GenerationConfig(
        temperature=0.7,
        max_output_tokens=512,
        max_response_words=150,
    ),
)

PROFILE_DEEP_EXPLANATION = RAGConfig(
    retrieval=RetrievalConfig(
        strategy=RetrievalStrategy.MULTI_QUERY,
        top_k=20,
        final_k=10,
        num_query_variations=4,
    ),
    generation=GenerationConfig(
        temperature=0.6,
        max_output_tokens=2048,
        max_response_words=500,
    ),
)