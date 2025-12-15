# RAG Pipeline Architecture

## File Structure

```
app/services/rag/
├── __init__.py          # Public API exports & factory functions
├── config.py            # Configuration classes & profiles
├── embeddings.py        # Embedding service with caching
├── document_processor.py # Document extraction & chunking
├── vector_store.py      # Qdrant vector store with hybrid search
├── query_processor.py   # Query analysis & enhancement
├── retriever.py         # Multi-strategy retrieval
├── prompts.py           # Prompt templates & builder
├── cache.py             # Redis/in-memory cache adapters
├── evaluation.py        # Metrics & evaluation framework
└── rag_engine.py        # Main orchestrator

scripts/
└── ingest_documents.py  # Document ingestion CLI
```

## Component Relationships

```
┌─────────────────────────────────────────────────────────────────────┐
│                         RAG Engine                                   │
│  (Main Orchestrator - rag_engine.py)                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐       │
│   │   Query     │───▶│   Retriever  │───▶│  Context        │       │
│   │  Processor  │    │              │    │  Builder        │       │
│   └─────────────┘    └──────┬───────┘    └────────┬────────┘       │
│                             │                      │                 │
│                             ▼                      ▼                 │
│                    ┌────────────────┐    ┌─────────────────┐       │
│                    │  Vector Store  │    │ Prompt Builder  │       │
│                    │   (Qdrant)     │    │                 │       │
│                    └────────┬───────┘    └────────┬────────┘       │
│                             │                      │                 │
│                             ▼                      ▼                 │
│                    ┌────────────────┐    ┌─────────────────┐       │
│                    │   Embedding    │    │   LLM (Gemini)  │       │
│                    │   Service      │    │   Generation    │       │
│                    └────────────────┘    └─────────────────┘       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Query Processing Flow

```
User Query
    │
    ▼
┌─────────────────────┐
│   QueryProcessor    │
│  - Intent detection │
│  - Subject detect.  │
│  - Keyword extract  │
│  - Query variations │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│     Retriever       │
│  - Strategy select  │
│  - Hybrid search    │
│  - RRF fusion       │
│  - Reranking        │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   Context Builder   │
│  - Doc formatting   │
│  - Token limiting   │
│  - Source citation  │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   Prompt Builder    │
│  - Mode selection   │
│  - Context inject   │
│  - History inject   │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   LLM Generation    │
│  - Mode-specific    │
│  - Post-processing  │
└─────────┬───────────┘
          │
          ▼
    RAGResponse
```

### 2. Document Ingestion Flow

```
Document File (PDF/DOCX/TXT)
    │
    ▼
┌─────────────────────┐
│  Content Extractor  │
│  - PDF: PyMuPDF     │
│  - DOCX: python-docx│
│  - Tables & images  │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   Preprocessor      │
│  - Normalization    │
│  - OCR cleanup      │
│  - Structure detect │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   Chunking Engine   │
│  - Strategy select  │
│  - Semantic split   │
│  - Overlap handling │
│  - Parent-child     │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Quality Scorer     │
│  - Content quality  │
│  - Deduplication    │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Embedding Service  │
│  - Batch generation │
│  - Caching (L1/L2)  │
│  - Rate limiting    │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   Vector Store      │
│  - Dense vectors    │
│  - Sparse vectors   │
│  - Payload index    │
└─────────────────────┘
```

## Retrieval Strategies

| Strategy | Use Case | Description |
|----------|----------|-------------|
| `DENSE_ONLY` | Quick lookups | Pure vector similarity |
| `HYBRID` | Default | Dense + sparse BM25 |
| `MULTI_QUERY` | Complex queries | Query expansion + RRF |
| `HYDE` | Abstract questions | Hypothetical doc generation |

## Response Modes

| Mode | Temperature | Use Case |
|------|-------------|----------|
| `socratic` | 0.7 | Guide without answers |
| `explain` | 0.5 | Clear explanations |
| `practice` | 0.6 | Practice questions |
| `hint` | 0.6 | Progressive hints |
| `summary` | 0.4 | Concise summaries |
| `quiz` | 0.7 | Generate quizzes |
| `marking` | 0.3 | Answer evaluation |

## Caching Architecture

```
┌─────────────────────────────────────┐
│           Request                    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      L1 Cache (In-Memory LRU)       │
│      - Fast, ~10K entries           │
│      - Per-worker                   │
└──────────────┬──────────────────────┘
               │ miss
               ▼
┌─────────────────────────────────────┐
│      L2 Cache (Redis)               │
│      - Shared across workers        │
│      - TTL: 7 days                  │
└──────────────┬──────────────────────┘
               │ miss
               ▼
┌─────────────────────────────────────┐
│      Embedding API (Gemini)         │
│      - Rate limited                 │
│      - Retry with backoff           │
└─────────────────────────────────────┘
```

## Configuration Profiles

```python
# For exam preparation
PROFILE_EXAM_PREP = RAGConfig(
    retrieval=RetrievalConfig(top_k=15, final_k=7),
    generation=GenerationConfig(temperature=0.5)
)

# For quick help
PROFILE_QUICK_HELP = RAGConfig(
    retrieval=RetrievalConfig(top_k=5, final_k=3),
    generation=GenerationConfig(max_output_tokens=512)
)

# For deep explanations
PROFILE_DEEP_EXPLANATION = RAGConfig(
    retrieval=RetrievalConfig(strategy=MULTI_QUERY, top_k=20),
    generation=GenerationConfig(max_output_tokens=2048)
)
```

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Retrieval latency | < 200ms | P95 |
| Generation latency | < 2000ms | P95 |
| Total latency | < 2500ms | P95 |
| Cache hit rate | > 70% | Embedding cache |
| Zero results rate | < 5% | With fallback |

## Monitoring

The `evaluation.py` module provides:

- **QueryMetrics**: Per-query timing and quality metrics
- **MetricsCollector**: Aggregation and statistics
- **ResponseQualityEvaluator**: Heuristic quality scoring
- **EvaluationTestSuite**: Automated testing

```python
from app.services.rag import get_metrics_collector, record_rag_query

# Record metrics automatically
record_rag_query(query_id, query, response, subject, grade)

# Get statistics
stats = get_metrics_collector().get_stats(period_hours=24)
```