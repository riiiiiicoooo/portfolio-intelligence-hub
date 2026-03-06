# Portfolio Intelligence Hub -- Improvements & Technology Roadmap

## Product Overview

Portfolio Intelligence Hub is a RAG-powered natural language analytics platform designed for mid-market real estate operators. It sits on top of Snowflake and combines two core engines -- **Text-to-SQL generation** for structured warehouse queries and **semantic document search (RAG)** for unstructured documents (leases, inspection reports, maintenance logs) -- behind a single conversational interface.

The platform serves four user personas (Property Managers, Brokers, Finance teams, Executives) across 87 properties in 12 states, replacing a two-analyst bottleneck with self-service analytics. Report turnaround dropped from 24-48 hours to under 30 seconds, with SQL generation accuracy at 89% F1 and document search relevance at NDCG@5 of 0.82.

Key capabilities include:
- Natural language to Snowflake SQL via Claude with few-shot prompting and a semantic business layer (15+ KPIs)
- Hybrid BM25 + vector search with Cohere reranking for document retrieval
- Three-layer RBAC (Clerk SSO, Supabase RLS, Snowflake view-level filtering)
- Async document ingestion and embedding via Trigger.dev and n8n workflows
- React Email notifications and multi-format report export (Excel, PDF, CSV)

---

## Current Architecture

### Tech Stack Summary

| Layer | Technology | Version (from requirements.txt / package.json) |
|---|---|---|
| Backend API | FastAPI + Uvicorn | fastapi==0.115.0, uvicorn==0.30.0 |
| Data Validation | Pydantic + Pydantic Settings | pydantic==2.10.0, pydantic-settings==2.6.0 |
| Data Warehouse | Snowflake | snowflake-connector-python==3.6.0, snowflake-sqlalchemy==1.5.0 |
| Vector DB | Supabase pgvector | supabase==2.1.0, pgvector==0.2.4 |
| ORM / Migrations | SQLAlchemy + Alembic | sqlalchemy==2.0.36, alembic==1.14.0 |
| Cache | Redis | redis==5.2.0, aioredis==2.0.1 |
| LLM (Text-to-SQL) | Claude API (Anthropic) | anthropic (imported, not pinned) |
| LLM (Fallback) | GPT-4 (OpenAI) | openai==1.3.10 |
| Embeddings | OpenAI text-embedding-3-small | 1536 dimensions |
| Reranking | Cohere Rerank v2.0 | cohere (imported, not pinned) |
| SQL Parsing | sqlglot | sqlglot==20.11.0 |
| Auth | Clerk JWT + PyJWT | PyJWT==2.8.1 |
| Async Jobs | Trigger.dev v3 | @trigger.dev/sdk ^3.0.0 |
| Workflows | n8n | Self-hosted |
| Frontend | Next.js + React (JSX) | React 18 (inferred) |
| Email | React Email + Resend | resend==0.3.1 |
| Deployment | Vercel (frontend) + Docker Compose (dev) | docker-compose 3.9 |
| Testing | pytest + Playwright | pytest==8.3.0, @playwright/test ^1.48.0 |
| Code Quality | ruff + mypy | ruff==0.8.0, mypy==1.13.0 |

### Key Components

1. **Query Router** (`src/query_engine/router.py`): Classifies queries into TEXT_TO_SQL, SEMANTIC_SEARCH, or HYBRID using Claude zero-shot classification. Checks Redis cache, routes to appropriate pipeline, caches results.

2. **Semantic Layer** (`src/query_engine/semantic_layer.py`): Defines 15 real estate KPIs (NOI, occupancy rate, cap rate, etc.) as `MetricDefinition` objects with canonical SQL expressions. Maintains an approved table whitelist and business term mappings.

3. **Prompts** (`src/query_engine/prompts.py`): Contains system prompts, intent extraction templates, SQL generation few-shot examples (8 examples), query classification prompts, and result formatting prompts -- all tuned for Snowflake dialect.

4. **Document Processor** (`src/rag/document_processor.py`): Handles PDF extraction (Docling), OCR fallback (Azure Document Intelligence), and semantic chunking by document type (clause-level for leases, section-level for reports, paragraph-level default).

