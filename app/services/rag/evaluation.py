# ============================================================================
# RAG Evaluation & Metrics
# ============================================================================
"""
Evaluation framework for RAG pipeline quality:
- Retrieval metrics (MRR, Recall, Precision)
- Response quality scoring
- Latency tracking
- A/B testing support
- Logging and analytics
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


# ============================================================================
# Enums and Data Classes
# ============================================================================
class MetricType(str, Enum):
    """Types of metrics tracked"""
    RETRIEVAL_LATENCY = "retrieval_latency"
    GENERATION_LATENCY = "generation_latency"
    TOTAL_LATENCY = "total_latency"
    RETRIEVAL_COUNT = "retrieval_count"
    CONFIDENCE_SCORE = "confidence_score"
    USER_FEEDBACK = "user_feedback"
    ERROR_RATE = "error_rate"


@dataclass
class QueryMetrics:
    """Metrics for a single query"""
    query_id: str
    timestamp: datetime
    query_text: str
    
    # Timing
    retrieval_time_ms: float
    generation_time_ms: float
    total_time_ms: float
    
    # Retrieval quality
    docs_retrieved: int
    top_score: float
    avg_score: float
    
    # Response
    response_length: int
    confidence: float
    mode: str
    
    # Context
    subject: Optional[str] = None
    grade: Optional[str] = None
    
    # User feedback (updated later)
    feedback_score: Optional[int] = None  # 1-5
    feedback_helpful: Optional[bool] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.query_id,
            "timestamp": self.timestamp.isoformat(),
            "query": self.query_text[:100],
            "timing": {
                "retrieval_ms": self.retrieval_time_ms,
                "generation_ms": self.generation_time_ms,
                "total_ms": self.total_time_ms,
            },
            "retrieval": {
                "count": self.docs_retrieved,
                "top_score": self.top_score,
                "avg_score": self.avg_score,
            },
            "response": {
                "length": self.response_length,
                "confidence": self.confidence,
                "mode": self.mode,
            },
            "context": {
                "subject": self.subject,
                "grade": self.grade,
            },
            "feedback": {
                "score": self.feedback_score,
                "helpful": self.feedback_helpful,
            }
        }


@dataclass
class RetrievalEvaluation:
    """Evaluation results for retrieval quality"""
    query: str
    relevant_doc_ids: List[str]
    retrieved_doc_ids: List[str]
    
    # Metrics
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    mrr: float = 0.0  # Mean Reciprocal Rank
    ndcg: float = 0.0  # Normalized Discounted Cumulative Gain
    
    def calculate_metrics(self):
        """Calculate all retrieval metrics"""
        if not self.relevant_doc_ids:
            return
        
        relevant_set = set(self.relevant_doc_ids)
        retrieved_set = set(self.retrieved_doc_ids)
        
        # Precision & Recall
        true_positives = len(relevant_set & retrieved_set)
        self.precision = true_positives / len(retrieved_set) if retrieved_set else 0
        self.recall = true_positives / len(relevant_set) if relevant_set else 0
        
        # F1
        if self.precision + self.recall > 0:
            self.f1 = 2 * (self.precision * self.recall) / (self.precision + self.recall)
        
        # MRR (Mean Reciprocal Rank)
        for i, doc_id in enumerate(self.retrieved_doc_ids):
            if doc_id in relevant_set:
                self.mrr = 1.0 / (i + 1)
                break
        
        # NDCG (simplified)
        dcg = 0.0
        for i, doc_id in enumerate(self.retrieved_doc_ids):
            if doc_id in relevant_set:
                dcg += 1.0 / (i + 2)  # log2(i+2) simplified
        
        idcg = sum(1.0 / (i + 2) for i in range(min(len(relevant_set), len(self.retrieved_doc_ids))))
        self.ndcg = dcg / idcg if idcg > 0 else 0


# ============================================================================
# Metrics Collector
# ============================================================================
class MetricsCollector:
    """
    Collects and aggregates RAG metrics.
    
    Usage:
        collector = MetricsCollector()
        
        # Record a query
        collector.record_query(QueryMetrics(...))
        
        # Get aggregates
        stats = collector.get_stats(period_hours=24)
    """
    
    def __init__(self, max_history: int = 10000):
        self._metrics: List[QueryMetrics] = []
        self._max_history = max_history
        self._error_count = 0
        self._total_queries = 0
        
        # Aggregated stats
        self._hourly_stats: Dict[str, Dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )
    
    def record_query(self, metrics: QueryMetrics) -> None:
        """Record metrics for a query"""
        self._metrics.append(metrics)
        self._total_queries += 1
        
        # Trim history if needed
        if len(self._metrics) > self._max_history:
            self._metrics = self._metrics[-self._max_history:]
        
        # Update hourly aggregates
        hour_key = metrics.timestamp.strftime("%Y-%m-%d-%H")
        self._hourly_stats[hour_key]["count"] += 1
        self._hourly_stats[hour_key]["total_latency"] += metrics.total_time_ms
        self._hourly_stats[hour_key]["total_confidence"] += metrics.confidence
    
    def record_error(self) -> None:
        """Record an error occurrence"""
        self._error_count += 1
    
    def record_feedback(
        self,
        query_id: str,
        score: Optional[int] = None,
        helpful: Optional[bool] = None
    ) -> None:
        """Record user feedback for a query"""
        for metric in reversed(self._metrics):
            if metric.query_id == query_id:
                metric.feedback_score = score
                metric.feedback_helpful = helpful
                break
    
    def get_stats(self, period_hours: int = 24) -> Dict[str, Any]:
        """Get aggregated statistics for a time period"""
        cutoff = datetime.now() - timedelta(hours=period_hours)
        recent = [m for m in self._metrics if m.timestamp > cutoff]
        
        if not recent:
            return {
                "period_hours": period_hours,
                "query_count": 0,
                "error_rate": 0,
            }
        
        # Calculate aggregates
        latencies = [m.total_time_ms for m in recent]
        confidences = [m.confidence for m in recent]
        retrieval_counts = [m.docs_retrieved for m in recent]
        
        feedback_scores = [m.feedback_score for m in recent if m.feedback_score]
        helpful_count = sum(1 for m in recent if m.feedback_helpful is True)
        feedback_total = sum(1 for m in recent if m.feedback_helpful is not None)
        
        return {
            "period_hours": period_hours,
            "query_count": len(recent),
            "total_queries": self._total_queries,
            "error_count": self._error_count,
            "error_rate": self._error_count / self._total_queries if self._total_queries > 0 else 0,
            
            "latency": {
                "avg_ms": sum(latencies) / len(latencies),
                "p50_ms": sorted(latencies)[len(latencies) // 2],
                "p95_ms": sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 20 else max(latencies),
                "p99_ms": sorted(latencies)[int(len(latencies) * 0.99)] if len(latencies) > 100 else max(latencies),
            },
            
            "confidence": {
                "avg": sum(confidences) / len(confidences),
                "min": min(confidences),
                "max": max(confidences),
            },
            
            "retrieval": {
                "avg_docs": sum(retrieval_counts) / len(retrieval_counts),
                "zero_results_rate": sum(1 for c in retrieval_counts if c == 0) / len(retrieval_counts),
            },
            
            "feedback": {
                "response_count": len(feedback_scores),
                "avg_score": sum(feedback_scores) / len(feedback_scores) if feedback_scores else None,
                "helpful_rate": helpful_count / feedback_total if feedback_total > 0 else None,
            },
            
            "by_mode": self._group_by_mode(recent),
            "by_subject": self._group_by_subject(recent),
        }
    
    def _group_by_mode(self, metrics: List[QueryMetrics]) -> Dict[str, Dict[str, float]]:
        """Group statistics by response mode"""
        by_mode: Dict[str, List[QueryMetrics]] = defaultdict(list)
        for m in metrics:
            by_mode[m.mode].append(m)
        
        return {
            mode: {
                "count": len(items),
                "avg_latency_ms": sum(i.total_time_ms for i in items) / len(items),
                "avg_confidence": sum(i.confidence for i in items) / len(items),
            }
            for mode, items in by_mode.items()
        }
    
    def _group_by_subject(self, metrics: List[QueryMetrics]) -> Dict[str, int]:
        """Count queries by subject"""
        by_subject: Dict[str, int] = defaultdict(int)
        for m in metrics:
            subject = m.subject or "unknown"
            by_subject[subject] += 1
        return dict(by_subject)
    
    def get_recent_queries(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent query details"""
        return [m.to_dict() for m in self._metrics[-limit:]]


