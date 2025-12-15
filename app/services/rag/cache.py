# ============================================================================
# Cache Adapters for RAG Pipeline
# ============================================================================
"""
Cache backend implementations for the RAG system.
Provides Redis adapter and in-memory fallback.
"""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, Union
import asyncio

logger = logging.getLogger(__name__)


# ============================================================================
# Cache Protocol (Interface)
# ============================================================================
class CacheBackend(Protocol):
    """Protocol defining cache backend interface"""
    
    async def get(self, key: str) -> Optional[str]:
        """Get a value by key"""
        ...
    
    async def set(self, key: str, value: str, ttl: int = 3600) -> None:
        """Set a value with TTL"""
        ...
    
    async def delete(self, key: str) -> bool:
        """Delete a key"""
        ...
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        ...
    
    async def mget(self, keys: List[str]) -> List[Optional[str]]:
        """Get multiple values"""
        ...
    
    async def mset(self, mapping: Dict[str, str], ttl: int = 3600) -> None:
        """Set multiple values"""
        ...


# ============================================================================
# Redis Cache Adapter
# ============================================================================
class RedisCacheAdapter:
    """
    Redis cache adapter for RAG components.
    
    Usage:
        from app.core.redis import get_redis_client
        
        redis_client = await get_redis_client()
        cache = RedisCacheAdapter(redis_client)
        
        embedding_service = EmbeddingService(
            api_key=settings.GEMINI_API_KEY,
            redis_cache=cache
        )
    """
    
    def __init__(self, redis_client, prefix: str = "rag"):
        """
        Initialize Redis cache adapter.
        
        Args:
            redis_client: aioredis/redis-py async client
            prefix: Key prefix for namespacing
        """
        self._redis = redis_client
        self._prefix = prefix
        self._stats = {"hits": 0, "misses": 0, "errors": 0}
    
    def _make_key(self, key: str) -> str:
        """Add prefix to key"""
        return f"{self._prefix}:{key}"
    
    async def get(self, key: str) -> Optional[str]:
        """Get a cached value"""
        try:
            result = await self._redis.get(self._make_key(key))
            if result:
                self._stats["hits"] += 1
                return result.decode() if isinstance(result, bytes) else result
            self._stats["misses"] += 1
            return None
        except Exception as e:
            self._stats["errors"] += 1
            logger.warning(f"Redis GET error: {e}")
            return None
    
    async def set(self, key: str, value: str, ttl: int = 3600) -> None:
        """Set a cached value with TTL"""
        try:
            await self._redis.setex(
                self._make_key(key),
                ttl,
                value
            )
        except Exception as e:
            self._stats["errors"] += 1
            logger.warning(f"Redis SET error: {e}")
    
    async def delete(self, key: str) -> bool:
        """Delete a cached value"""
        try:
            result = await self._redis.delete(self._make_key(key))
            return result > 0
        except Exception as e:
            self._stats["errors"] += 1
            logger.warning(f"Redis DELETE error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return await self._redis.exists(self._make_key(key)) > 0
        except Exception as e:
            self._stats["errors"] += 1
            return False
    
    async def mget(self, keys: List[str]) -> List[Optional[str]]:
        """Get multiple values at once"""
        if not keys:
            return []
        
        try:
            prefixed_keys = [self._make_key(k) for k in keys]
            results = await self._redis.mget(prefixed_keys)
            
            decoded = []
            for r in results:
                if r:
                    self._stats["hits"] += 1
                    decoded.append(r.decode() if isinstance(r, bytes) else r)
                else:
                    self._stats["misses"] += 1
                    decoded.append(None)
            return decoded
            
        except Exception as e:
            self._stats["errors"] += 1
            logger.warning(f"Redis MGET error: {e}")
            return [None] * len(keys)
    
    async def mset(self, mapping: Dict[str, str], ttl: int = 3600) -> None:
        """Set multiple values at once with TTL"""
        if not mapping:
            return
        
        try:
            # Redis doesn't have native MSETEX, so we use pipeline
            pipe = self._redis.pipeline()
            for key, value in mapping.items():
                pipe.setex(self._make_key(key), ttl, value)
            await pipe.execute()
        except Exception as e:
            self._stats["errors"] += 1
            logger.warning(f"Redis MSET error: {e}")
    
    async def get_json(self, key: str) -> Optional[Any]:
        """Get and parse JSON value"""
        result = await self.get(key)
        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return None
        return None
    
    async def set_json(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Serialize and set JSON value"""
        await self.set(key, json.dumps(value), ttl)
    
    async def clear_prefix(self, prefix: str = "") -> int:
        """Clear all keys with given prefix"""
        try:
            pattern = f"{self._prefix}:{prefix}*"
            cursor = 0
            deleted = 0
            
            while True:
                cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
                if keys:
                    deleted += await self._redis.delete(*keys)
                if cursor == 0:
                    break
            
            return deleted
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            return 0
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self._stats["hits"] + self._stats["misses"]
        return {
            **self._stats,
            "hit_rate": self._stats["hits"] / total if total > 0 else 0,
        }


# ============================================================================
# In-Memory Cache (Fallback/Testing)
# ============================================================================
class InMemoryCacheAdapter:
    """
    In-memory cache for testing or when Redis is unavailable.
    Not recommended for production with multiple workers.
    """
    
    def __init__(self, max_size: int = 10000, default_ttl: int = 3600):
        self._cache: Dict[str, tuple] = {}  # (value, expiry_time)
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[str]:
        async with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                import time
                if time.time() < expiry:
                    return value
                del self._cache[key]
            return None
    
    async def set(self, key: str, value: str, ttl: int = None) -> None:
        import time
        async with self._lock:
            if len(self._cache) >= self._max_size:
                # Evict oldest
                oldest = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                del self._cache[oldest]
            
            expiry = time.time() + (ttl or self._default_ttl)
            self._cache[key] = (value, expiry)
    
    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def exists(self, key: str) -> bool:
        return await self.get(key) is not None
    
    async def mget(self, keys: List[str]) -> List[Optional[str]]:
        return [await self.get(k) for k in keys]
    
    async def mset(self, mapping: Dict[str, str], ttl: int = None) -> None:
        for key, value in mapping.items():
            await self.set(key, value, ttl)
    
    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()


# ============================================================================
# Cache Factory
# ============================================================================
async def create_cache_adapter(
    settings,
    use_redis: bool = True
) -> Union[RedisCacheAdapter, InMemoryCacheAdapter]:
    """
    Create appropriate cache adapter based on configuration.
    
    Args:
        settings: Application settings
        use_redis: Whether to use Redis (falls back to in-memory if unavailable)
    
    Returns:
        Cache adapter instance
    """
    if use_redis:
        try:
            # Try to import and connect to Redis
            from app.core.redis import get_redis_client
            redis_client = await get_redis_client()
            
            # Test connection
            await redis_client.ping()
            
            logger.info("Using Redis cache adapter")
            return RedisCacheAdapter(redis_client, prefix="rag")
            
        except Exception as e:
            logger.warning(f"Redis unavailable ({e}), falling back to in-memory cache")
    
    logger.info("Using in-memory cache adapter")
    return InMemoryCacheAdapter()


# ============================================================================
# Conversation Cache Helper
# ============================================================================
class ConversationCache:
    """
    Specialized cache for conversation history.
    Used by RAG engine to maintain context across messages.
    """
    
    def __init__(self, cache: CacheBackend, max_history: int = 10):
        self._cache = cache
        self._max_history = max_history
        self._ttl = 3600 * 24  # 24 hours
    
    def _key(self, student_id: str) -> str:
        return f"conv:{student_id}"
    
    async def get_history(self, student_id: str) -> List[Dict[str, str]]:
        """Get conversation history for a student"""
        result = await self._cache.get(self._key(student_id))
        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return []
        return []
    
    async def add_message(
        self,
        student_id: str,
        role: str,
        content: str
    ) -> None:
        """Add a message to conversation history"""
        history = await self.get_history(student_id)
        history.append({"role": role, "content": content})
        
        # Keep only recent messages
        if len(history) > self._max_history:
            history = history[-self._max_history:]
        
        await self._cache.set(
            self._key(student_id),
            json.dumps(history),
            self._ttl
        )
    
    async def clear_history(self, student_id: str) -> None:
        """Clear conversation history"""
        await self._cache.delete(self._key(student_id))


# ============================================================================
# Session State Cache
# ============================================================================
class SessionStateCache:
    """
    Cache for practice session state.
    Maintains state between messages in a practice session.
    """
    
    def __init__(self, cache: CacheBackend):
        self._cache = cache
        self._ttl = 3600  # 1 hour
    
    def _key(self, session_id: str) -> str:
        return f"session:{session_id}"
    
    async def get_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session state"""
        result = await self._cache.get(self._key(session_id))
        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return None
        return None
    
    async def set_state(self, session_id: str, state: Dict[str, Any]) -> None:
        """Set session state"""
        await self._cache.set(
            self._key(session_id),
            json.dumps(state),
            self._ttl
        )
    
    async def update_state(self, session_id: str, updates: Dict[str, Any]) -> None:
        """Update specific fields in session state"""
        state = await self.get_state(session_id) or {}
        state.update(updates)
        await self.set_state(session_id, state)
    
    async def delete_state(self, session_id: str) -> None:
        """Delete session state"""
        await self._cache.delete(self._key(session_id))