5. **Embedder** (`src/rag/embedder.py`): Wraps OpenAI text-embedding-3-small with batch processing, rate limiting (3000 tokens/min), and retry logic.

6. **Retriever** (`src/rag/retriever.py`): Three-stage hybrid search pipeline -- parallel BM25 + vector search, Reciprocal Rank Fusion merge, Cohere reranking.

7. **LLM Augmentation** (`src/rag/llm_augmentation.py`): Synthesizes answers from retrieved chunks using Claude, extracts citations via regex, and generates follow-up questions.

8. **RBAC** (`src/access_control/rbac.py`): Five roles (Admin, Property Manager, Broker, Finance, Executive) with a permission matrix covering resource access, property scope, and column masking.

9. **Snowflake Connector** (`src/connectors/snowflake_connector.py`): Connection management with context managers, tenant-aware query execution, and audit logging.

10. **Supabase Schema** (`supabase/migrations/001_schema.sql`): Six tables (users, documents, document_chunks, query_history, saved_queries, access_logs, notifications) with RLS policies, HNSW vector indexes, and GIN text search indexes.

### Architecture Gaps Identified

- The `embedder.py` uses `text-embedding-3-small` (1536-dim) but the Supabase schema defines `VECTOR(3072)` for `text-embedding-3-large` -- a dimensional mismatch.
- The `openai` Python package is pinned at `1.3.10` which is quite old (December 2023). Current versions are past 1.50+.
- The `anthropic` and `cohere` packages are imported but not pinned in `requirements.txt`, risking breaking changes.
- The `aioredis` package (`2.0.1`) is deprecated and merged into `redis-py` (which is already present as `redis==5.2.0`).
- `router.py` uses synchronous Anthropic and Redis calls inside what is presumably an async FastAPI app -- blocking the event loop.
- The rate limit middleware in `main.py` uses `request.state.get()` which will raise `AttributeError` since `State` does not have a `.get()` method.
- SQL injection risk in `snowflake_connector.py:execute_with_tenant_filter()` -- tenant_id and properties are string-interpolated into SQL rather than parameterized.
- The `document_processor.py` imports `re` at the bottom of the file (line 517), after functions that reference it.
- No streaming support for LLM responses -- users must wait for full completion.

---

## Recommended Improvements

### 1. Fix the Embedding Dimension Mismatch

**File:** `src/rag/embedder.py` (lines 30-31) and `supabase/migrations/001_schema.sql` (line 144)

The embedder uses `text-embedding-3-small` at 1536 dimensions, but the database schema declares `VECTOR(3072)` for `text-embedding-3-large`. This will cause insertion failures.

**Fix:** Either upgrade the embedder to use `text-embedding-3-large` (better retrieval quality, higher cost) or change the schema to `VECTOR(1536)`. Given the README states `text-embedding-3-large (3072-dim)` is the intended model:

```python
# src/rag/embedder.py
EMBEDDING_MODEL = "text-embedding-3-large"  # was: text-embedding-3-small
EMBEDDING_DIMENSIONS = 3072                  # was: 1536
```

### 2. Make LLM Calls Async Throughout

**Files:** `src/query_engine/router.py`, `src/rag/llm_augmentation.py`, `src/rag/retriever.py`

All Claude and OpenAI API calls are synchronous, which blocks the FastAPI event loop. Convert to async using the async clients:

```python
# router.py - use async Anthropic client
from anthropic import AsyncAnthropic

client = AsyncAnthropic()
message = await client.messages.create(...)
```

```python
# embedder.py - use async OpenAI client
from openai import AsyncOpenAI

client = AsyncOpenAI()
response = await client.embeddings.create(...)
```

This also enables concurrent BM25 + vector search in the retriever using `asyncio.gather()`:

```python
# retriever.py
bm25_results, vector_results = await asyncio.gather(
    bm25_search(query, tenant_id),
    vector_search(query, tenant_id),
)
```

### 3. Eliminate SQL Injection Vulnerability

**File:** `src/connectors/snowflake_connector.py` (lines 212-220)

The `execute_with_tenant_filter()` method uses string interpolation for `tenant_id` and `property_id` values, creating a SQL injection risk:

```python
# VULNERABLE - current code
sql = sql.replace("WHERE", f"WHERE tenant_id = '{tenant_id}' AND")
```

