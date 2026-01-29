# ============================================================================
# Retriever
# ============================================================================
"""
Sophisticated retrieval system with:
- Multiple retrieval strategies (dense, hybrid, multi-query, HyDE)
- Query expansion and rewriting
- Reciprocal Rank Fusion for result merging
- Contextual compression
- Parent document retrieval
"""
from __future__ import annotations

import asyncio
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import google.generativeai as genai

from app.services.rag.config import (
    RetrievalConfig, RetrievalStrategy, RerankingStrategy, get_rag_config
)
from app.services.rag.vector_store import VectorStore, SearchResult
from app.services.rag.embeddings import EmbeddingService
from app.services.rag.query_processor import QueryProcessor

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================
@dataclass
class RetrievalResult:
    """Result from retrieval pipeline"""
    documents: List[SearchResult]
    query_variations: List[str] = field(default_factory=list)
    strategy_used: str = ""
    total_candidates: int = 0
    retrieval_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StudentContext:
    """Context about the student for personalized retrieval"""
    education_level: str = "secondary"
    grade: str = "Form 3"
    subject: Optional[str] = None
    topics_studied: List[str] = field(default_factory=list)
    difficulty_preference: str = "medium"
    language: str = "English"
    
    def to_filters(self) -> Dict[str, Any]:
        """Convert to retrieval filters"""
        filters = {}
        if self.education_level:
            filters["education_level"] = self.education_level
        if self.grade:
            filters["grade"] = self.grade
        if self.subject:
            filters["subject"] = self.subject
        return filters


# ============================================================================
# Retrieval Strategies
# ============================================================================
class RetrievalStrategyBase(ABC):
    """Base class for retrieval strategies"""
    
    def __init__(
        self,
        vector_store: VectorStore,
        embedding_service: EmbeddingService,
        config: RetrievalConfig
    ):
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.config = config
    
    @abstractmethod
    async def retrieve(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[SearchResult]:
        """Execute retrieval strategy"""
        pass


class DenseRetrieval(RetrievalStrategyBase):
    """Pure dense vector retrieval"""
    
    async def retrieve(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[SearchResult]:
        return await self.vector_store.search(
            query=query,
            filters=filters,
            limit=self.config.top_k,
            score_threshold=self.config.min_score_threshold,
            use_sparse=False
        )


class HybridRetrieval(RetrievalStrategyBase):
    """Hybrid dense + sparse retrieval"""
    
    async def retrieve(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[SearchResult]:
        return await self.vector_store.hybrid_search(
            query=query,
            filters=filters,
            limit=self.config.top_k,
            dense_weight=self.config.dense_weight,
            sparse_weight=self.config.sparse_weight
        )


class MultiQueryRetrieval(RetrievalStrategyBase):
    """Multi-query retrieval with reciprocal rank fusion"""
    
    def __init__(self, *args, query_processor: QueryProcessor, **kwargs):
        super().__init__(*args, **kwargs)
        self.query_processor = query_processor
    
    async def retrieve(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        context: Optional[StudentContext] = None,
        **kwargs
    ) -> List[SearchResult]:
        # Process query using QueryProcessor
        processed = self.query_processor.process(
            query, 
            {"subject": context.subject if context else None, "grade": context.grade if context else None}
        )
        variations = processed.variations
        
        if self.config.include_original_query and query not in variations:
            variations = [query] + variations
        
        # Execute searches in parallel
        tasks = [
            self.vector_store.hybrid_search(
                query=q,
                filters=filters,
                limit=self.config.top_k
            )
            for q in variations[:self.config.num_query_variations]
        ]
        
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Merge with reciprocal rank fusion
        return self._reciprocal_rank_fusion(
            [r for r in results_lists if not isinstance(r, Exception)]
        )
    
    def _reciprocal_rank_fusion(
        self,
        result_lists: List[List[SearchResult]],
        k: int = 60
    ) -> List[SearchResult]:
        """
        Merge multiple result lists using Reciprocal Rank Fusion.
        
        RRF score = Σ 1/(k + rank_i) for each list where document appears
        """
        scores: Dict[str, float] = {}
        docs: Dict[str, SearchResult] = {}
        
        for results in result_lists:
            for rank, result in enumerate(results):
                doc_id = result.id
                rrf_score = 1.0 / (k + rank + 1)
                
                scores[doc_id] = scores.get(doc_id, 0.0) + rrf_score
                
                if doc_id not in docs:
                    docs[doc_id] = result
        
        # Sort by RRF score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        
        # Update combined scores
        results = []
        for doc_id in sorted_ids:
            doc = docs[doc_id]
            doc.combined_score = scores[doc_id]
            results.append(doc)
        
        return results


class HyDERetrieval(RetrievalStrategyBase):
    """
    Hypothetical Document Embeddings (HyDE) retrieval.
    Generates a hypothetical answer and uses it for retrieval.
    """
    
    def __init__(self, *args, llm_model: str = "gemini-2.5-flash", **kwargs):
        super().__init__(*args, **kwargs)
        self.model = genai.GenerativeModel(llm_model)
    
    async def retrieve(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        context: Optional[StudentContext] = None,
        **kwargs
    ) -> List[SearchResult]:
        # Generate hypothetical document
        hypothetical_doc = await self._generate_hypothetical(query, context)
        
        # Search using hypothetical document
        results = await self.vector_store.hybrid_search(
            query=hypothetical_doc,
            filters=filters,
            limit=self.config.top_k
        )
        
        return results
    
    async def _generate_hypothetical(
        self,
        query: str,
        context: Optional[StudentContext]
    ) -> str:
        """Generate a hypothetical answer document"""
        grade = context.grade if context else "Form 3"
        subject = context.subject if context else "the subject"
        
        prompt = f"""You are a ZIMSEC curriculum expert. Generate a detailed, 
factual answer to this question as it would appear in a {grade} {subject} textbook.
Do not add disclaimers or meta-commentary. Just provide the educational content.

Question: {query}

Answer:"""
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.3,
                        max_output_tokens=300
                    )
                )
            )
            # Safely extract text from response
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].text
            return query  # Fallback to original query
        except Exception as e:
            logger.warning(f"HyDE generation failed: {e}")
            return query  # Fallback to original query


