# Architecture Decision Records

This document captures the key architectural decisions made for Portfolio Intelligence Hub, a RAG-powered natural language analytics platform for real estate portfolios. Each ADR explains the context, decision, alternatives considered, and trade-offs.

---

## ADR-001: LLM-Generated SQL via Semantic Layer (Text-to-SQL Approach)

**Status:** Accepted
**Date:** 2024-02
**Context:** Real estate operators need instant access to structured metrics (occupancy, NOI, collections, maintenance costs) without knowing SQL. The system must convert natural language questions like "Which buildings have the most open work orders?" into valid Snowflake SQL. Two core challenges exist: (1) ensuring metric consistency so that "occupancy rate" always uses the same formula regardless of who asks, and (2) preventing the LLM from generating unsafe or incorrect SQL.
**Decision:** Use a 5-step pipeline: (1) parse intent via Claude, (2) map to approved tables through a semantic business layer (`semantic_layer.py`) with 15+ pre-defined metric definitions (`MetricDefinition` dataclass), (3) generate SQL via Claude with few-shot prompting and full schema injection (`prompts.py`), (4) validate via sqlglot AST parsing (`validate_sql` in `text_to_sql.py`), (5) execute on Snowflake with injected tenant filtering. The semantic layer (`METRIC_REGISTRY`) defines canonical SQL expressions for each KPI (NOI, occupancy rate, cap rate, collections rate, budget variance, etc.) and maps business terminology to database columns via `resolve_business_term()`.
**Alternatives Considered:**
- **Direct prompt-to-SQL** (no semantic layer): Faster to ship, but two users asking "what's the occupancy rate?" could get different SQL depending on LLM interpretation. Rejected because metric inconsistency destroys trust in analytics tools.
- **LangChain SQL agent**: Would manage LLM interactions automatically, but provides less control over SQL validation and tenant filtering injection. The real estate domain requires precise metric definitions that a generic agent cannot enforce.
- **Fine-tuned model on historical queries**: Would require maintaining a training dataset and retraining on schema changes. Too expensive for a mid-market operator with evolving schema.
**Consequences:** The semantic layer added approximately 3 weeks to Phase 2 development but eliminated the "why do these numbers not match?" problem. Every query for a given metric uses the same SQL expression. The approved table whitelist (`APPROVED_TABLES` in `semantic_layer.py`) constrains what the LLM can reference, and the `validate_sql()` function uses sqlglot AST parsing to enforce this at the syntax tree level rather than relying solely on regex. The trade-off is that new metrics require explicit registration in `METRIC_REGISTRY` rather than being inferred automatically.

---

## ADR-002: SQL Validation via sqlglot AST Parsing

**Status:** Accepted
**Date:** 2024-03
**Context:** LLM-generated SQL poses inherent security risks. The system must prevent SQL injection, data exfiltration (e.g., UNION attacks to read unauthorized tables), destructive operations (DROP, DELETE, TRUNCATE), and multi-statement attacks. Regex-based pattern matching alone is insufficient because attackers can bypass it with SQL comments, backticks, inline comment obfuscation (`DR/**/OP`), and quoted identifier tricks.
**Decision:** Implement a two-layer validation strategy in `validate_sql()` (`text_to_sql.py`). Layer 1 is a fast regex pre-check against `DANGEROUS_PATTERNS` (12 patterns covering DROP, DELETE, TRUNCATE, ALTER, CREATE, GRANT, REVOKE, INSERT, UPDATE, EXEC). Layer 2 parses the SQL into an AST using `sqlglot.parse(sql, dialect="snowflake")` and performs structural validation: only single statements allowed, only `exp.Select` statement types accepted, all `exp.Table` references checked against `APPROVED_TABLES`, and subqueries recursively validated. A mandatory `TENANT_ID` filter check ensures tenant isolation is present.
**Alternatives Considered:**
- **Regex-only validation**: Simpler but fundamentally bypassable. The test suite (`test_text_to_sql.py`, `TestSQLInjectionBypass` class) demonstrates 8 specific attack vectors that regex alone would miss, including comment-hidden DROP, inline comment obfuscation, CTE-based unauthorized table access, and UNION-based data exfiltration.
- **Snowflake query tagging and role-based restrictions**: Would push validation to the database layer. Rejected because errors at the database level are harder to surface as user-friendly messages, and the application loses the ability to inspect and explain the query before execution.
- **Query plan analysis**: Would validate against the actual execution plan from Snowflake. Too slow for real-time use (adds 500ms+ per query) and requires an active connection just for validation.
**Consequences:** AST-based validation provides structural guarantees that regex cannot. Adding sqlglot as a dependency is lightweight (pure Python). The Snowflake dialect mode ensures Snowflake-specific syntax (DATEDIFF, DATEADD, DATE_TRUNC) parses correctly. The downside is that sqlglot may lag behind new Snowflake syntax additions. The parameterized tenant filtering in `build_tenant_filter()` (`rbac.py`) uses `%s` placeholders rather than string interpolation, providing defense-in-depth at the execution layer.

