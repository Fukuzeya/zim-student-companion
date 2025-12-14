# ============================================================================
# Advanced Vector Store with Production-Ready Features
# Compatible with qdrant-client 1.16.1
# Backward compatible with existing Settings objects
# ============================================================================
from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import uuid4

import google.generativeai as genai
from qdrant_client import AsyncQdrantClient, QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter, FieldCondition,
    MatchValue, TextIndexParams, TokenizerType, PayloadSchemaType,
    OptimizersConfigDiff, HnswConfigDiff
)
from qdrant_client.http import models

logger = logging.getLogger(__name__)

# ============================================================================
# Custom Exceptions
# ============================================================================
class VectorStoreError(Exception):
    """Base exception for vector store operations"""
    pass

class VectorStoreConnectionError(VectorStoreError):
    """Connection-related errors"""
    pass

class EmbeddingError(VectorStoreError):
    """Embedding generation errors"""
    pass

class CollectionError(VectorStoreError):
    """Collection operation errors"""
    pass

class SearchError(VectorStoreError):
    """Search operation errors"""
    pass

# ============================================================================
# Caching Infrastructure
# ============================================================================
@dataclass
class CacheEntry:
    """Cache entry with TTL"""
    value: Any
    created_at: datetime
    ttl_seconds: int
    
    @property
    def is_expired(self) -> bool:
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl_seconds)

class LRUCache:
    """Thread-safe LRU cache with TTL support"""
    def __init__(self, max_size: int = 10000, ttl_seconds: int = 3600):
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0
    
    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.is_expired:
                del self._cache[key]
                self._misses += 1
                return None
            self._hits += 1
            return entry.value
    
    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            if len(self._cache) >= self._max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            self._cache[key] = CacheEntry(value, datetime.now(), self._ttl)
    
    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()
    
    @property
    def stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0
        }

# ============================================================================
# Rate Limiter
# ============================================================================
class TokenBucketRateLimiter:
    """Token bucket rate limiter for API calls"""
    def __init__(self, tokens_per_minute: int = 1500):
        self._capacity = tokens_per_minute
        self._tokens = float(tokens_per_minute)
        self._last_update = time.monotonic()
        self._lock = asyncio.Lock()
        self._refill_rate = tokens_per_minute / 60.0
    
    async def acquire(self, tokens: int = 1) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_update
            self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_rate)
            self._last_update = now
            
            if self._tokens < tokens:
                wait_time = (tokens - self._tokens) / self._refill_rate
                await asyncio.sleep(wait_time)
                self._tokens = 0
            else:
                self._tokens -= tokens

