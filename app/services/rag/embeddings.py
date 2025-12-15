# ============================================================================
# Embedding Service
# ============================================================================
"""
High-performance embedding service with:
- Async batch processing with concurrency control
- Multi-level caching (in-memory LRU + Redis)
- Automatic retry with exponential backoff
- Rate limiting to respect API quotas
- Telemetry and observability
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, List, Optional, Protocol, Tuple, Union
import json

import google.generativeai as genai
import numpy as np

from app.services.rag.config import EmbeddingConfig, get_rag_config

logger = logging.getLogger(__name__)


# ============================================================================
# Protocols and Interfaces
# ============================================================================
class CacheBackend(Protocol):
    """Protocol for cache implementations"""
    async def get(self, key: str) -> Optional[str]: ...
    async def set(self, key: str, value: str, ttl: int) -> None: ...
    async def mget(self, keys: List[str]) -> List[Optional[str]]: ...
    async def mset(self, mapping: Dict[str, str], ttl: int) -> None: ...


class EmbeddingProvider(ABC):
    """Abstract base for embedding providers"""
    @abstractmethod
    async def embed_single(self, text: str, task_type: str) -> List[float]: ...
    
    @abstractmethod
    async def embed_batch(
        self, texts: List[str], task_type: str
    ) -> List[List[float]]: ...


# ============================================================================
# In-Memory LRU Cache with TTL
# ============================================================================
@dataclass
class CacheEntry:
    """Single cache entry with expiration"""
    value: Any
    expires_at: float
    
    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class LRUCache:
    """
    Thread-safe LRU cache with TTL support.
    Used as L1 cache before Redis.
    """
    __slots__ = ('_cache', '_max_size', '_ttl', '_lock', '_stats')
    
    def __init__(self, max_size: int = 10000, ttl_seconds: int = 3600):
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._lock = asyncio.Lock()
        self._stats = {"hits": 0, "misses": 0}
    
    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._stats["misses"] += 1
                return None
            if entry.is_expired:
                del self._cache[key]
                self._stats["misses"] += 1
                return None
            self._stats["hits"] += 1
            # Move to end (most recently used)
            self._cache[key] = self._cache.pop(key)
            return entry.value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        async with self._lock:
            # Evict oldest if at capacity
            while len(self._cache) >= self._max_size:
                oldest = next(iter(self._cache))
                del self._cache[oldest]
            
            expires = time.time() + (ttl or self._ttl)
            self._cache[key] = CacheEntry(value, expires)
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Batch get for multiple keys"""
        results = {}
        async with self._lock:
            for key in keys:
                entry = self._cache.get(key)
                if entry and not entry.is_expired:
                    results[key] = entry.value
                    self._stats["hits"] += 1
                else:
                    self._stats["misses"] += 1
        return results
    
    async def set_many(self, items: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """Batch set for multiple key-value pairs"""
        async with self._lock:
            expires = time.time() + (ttl or self._ttl)
            for key, value in items.items():
                if len(self._cache) >= self._max_size:
                    oldest = next(iter(self._cache))
                    del self._cache[oldest]
                self._cache[key] = CacheEntry(value, expires)
    
    @property
    def stats(self) -> Dict[str, Any]:
        total = self._stats["hits"] + self._stats["misses"]
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": self._stats["hits"] / total if total > 0 else 0.0,
        }
    
    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()


# ============================================================================
# Token Bucket Rate Limiter
# ============================================================================
class TokenBucketRateLimiter:
    """
    Async-safe token bucket rate limiter.
    Ensures we don't exceed API rate limits.
    """
    __slots__ = ('_capacity', '_tokens', '_refill_rate', '_last_update', '_lock')
    
    def __init__(self, requests_per_minute: int = 1500):
        self._capacity = float(requests_per_minute)
        self._tokens = float(requests_per_minute)
        self._refill_rate = requests_per_minute / 60.0  # tokens per second
        self._last_update = time.monotonic()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> float:
        """
        Acquire tokens, waiting if necessary.
        Returns the time waited.
        """
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_update
            self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_rate)
            self._last_update = now
            
            if self._tokens >= tokens:
                self._tokens -= tokens
                return 0.0
            
            # Calculate wait time
            needed = tokens - self._tokens
            wait_time = needed / self._refill_rate
            
            await asyncio.sleep(wait_time)
            self._tokens = 0
            self._last_update = time.monotonic()
            return wait_time