---

## ADR-003: Hybrid RAG Search (BM25 + Vector + Cohere Rerank)

**Status:** Accepted
**Date:** 2024-03
**Context:** Property documents (leases, inspection reports, maintenance logs) contain critical unstructured information that must be searchable. Users ask questions like "What are the maintenance obligations for Unit 204?" where keyword matching alone misses semantic equivalents ("repair responsibilities") and vector search alone misses exact terms ("Unit 204"). The system needs to handle 200+ documents across 87 properties with retrieval quality above NDCG@5 of 0.82.
**Decision:** Implement a three-stage retrieval pipeline in `retriever.py`: (1) parallel BM25 keyword search on PostgreSQL `tsvector` indexes and vector cosine similarity search on pgvector HNSW indexes, (2) merge results using Reciprocal Rank Fusion (RRF) with k=60, (3) rerank the merged candidates using Cohere's cross-encoder reranker (`rerank-english-v2.0`). Documents are chunked at semantic boundaries in `document_processor.py`: clause-level for leases (12 standard sections including payment terms, tenant obligations, renewal options) and section-level for reports. Embeddings use OpenAI `text-embedding-3-small` at 1536 dimensions with batch processing and rate limiting (`embedder.py`).
**Alternatives Considered:**
- **Vector search only**: Simpler architecture, but misses exact-match queries common in real estate ("Unit 204", "Section 8", specific dollar amounts). Vector search alone measured 15-20% lower NDCG than hybrid.
- **BM25 only**: Fast and precise for keyword queries but fails on semantic queries like "repair obligations" when the document says "maintenance responsibilities."
- **No reranking**: Saves ~200ms per query and eliminates the Cohere dependency. Rejected because reranking consistently improved NDCG@5 by 15-20% over raw RRF scores, which is critical for trust when surfacing legal document clauses.
- **Pinecone or Weaviate** (dedicated vector database): Higher query performance at scale, but would require syncing document metadata and tenant isolation separately. pgvector in Supabase keeps vectors and RLS policies in the same database.
**Consequences:** The hybrid approach delivers the best retrieval quality at the cost of higher latency (~400ms total: 50ms BM25 + 100ms vector + 10ms merge + 200ms rerank). The Cohere dependency adds a third-party API call and associated cost ($0.10 per 1000 searches). Semantic chunking preserves legal context in lease clauses, making source attribution precise -- users see the exact clause, not a fragment split mid-sentence.

---

## ADR-004: Three-Layer Tenant Isolation (Clerk JWT + Supabase RLS + Snowflake Views)

**Status:** Accepted
**Date:** 2024-02
**Context:** The platform serves multiple real estate operators (tenants) from a single deployment. A data breach exposing one tenant's financial data to another would be catastrophic. Within each tenant, different personas (property managers, brokers, finance, executives) need different data scopes -- property managers see only assigned buildings, brokers cannot see rent amounts, finance cannot see employee salaries. The system must enforce isolation at every layer so that even a SQL injection bypass at one layer cannot leak cross-tenant data.
**Decision:** Implement defense-in-depth with three enforcement layers:
- **Layer 1 - Application (Clerk JWT)**: Authentication via Clerk with RS256 JWT verification (`auth.py`). The `UserContext` dataclass carries `tenant_id`, `role`, and `assigned_properties` extracted from JWT claims. FastAPI dependencies (`get_current_user`, `require_role`, `require_property_access`) enforce access at the API boundary.
- **Layer 2 - App Database (Supabase RLS)**: Row Level Security policies on all 7 tables (`001_schema.sql`). Every policy filters by `tenant_id = auth.jwt()->'claims'->>'tenant_id'`. Document chunks inherit tenant isolation through a JOIN to the documents table. Even direct database access cannot read cross-tenant data.
- **Layer 3 - Data Warehouse (Snowflake Views)**: Role-specific views generated by `snowflake_views.py` (e.g., `properties_for_pm`, `units_for_brokers`, `financials_for_finance`). Column masking NULLs out sensitive fields (tenant names for brokers, acquisition prices for property managers). Executives get only aggregated views (`portfolio_summary`, `regional_performance`).
**Alternatives Considered:**
- **Physical isolation (separate Snowflake database per tenant)**: Strongest isolation guarantee but dramatically increases operational overhead and cost. At mid-market scale (tens of tenants, not thousands), logical isolation with defense-in-depth is sufficient.
- **Application-layer only isolation**: Simpler to implement but a single bug in tenant filtering code could leak data. RLS and Snowflake views provide database-level guardrails that catch application-layer failures.
- **Snowflake Row Access Policies (RAP)**: Noted in `main.py` docstring as a production enhancement. RAP would provide the strongest Snowflake-side guarantee but requires managing Snowflake roles per user, adding operational complexity.
**Consequences:** Three-layer isolation means tenant filtering must be maintained in three places, increasing development overhead when adding new tables or roles. The `ROLE_PERMISSIONS` matrix in `rbac.py` and `generate_view_ddl()` in `snowflake_views.py` must stay synchronized with the Supabase RLS policies. The benefit is that a compromise at any single layer does not leak cross-tenant data. Column masking at the Snowflake view level means even if the API were bypassed, the database itself enforces data restrictions.

