# ============================================================================
# Embedding Service
# ============================================================================
import google.generativeai as genai
from typing import List, Optional, Dict, Any
import asyncio
import hashlib
import json
from app.config import get_settings
from app.core.redis import cache
from app.services.rag.config import EmbeddingConfig, default_rag_config

settings = get_settings()

class EmbeddingService:
    """Service for generating and managing embeddings"""
    
    def __init__(self, config: EmbeddingConfig = None):
        self.config = config or default_rag_config.embedding
        genai.configure(api_key=settings.GEMINI_API_KEY)
    
    async def embed_text(
        self,
        text: str,
        task_type: str = None
    ) -> List[float]:
        """Generate embedding for a single text"""
        task = task_type or self.config.document_task_type
        
        # Check cache first
        if self.config.cache_embeddings:
            cache_key = self._get_cache_key(text, task)
            cached = await cache.get(cache_key)
            if cached:
                return json.loads(cached)
        
        # Generate embedding
        result = genai.embed_content(
            model=f"models/{self.config.model}",
            content=text,
            task_type=task
        )
        embedding = result['embedding']
        
        # Cache the result
        if self.config.cache_embeddings:
            await cache.set(
                cache_key,
                json.dumps(embedding),
                ttl=self.config.cache_ttl
            )
        
        return embedding
    
    async def embed_texts(
        self,
        texts: List[str],
        task_type: str = None
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts with batching"""
        task = task_type or self.config.document_task_type
        embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i:i + self.config.batch_size]
            batch_embeddings = await self._embed_batch(batch, task)
            embeddings.extend(batch_embeddings)
            
            # Small delay to avoid rate limiting
            if i + self.config.batch_size < len(texts):
                await asyncio.sleep(0.1)
        
        return embeddings
    
    async def embed_query(self, query: str) -> List[float]:
        """Generate embedding optimized for search queries"""
        return await self.embed_text(
            query,
            task_type=self.config.query_task_type
        )
    
    async def embed_document(self, document: str) -> List[float]:
        """Generate embedding optimized for documents"""
        return await self.embed_text(
            document,
            task_type=self.config.document_task_type
        )
    
    async def _embed_batch(
        self,
        texts: List[str],
        task_type: str
    ) -> List[List[float]]:
        """Embed a batch of texts"""
        embeddings = []
        
        for text in texts:
            # Check cache
            if self.config.cache_embeddings:
                cache_key = self._get_cache_key(text, task_type)
                cached = await cache.get(cache_key)
                if cached:
                    embeddings.append(json.loads(cached))
                    continue
            
            # Generate embedding
            result = genai.embed_content(
                model=f"models/{self.config.model}",
                content=text,
                task_type=task_type
            )
            embedding = result['embedding']
            embeddings.append(embedding)
            
            # Cache
            if self.config.cache_embeddings:
                cache_key = self._get_cache_key(text, task_type)
                await cache.set(
                    cache_key,
                    json.dumps(embedding),
                    ttl=self.config.cache_ttl
                )
        
        return embeddings
    
    def _get_cache_key(self, text: str, task_type: str) -> str:
        """Generate cache key for embedding"""
        content_hash = hashlib.md5(text.encode()).hexdigest()[:16]
        return f"emb:{self.config.model}:{task_type}:{content_hash}"
    
    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        import math
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)