**Fix:** Use parameterized queries:

```python
def execute_with_tenant_filter(self, sql, tenant_id, role, properties=None):
    params = {"tenant_id": tenant_id}
    if "WHERE" in sql.upper():
        sql = sql.replace("WHERE", "WHERE tenant_id = %(tenant_id)s AND", 1)
    else:
        sql = f"{sql} WHERE tenant_id = %(tenant_id)s"

    if properties:
        sql += " AND property_id IN (%(props)s)"
        params["props"] = tuple(properties)

    return self.execute_query(sql, params)
```

### 4. Add LLM Response Streaming

**Files:** `src/api/endpoints/queries.py`, `src/rag/llm_augmentation.py`

For queries that involve RAG answer synthesis, users currently wait for the entire response. Add streaming via FastAPI's `StreamingResponse` and Anthropic's streaming API:

```python
from fastapi.responses import StreamingResponse

async def stream_answer(query, chunks, user_context):
    client = AsyncAnthropic()
    async with client.messages.stream(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        async for text in stream.text_stream:
            yield f"data: {json.dumps({'text': text})}\n\n"
    yield "data: [DONE]\n\n"
```

### 5. Upgrade to Structured Outputs for SQL Generation

**File:** `src/query_engine/router.py` (lines 296-336)

Replace JSON string parsing for query classification with Claude's tool use or structured output feature for guaranteed schema compliance:

```python
import anthropic

client = anthropic.Anthropic()

tools = [{
    "name": "classify_query",
    "description": "Classify a real estate query",
    "input_schema": {
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": ["text_to_sql", "semantic_search", "hybrid"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "reasoning": {"type": "string"},
        },
        "required": ["type", "confidence", "reasoning"],
    },
}]

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=300,
    tools=tools,
    tool_choice={"type": "tool", "name": "classify_query"},
    messages=[{"role": "user", "content": query}],
)
```

This eliminates the `json.JSONDecodeError` fallback path and ensures type-safe outputs.

### 6. Remove Deprecated aioredis Dependency

**File:** `requirements.txt` (line 19)

`aioredis==2.0.1` is deprecated and has been merged into `redis-py`. The project already has `redis==5.2.0` which includes `redis.asyncio`. Remove `aioredis` from requirements.txt -- the app already uses `redis.asyncio` in `main.py`.

### 7. Fix Rate Limiting Middleware Bug

**File:** `src/api/main.py` (lines 246-248)

```python
# BUG: State object doesn't have .get() method
user_id = request.state.get("user_id", "anonymous")  # AttributeError
```

**Fix:**
```python
user_id = getattr(request.state, "user_id", "anonymous")
is_premium = getattr(request.state, "is_premium", False)
```

### 8. Implement Proper Snowflake Connection Pooling

**File:** `src/connectors/snowflake_connector.py`

The current implementation creates a new connection per query via context managers. Add connection pooling using SQLAlchemy's pool:

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    f"snowflake://{user}:{password}@{account}/{database}/{schema}",
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,
)
```

### 9. Add Query Feedback Loop for Continuous Improvement

**Files:** `src/api/endpoints/queries.py`, `supabase/migrations/001_schema.sql`

The `query_history` table already has `feedback_rating` and `feedback_comment` columns. Wire these into the API:

```python
@router.post("/{query_id}/feedback")
async def submit_feedback(
    query_id: str,
    rating: int = Field(ge=1, le=5),
    comment: Optional[str] = None,
    user: UserContext = Depends(get_current_user),
):
    # Store feedback, use for few-shot example curation
    # High-rated queries become candidates for prompt examples
    ...
```

Use feedback data to:
- Curate few-shot examples (promote high-rated query/SQL pairs)
- Detect low-performing query patterns
- Build an evaluation dataset from production usage

### 10. Add Observability with OpenTelemetry

**Files:** `src/api/main.py`, `src/core/config.py`

The current logging is basic `logging.basicConfig`. Add structured observability:

```python
# requirements.txt additions
opentelemetry-api==1.27.0
opentelemetry-sdk==1.27.0
opentelemetry-instrumentation-fastapi==0.48b0
opentelemetry-exporter-otlp==1.27.0
```

Instrument LLM calls, Snowflake queries, and vector search with spans:

```python
from opentelemetry import trace
tracer = trace.get_tracer("portfolio-intelligence-hub")

