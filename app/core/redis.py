# ============================================================================
# Redis Connection
# ============================================================================
import redis.asyncio as redis
from app.config import get_settings

settings = get_settings()

redis_client = redis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True
)

class RedisCache:
    """Redis caching utility"""
    
    def __init__(self, client: redis.Redis):
        self.client = client
    
    async def get(self, key: str) -> str | None:
        return await self.client.get(key)
    
    async def set(self, key: str, value: str, ttl: int = 3600) -> None:
        await self.client.setex(key, ttl, value)
    
    async def delete(self, key: str) -> None:
        await self.client.delete(key)
    
    async def get_json(self, key: str) -> dict | None:
        import json
        data = await self.get(key)
        return json.loads(data) if data else None
    
    async def set_json(self, key: str, value: dict, ttl: int = 3600) -> None:
        import json
        await self.set(key, json.dumps(value), ttl)
    
    # Rate limiting
    async def check_rate_limit(self, key: str, limit: int, window: int = 86400) -> tuple[bool, int]:
        """Check if rate limit exceeded. Returns (allowed, remaining)"""
        current = await self.client.get(key)
        if current is None:
            await self.client.setex(key, window, 1)
            return True, limit - 1
        
        current = int(current)
        if current >= limit:
            return False, 0
        
        await self.client.incr(key)
        return True, limit - current - 1

cache = RedisCache(redis_client)