# ============================================================================
# Response Quality Evaluator
# ============================================================================
class ResponseQualityEvaluator:
    """
    Evaluate response quality using various heuristics.
    For more advanced evaluation, integrate with LLM-as-judge.
    """
    
    # Quality indicators
    POSITIVE_INDICATORS = [
        r'\b(because|therefore|thus|hence|so that)\b',  # Explanatory
        r'\b(for example|such as|like|e\.g\.)\b',  # Examples
        r'\b(first|second|third|step|next)\b',  # Structured
        r'\b(important|key|main|primary)\b',  # Emphasis
    ]
    
    NEGATIVE_INDICATORS = [
        r"i don't know",
        r"i'm not sure",
        r"i cannot",
        r"error",
        r"sorry",
    ]
    
    @classmethod
    def evaluate(
        cls,
        query: str,
        response: str,
        retrieved_docs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluate response quality.
        
        Returns:
            Dict with quality scores and indicators
        """
        import re
        
        scores = {}
        
        # Length appropriateness
        word_count = len(response.split())
        scores["length_score"] = min(word_count / 100, 1.0)  # Ideal ~100 words
        if word_count < 20:
            scores["length_score"] *= 0.5  # Penalize very short
        if word_count > 500:
            scores["length_score"] *= 0.8  # Slight penalty for very long
        
        # Structure indicators
        positive_count = sum(
            len(re.findall(pattern, response.lower()))
            for pattern in cls.POSITIVE_INDICATORS
        )
        scores["structure_score"] = min(positive_count / 3, 1.0)
        
        # Negative indicators
        negative_count = sum(
            len(re.findall(pattern, response.lower()))
            for pattern in cls.NEGATIVE_INDICATORS
        )
        scores["negativity_penalty"] = negative_count * 0.2
        
        # Relevance (keyword overlap with query)
        query_words = set(re.findall(r'\b\w{4,}\b', query.lower()))
        response_words = set(re.findall(r'\b\w{4,}\b', response.lower()))
        overlap = len(query_words & response_words)
        scores["relevance_score"] = overlap / len(query_words) if query_words else 0
        
        # Context utilization
        if retrieved_docs:
            doc_content = " ".join(d.get("content", "")[:200] for d in retrieved_docs[:3])
            doc_words = set(re.findall(r'\b\w{4,}\b', doc_content.lower()))
            context_overlap = len(doc_words & response_words)
            scores["context_utilization"] = context_overlap / len(doc_words) if doc_words else 0
        else:
            scores["context_utilization"] = 0
        
        # Overall score
        scores["overall"] = (
            scores["length_score"] * 0.2 +
            scores["structure_score"] * 0.2 +
            scores["relevance_score"] * 0.3 +
            scores["context_utilization"] * 0.3 -
            scores["negativity_penalty"]
        )
        scores["overall"] = max(0, min(1, scores["overall"]))
        
        return scores


# ============================================================================
# Evaluation Test Suite
# ============================================================================
class EvaluationTestSuite:
    """
    Run evaluation tests on the RAG pipeline.
    
    Usage:
        suite = EvaluationTestSuite(rag_engine)
        results = await suite.run_retrieval_tests(test_cases)
    """
    
    def __init__(self, rag_engine):
        self.rag_engine = rag_engine
        self.results: List[Dict[str, Any]] = []
    
    async def run_retrieval_tests(
        self,
        test_cases: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Run retrieval evaluation on test cases.
        
        Args:
            test_cases: List of {query, relevant_doc_ids, student_context}
        
        Returns:
            Aggregated evaluation results
        """
        evaluations = []
        
        for case in test_cases:
            query = case["query"]
            relevant_ids = case.get("relevant_doc_ids", [])
            context = case.get("student_context", {})
            
            # Run retrieval
            response = await self.rag_engine.query_with_metadata(
                question=query,
                student_context=context,
                mode="explain"
            )
            
            # Get retrieved doc IDs
            retrieved_ids = [
                doc.get("id") or doc.get("chunk_id", "")
                for doc in response.retrieved_docs
            ]
            
            # Evaluate
            evaluation = RetrievalEvaluation(
                query=query,
                relevant_doc_ids=relevant_ids,
                retrieved_doc_ids=retrieved_ids
            )
            evaluation.calculate_metrics()
            evaluations.append(evaluation)
        
        # Aggregate results
        return {
            "test_count": len(evaluations),
            "avg_precision": sum(e.precision for e in evaluations) / len(evaluations),
            "avg_recall": sum(e.recall for e in evaluations) / len(evaluations),
            "avg_f1": sum(e.f1 for e in evaluations) / len(evaluations),
            "avg_mrr": sum(e.mrr for e in evaluations) / len(evaluations),
            "avg_ndcg": sum(e.ndcg for e in evaluations) / len(evaluations),
        }
    
    async def run_response_quality_tests(
        self,
        test_cases: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Run response quality evaluation"""
        scores = []
        
        for case in test_cases:
            response = await self.rag_engine.query_with_metadata(
                question=case["query"],
                student_context=case.get("student_context", {}),
                mode=case.get("mode", "explain")
            )
            
            quality = ResponseQualityEvaluator.evaluate(
                query=case["query"],
                response=response.response_text,
                retrieved_docs=response.retrieved_docs
            )
            
            scores.append(quality)
        
        # Aggregate
        return {
            "test_count": len(scores),
            "avg_overall": sum(s["overall"] for s in scores) / len(scores),
            "avg_relevance": sum(s["relevance_score"] for s in scores) / len(scores),
            "avg_context_utilization": sum(s["context_utilization"] for s in scores) / len(scores),
        }
    
    async def run_latency_benchmark(
        self,
        queries: List[str],
        iterations: int = 3
    ) -> Dict[str, Any]:
        """Run latency benchmarks"""
        latencies = []
        
        for query in queries:
            for _ in range(iterations):
                start = time.time()
                await self.rag_engine.query(
                    question=query,
                    student_context={"grade": "Form 3"},
                    mode="explain"
                )
                latencies.append((time.time() - start) * 1000)
        
        latencies.sort()
        
        return {
            "query_count": len(queries),
            "iterations": iterations,
            "total_samples": len(latencies),
            "avg_ms": sum(latencies) / len(latencies),
            "p50_ms": latencies[len(latencies) // 2],
            "p95_ms": latencies[int(len(latencies) * 0.95)],
            "p99_ms": latencies[int(len(latencies) * 0.99)],
            "min_ms": min(latencies),
            "max_ms": max(latencies),
        }


# ============================================================================
# Global Metrics Instance
# ============================================================================
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def record_rag_query(
    query_id: str,
    query_text: str,
    response,  # RAGResponse
    subject: Optional[str] = None,
    grade: Optional[str] = None
) -> None:
    """Convenience function to record RAG query metrics"""
    collector = get_metrics_collector()
    
    docs = response.retrieved_docs
    scores = [d.get("score", 0) for d in docs] if docs else [0]
    
    metrics = QueryMetrics(
        query_id=query_id,
        timestamp=datetime.now(),
        query_text=query_text,
        retrieval_time_ms=response.retrieval_time_ms,
        generation_time_ms=response.generation_time_ms,
        total_time_ms=response.total_time_ms,
        docs_retrieved=len(docs),
        top_score=max(scores),
        avg_score=sum(scores) / len(scores),
        response_length=len(response.response_text),
        confidence=response.confidence_score,
        mode=response.mode_used,
        subject=subject,
        grade=grade,
    )
    
    collector.record_query(metrics)