with tracer.start_as_current_span("text_to_sql.generate") as span:
    span.set_attribute("query.text", query[:100])
    span.set_attribute("query.tenant_id", tenant_id)
    result = await generate_sql(...)
    span.set_attribute("query.execution_ms", result.execution_time_ms)
```

### 11. Add Guardrails for Generated SQL

**File:** `src/query_engine/prompts.py`, new file `src/query_engine/sql_validator.py`

Currently, the generated SQL is not validated before execution beyond the approved tables list. Add a SQL validation layer using `sqlglot` (already a dependency):

```python
import sqlglot

def validate_generated_sql(sql: str, approved_tables: list[str]) -> tuple[bool, str]:
    try:
        parsed = sqlglot.parse_one(sql, dialect="snowflake")

        # Check all referenced tables are approved
        tables = [t.name for t in parsed.find_all(sqlglot.exp.Table)]
        unauthorized = [t for t in tables if t.lower() not in approved_tables]
        if unauthorized:
            return False, f"Unauthorized tables: {unauthorized}"

        # Block dangerous operations
        if parsed.find(sqlglot.exp.Drop, sqlglot.exp.Delete, sqlglot.exp.Update):
            return False, "DML/DDL operations not allowed"

        # Verify tenant_id filter exists
        where = parsed.find(sqlglot.exp.Where)
        if not where or "tenant_id" not in str(where):
            return False, "Missing tenant_id filter"

        return True, "Valid"
    except sqlglot.errors.ParseError as e:
        return False, f"SQL parse error: {e}"
```

### 12. Implement Document Type-Specific Embedding Models

**File:** `src/rag/embedder.py`

Legal documents (leases) and operational documents (inspection reports) have very different vocabularies. Consider using domain-specific embedding approaches:

- Use `text-embedding-3-large` with `dimensions` parameter to optimize cost/quality tradeoff per document type
- Add a title/description prefix to chunks before embedding for improved retrieval:

```python
def prepare_chunk_for_embedding(chunk_text: str, doc_type: str, section: str) -> str:
    prefix = f"Document type: {doc_type}. Section: {section}. "
    return prefix + chunk_text
```

---

## New Technologies & Trends

### 1. Claude's Native Citations API

Anthropic introduced a citations feature for Claude that returns source attributions directly in the API response, eliminating the need for the regex-based citation extraction in `src/rag/llm_augmentation.py` (lines 105-159). The feature works by passing source documents as content blocks and receiving back citations that point to exact character ranges in the source material.

**Why:** The current `extract_citations()` function uses brittle regex patterns (`page|pg\s*(\d+)`) to find page references. Claude's native citations provide exact character-range mappings back to source documents, with no regex needed.

**How:** Replace the current `generate_answer()` function with one that uses Claude's document content blocks:

```python
message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1000,
    messages=[{
        "role": "user",
        "content": [
            {"type": "document", "source": {"type": "text", "data": chunk.chunk_text},
             "title": f"{chunk.doc_id} - {chunk.section}"}
            for chunk in retrieved_chunks
        ] + [{"type": "text", "text": f"Answer this question: {query}"}]
    }]
)
# Citations are returned automatically in the response content blocks
```

**Reference:** https://docs.anthropic.com/en/docs/build-with-claude/citations

### 2. Vanna AI for Text-to-SQL Training

Vanna (https://github.com/vanna-ai/vanna) is an open-source Python framework purpose-built for text-to-SQL that learns from your data. Instead of hand-crafting few-shot examples in prompts, Vanna builds a RAG-based training set from DDL statements, documentation, and validated SQL queries.

**Why:** The current `prompts.py` has 8 hand-coded few-shot examples. As the query corpus grows, maintaining these manually becomes untenable. Vanna auto-selects the most relevant examples for each query using its own vector store.

**How:** Integrate Vanna alongside the existing semantic layer:

```python
import vanna
from vanna.openai import OpenAI_Chat
from vanna.chromadb import ChromaDB_VectorStore