# ============================================================================
# Circuit Breaker Pattern
# ============================================================================
class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """Circuit breaker for fault tolerance"""
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        async with self._lock:
            if self._state == CircuitState.OPEN:
                if self._last_failure_time and \
                   time.monotonic() - self._last_failure_time >= self._recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                else:
                    raise VectorStoreConnectionError("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            async with self._lock:
                if self._state == CircuitState.HALF_OPEN:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
            return result
        except Exception as e:
            async with self._lock:
                self._failure_count += 1
                self._last_failure_time = time.monotonic()
                if self._failure_count >= self._failure_threshold:
                    self._state = CircuitState.OPEN
                    logger.warning(f"Circuit breaker opened after {self._failure_count} failures")
            raise

# ============================================================================
# Retry Decorator
# ============================================================================
def async_retry(max_retries: int = 3, base_delay: float = 1.0, 
                exponential_base: float = 2.0):
    """Async retry decorator with exponential backoff"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = base_delay * (exponential_base ** attempt)
                        logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s")
                        await asyncio.sleep(delay)
            raise last_exception
        return wrapper
    return decorator

# ============================================================================
# Helper function to safely get settings attributes
# ============================================================================
def get_setting(settings, name: str, default: Any = None) -> Any:
    """Safely get a setting attribute with a default value"""
    return getattr(settings, name, default)

# ============================================================================
# Main Vector Store Implementation (Keeping original class name for compatibility)
# ============================================================================
class VectorStore:
    """
    Advanced Qdrant vector store for ZIMSEC documents with robust search.
    Backward compatible with existing Settings objects.
    """
    
    def __init__(self, settings):
        """
        Initialize VectorStore with settings object.
        
        Args:
            settings: Settings object with at minimum:
                - QDRANT_HOST
                - QDRANT_PORT
                - QDRANT_COLLECTION
                - GEMINI_API_KEY
                - GEMINI_EMBEDDING_MODEL
        """
        self.settings = settings
        
        # Extract settings with safe defaults
        self._qdrant_host = get_setting(settings, 'QDRANT_HOST', 'localhost')
        self._qdrant_port = get_setting(settings, 'QDRANT_PORT', 6333)
        self._qdrant_grpc_port = get_setting(settings, 'QDRANT_GRPC_PORT', 6334)
        self._qdrant_api_key = get_setting(settings, 'QDRANT_API_KEY', None)
        self._use_grpc = get_setting(settings, 'QDRANT_USE_GRPC', False)
        self._embedding_model = get_setting(settings, 'GEMINI_EMBEDDING_MODEL', 'embedding-001')
        self._embedding_dimension = get_setting(settings, 'EMBEDDING_DIMENSION', 768)
        
        # Performance settings with defaults
        self._batch_size = get_setting(settings, 'BATCH_SIZE', 100)
        self._max_retries = get_setting(settings, 'MAX_RETRIES', 3)
        self._enable_cache = get_setting(settings, 'ENABLE_EMBEDDING_CACHE', True)
        self._cache_ttl = get_setting(settings, 'CACHE_TTL_SECONDS', 3600)
        self._cache_max_size = get_setting(settings, 'CACHE_MAX_SIZE', 10000)
        
        # Initialize clients (both sync and async for compatibility)
        self.client = QdrantClient(
            host=self._qdrant_host,
            port=self._qdrant_port,
            api_key=self._qdrant_api_key,
            timeout=get_setting(settings, 'QDRANT_TIMEOUT', 30.0)
        )
        
        self._async_client: Optional[AsyncQdrantClient] = None
        self.collection_name = get_setting(settings, 'QDRANT_COLLECTION', 'zimsec_documents')
        
        # Initialize Gemini for embeddings
        genai.configure(api_key=settings.GEMINI_API_KEY)
        
        # Collection configs for different document types
        self.collections = {
            "zimsec_syllabi": "zimsec_syllabi",
            "zimsec_past_papers": "zimsec_past_papers",
            "zimsec_marking_schemes": "zimsec_marking_schemes",
            "teacher_notes": "teacher_notes",
            "textbooks": "textbooks"
        }
        
        # Initialize caching and rate limiting
        self._embedding_cache = LRUCache(
            max_size=self._cache_max_size,
            ttl_seconds=self._cache_ttl
        ) if self._enable_cache else None
        
        self._rate_limiter = TokenBucketRateLimiter(
            tokens_per_minute=get_setting(settings, 'EMBEDDINGS_PER_MINUTE', 1500)
        )
        self._circuit_breaker = CircuitBreaker()
        
        # Stop words for keyword extraction
        self._stop_words = frozenset({
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can',
            'had', 'her', 'was', 'one', 'our', 'out', 'has', 'have', 'been',
            'would', 'could', 'should', 'their', 'there', 'will', 'with',
            'this', 'that', 'from', 'they', 'which', 'what', 'when', 'where',
            'about', 'into', 'more', 'other', 'some', 'such', 'than', 'then',
            'these', 'those', 'very', 'just', 'also', 'only', 'over', 'after'
        })
    
    # ==================== Async Client Management ====================
    
    async def _get_async_client(self) -> AsyncQdrantClient:
        """Get or create async client"""
        if self._async_client is None:
            self._async_client = AsyncQdrantClient(
                host=self._qdrant_host,
                port=self._qdrant_grpc_port if self._use_grpc else self._qdrant_port,
                grpc_port=self._qdrant_grpc_port,
                prefer_grpc=self._use_grpc,
                api_key=self._qdrant_api_key,
                timeout=get_setting(self.settings, 'QDRANT_TIMEOUT', 30.0)
            )
        return self._async_client
    
    async def close(self) -> None:
        """Close async client connection"""
        if self._async_client:
            await self._async_client.close()
            self._async_client = None
    
    # ==================== Collection Management ====================
    
    async def initialize_collections(self):
        """Create all required collections with proper indexing"""
        client = await self._get_async_client()
        
        for collection_key, collection_name in self.collections.items():
            try:
                exists = await client.collection_exists(collection_name)
                
                if not exists:
                    await client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=self._embedding_dimension,
                            distance=Distance.COSINE
                        ),
                        optimizers_config=OptimizersConfigDiff(
                            indexing_threshold=20000,
                            memmap_threshold=50000
                        ),
                        hnsw_config=HnswConfigDiff(
                            m=16,
                            ef_construct=100
                        )
                    )
                    logger.info(f"Created collection: {collection_name}")
                    
                    # Create payload indexes
                    await self._create_payload_indexes(client, collection_name)
                else:
                    logger.info(f"Collection already exists: {collection_name}")
                    
            except Exception as e:
                logger.error(f"Error initializing collection {collection_name}: {e}")
    
    async def _create_payload_indexes(self, client: AsyncQdrantClient, collection_name: str):
        """Create payload indexes for filtering"""
        keyword_fields = ["subject", "education_level", "grade", "document_type",
                         "year", "paper_number", "topic"]
        
        for field in keyword_fields:
            try:
                await client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field,
                    field_schema=PayloadSchemaType.KEYWORD
                )
                # Lowercase version for case-insensitive search
                await client.create_payload_index(
                    collection_name=collection_name,
                    field_name=f"{field}_lower",
                    field_schema=PayloadSchemaType.KEYWORD
                )
            except Exception as e:
                logger.debug(f"Index may exist for {field}: {e}")
        
        # Full-text index for content
        try:
            await client.create_payload_index(
                collection_name=collection_name,
                field_name="content",
                field_schema=TextIndexParams(
                    type="text",
                    tokenizer=TokenizerType.WORD,
                    min_token_len=2,
                    max_token_len=30,
                    lowercase=True
                )
            )
        except Exception as e:
            logger.debug(f"Text index note: {e}")
    
    # ==================== Text Processing ====================
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for case-insensitive matching"""
        if not text:
            return ""
        return text.lower().strip()
    
    def _normalize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Add normalized versions of key fields for case-insensitive search"""
        normalized = metadata.copy()
        
        fields_to_normalize = ["subject", "grade", "education_level", 
                              "document_type", "topic", "year"]
        
        for field in fields_to_normalize:
            if field in metadata and metadata[field]:
                normalized[f"{field}_lower"] = self._normalize_text(str(metadata[field]))
        
        # Extract keywords
        if "content" in metadata:
            normalized["keywords"] = self._extract_keywords(metadata["content"])
        
        return normalized
    
    def _extract_keywords(self, text: str, max_keywords: int = 50) -> List[str]:
        """Extract searchable keywords from text"""
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        keywords = [w for w in words if w not in self._stop_words]
        
        seen = set()
        unique = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique.append(kw)
        
        return unique[:max_keywords]
    
    # ==================== Embedding Generation ====================
    
    def _get_cache_key(self, text: str, task_type: str) -> str:
        """Generate cache key for embeddings"""
        content = f"{task_type}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    async def _generate_embedding_uncached(self, text: str, 
                                           task_type: str = "retrieval_document") -> List[float]:
        """Generate embedding without caching"""
        await self._rate_limiter.acquire()
        
        try:
            result = genai.embed_content(
                model=f"models/{self._embedding_model}",
                content=text,
                task_type=task_type
            )
            return result['embedding']
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise EmbeddingError(f"Failed to generate embedding: {e}") from e
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for document with caching"""
        task_type = "retrieval_document"
        
        if self._embedding_cache:
            cache_key = self._get_cache_key(text, task_type)
            cached = await self._embedding_cache.get(cache_key)
            if cached is not None:
                return cached
        
        embedding = await self._circuit_breaker.call(
            self._generate_embedding_uncached, text, task_type
        )
        
        if self._embedding_cache:
            await self._embedding_cache.set(cache_key, embedding)
        
        return embedding
    
    async def generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for search query"""
        task_type = "retrieval_query"
        
        if self._embedding_cache:
            cache_key = self._get_cache_key(query, task_type)
            cached = await self._embedding_cache.get(cache_key)
            if cached is not None:
                return cached
        
        embedding = await self._circuit_breaker.call(
            self._generate_embedding_uncached, query, task_type
        )
        
        if self._embedding_cache:
            await self._embedding_cache.set(cache_key, embedding)
        
        return embedding
    
    # ==================== Document Indexing ====================
    
    async def add_chunks(
        self,
        chunks: List,  # List of DocumentChunk
        collection_key: str = "zimsec_past_papers"
    ) -> int:
        """Add document chunks to vector store with normalized metadata"""
        client = await self._get_async_client()
        collection_name = self.collections.get(collection_key, self.collection_name)
        
        total_added = 0
        
        # Process in batches
        for i in range(0, len(chunks), self._batch_size):
            batch = chunks[i:i + self._batch_size]
            points = []
            
            for chunk in batch:
                try:
                    embedding = await self.generate_embedding(chunk.content)
                    
                    metadata = {
                        "content": chunk.content,
                        "chunk_id": chunk.chunk_id,
                        "indexed_at": datetime.now().isoformat(),
                        **chunk.metadata
                    }
                    normalized_metadata = self._normalize_metadata(metadata)
                    
                    point = PointStruct(
                        id=str(uuid4()),
                        vector=embedding,
                        payload=normalized_metadata
                    )
                    points.append(point)
                    
                except Exception as e:
                    logger.error(f"Error processing chunk: {e}")
                    continue
            
            if points:
                try:
                    await client.upsert(
                        collection_name=collection_name,
                        points=points,
                        wait=True
                    )
                    total_added += len(points)
                    logger.info(f"Added batch: {len(points)} chunks to {collection_name}")
                except Exception as e:
                    logger.error(f"Failed to upsert batch: {e}")
        
        logger.info(f"✅ Total added: {total_added} chunks to {collection_name}")
        return total_added
    
    # ==================== Search Operations ====================
    
    def _build_filter(self, filters: Dict[str, Any]) -> Optional[Filter]:
        """Build Qdrant filter from dict with case-insensitive matching"""
        if not filters:
            return None
        
        conditions = []
        for key, value in filters.items():
            if value is None:
                continue
            
            # Use lowercase version for case-insensitive matching
            field_key = f"{key}_lower" if key in ["subject", "grade", "education_level",
                                                   "document_type", "topic"] else key
            normalized_value = self._normalize_text(str(value)) if isinstance(value, str) else value
            
            conditions.append(
                FieldCondition(key=field_key, match=MatchValue(value=normalized_value))
            )
        
        return Filter(must=conditions) if conditions else None
    
    async def search(
        self,
        query: str,
        collection_keys: List[str] = None,
        filters: Dict[str, Any] = None,
        limit: int = 5,
        score_threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Vector similarity search with case-insensitive filtering.
        """
        client = await self._get_async_client()
        query_embedding = await self.generate_query_embedding(query)
        
        all_results = []
        collections = collection_keys or list(self.collections.values())
        
        query_filter = self._build_filter(filters)
        
        for coll_key in collections:
            collection_name = self.collections.get(coll_key, coll_key)
            
            try:
                # Check if collection exists and has points
                try:
                    collection_info = await client.get_collection(collection_name)
                    if collection_info.points_count == 0:
                        continue
                except Exception:
                    continue
                
                logger.debug(f"Searching {collection_name} ({collection_info.points_count} points)")
                
                # Use query_points (new API in qdrant-client 1.16.x)
                results = await client.query_points(
                    collection_name=collection_name,
                    query=query_embedding,
                    query_filter=query_filter,
                    limit=limit,
                    with_payload=True,
                    score_threshold=score_threshold
                )
                
                points = results.points if hasattr(results, 'points') else results
                
                # Fallback to unfiltered if no results with filters
                if not points and query_filter:
                    logger.debug(f"No filtered results, trying unfiltered on {collection_name}")
                    results = await client.query_points(
                        collection_name=collection_name,
                        query=query_embedding,
                        limit=limit,
                        with_payload=True,
                        score_threshold=score_threshold
                    )
                    points = results.points if hasattr(results, 'points') else results
                
                for result in points:
                    payload = result.payload if hasattr(result, 'payload') else {}
                    score = result.score if hasattr(result, 'score') else 0.0
                    
                    all_results.append({
                        "content": payload.get("content", ""),
                        "metadata": {
                            k: v for k, v in payload.items()
                            if k not in ["content", "keywords", "indexed_at"] 
                            and not k.endswith("_lower")
                        },
                        "score": score,
                        "collection": collection_name
                    })
                    
            except Exception as e:
                logger.warning(f"Error searching {collection_name}: {e}")
                continue
        
        # Sort by score
        all_results.sort(key=lambda x: x["score"], reverse=True)
        
        if all_results:
            logger.info(f"✅ Found {len(all_results)} results, top score: {all_results[0]['score']:.3f}")
        else:
            logger.warning(f"⚠️ No results found for query: {query[:50]}...")
        
        return all_results[:limit]
    
    async def hybrid_search(
        self,
        query: str,
        filters: Dict[str, Any] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Advanced hybrid search combining:
        1. Vector similarity search
        2. Keyword boosting
        3. Phrase matching
        """
        # Get more candidates for re-ranking
        vector_results = await self.search(
            query=query,
            filters=filters,
            limit=limit * 3,
            score_threshold=0.2
        )
        
        # Fallback to full-text if no vector results
        if not vector_results:
            logger.info("Vector search empty, trying full-text search")
            vector_results = await self._fulltext_search(query, limit)
        
        if not vector_results:
            logger.warning("No results from any search method")
            return []
        
        # Keyword boosting
        query_keywords = set(self._extract_keywords(query))
        query_lower = query.lower()
        
        for result in vector_results:
            content_lower = result["content"].lower()
            
            # Keyword match bonus
            keyword_matches = sum(1 for kw in query_keywords if kw in content_lower)
            keyword_bonus = keyword_matches * 0.03
            
            # Exact phrase bonus
            phrase_bonus = 0.1 if query_lower in content_lower else 0
            
            # Metadata match bonus
            metadata = result.get("metadata", {})
            metadata_bonus = 0
            for key, value in metadata.items():
                if value and str(value).lower() in query_lower:
                    metadata_bonus += 0.05
            
            # Combined score
            result["combined_score"] = (
                result["score"] + keyword_bonus + phrase_bonus + metadata_bonus
            )
        
        # Re-sort by combined score
        vector_results.sort(key=lambda x: x.get("combined_score", x["score"]), reverse=True)
        
        return vector_results[:limit]
    
    async def _fulltext_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fallback full-text search using scroll with keyword matching"""
        client = await self._get_async_client()
        all_results = []
        query_keywords = set(self._extract_keywords(query))
        
        if not query_keywords:
            return []
        
        for collection_name in self.collections.values():
            try:
                collection_info = await client.get_collection(collection_name)
                if collection_info.points_count == 0:
                    continue
                
                scroll_result = await client.scroll(
                    collection_name=collection_name,
                    limit=100,
                    with_payload=True,
                    with_vectors=False
                )
                
                points, _ = scroll_result
                
                for point in points:
                    payload = point.payload
                    content = payload.get("content", "").lower()
                    
                    matches = sum(1 for kw in query_keywords if kw in content)
                    
                    if matches >= 2:
                        all_results.append({
                            "content": payload.get("content", ""),
                            "metadata": {
                                k: v for k, v in payload.items()
                                if k not in ["content", "keywords", "indexed_at"]
                                and not k.endswith("_lower")
                            },
                            "score": matches / len(query_keywords),
                            "collection": collection_name
                        })
                        
            except Exception as e:
                logger.warning(f"Full-text search error on {collection_name}: {e}")
                continue
        
        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results[:limit]
    
    # ==================== Diagnostic Methods ====================
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics for all collections"""
        client = await self._get_async_client()
        stats = {}
        
        for key, collection_name in self.collections.items():
            try:
                info = await client.get_collection(collection_name)
                stats[collection_name] = {
                    "points_count": info.points_count,
                    "vectors_count": info.vectors_count,
                    "status": str(info.status),
                    "indexed_vectors_count": getattr(info, 'indexed_vectors_count', 'N/A')
                }
            except Exception as e:
                stats[collection_name] = {"error": str(e)}
        
        return stats
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        result = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {}
        }
        
        # Check Qdrant
        try:
            client = await self._get_async_client()
            collections = await client.get_collections()
            result["components"]["qdrant"] = {
                "status": "healthy",
                "collections_count": len(collections.collections)
            }
        except Exception as e:
            result["status"] = "unhealthy"
            result["components"]["qdrant"] = {"status": "unhealthy", "error": str(e)}
        
        # Check embeddings
        try:
            await self._generate_embedding_uncached("health check test")
            result["components"]["embeddings"] = {"status": "healthy"}
        except Exception as e:
            result["status"] = "degraded"
            result["components"]["embeddings"] = {"status": "unhealthy", "error": str(e)}
        
        # Cache stats
        if self._embedding_cache:
            result["components"]["cache"] = self._embedding_cache.stats
        
        return result
    
    async def browse_collection(
        self,
        collection_name: str,
        limit: int = 10,
        offset: Optional[str] = None
    ) -> Dict[str, Any]:
        """Browse documents in a collection"""
        client = await self._get_async_client()
        
        try:
            scroll_result = await client.scroll(
                collection_name=collection_name,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            
            points, next_offset = scroll_result
            
            documents = []
            for point in points:
                payload = point.payload or {}
                content = payload.get("content", "")
                
                doc = {
                    "id": str(point.id),
                    "content_preview": content[:300] + "..." if len(content) > 300 else content,
                    "content_length": len(content),
                    "metadata": {
                        k: v for k, v in payload.items()
                        if not k.endswith("_lower") and k not in ["content", "keywords"]
                    }
                }
                documents.append(doc)
            
            return {
                "collection": collection_name,
                "documents": documents,
                "count": len(documents),
                "next_offset": next_offset
            }
            
        except Exception as e:
            logger.error(f"Error browsing collection: {e}")
            return {"error": str(e)}
    
    async def get_unique_values(
        self,
        collection_name: str,
        field: str,
        limit: int = 100
    ) -> List[str]:
        """Get unique values for a field in a collection"""
        client = await self._get_async_client()
        
        try:
            unique_values = set()
            offset = None
            
            while len(unique_values) < limit:
                scroll_result = await client.scroll(
                    collection_name=collection_name,
                    limit=100,
                    offset=offset,
                    with_payload=[field]
                )
                
                points, next_offset = scroll_result
                
                if not points:
                    break
                
                for point in points:
                    value = point.payload.get(field) if point.payload else None
                    if value:
                        unique_values.add(str(value))
                
                offset = next_offset
                if offset is None:
                    break
            
            return sorted(list(unique_values))[:limit]
            
        except Exception as e:
            logger.error(f"Error getting unique values: {e}")
            return []
    
    async def delete_all_points(self, collection_name: str) -> bool:
        """Delete all points in a collection"""
        client = await self._get_async_client()
        
        try:
            await client.delete(
                collection_name=collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(must=[])
                )
            )
            logger.info(f"Deleted all points from {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting points: {e}")
            return False
    
    async def test_search(self, query: str, collection_name: str = None) -> Dict[str, Any]:
        """Test search with detailed diagnostics"""
        result = {
            "query": query,
            "query_keywords": self._extract_keywords(query),
            "collections_searched": [],
            "results": []
        }
        
        try:
            query_embedding = await self.generate_query_embedding(query)
            result["embedding_generated"] = True
            result["embedding_dimension"] = len(query_embedding)
        except Exception as e:
            result["embedding_error"] = str(e)
            return result
        
        client = await self._get_async_client()
        collections = [collection_name] if collection_name else list(self.collections.values())
        
        for coll_name in collections:
            coll_result = {
                "name": coll_name,
                "points_count": 0,
                "search_results": 0,
                "top_score": None,
                "sample_results": []
            }
            
            try:
                info = await client.get_collection(coll_name)
                coll_result["points_count"] = info.points_count
                
                if info.points_count > 0:
                    search_results = await client.query_points(
                        collection_name=coll_name,
                        query=query_embedding,
                        limit=5,
                        with_payload=True
                    )
                    
                    points = search_results.points if hasattr(search_results, 'points') else search_results
                    coll_result["search_results"] = len(points)
                    
                    if points:
                        coll_result["top_score"] = points[0].score
                        for p in points[:3]:
                            coll_result["sample_results"].append({
                                "score": round(p.score, 4),
                                "subject": p.payload.get("subject") if p.payload else None,
                                "grade": p.payload.get("grade") if p.payload else None,
                                "content_preview": (p.payload.get("content", "")[:150] 
                                                   if p.payload else "")
                            })
                            
            except Exception as e:
                coll_result["error"] = str(e)
            
            result["collections_searched"].append(coll_result)
        
        return result