# ============================================================================
# Reranking
# ============================================================================
class Reranker:
    """Rerank retrieved documents for improved relevance"""
    
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model = genai.GenerativeModel(model_name)
    
    async def rerank(
        self,
        query: str,
        documents: List[SearchResult],
        top_k: int = 5
    ) -> List[SearchResult]:
        """Rerank documents using LLM relevance scoring"""
        if len(documents) <= top_k:
            return documents
        
        # Score each document
        scored_docs = []
        
        for doc in documents[:20]:  # Limit for efficiency
            score = await self._score_relevance(query, doc.content)
            doc.combined_score = (doc.combined_score + score) / 2
            scored_docs.append(doc)
        
        # Sort by new scores
        scored_docs.sort(key=lambda x: x.combined_score, reverse=True)
        
        return scored_docs[:top_k]
    
    async def _score_relevance(self, query: str, document: str) -> float:
        """Score document relevance to query using LLM"""
        prompt = f"""Rate how relevant this document is to the query on a scale of 0-10.
Only respond with a single number.

Query: {query}

Document: {document[:500]}

Relevance score (0-10):"""
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.0,
                        max_output_tokens=5
                    )
                )
            )
            # Safely extract text from response
            response_text = ""
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                response_text = response.candidates[0].content.parts[0].text
            if response_text:
                score = float(re.search(r'(\d+(?:\.\d+)?)', response_text).group(1))
                return min(score / 10.0, 1.0)
            return 0.5  # Default if no response
        except Exception:
            return 0.5  # Default middle score