class PortfolioVanna(ChromaDB_VectorStore, OpenAI_Chat):
    def __init__(self):
        ChromaDB_VectorStore.__init__(self)
        OpenAI_Chat.__init__(self, model="gpt-4o")

vn = PortfolioVanna()
vn.train(ddl="CREATE TABLE properties ...")
vn.train(sql="SELECT ... -- occupancy by region")
vn.train(documentation="NOI = Gross Income - Operating Expenses")

# At query time
sql = vn.generate_sql("What is the occupancy rate by city?")
```

**Reference:** https://github.com/vanna-ai/vanna (MIT license, 12k+ GitHub stars)

### 3. pgvector 0.8+ with Improved HNSW and IVFFlat

pgvector has continued rapid development. Version 0.7+ introduced parallel index builds for HNSW, significantly reducing index build time. Version 0.8 added support for halfvec (float16 vectors) which halves storage and improves cache efficiency. The project also supports quantized binary vectors for ultra-fast approximate search.

**Why:** The project uses `pgvector==0.2.4` (very old). Upgrading brings:
- 2-4x faster HNSW index builds via parallel construction
- `halfvec` type for 50% storage reduction with minimal recall loss
- Improved query planning for filtered vector searches
- Better distance function performance

**How:**
```sql
-- Use halfvec for 50% storage savings
ALTER TABLE document_chunks
ALTER COLUMN embedding TYPE halfvec(3072);

-- Rebuild HNSW index with parallel workers
CREATE INDEX CONCURRENTLY idx_chunks_embedding
ON document_chunks USING hnsw (embedding halfvec_cosine_ops)
WITH (m = 16, ef_construction = 200);
```

```
# requirements.txt
pgvector>=0.3.6
```

**Reference:** https://github.com/pgvector/pgvector

### 4. Cohere Rerank 3.5 (Latest Model)

Cohere released Rerank 3.5 which significantly improves multilingual and long-document reranking performance. The current codebase uses `rerank-english-v2.0` which is two generations behind.

**Why:** Rerank 3.5 delivers 10-15% better NDCG over v2.0 on domain-specific benchmarks, handles longer documents (up to 4096 tokens per document vs 512), and supports structured data fields for metadata-aware reranking.

**How:** Update `src/rag/retriever.py` line 282:

```python
response = co.rerank(
    model="rerank-v3.5",  # was: rerank-english-v2.0
    query=query,
    documents=documents,
    top_n=top_k,
    max_chunks_per_doc=10,  # new: handles longer documents
)
```

**Reference:** https://docs.cohere.com/docs/rerank-2

### 5. LangSmith / Langfuse for LLM Observability

LLM-specific observability tools have matured significantly. Langfuse (open-source, self-hostable) and LangSmith provide:
- Trace every LLM call with inputs, outputs, latency, cost
- Evaluation datasets from production traces
- A/B testing of prompt variants
- Cost tracking per tenant/user

**Why:** The current system has basic Python logging. There is no way to trace an end-to-end query from classification through SQL generation through result formatting, or to track per-tenant LLM costs.

**How:**

```python
# Using Langfuse (self-hostable, data sovereignty friendly)
from langfuse.decorators import observe, langfuse_context

@observe(name="query_classification")
def classify_query(query: str) -> tuple[QueryType, float]:
    langfuse_context.update_current_observation(
        metadata={"query_length": len(query)},
    )
    # ... existing classification logic
```

```
# requirements.txt
langfuse>=2.40.0
```

**Reference:** https://langfuse.com (MIT license), https://smith.langchain.com

### 6. Anthropic Claude Opus 4 and Sonnet 4 Models

The project currently uses `claude-3-5-sonnet-20241022`. Anthropic has since released Claude Sonnet 4 (`claude-sonnet-4-20250514`) and Claude Opus 4 (`claude-opus-4-20250514`) with significant improvements in coding, structured output, and instruction following.

**Why:** Claude Sonnet 4 provides better structured JSON output (reducing classification parse failures), improved SQL generation accuracy, and extended thinking for complex multi-table joins. It also supports native tool use which is more reliable than JSON-in-text parsing.

**How:** Update model references across the codebase:

```python
# src/query_engine/router.py line 318
model="claude-sonnet-4-20250514"  # was: claude-3-5-sonnet-20241022

