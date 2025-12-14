# ============================================================================
# RAG System Configuration
# ============================================================================
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

class ChunkingStrategy(str, Enum):
    """Document chunking strategies"""
    FIXED_SIZE = "fixed_size"
    SEMANTIC = "semantic"
    HIERARCHICAL = "hierarchical"
    QUESTION_BASED = "question_based"

class RetrievalStrategy(str, Enum):
    """Retrieval strategies"""
    VECTOR_ONLY = "vector_only"
    KEYWORD_ONLY = "keyword_only"
    HYBRID = "hybrid"
    MULTI_QUERY = "multi_query"

@dataclass
class ChunkingConfig:
    """Configuration for document chunking"""
    strategy: ChunkingStrategy = ChunkingStrategy.HIERARCHICAL
    chunk_size: int = 500  # tokens
    chunk_overlap: int = 50
    min_chunk_size: int = 100
    max_chunk_size: int = 1500
    
    # Hierarchical chunking settings
    parent_chunk_size: int = 1500
    child_chunk_size: int = 300
    
    # Separators for splitting (in order of priority)
    separators: List[str] = field(default_factory=lambda: [
        "\n\n",  # Paragraph breaks
        "\n",    # Line breaks
        ". ",    # Sentences
        "? ",    # Questions
        "! ",    # Exclamations
        "; ",    # Semicolons
        ", ",    # Commas
        " "      # Words
    ])

@dataclass
class EmbeddingConfig:
    """Configuration for embeddings"""
    model: str = "text-embedding-004"
    dimension: int = 768
    batch_size: int = 100
    
    # Task types for Gemini embeddings
    document_task_type: str = "retrieval_document"
    query_task_type: str = "retrieval_query"
    
    # Caching
    cache_embeddings: bool = True
    cache_ttl: int = 86400 * 7  # 7 days

@dataclass
class RetrievalConfig:
    """Configuration for retrieval"""
    strategy: RetrievalStrategy = RetrievalStrategy.HYBRID
    top_k: int = 5
    similarity_threshold: float = 0.7
    
    # Hybrid search weights
    vector_weight: float = 0.6
    keyword_weight: float = 0.3
    metadata_weight: float = 0.1
    
    # Reranking
    enable_reranking: bool = True
    rerank_top_k: int = 10
    
    # Multi-query
    enable_multi_query: bool = False
    num_query_variations: int = 3

@dataclass 
class GenerationConfig:
    """Configuration for response generation"""
    model: str = "gemini-2.0-flash-exp"
    temperature: float = 0.7
    top_p: float = 0.9
    max_output_tokens: int = 1024
    
    # Response constraints
    max_response_length: int = 300  # words for WhatsApp
    include_sources: bool = False
    
    # Socratic settings
    socratic_mode: bool = True
    max_hints_per_question: int = 3

@dataclass
class RAGConfig:
    """Main RAG configuration"""
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    
    # Collection names
    collections: Dict[str, str] = field(default_factory=lambda: {
        "syllabi": "zimsec_syllabi",
        "past_papers": "zimsec_past_papers",
        "marking_schemes": "zimsec_marking_schemes",
        "teacher_notes": "teacher_notes",
        "textbooks": "textbooks"
    })
    
    # Document type weights (for retrieval priority)
    doc_type_weights: Dict[str, float] = field(default_factory=lambda: {
        "syllabus": 1.2,
        "past_paper": 1.5,
        "marking_scheme": 1.3,
        "textbook": 1.0,
        "teacher_notes": 0.9
    })

# Default configuration instance
default_rag_config = RAGConfig()