# ============================================================================
# Gemini Embedding Provider
# ============================================================================
class GeminiEmbeddingProvider(EmbeddingProvider):
    """
    Google Gemini embedding provider with built-in retry logic.
    """
    def __init__(self, api_key: str, config: EmbeddingConfig):
        self.config = config
        genai.configure(api_key=api_key)
        self._model_name = f"models/{config.model}"
    
    async def embed_single(self, text: str, task_type: str) -> List[float]:
        """Generate embedding for single text"""
        loop = asyncio.get_event_loop()
        
        def _embed():
            result = genai.embed_content(
                model=self._model_name,
                content=text,
                task_type=task_type
            )
            return result['embedding']
        
        return await loop.run_in_executor(None, _embed)
    
    async def embed_batch(
        self, texts: List[str], task_type: str
    ) -> List[List[float]]:
        """Generate embeddings for batch of texts"""
        # Gemini doesn't support true batch embedding, so we parallelize
        tasks = [self.embed_single(text, task_type) for text in texts]
        return await asyncio.gather(*tasks)


# ============================================================================
# Main Embedding Service
# ============================================================================
class EmbeddingService:
    """
    Production-ready embedding service with:
    - Two-level caching (L1: in-memory, L2: Redis)
    - Rate limiting
    - Batch processing with concurrency control
    - Automatic retries with exponential backoff
    - Comprehensive telemetry
    """
    
    def __init__(
        self,
        api_key: str,
        config: Optional[EmbeddingConfig] = None,
        redis_cache: Optional[CacheBackend] = None,
    ):
        self.config = config or get_rag_config().embedding
        self._provider = GeminiEmbeddingProvider(api_key, self.config)
        self._redis = redis_cache
        
        # L1 cache (in-memory)
        self._l1_cache = LRUCache(
            max_size=10000,
            ttl_seconds=self.config.cache_ttl_seconds
        ) if self.config.cache_enabled else None
        
        # Rate limiter
        self._rate_limiter = TokenBucketRateLimiter(requests_per_minute=1500)
        
        # Semaphore for concurrency control
        self._semaphore = asyncio.Semaphore(10)
        
        # Telemetry
        self._stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "api_calls": 0,
            "total_tokens": 0,
            "errors": 0,
        }
    
    # ==================== Cache Key Generation ====================
    
    def _cache_key(self, text: str, task_type: str) -> str:
        """Generate deterministic cache key"""
        content = f"{task_type}:{text}"
        hash_val = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"{self.config.cache_prefix}:{self.config.model}:{hash_val}"
    
    # ==================== Single Embedding ====================
    
    async def embed_text(
        self,
        text: str,
        task_type: Optional[str] = None
    ) -> List[float]:
        """
        Generate embedding for a single text with full caching.
        
        Args:
            text: Text to embed
            task_type: Gemini task type (defaults to document)
        
        Returns:
            Embedding vector as list of floats
        """
        task = task_type or self.config.document_task
        self._stats["total_requests"] += 1
        
        # Check L1 cache
        cache_key = self._cache_key(text, task)
        if self._l1_cache:
            cached = await self._l1_cache.get(cache_key)
            if cached is not None:
                self._stats["cache_hits"] += 1
                return cached
        
        # Check L2 cache (Redis)
        if self._redis:
            try:
                cached_str = await self._redis.get(cache_key)
                if cached_str:
                    embedding = json.loads(cached_str)
                    # Populate L1 cache
                    if self._l1_cache:
                        await self._l1_cache.set(cache_key, embedding)
                    self._stats["cache_hits"] += 1
                    return embedding
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")
        
        # Generate embedding with retry
        embedding = await self._generate_with_retry(text, task)
        
        # Cache the result
        await self._cache_embedding(cache_key, embedding)
        
        return embedding
    
    async def embed_query(self, query: str) -> List[float]:
        """Embed a search query (optimized for retrieval)"""
        return await self.embed_text(query, self.config.query_task)
    
    async def embed_document(self, document: str) -> List[float]:
        """Embed a document chunk (optimized for storage)"""
        return await self.embed_text(document, self.config.document_task)
    
    # ==================== Batch Embedding ====================
    
    async def embed_texts(
        self,
        texts: List[str],
        task_type: Optional[str] = None,
        show_progress: bool = False
    ) -> List[List[float]]:
        """
        Batch embed multiple texts with optimal caching and parallelism.
        
        Args:
            texts: List of texts to embed
            task_type: Gemini task type
            show_progress: Log progress updates
        
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        task = task_type or self.config.document_task
        n_texts = len(texts)
        
        # Check cache for all texts
        cache_keys = [self._cache_key(t, task) for t in texts]
        cached_results: Dict[int, List[float]] = {}
        uncached_indices: List[int] = []
        
        # L1 cache lookup
        if self._l1_cache:
            l1_results = await self._l1_cache.get_many(cache_keys)
            for i, key in enumerate(cache_keys):
                if key in l1_results:
                    cached_results[i] = l1_results[key]
                else:
                    uncached_indices.append(i)
        else:
            uncached_indices = list(range(n_texts))
        
        # L2 cache lookup for remaining
        if self._redis and uncached_indices:
            try:
                remaining_keys = [cache_keys[i] for i in uncached_indices]
                l2_results = await self._redis.mget(remaining_keys)
                
                still_uncached = []
                for idx, (i, result) in enumerate(zip(uncached_indices, l2_results)):
                    if result:
                        embedding = json.loads(result)
                        cached_results[i] = embedding
                        # Populate L1
                        if self._l1_cache:
                            await self._l1_cache.set(cache_keys[i], embedding)
                    else:
                        still_uncached.append(i)
                uncached_indices = still_uncached
            except Exception as e:
                logger.warning(f"Redis batch lookup failed: {e}")
        
        self._stats["cache_hits"] += len(cached_results)
        
        if show_progress:
            logger.info(f"Embedding: {len(cached_results)}/{n_texts} cached, "
                       f"{len(uncached_indices)} to generate")
        
        # Generate embeddings for uncached texts
        if uncached_indices:
            uncached_texts = [texts[i] for i in uncached_indices]
            new_embeddings = await self._batch_generate(uncached_texts, task, show_progress)
            
            # Cache new embeddings
            to_cache = {}
            for idx, embedding in zip(uncached_indices, new_embeddings):
                cached_results[idx] = embedding
                to_cache[cache_keys[idx]] = embedding
            
            await self._cache_embeddings_batch(to_cache)
        
        # Reconstruct ordered results
        return [cached_results[i] for i in range(n_texts)]
    
    async def _batch_generate(
        self,
        texts: List[str],
        task_type: str,
        show_progress: bool = False
    ) -> List[List[float]]:
        """Generate embeddings in batches with concurrency control"""
        results: List[List[float]] = []
        batch_size = self.config.batch_size
        total_batches = (len(texts) + batch_size - 1) // batch_size
        
        for batch_idx in range(0, len(texts), batch_size):
            batch = texts[batch_idx:batch_idx + batch_size]
            
            # Process batch with concurrency control
            async def process_text(text: str) -> List[float]:
                async with self._semaphore:
                    return await self._generate_with_retry(text, task_type)
            
            batch_results = await asyncio.gather(
                *[process_text(t) for t in batch],
                return_exceptions=True
            )
            
            # Handle any errors
            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Embedding failed for text {batch_idx + i}: {result}")
                    # Return zero vector as fallback
                    results.append([0.0] * self.config.dimension)
                    self._stats["errors"] += 1
                else:
                    results.append(result)
            
            if show_progress:
                current_batch = batch_idx // batch_size + 1
                logger.info(f"Batch {current_batch}/{total_batches} complete")
            
            # Small delay between batches to avoid rate limits
            if batch_idx + batch_size < len(texts):
                await asyncio.sleep(0.05)
        
        return results
    
    # ==================== Retry Logic ====================
    
    async def _generate_with_retry(
        self,
        text: str,
        task_type: str
    ) -> List[float]:
        """Generate embedding with exponential backoff retry"""
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                # Acquire rate limit token
                await self._rate_limiter.acquire()
                
                # Generate embedding
                embedding = await self._provider.embed_single(text, task_type)
                
                self._stats["api_calls"] += 1
                self._stats["total_tokens"] += len(text.split())
                
                return embedding
                
            except Exception as e:
                last_error = e
                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Embedding attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
        
        self._stats["errors"] += 1
        raise RuntimeError(f"Embedding failed after {self.config.max_retries} attempts: {last_error}")
    
    # ==================== Cache Management ====================
    
    async def _cache_embedding(self, key: str, embedding: List[float]) -> None:
        """Cache single embedding to both levels"""
        if self._l1_cache:
            await self._l1_cache.set(key, embedding)
        
        if self._redis:
            try:
                await self._redis.set(
                    key,
                    json.dumps(embedding),
                    self.config.cache_ttl_seconds
                )
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")
    
    async def _cache_embeddings_batch(self, embeddings: Dict[str, List[float]]) -> None:
        """Cache multiple embeddings"""
        if self._l1_cache:
            await self._l1_cache.set_many(embeddings)
        
        if self._redis:
            try:
                json_data = {k: json.dumps(v) for k, v in embeddings.items()}
                await self._redis.mset(json_data, self.config.cache_ttl_seconds)
            except Exception as e:
                logger.warning(f"Redis batch cache write failed: {e}")
    
    # ==================== Utilities ====================
    
    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Compute cosine similarity between two vectors"""
        a = np.array(v1)
        b = np.array(v2)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))
    
    @staticmethod
    def normalize_vector(v: List[float]) -> List[float]:
        """L2 normalize a vector"""
        arr = np.array(v)
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
        return arr.tolist()
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        cache_stats = self._l1_cache.stats if self._l1_cache else {}
        return {
            **self._stats,
            "l1_cache": cache_stats,
        }
    
    async def clear_cache(self) -> None:
        """Clear all caches"""
        if self._l1_cache:
            await self._l1_cache.clear()
        logger.info("Embedding cache cleared")