# src/rag/llm_augmentation.py line 298
model="claude-sonnet-4-20250514"  # was: claude-3-5-sonnet-20241022
```

**Reference:** https://docs.anthropic.com/en/docs/about-claude/models

### 7. Late Chunking / Contextual Retrieval

Traditional chunking loses context about where a chunk fits in the overall document. Anthropic published research on "Contextual Retrieval" where each chunk is prepended with a short LLM-generated context summary before embedding. This improves retrieval accuracy by 49% when combined with BM25 hybrid search.

**Why:** The current `document_processor.py` chunks documents at semantic boundaries but each chunk is embedded in isolation. A chunk like "The tenant shall comply with the above" loses meaning without its parent section context.

**How:** Add a context generation step after chunking:

```python
async def add_chunk_context(chunk: DocumentChunk, full_doc_text: str) -> str:
    """Generate contextual prefix for each chunk before embedding."""
    client = AsyncAnthropic()
    message = await client.messages.create(
        model="claude-haiku-4-20250514",
        max_tokens=100,
        messages=[{
            "role": "user",
            "content": f"""<document>{full_doc_text[:10000]}</document>
            Here is a chunk: <chunk>{chunk.chunk_text}</chunk>
            Write a short (1-2 sentence) context for this chunk within the document."""
        }]
    )
    context = message.content[0].text
    return f"{context}\n\n{chunk.chunk_text}"
```

**Reference:** https://www.anthropic.com/news/contextual-retrieval

### 8. MCP (Model Context Protocol) for Tool Integration

Anthropic's Model Context Protocol (MCP) provides a standardized way for LLMs to interact with external data sources and tools. Instead of manually building Snowflake connectors and document search functions, an MCP server can expose these as standardized tools.

**Why:** The current architecture hard-codes integrations in Python. MCP would allow the LLM to dynamically discover and use data sources, making the system more extensible for new data sources (e.g., adding a property management system API).

**How:** Create an MCP server that exposes Snowflake query execution and document search as tools:

```python
from mcp.server import Server
from mcp.types import Tool

server = Server("portfolio-intelligence-hub")

@server.tool()
async def query_snowflake(sql: str, tenant_id: str) -> list[dict]:
    """Execute a validated SQL query against the portfolio database."""
    ...

@server.tool()
async def search_documents(query: str, tenant_id: str, top_k: int = 5) -> list[dict]:
    """Search property documents using semantic similarity."""
    ...
```

**Reference:** https://modelcontextprotocol.io

### 9. OpenAI text-embedding-3-large with Matryoshka Dimensionality

OpenAI's `text-embedding-3-large` supports Matryoshka Representation Learning (MRL), allowing you to truncate embedding vectors to smaller dimensions (256, 512, 1024) while retaining most retrieval quality. This enables a cost/quality tradeoff at query time.

**Why:** The project currently uses a fixed 1536 or 3072 dimension. With MRL, you can use 256-dim vectors for fast initial retrieval (cheaper storage, faster HNSW search) and full 3072-dim for reranking candidates.

**How:** Two-stage retrieval with dimension reduction:

```python
# Stage 1: Fast retrieval with 256-dim vectors
response = client.embeddings.create(
    model="text-embedding-3-large",
    input=query,
    dimensions=256,  # Matryoshka truncation
)