---

## ADR-005: Redis Caching with Tenant-Scoped Keys

**Status:** Accepted
**Date:** 2024-03
**Context:** Common portfolio queries like "What's our occupancy rate?" are asked daily by multiple users within the same tenant. Each query execution involves an LLM call for classification (~500ms), another for SQL generation (~1000ms), and a Snowflake query (~500ms), totaling ~2 seconds. Caching identical queries can reduce this to near-zero for repeated questions, but cache keys must be tenant-aware to prevent cross-tenant data leakage.
**Decision:** Implement query result caching in Redis (`router.py`) with tenant-scoped keys. The cache key is computed by `_hash_query()` as `SHA-256(query_text + "#" + tenant_id + "#" + sorted(assigned_properties))`, ensuring that the same question from different tenants or users with different property assignments produces different cache keys. Cache lookup happens before classification (`_get_cached_result()`), and successful results are cached after execution (`_cache_result()`). Default TTL is 3600 seconds (1 hour), configurable per query. Redis is initialized in the FastAPI lifespan handler (`main.py`) with an async connection pool (`max_connections=20`). Rate limiting also uses Redis with per-user keys and a 60-second sliding window (100 requests/minute standard, 500 premium).
**Alternatives Considered:**
- **No caching (always query Snowflake)**: Simplest approach but wasteful. "Portfolio NOI" gets asked daily by 5+ people -- without caching, that is 5+ identical Snowflake queries and 10+ LLM calls per day for the same answer.
- **Snowflake result caching only**: Snowflake has built-in result caching, but it does not cache across different users and does not eliminate the LLM classification and SQL generation steps.
- **In-memory caching (LRU)**: No shared state across API instances. Would not work in a horizontally scaled deployment.
**Consequences:** Redis adds an infrastructure dependency but provides both caching and rate limiting from a single service. The `CACHE_ENABLED` environment variable allows disabling caching entirely for testing. Cache invalidation is time-based (TTL), which means stale data is possible within the TTL window. The `main.py` docstring notes that production should invalidate on data refresh and use a maximum TTL of 15 minutes for operational data. Failed queries (where `error` is not None) are explicitly excluded from caching.

---

## ADR-006: RBAC Design with 5 Personas and Column Masking

**Status:** Accepted
**Date:** 2024-02
**Context:** The platform serves 4 distinct operational personas (property managers, brokers, finance, executives) plus administrators, each with fundamentally different data needs and access rights. Property managers should see only their assigned buildings. Brokers should see available units and leasing data but not rent amounts or tenant PII. Finance should see complete financials but not employee salaries. Executives should see only portfolio-level aggregated KPIs, not individual property details. Access must be enforced consistently across both SQL queries and document searches.
**Decision:** Define a `Role` enum with 5 values (ADMIN, PROPERTY_MANAGER, BROKER, FINANCE, EXECUTIVE) in `rbac.py`. Each role has a permission matrix (`ROLE_PERMISSIONS`) specifying allowed resources, CRUD actions, property scope (`all`, `assigned`, `none`), and column masks. Column masking is implemented at two levels: in the application layer via `get_column_mask()` and `filter_columns()` functions, and in the data warehouse via Snowflake view DDL (`snowflake_views.py`) that replaces sensitive columns with `NULL`. The `build_tenant_filter()` function generates parameterized SQL fragments (`%s` placeholders) for tenant and property isolation. An `audit_log()` function records every access attempt for compliance. FastAPI dependencies (`require_role()` and `require_property_access()` in `auth.py`) enforce role checks at the endpoint level.
**Alternatives Considered:**
- **Simple admin/user dichotomy**: Too coarse. Real estate operations have genuinely distinct data needs per persona. A broker viewing financial P&L data or a property manager accessing acquisition prices would be inappropriate.
- **Attribute-based access control (ABAC)**: More flexible but harder to reason about and audit. RBAC with property-level scoping provides sufficient granularity for 5 well-defined personas.
- **Dynamic permissions from database**: Would allow runtime permission changes without code deployment. Rejected for the initial build because the persona set is stable (property managers, brokers, finance, executives are standard real estate roles). The `ROLE_PERMISSIONS` matrix can be migrated to a database table in a future phase.
**Consequences:** The 5-role model maps directly to real estate organizational structure, making it intuitive for tenant admins to assign roles. Column masking at the Snowflake view level means even SQL injection through the text-to-SQL pipeline cannot expose masked columns, because the views themselves return NULL for those fields. The trade-off is rigidity -- adding a new role or modifying permissions requires code changes to `ROLE_PERMISSIONS`, `generate_view_ddl()`, and the Supabase RLS policies. The audit log provides a compliance-ready trail of all data access attempts, but production implementation requires persisting to the `access_logs` table in Supabase (currently logged to stdout).