# ============================================================================
# Main Retriever
# ============================================================================
class Retriever:
    """
    Main retrieval orchestrator supporting multiple strategies.
    
    Usage:
        retriever = Retriever(vector_store, embedding_service, settings)
        results = await retriever.retrieve(
            query="Explain photosynthesis",
            context=StudentContext(grade="Form 3", subject="Biology")
        )
    """
    
    def __init__(
        self,
        vector_store: VectorStore,
        embedding_service: EmbeddingService,
        settings,
        config: Optional[RetrievalConfig] = None
    ):
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.settings = settings
        self.config = config or get_rag_config().retrieval
        
        # Initialize components
        self.query_processor = QueryProcessor()
        self.reranker = Reranker()
        
        # Initialize strategies
        self._strategies = {
            RetrievalStrategy.DENSE_ONLY: DenseRetrieval(
                vector_store, embedding_service, self.config
            ),
            RetrievalStrategy.HYBRID: HybridRetrieval(
                vector_store, embedding_service, self.config
            ),
            RetrievalStrategy.MULTI_QUERY: MultiQueryRetrieval(
                vector_store, embedding_service, self.config,
                query_processor=self.query_processor
            ),
            RetrievalStrategy.HYDE: HyDERetrieval(
                vector_store, embedding_service, self.config
            ),
        }
    
    async def retrieve(
        self,
        query: str,
        context: Optional[StudentContext] = None,
        strategy: Optional[RetrievalStrategy] = None,
        filters: Optional[Dict[str, Any]] = None,
        rerank: bool = True
    ) -> RetrievalResult:
        """
        Execute retrieval pipeline.
        
        Args:
            query: Search query
            context: Student context for personalization
            strategy: Override retrieval strategy
            filters: Additional metadata filters
            rerank: Whether to apply reranking
        
        Returns:
            RetrievalResult with documents and metadata
        """
        import time
        start_time = time.time()
        
        # Process query
        processed = self.query_processor.process(
            query,
            {"subject": context.subject if context else None, "grade": context.grade if context else None}
        )
        
        # Build filters from context
        combined_filters = {}
        if context:
            combined_filters.update(context.to_filters())
        if filters:
            combined_filters.update(filters)
        
        # Select strategy
        selected_strategy = strategy or self.config.strategy
        retriever = self._strategies.get(
            selected_strategy,
            self._strategies[RetrievalStrategy.HYBRID]
        )
        
        # Execute retrieval
        documents = await retriever.retrieve(
            query=query,
            filters=combined_filters if combined_filters else None,
            context=context
        )
        
        total_candidates = len(documents)
        
        # Apply reranking if enabled
        if rerank and self.config.reranking_strategy != RerankingStrategy.NONE:
            if self.config.reranking_strategy == RerankingStrategy.LLM_RERANK:
                documents = await self.reranker.rerank(
                    query, documents, self.config.final_k
                )
            else:
                # Simple score-based cutoff
                documents = documents[:self.config.final_k]
        
        # Calculate timing
        retrieval_time = (time.time() - start_time) * 1000
        
        return RetrievalResult(
            documents=documents,
            query_variations=processed.variations,
            strategy_used=selected_strategy.value,
            total_candidates=total_candidates,
            retrieval_time_ms=retrieval_time,
            metadata={
                "subject_detected": processed.subject,
                "intent_detected": processed.intent.value if hasattr(processed.intent, 'value') else str(processed.intent),
                "keywords": processed.keywords,
                "filters_applied": combined_filters,
            }
        )
    
    async def retrieve_with_fallback(
        self,
        query: str,
        context: Optional[StudentContext] = None,
        **kwargs
    ) -> RetrievalResult:
        """
        Retrieve with automatic fallback if primary strategy fails.
        """
        # Try primary strategy
        result = await self.retrieve(query, context, **kwargs)
        
        # If no results, try without filters
        if not result.documents and context:
            logger.info("No results with filters, trying broader search")
            result = await self.retrieve(query, context=None, **kwargs)
            result.metadata["fallback_used"] = "no_filters"
        
        # If still no results, try different strategy
        if not result.documents:
            logger.info("No results, trying multi-query strategy")
            result = await self.retrieve(
                query, context,
                strategy=RetrievalStrategy.MULTI_QUERY,
                **kwargs
            )
            result.metadata["fallback_used"] = "multi_query"
        
        return result