# Stage 2: Rerank candidates with full 3072-dim
response = client.embeddings.create(
    model="text-embedding-3-large",
    input=query,
    dimensions=3072,
)
```

**Reference:** https://platform.openai.com/docs/guides/embeddings

### 10. Docling 2.x for Advanced Document Parsing

The `document_processor.py` mentions Docling for PDF extraction but uses a placeholder implementation. Docling v2 (by IBM, open-source) now supports:
- Deep learning-based layout analysis
- Table structure recognition with cell-level extraction
- Figure detection and caption extraction
- Multi-format output (Markdown, JSON, DocTR)

**Why:** Real estate documents (leases, appraisals) contain complex tables (rent schedules, financial summaries) that standard PDF extraction misses. Docling 2 preserves table structure, which is critical for accurate chunking and retrieval.

**How:**
```python
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("lease.pdf")
markdown = result.document.export_to_markdown()
# Tables are preserved as markdown tables
# Sections are properly delineated
```

```
# requirements.txt
docling>=2.5.0
```

**Reference:** https://github.com/DS4SD/docling (MIT license)

### 11. Semantic Caching with LLM-Aware Cache Keys

The current Redis caching uses exact hash matching of `query + tenant_id + properties`. Two semantically identical queries with different wording ("occupancy rate" vs "what percent of units are occupied") generate different cache keys and bypass the cache.

**Why:** Could save 30-40% of LLM API calls by recognizing semantically equivalent queries.

**How:** Use embedding similarity for cache lookup:

```python
async def get_semantic_cache(query: str, user_context: UserContext, threshold=0.95):
    query_embedding = await embed_text(query)
    # Search recent cached queries by vector similarity
    cached = await supabase.rpc("match_cached_queries", {
        "query_embedding": query_embedding,
        "p_tenant_id": user_context.tenant_id,
        "similarity_threshold": threshold,
    })
    if cached:
        return cached[0]["result"]
    return None
```

**Reference:** https://github.com/zilliztech/GPTCache

### 12. Evaluation Framework with RAGAS

The project mentions F1 and NDCG metrics but lacks an automated evaluation pipeline. RAGAS (Retrieval Augmented Generation Assessment) provides standardized metrics for RAG systems:
- **Faithfulness**: Are answers grounded in retrieved context?
- **Answer Relevancy**: Does the answer address the question?
- **Context Precision**: Are retrieved documents relevant?
- **Context Recall**: Are all relevant documents retrieved?

**How:**
```python
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision

result = evaluate(
    dataset=eval_dataset,  # Built from query_history feedback
    metrics=[faithfulness, answer_relevancy, context_precision],
)
```

```
# requirements.txt
ragas>=0.1.10
```

**Reference:** https://github.com/explodinggradients/ragas

---

## Priority Roadmap

### P0 -- Critical (Fix in Sprint 1, Week 1-2)

| # | Item | Effort | Impact | Files |
|---|---|---|---|---|
| 1 | **Fix embedding dimension mismatch** (1536 vs 3072) | 1 hour | Blocks document search entirely | `src/rag/embedder.py`, `supabase/migrations/001_schema.sql` |
| 2 | **Fix SQL injection in tenant filtering** | 2 hours | Security vulnerability | `src/connectors/snowflake_connector.py` |
| 3 | **Fix rate limit middleware bug** (`request.state.get()`) | 30 min | Runtime crash on auth'd requests | `src/api/main.py` |
| 4 | **Remove deprecated aioredis** | 15 min | Deprecation warnings, potential conflicts | `requirements.txt` |
| 5 | **Pin anthropic and cohere packages** in requirements.txt | 15 min | Prevents breaking changes on deploy | `requirements.txt` |
| 6 | **Fix import ordering** (`re` imported at EOF) | 15 min | Potential NameError in production | `src/rag/document_processor.py` |

### P1 -- High Priority (Weeks 2-4)

| # | Item | Effort | Impact | Files |
|---|---|---|---|---|
| 7 | **Make all LLM calls async** | 1 day | Unblocks FastAPI event loop; 2-5x throughput | `router.py`, `llm_augmentation.py`, `embedder.py`, `retriever.py` |
| 8 | **Add SQL validation guardrails** with sqlglot | 1 day | Prevents dangerous/invalid SQL execution | New: `src/query_engine/sql_validator.py` |
| 9 | **Upgrade to Claude Sonnet 4** | 2 hours | Better SQL gen, structured output, tool use | `router.py`, `llm_augmentation.py`, `prompts.py` |
| 10 | **Upgrade Cohere Rerank to v3.5** | 1 hour | 10-15% NDCG improvement | `src/rag/retriever.py` |
| 11 | **Upgrade pgvector to 0.3.6+** | 2 hours | Faster indexes, halfvec support | `requirements.txt`, `supabase/migrations/` |
| 12 | **Use structured outputs (tool_use) for classification** | 3 hours | Eliminates JSON parse failures | `src/query_engine/router.py` |
| 13 | **Implement proper Snowflake connection pooling** | 3 hours | Reduces connection overhead | `src/connectors/snowflake_connector.py` |

### P2 -- Medium Priority (Weeks 4-8)

| # | Item | Effort | Impact | Files |
|---|---|---|---|---|
| 14 | **Add LLM response streaming** (SSE) | 2 days | Better UX, perceived latency reduction | `queries.py`, `llm_augmentation.py`, `query_interface.jsx` |
| 15 | **Implement Claude native citations** | 1 day | Accurate source attribution, remove regex | `src/rag/llm_augmentation.py` |
| 16 | **Add contextual retrieval** (chunk context prepending) | 2 days | Up to 49% retrieval improvement | `src/rag/document_processor.py`, `src/rag/embedder.py` |
| 17 | **Integrate Langfuse for LLM observability** | 1 day | End-to-end tracing, cost tracking | `main.py`, `router.py`, `llm_augmentation.py` |
| 18 | **Wire up query feedback API** | 1 day | Continuous improvement, eval dataset | `src/api/endpoints/queries.py` |
| 19 | **Implement semantic caching** | 2 days | 30-40% LLM cost reduction | `src/query_engine/router.py`, new Supabase function |
| 20 | **Upgrade OpenAI package** from 1.3.10 to 1.50+ | 2 hours | Access to latest API features, bug fixes | `requirements.txt` |
| 21 | **Add OpenTelemetry instrumentation** | 1 day | Distributed tracing across services | `main.py`, new: `src/core/telemetry.py` |
| 22 | **Implement Docling 2.x** for real PDF extraction | 2 days | Production-ready document parsing | `src/rag/document_processor.py` |

### P3 -- Future Enhancements (Weeks 8-16+)

| # | Item | Effort | Impact | Files |
|---|---|---|---|---|
| 23 | **Evaluate Vanna AI** for text-to-SQL training | 3 days | Auto-curated few-shot examples, higher accuracy | New module, `src/query_engine/` |
| 24 | **Implement MCP server** for tool-based data access | 3 days | Extensible architecture for new data sources | New: `mcp/server.py` |
| 25 | **Add RAGAS evaluation pipeline** | 2 days | Automated RAG quality measurement | New: `evals/ragas_eval.py` |
| 26 | **Matryoshka embedding** two-stage retrieval | 2 days | Faster initial retrieval, lower storage cost | `src/rag/embedder.py`, `src/rag/retriever.py` |
| 27 | **Multi-modal document understanding** (charts/floor plans) | 5 days | Extract data from visual content in reports | `src/rag/document_processor.py` |
| 28 | **Agentic query refinement** with iterative SQL correction | 3 days | Self-healing SQL generation on errors | `src/query_engine/router.py` |
| 29 | **Fine-tune embedding model** on real estate corpus | 5 days | Domain-specific retrieval improvements | `src/rag/embedder.py` |
| 30 | **Add conversation memory** for multi-turn queries | 2 days | "Show me the same thing but for Q2" | `src/query_engine/router.py`, `src/api/endpoints/queries.py` |
| 31 | **GraphRAG** for entity relationship queries | 5 days | "Which tenants are connected to late-paying properties?" | New module |
| 32 | **Implement real-time materialized view refresh** via Snowflake Streams | 3 days | Near-real-time KPI updates instead of nightly batch | `snowflake/`, `trigger-jobs/` |

---

## Summary

The Portfolio Intelligence Hub has a solid architectural foundation. The most impactful near-term improvements are:

1. **Fix the six P0 bugs** (security, correctness, and crashes) -- estimated 4 hours total
2. **Make LLM calls async** to unlock FastAPI's concurrency model -- 1 day
3. **Upgrade to latest model versions** (Claude Sonnet 4, Cohere Rerank 3.5, pgvector 0.3.6+) -- immediate quality improvements with minimal code changes
4. **Add SQL validation guardrails** using the already-installed sqlglot -- prevents the most dangerous failure mode (executing bad SQL)
5. **Implement Claude native citations** to replace fragile regex-based citation extraction -- better accuracy with less code

The longer-term investments in contextual retrieval, semantic caching, LLM observability, and Vanna-based text-to-SQL training would collectively push SQL accuracy toward 95%+ F1 and document retrieval toward 0.90+ NDCG@5, while significantly reducing per-query LLM costs.
