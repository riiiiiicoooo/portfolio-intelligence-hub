# Portfolio Intelligence Hub - System Architecture

**Version:** 1.0  
**Status:** Active Development  
**Last Updated:** 2026-03-04  
**Owner:** Engineering Leadership  
**Audience:** Engineering team, DevOps, Technical stakeholders

---

## 1. High-Level System Overview

Portfolio Intelligence Hub is a distributed system combining real-time structured data access with semantic document search to provide portfolio operators instant answers to complex queries.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE LAYER                         │
│  ┌──────────────┐  ┌────────────────┐  ┌──────────────────────────┐ │
│  │  Next.js App │  │ React Chat UI  │  │  Admin Dashboard         │ │
│  │ (Vercel)     │  │ (Streaming)    │  │  (User Mgmt, Audit)      │ │
│  └──────────────┘  └────────────────┘  └──────────────────────────┘ │
└──────────────────────────────────────┬──────────────────────────────┘
                                       │ JWT Token (Clerk)
                                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      API & QUERY ROUTER LAYER                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ FastAPI Server (Uvicorn, 3 instances)                       │   │
│  │  - Authentication & Authorization (RBAC)                    │   │
│  │  - Query classification (SQL vs. semantic vs. hybrid)       │   │
│  │  - Rate limiting (100 req/user/min)                         │   │
│  │  - Query queuing & timeout enforcement                      │   │
│  └───┬──────────────┬──────────────────┬──────────────────────┘   │
│       │              │                  │                          │
│  ┌────▼──┐  ┌────────▼─────┐  ┌────────▼──────┐  ┌─────────────┐ │
│  │ Redis │  │ Cache Layer  │  │ Audit Logging │  │  Telemetry  │ │
│  │Caching│  │ (Query,      │  │  (PostgreSQL) │  │   (Datadog) │ │
│  │(6GB)  │  │ Documents)   │  │               │  │             │ │
│  └────┬──┘  └────┬─────────┘  └───────────────┘  └─────────────┘ │
└───────┼──────────┼──────────────────────────────────────────────┬──┘
        │          │                                              │
        ▼          ▼                                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    INTELLIGENCE ENGINE LAYER                          │
│  ┌──────────────────────────┐          ┌───────────────────────────┐│
│  │ Text-to-SQL Engine       │          │ Semantic Search Engine    ││
│  │ - Claude Opus 4          │          │ - OpenAI embeddings      ││
│  │ - Schema understanding   │          │ - pgvector similarity    ││
│  │ - Query generation       │          │ - Cohere reranking       ││
│  │ - Execution planning     │          │ - Document retrieval     ││
│  │ - Result formatting      │          └────────┬─────────────────┘│
│  └──────────┬───────────────┘                   │                 │
│             │                                   │                 │
│             ▼                                   ▼                 │
│  ┌───────────────────────┐   ┌──────────────────────────────────┐ │
│  │ SQL Validation Engine │   │ Answer Synthesis                 │ │
│  │ - Query analysis      │   │ - Natural language formatting    │ │
│  │ - Cost estimation     │   │ - Context extraction             │ │
│  │ - Permission checks   │   │ - Confidence scoring             │ │
│  └───────────────────────┘   └──────────────────────────────────┘ │
└──────────────┬───────────────────────────────────────────────────┬──┘
               │                                                   │
               ▼                                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      DATA & STORAGE LAYER                             │
│  ┌──────────────────────────┐          ┌───────────────────────────┐│
│  │ Snowflake Data Warehouse │          │ Supabase (PostgreSQL)     ││
│  │ - Properties table       │          │ - Users table             ││
│  │ - Units table            │          │ - Documents table         ││
│  │ - Tenancies table        │          │ - Document chunks (pgvec) ││
│  │ - Leases table           │          │ - Query history           ││
│  │ - Work orders table      │          │ - Access logs (RLS)       ││
│  │ - Financials table       │          │ - Saved queries           ││
│  │ - Collections table      │          │ - Integration metadata    ││
│  │ - Occupancy snapshots    │          └───────────────────────────┘│
│  │ - Materialized views     │                                        │
│  │   (KPI summary, scorecard)           ┌──────────────────────────┐│
│  │ - Dynamic RLS views      │           │ External APIs            ││
│  │   (per-user filtered)    │           │ - OpenAI embeddings      ││
│  └──────────────────────────┘           │ - Cohere reranking       ││
│                                         └──────────────────────────┘│
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. Text-to-SQL Engine Deep Dive

### 2.1 Overview
The Text-to-SQL engine converts natural language portfolio questions into executable Snowflake SQL queries. Built on Claude Opus 4, the engine combines prompt engineering, schema understanding, and execution planning to generate accurate queries without user SQL knowledge.

### 2.2 Five-Step Pipeline

```
┌────────────────────────────────────────────────────────────────────┐
│ STEP 1: QUERY UNDERSTANDING                                        │
│ ────────────────────────────────────────────────────────────────── │
│ Input: "What's our occupancy at Riverside Plaza this month?"       │
│                                                                     │
│ Process:                                                            │
│  - Parse query intent (metric request: occupancy)                  │
│  - Extract entities (property: Riverside Plaza, time: this month)   │
│  - Detect temporal requirement (month-to-date vs. historical)      │
│  - Identify persona context (Property Manager has access)          │
│                                                                     │
│ Output: {                                                           │
│   "intent": "metric_retrieval",                                    │
│   "metric": "occupancy",                                           │
│   "entities": {"property": "Riverside Plaza"},                     │
│   "temporal": "current_month",                                     │
│   "confidence": 0.98                                               │
│ }                                                                   │
└────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────┐
│ STEP 2: TABLE MAPPING & SCHEMA UNDERSTANDING                        │
│ ────────────────────────────────────────────────────────────────── │
│ Input: Entity extraction from Step 1 + User's RBAC context         │
│                                                                     │
│ Process:                                                            │
│  1. Retrieve schema context for required tables:                   │
│     - Properties table: property_id, property_name, status         │
│     - Units table: unit_id, property_id, occupancy_status          │
│     - Occupancy_snapshots: unit_id, snapshot_date, occupied        │
│                                                                     │
│  2. Map entities to schema:                                        │
│     - "Riverside Plaza" → properties.property_name = 'Riverside'   │
│     - "occupancy" → COUNT(units where occupied=true) / COUNT(*)    │
│     - "this month" → occupancy_snapshots WHERE snapshot_date >= ?  │
│                                                                     │
│  3. Verify user RBAC permissions:                                  │
│     - Can user query properties table? ✓                           │
│     - Does user have access to Riverside Plaza? ✓                  │
│     - Any field masking required? (PII) ✗                          │
│                                                                     │
│ Output: {                                                           │
│   "required_tables": ["properties", "units", "occupancy_snapshots"],
│   "joins": [                                                        │
│     {"left": "properties", "right": "units", "on": "property_id"}, │
│     {"left": "units", "right": "occupancy_snapshots",              │
│      "on": "unit_id"}                                              │
│   ],                                                                │
│   "filters": {"property_name": "Riverside Plaza"},                 │
│   "permissions_ok": true                                           │
│ }                                                                   │
└────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────┐
│ STEP 3: SQL GENERATION                                              │
│ ────────────────────────────────────────────────────────────────── │
│ Input: Table mapping + schema definitions + in-context examples    │
│                                                                     │
│ Process:                                                            │
│  1. Claude Opus 4 generates SQL using prompt:                      │
│                                                                     │
│     "You are an expert Snowflake SQL writer. Given the query:      │
│      'What's our occupancy at Riverside Plaza this month?'         │
│      Generate a valid SQL query that:                              │
│      - Uses tables: properties, units, occupancy_snapshots         │
│      - Filters to current month occupancy                          │
│      - Returns occupancy percentage and unit breakdown             │
│      - Handles NULL values gracefully                              │
│      - Limits results to 100 rows max                              │
│      - Does NOT access any restricted tables                       │
│      - Returns results sorted by relevance to query                │
│                                                                     │
│      Reference examples of similar queries:                        │
│      [Example 1] Occupancy trend: ...SQL...                        │
│      [Example 2] Property comparison: ...SQL..."                   │
│                                                                     │
│  2. Model generates SQL:                                           │
│     WITH current_month_occupancy AS (                              │
│       SELECT                                                        │
│         p.property_name,                                           │
│         COUNT(CASE WHEN os.occupied = true THEN 1 END) as occupied,
│         COUNT(u.unit_id) as total_units,                           │
│         ROUND(100.0 * COUNT(CASE WHEN os.occupied = true THEN 1    │
│           END) / COUNT(u.unit_id), 1) as occupancy_pct            │
│       FROM properties p                                            │
│       JOIN units u ON p.property_id = u.property_id               │
│       LEFT JOIN occupancy_snapshots os ON u.unit_id =             │
│         os.unit_id AND os.snapshot_date >= TRUNC(CURRENT_DATE, 'M')
│       WHERE p.property_name = 'Riverside Plaza'                    │
│       GROUP BY p.property_name                                     │
│     )                                                               │
│     SELECT * FROM current_month_occupancy;                         │
│                                                                     │
│  3. Validation:                                                    │
│     - Syntax check (ParseSql library)                              │
│     - Column reference validation                                  │
│     - Join logic validation                                        │
│     - Row limit enforcement                                        │
│                                                                     │
│ Output: {                                                           │
│   "sql": "WITH current_month_occupancy AS (...)",                  │
│   "confidence": 0.94,                                              │
│   "tables_used": ["properties", "units", "occupancy_snapshots"],   │
│   "estimated_rows": 1,                                             │
│   "estimated_cost_credits": 0.02                                   │
│ }                                                                   │
└────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────┐
│ STEP 4: EXECUTION & ERROR HANDLING                                  │
│ ────────────────────────────────────────────────────────────────── │
│ Input: Generated SQL + Snowflake connection                         │
│                                                                     │
│ Process:                                                            │
│  1. Execute query with safety guards:                              │
│     - 30-second timeout (prevent runaway queries)                  │
│     - Row limit 100K (prevent memory overload)                     │
│     - Query submitted to warehouse queue                           │
│     - Cost pre-check (estimated vs. budget)                        │
│                                                                     │
│  2. Handle execution errors gracefully:                            │
│     - If timeout: "Query too complex, try narrowing date range"    │
│     - If syntax error: Re-generate SQL with error context          │
│     - If permission error: "You don't have access to this data"    │
│     - If no results: "No data matches your filters, try broadening"
│                                                                     │
│  3. Execution success case:                                        │
│     Results:                                                        │
│     property_name     | occupied | total_units | occupancy_pct    │
│     Riverside Plaza   |      342 |         365 |            93.7   │
│                                                                     │
│ Output: {                                                           │
│   "status": "success",                                             │
│   "rows_returned": 1,                                              │
│   "execution_time_ms": 480,                                        │
│   "snowflake_cost_credits": 0.018,                                 │
│   "results": [[...]]                                               │
│ }                                                                   │
└────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────┐
│ STEP 5: RESULT FORMATTING & ANSWER SYNTHESIS                        │
│ ────────────────────────────────────────────────────────────────── │
│ Input: Raw SQL results + query context + persona context            │
│                                                                     │
│ Process:                                                            │
│  1. Transform tabular results to natural language narrative:       │
│     Raw data: occupancy_pct = 93.7%                                │
│     Context: This is Property Manager query, interested in status  │
│                                                                     │
│  2. Generate contextual answer:                                    │
│     "Your portfolio occupancy at Riverside Plaza is currently       │
│     93.7% (342 of 365 units occupied). This is above your target   │
│     of 90%. Year-to-date average: 94.1%. Last month: 94.2%."       │
│                                                                     │
│  3. Add data quality indicators:                                   │
│     - Last updated: Today 8:45 AM                                  │
│     - Data source: Operational systems (real-time)                 │
│     - Confidence: High (routine occupancy calculation)             │
│                                                                     │
│  4. Include follow-up suggestions:                                 │
│     - "Ask for: ...occupancy trend this year..."                   │
│     - "Ask for: ...units ready to lease by date..."                │
│                                                                     │
│ Output: {                                                           │
│   "answer": "Your portfolio occupancy...",                         │
│   "data": [[...]],                                                 │
│   "confidence": 0.96,                                              │
│   "execution_time_ms": 480,                                        │
│   "data_freshness": "real-time",                                   │
│   "follow_up_suggestions": [...]                                   │
│ }                                                                   │
└────────────────────────────────────────────────────────────────────┘
```

### 2.3 Code-Level Implementation Detail

```python
# text_to_sql_engine.py

class TextToSQLEngine:
    def __init__(self, snowflake_client, claude_client, schema_context):
        self.sf = snowflake_client
        self.claude = claude_client
        self.schema = schema_context
        self.cache = RedisCache()
    
    async def process_query(self, user_query: str, user_context: UserContext) -> QueryResult:
        # Step 1: Query Understanding
        understanding = await self._understand_query(user_query)
        
        # Step 2: Table Mapping with RBAC
        table_mapping = await self._map_tables(understanding, user_context)
        
        # Step 3: SQL Generation
        sql_result = await self._generate_sql(
            understanding,
            table_mapping,
            user_context
        )
        
        if sql_result.confidence < 0.7:
            return QueryResult(
                status="low_confidence",
                message=f"I'm not confident about this query. Did you mean...?"
            )
        
        # Step 4: Execute with safety guards
        execution_result = await self._execute_with_guards(
            sql_result.sql,
            timeout_seconds=30,
            max_rows=100000
        )
        
        # Step 5: Format results to natural language
        answer = await self._format_answer(
            execution_result,
            understanding,
            user_context
        )
        
        # Log for audit and improvement
        self._log_query(user_query, sql_result, execution_result, user_context)
        
        return answer
    
    async def _understand_query(self, user_query: str) -> QueryUnderstanding:
        prompt = f"""Analyze this portfolio query and extract the intent.
        Query: {user_query}
        
        Return JSON with:
        - intent: metric_retrieval, comparison, trend, exception_detection
        - metric: occupancy, rent, expense, etc.
        - entities: {{'property': ..., 'tenant': ..., 'date_range': ...}}
        - temporal: current, ytd, trending, historical
        - complexity: simple, moderate, complex
        """
        
        response = await self.claude.chat(prompt)
        return QueryUnderstanding.from_json(response)
    
    async def _map_tables(self, understanding: QueryUnderstanding, 
                         user_context: UserContext) -> TableMapping:
        """Map query entities to Snowflake schema + RBAC filtering"""
        
        required_tables = self._infer_required_tables(understanding.metric)
        
        # Apply RBAC: get user's accessible properties/data
        accessible_properties = await self.sf.get_user_accessible_properties(
            user_context.user_id,
            user_context.role
        )
        
        # Build join logic with property filters
        joins = self._build_joins(required_tables)
        
        # Add RBAC filtering to WHERE clause
        rbac_filter = f"WHERE property_id IN ({accessible_properties})"
        
        return TableMapping(
            tables=required_tables,
            joins=joins,
            rbac_filter=rbac_filter
        )
    
    async def _generate_sql(self, understanding: QueryUnderstanding,
                           table_mapping: TableMapping,
                           user_context: UserContext) -> SQLGenerationResult:
        """Claude Opus 4 SQL generation with schema context"""
        
        # Build prompt with schema definitions + examples
        schema_context = self._build_schema_context(table_mapping.tables)
        
        in_context_examples = self._get_similar_examples(understanding)
        
        prompt = f"""You are an expert Snowflake SQL developer.
        
        Schema:
        {schema_context}
        
        User Query: {understanding.raw_query}
        
        Similar example queries:
        {in_context_examples}
        
        Generate a valid Snowflake SQL query that:
        1. Uses ONLY these tables: {', '.join(table_mapping.tables)}
        2. Includes RBAC filtering: {table_mapping.rbac_filter}
        3. Returns at most 100 rows
        4. Handles NULL values with COALESCE or CASE
        5. Uses proper Snowflake functions for date math
        6. Orders results by relevance to the query
        7. Does NOT use CREATE, DROP, DELETE, UPDATE statements
        
        Return ONLY the SQL query, no explanation.
        """
        
        raw_sql = await self.claude.chat(prompt)
        
        # Validate SQL syntax and safety
        validation = self._validate_sql(raw_sql, table_mapping, user_context)
        
        if not validation.is_safe:
            return SQLGenerationResult(
                confidence=0,
                error=f"Safety validation failed: {validation.error}"
            )
        
        # Estimate query cost before execution
        cost_estimate = await self.sf.estimate_query_cost(raw_sql)
        
        return SQLGenerationResult(
            sql=raw_sql,
            confidence=understanding.confidence * 0.95,  # Slightly lower confidence
            estimated_cost=cost_estimate,
            tables=table_mapping.tables
        )
    
    async def _execute_with_guards(self, sql: str, timeout_seconds: int = 30,
                                   max_rows: int = 100000) -> ExecutionResult:
        """Execute SQL with timeouts, row limits, cost controls"""
        
        try:
            # Submit query with timeout and row limits
            query_handle = await self.sf.execute_query_async(
                sql,
                timeout_seconds=timeout_seconds,
                max_rows=max_rows
            )
            
            # Wait for results with timeout
            results = await asyncio.wait_for(
                self.sf.get_query_results(query_handle),
                timeout=timeout_seconds + 5
            )
            
            return ExecutionResult(
                status="success",
                rows=results.rows,
                execution_time_ms=results.execution_time_ms,
                cost_credits=results.cost_credits
            )
        
        except asyncio.TimeoutError:
            return ExecutionResult(
                status="timeout",
                error="Query exceeded 30-second limit. Try narrowing filters."
            )
        except Exception as e:
            return ExecutionResult(
                status="error",
                error=str(e)
            )
    
    async def _format_answer(self, execution_result: ExecutionResult,
                            understanding: QueryUnderstanding,
                            user_context: UserContext) -> QueryResult:
        """Transform raw results to natural language answer"""
        
        if execution_result.status != "success":
            return QueryResult(
                status="error",
                message=self._user_friendly_error(execution_result.error)
            )
        
        # Convert tabular results to narrative
        prompt = f"""Format these query results into a natural, helpful narrative.
        Query: {understanding.raw_query}
        Persona: {user_context.role}
        
        Results:
        {execution_result.rows}
        
        Generate a 2-3 sentence answer that:
        1. Directly answers the user's question
        2. Highlights key numbers and insights
        3. Notes any anomalies or important context
        4. Is written for a busy executive (concise)
        
        Example format:
        "Your occupancy across the portfolio is 93.1% (vs. 92.7% last month).
        This represents 3,412 occupied units of 3,665 total. Austin cluster
        is performing strongest at 96.2%, while Midwest industrial is below
        target at 89.1%."
        """
        
        answer_text = await self.claude.chat(prompt)
        
        return QueryResult(
            status="success",
            answer=answer_text,
            data=execution_result.rows,
            confidence=understanding.confidence,
            execution_time_ms=execution_result.execution_time_ms,
            data_freshness="real-time"  # Occupancy data refreshes hourly
        )
    
    def _log_query(self, query: str, sql_result, execution_result,
                   user_context: UserContext):
        """Log for audit, analytics, and model improvement"""
        
        self.sf.insert("audit_logs", {
            "user_id": user_context.user_id,
            "query_text": query,
            "generated_sql": sql_result.sql,
            "sql_confidence": sql_result.confidence,
            "execution_status": execution_result.status,
            "execution_time_ms": execution_result.execution_time_ms,
            "timestamp": datetime.now(),
            "accessed_properties": sql_result.tables,
        })
```

---

## 3. Semantic Search Engine Deep Dive

### 3.1 Overview
The semantic search engine retrieves contextual documents (leases, reports, policies) using vector embeddings and reranking. Users can search across portfolios of documents in natural language without keyword matching.

### 3.2 Four-Step Pipeline

```
┌────────────────────────────────────────────────────────────────────┐
│ STEP 1: DOCUMENT INGESTION & EMBEDDING                              │
│ ────────────────────────────────────────────────────────────────── │
│                                                                     │
│ User uploads document: "Riverside Plaza Lease Book.pdf" (250 pages) │
│                                                                     │
│ Process:                                                            │
│  1. Extract text from PDF:                                         │
│     - OCR if image-based (using pytesseract)                       │
│     - Text extraction if digital (using PyPDF2)                    │
│     - Result: ~50,000 words of raw text                            │
│                                                                     │
│  2. Chunk semantically (not fixed-size):                           │
│     - Use sentence tokenizer (NLTK) to split at boundaries         │
│     - Target: 512 tokens per chunk (~400 words)                    │
│     - Maintain 100-token overlap for context                       │
│     - Example chunk: "Unit 405 lease term: 60 months beginning     │
│       2024-03-01 through 2029-02-28. Tenant: Acme Corp. Rent:     │
│       $2,850/month, 3% annual escalation. Renewal options:         │
│       2x5-year at market rates with 30-day notice."                │
│                                                                     │
│  3. Generate embeddings (OpenAI embedding-3-large):                │
│     For each chunk:                                                │
│     - Call OpenAI API: embed_text(chunk)                           │
│     - Response: 3072-dimensional vector                            │
│     - Cost: ~0.015 tokens = $0.000000003/chunk                     │
│     - Total for 250-page doc: ~100 chunks, $0.0003 cost            │
│     - Batch processing to reduce per-call overhead                 │
│                                                                     │
│  4. Store in Supabase pgvector:                                    │
│     INSERT INTO document_chunks (                                  │
│       document_id,                                                 │
│       chunk_number,                                                │
│       content,                                                     │
│       embedding,  -- 3072-dimensional vector                       │
│       property_id,  -- for RBAC filtering                          │
│       page_number,  -- for reference back to source                │
│       chunk_metadata  -- JSON: {'tenant': ..., 'lease_term': ...}  │
│     ) VALUES (...)                                                 │
│                                                                     │
│ Output: {                                                           │
│   "document_id": "doc_123",                                        │
│   "document_name": "Riverside Plaza Lease Book",                   │
│   "chunks_created": 142,                                           │
│   "status": "indexed_ready_for_search",                            │
│   "embedding_cost": 0.0003,                                        │
│   "index_latency_seconds": 45                                      │
│ }                                                                   │
└────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────┐
│ STEP 2: SEMANTIC RETRIEVAL & RERANKING                              │
│ ────────────────────────────────────────────────────────────────── │
│ User query: "What are the renewal options in our Westwood lease?"  │
│                                                                     │
│ Process:                                                            │
│  1. Embed the user query:                                          │
│     - Call OpenAI: embed_text("What are the renewal options...")   │
│     - Response: 3072-dimensional vector                            │
│     - Cost: negligible (one query vector)                          │
│                                                                     │
│  2. Vector similarity search in pgvector:                          │
│     SELECT                                                         │
│       chunk_id,                                                    │
│       content,                                                     │
│       1 - (embedding <=> query_embedding) as similarity_score      │
│     FROM document_chunks                                           │
│     WHERE property_id IN (user_accessible_properties)  -- RBAC     │
│     AND document_id IN (doc_ids_for_leases)  -- Filter by doc type │
│     ORDER BY embedding <=> query_embedding  -- Vector distance     │
│     LIMIT 50;  -- Retrieve top 50 candidates                       │
│                                                                     │
│     Results (similarity_score, 0-1 scale):                         │
│     0.94  - "Renewal options: 2x5-year at market rates..."        │
│     0.91  - "Lease extension available with 30-day notice..."      │
│     0.87  - "Tenant given three 5-year renewal options..."         │
│     0.82  - "Rent escalation clause: 3% annually..."               │
│     0.78  - "Lease begins March 1, 2024, term 60 months..."        │
│     ... (45 more results)                                          │
│                                                                     │
│  3. Rerank top candidates with Cohere (for precision):             │
│     - Input: Query + top 50 documents                              │
│     - Cohere rerank-english-v3.0 evaluates relevance              │
│     - Returns top 5 with reranked scores                           │
│     - Improves precision from 78% → 90%+                           │
│                                                                     │
│     Cohere reranked results:                                       │
│     1. (score: 0.98) "Renewal options: 2x5-year..."                │
│     2. (score: 0.94) "Tenant given three 5-year renewal..."        │
│     3. (score: 0.89) "Lease extension available..."                │
│     4. (score: 0.82) "Notice requirement: 30 days..."              │
│     5. (score: 0.76) "Market rate determination process..."        │
│                                                                     │
│ Output: {                                                           │
│   "chunks": [                                                      │
│     {"rank": 1, "score": 0.98, "content": "...", "page": 47},     │
│     {"rank": 2, "score": 0.94, "content": "...", "page": 48},     │
│     ...                                                            │
│   ],                                                                │
│   "query_vector_cache_hit": true,  -- Cache reuses embeddings      │
│   "reranking_latency_ms": 120                                      │
│ }                                                                   │
└────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────┐
│ STEP 3: CONTEXT AUGMENTATION & ANSWER SYNTHESIS                     │
│ ────────────────────────────────────────────────────────────────── │
│ Input: Top 5 document chunks from retrieval                         │
│                                                                     │
│ Process:                                                            │
│  1. Extract relevant metadata:                                     │
│     - Chunk locations (page numbers): 47, 48, 52                   │
│     - Document version: "2023 Executed"                            │
│     - Property: "Westwood Commons"                                 │
│     - Lease party: "Acme Corporation"                              │
│     - Lease status: "Active"                                       │
│                                                                     │
│  2. Generate contextual answer with Claude:                        │
│     Prompt: "Based on these lease document excerpts, answer:       │
│     'What are the renewal options in our Westwood lease?'          │
│     Provide a clear, concise answer citing specific terms."        │
│                                                                     │
│     Response: "According to the Westwood Commons lease for Acme    │
│     Corporation (pages 47-52), the tenant has two 5-year renewal  │
│     options exercisable at market rates with 30 days' notice prior │
│     to expiration. The lease expires February 28, 2029. Renewal    │
│     rates are determined annually by independent appraisal or      │
│     mutual agreement. The document does not specify a rate cap or  │
│     floor for renewals."                                           │
│                                                                     │
│  3. Confidence scoring:                                            │
│     - High: Clear, multiple corroborating sources (top 3 chunks)   │
│     - Medium: Ambiguous or single source                           │
│     - Low: Conflicting information or speculative answer           │
│     - Score: 0.95 (high confidence, explicit lease terms)          │
│                                                                     │
│ Output: {                                                           │
│   "answer": "According to the lease...",                           │
│   "source_documents": ["Westwood Commons Lease Book"],             │
│   "page_references": [47, 48, 52],                                 │
│   "confidence": 0.95,                                              │
│   "extraction_method": "semantic_retrieval"                        │
│ }                                                                   │
└────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────┐
│ STEP 4: QUERY ROUTING & RESULT FORMATTING                           │
│ ────────────────────────────────────────────────────────────────── │
│ System now decides: return semantic search result alone, or         │
│ combine with Text-to-SQL results?                                   │
│                                                                     │
│ Routing logic:                                                      │
│  - Semantic search confidence: 0.95 (high)                         │
│  - Question type: document-specific (lease terms)                  │
│  - User preference: reading documents vs. structured data          │
│                                                                     │
│  → Decision: Return semantic search results (no SQL needed)         │
│                                                                     │
│ Format for user:                                                    │
│ ┌──────────────────────────────────────────────────────────┐       │
│ │ Answer: According to the lease, Acme Corporation has    │       │
│ │ two 5-year renewal options at market rates...           │       │
│ │                                                          │       │
│ │ Source: Westwood Commons Lease Book (Pages 47-52)       │       │
│ │ Confidence: Very High (95%)                             │       │
│ │                                                          │       │
│ │ [View Full Document] [View Related Clauses]             │       │
│ └──────────────────────────────────────────────────────────┘       │
│                                                                     │
│ Output: {                                                           │
│   "response_type": "semantic_document_search",                     │
│   "answer": "...",                                                 │
│   "source_documents": ["Westwood Commons Lease Book"],             │
│   "formatting": "narrative_with_source_attribution",               │
│   "user_suggested_followups": [                                    │
│     "What's the current rent at Westwood Commons?",                │
│     "Compare renewal terms across all our leases",                 │
│     "Show me Acme Corporation's contact info"                      │
│   ]                                                                 │
│ }                                                                   │
└────────────────────────────────────────────────────────────────────┘
```

### 3.3 Code-Level Implementation

```python
# semantic_search_engine.py

class SemanticSearchEngine:
    def __init__(self, openai_client, cohere_client, supabase_client):
        self.openai = openai_client
        self.cohere = cohere_client
        self.db = supabase_client
        self.cache = RedisCache()
    
    async def ingest_document(self, document_file, property_id: str,
                             metadata: Dict) -> IngestionResult:
        """Step 1: Ingest and embed document chunks"""
        
        # Extract text from PDF/DOCX
        raw_text = await self._extract_text(document_file)
        
        # Semantic chunking at sentence boundaries
        chunks = self._semantic_chunk(raw_text, target_tokens=512, overlap=100)
        
        # Generate embeddings for all chunks (batch processing)
        chunk_embeddings = []
        for i, chunk in enumerate(chunks):
            embedding = await self.openai.embed_text(chunk)
            chunk_embeddings.append({
                "chunk_number": i,
                "content": chunk,
                "embedding": embedding,
                "tokens": self._count_tokens(chunk)
            })
        
        # Store in Supabase pgvector
        document_id = f"doc_{uuid.uuid4()}"
        insert_result = await self.db.insert("document_chunks", {
            "document_id": document_id,
            "property_id": property_id,
            "file_name": document_file.filename,
            "chunks": chunk_embeddings,
            "metadata": metadata,
            "created_at": datetime.now()
        })
        
        return IngestionResult(
            document_id=document_id,
            chunks_created=len(chunks),
            embedding_cost=len(chunks) * 0.000001,  # Approx cost
            status="ready_for_search"
        )
    
    async def search_documents(self, user_query: str,
                             user_context: UserContext) -> SearchResult:
        """Step 2-4: Search, rerank, synthesize answer"""
        
        # Check cache for identical recent queries
        cache_key = f"semantic_search:{user_query}:{user_context.user_id}"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Step 2: Embed query and retrieve candidates
        query_embedding = await self.openai.embed_text(user_query)
        
        # Vector similarity search (pgvector HNSW index)
        candidates = await self.db.query("""
            SELECT chunk_id, content, page_number, property_id,
                   1 - (embedding <=> %s) as similarity_score
            FROM document_chunks
            WHERE property_id IN (%s)  -- RBAC filtering
            ORDER BY embedding <=> %s
            LIMIT 50
        """, [query_embedding, user_context.accessible_properties, query_embedding])
        
        # Rerank with Cohere for better precision
        rerank_input = [
            {"id": str(i), "text": c["content"]}
            for i, c in enumerate(candidates)
        ]
        
        reranked = await self.cohere.rerank(
            model="rerank-english-v3.0",
            query=user_query,
            documents=rerank_input,
            top_n=5
        )
        
        # Step 3: Synthesize answer from top chunks
        top_chunks = [candidates[r.index] for r in reranked.results]
        
        context_text = "\n\n".join([
            f"[Page {c['page_number']}] {c['content']}"
            for c in top_chunks
        ])
        
        answer_prompt = f"""Based on these document excerpts, answer the query:
        Query: {user_query}
        
        Document excerpts:
        {context_text}
        
        Provide a clear, specific answer citing the relevant sections.
        If the documents don't answer the query, say so explicitly.
        """
        
        answer = await self.claude.chat(answer_prompt)
        
        # Step 4: Format result
        result = SearchResult(
            answer=answer,
            source_documents=[
                {
                    "document_id": c["document_id"],
                    "page_number": c["page_number"],
                    "relevance_score": reranked.results[i].relevance_score
                }
                for i, c in enumerate(top_chunks)
            ],
            confidence=self._compute_confidence(reranked),
            retrieval_latency_ms=candidates.execution_time
        )
        
        # Cache for 24 hours
        self.cache.set(cache_key, result, ttl_seconds=86400)
        
        return result
    
    def _semantic_chunk(self, text: str, target_tokens: int = 512,
                        overlap: int = 100) -> List[str]:
        """Chunk text at sentence boundaries, not fixed-size"""
        
        # Sentence tokenization
        sentences = nltk.sent_tokenize(text)
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self._count_tokens(sentence)
            
            if current_tokens + sentence_tokens > target_tokens and current_chunk:
                # Save current chunk
                chunks.append(" ".join(current_chunk))
                
                # Start new chunk with overlap (last few sentences)
                overlap_tokens = 0
                overlap_sentences = []
                for s in reversed(current_chunk):
                    overlap_tokens += self._count_tokens(s)
                    if overlap_tokens > overlap:
                        break
                    overlap_sentences.insert(0, s)
                
                current_chunk = overlap_sentences
                current_tokens = overlap_tokens
            
            current_chunk.append(sentence)
            current_tokens += sentence_tokens
        
        # Add final chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
```

---

## 4. Role-Based Access Control (RBAC) Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                          JWT Token (Clerk)                           │
│  user_id: "user_123"                                                 │
│  role: "PROPERTY_MANAGER"                                            │
│  accessible_properties: ["prop_001", "prop_005", "prop_012"]         │
│  data_restrictions: {                                                │
│    "FINANCIAL": false,  -- PMs don't see financials                  │
│    "TENANT": true,      -- PMs see tenant info                       │
│    "LEASE": true,       -- PMs see leases                            │
│    "WORK_ORDER": true   -- PMs see maintenance                       │
│  }                                                                    │
└─────────────────────────────┬──────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Query Router     │
                    │ (FastAPI)        │
                    │ Validates JWT    │
                    │ Extracts scopes  │
                    └────────┬─────────┘
                             │
                   ┌─────────┴──────────┐
                   ▼                    ▼
         ┌─────────────────────┐  ┌──────────────────────┐
         │ Snowflake           │  │ Supabase             │
         │ Dynamic Views       │  │ Row-Level Security   │
         └─────────────────────┘  └──────────────────────┘
         │                        │
         │ CREATE VIEW            │ CREATE POLICY
         │ properties_filtered AS  │ document_chunks_select AS
         │                        │
         │ SELECT * FROM          │ SELECT * FROM document_chunks
         │   properties           │ WHERE property_id IN (
         │ WHERE property_id IN   │   SELECT accessible_properties
         │   (accessible_props)   │   FROM user_context
         │                        │ );
         │
         └─────────────────────┬──────────────────────┘
                               │
                      ┌────────┴──────────┐
                      ▼                   ▼
               ┌──────────────┐   ┌──────────────┐
               │ Filtered     │   │ Audit Log    │
               │ Results:     │   │ Entry        │
               │ 3 props      │   │ {            │
               │ returned     │   │   user_id,   │
               │              │   │   accessed_, │
               │              │   │   timestamp  │
               │              │   │ }            │
               └──────────────┘   └──────────────┘

RBAC Enforcement Points:
========================

1. Query Time (Text-to-SQL)
   - User can only query tables for which they have role permissions
   - PM: properties, units, tenancies, leases, work_orders
   - Finance: financials, rent_collections, leases
   - Executive: all tables with aggregated view
   - Broker: leases, properties, units (no financials)

2. SQL Execution Time (Dynamic Views)
   - Snowflake creates user-specific filtered views
   - WHERE clause automatically filters by accessible_properties
   - Query optimizer handles permission checks before execution

3. Document Search Time (Supabase RLS)
   - document_chunks table has RLS policy
   - Users only see documents tagged to properties they manage
   - Audit log tracks every document access

4. Results Return Time
   - PII masking applied (SSN, payment methods hidden)
   - Finance sees rent collected, PM doesn't
   - Executive sees tenant PII for credit decisions, PM doesn't
```

---

## 5. Data Flow Diagrams

### 5.1 Structured Query Flow (Text-to-SQL)
```
Property Manager asks:
"What's our occupancy at Riverside Plaza this month?"
          │
          ▼
    ┌─────────────────────────────────┐
    │ Extract user context from JWT:  │
    │ - user_id: "pm_456"             │
    │ - role: PROPERTY_MANAGER        │
    │ - accessible_props: [001,005,12]│
    │ - "001" = Riverside Plaza ✓     │
    └──────────┬──────────────────────┘
               │
               ▼
    ┌─────────────────────────────────┐
    │ Text-to-SQL Engine:             │
    │ 1. Understand query intent      │
    │ 2. Map to tables (units,        │
    │    occupancy_snapshots)         │
    │ 3. Generate SQL with RBAC filter│
    └──────────┬──────────────────────┘
               │
               ▼
    ┌─────────────────────────────────┐
    │ Generated SQL:                  │
    │ SELECT COUNT(*) as occupied,    │
    │   COUNT(DISTINCT unit_id) total │
    │ FROM units u                    │
    │ WHERE property_id = '001'       │
    │ AND occupancy_status = 'occupied'
    └──────────┬──────────────────────┘
               │
               ▼
    ┌─────────────────────────────────┐
    │ Snowflake Execution:            │
    │ - Compile query plan            │
    │ - Execute within 30s timeout    │
    │ - Check row limits              │
    │ - Return results                │
    └──────────┬──────────────────────┘
               │
               ▼
    ┌─────────────────────────────────┐
    │ Results: 342 occupied / 365 units│
    │ = 93.7% occupancy               │
    └──────────┬──────────────────────┘
               │
               ▼
    ┌─────────────────────────────────┐
    │ Format answer in natural lang:  │
    │ "Your portfolio occupancy at    │
    │ Riverside Plaza is 93.7%..."    │
    │                                 │
    │ Cache: store result for 1 hour  │
    │ Audit: log query to table       │
    └──────────┬──────────────────────┘
               │
               ▼
          Return to user
```

### 5.2 Semantic Search Flow (Document Retrieval)
```
Broker asks:
"What are the renewal terms in our Westwood lease?"
          │
          ▼
    ┌─────────────────────────────────┐
    │ Extract user context:           │
    │ - role: BROKER                  │
    │ - accessible_docs: all leases   │
    └──────────┬──────────────────────┘
               │
               ▼
    ┌─────────────────────────────────┐
    │ Check cache for similar queries │
    │ "renewal options westwood"      │
    │ Cache miss, proceed to search   │
    └──────────┬──────────────────────┘
               │
               ▼
    ┌─────────────────────────────────┐
    │ Embed query (OpenAI):           │
    │ 3072-dimensional vector         │
    └──────────┬──────────────────────┘
               │
               ▼
    ┌─────────────────────────────────┐
    │ pgvector similarity search:     │
    │ SELECT top 50 chunks where      │
    │ property_id IN (accessible)     │
    │ ORDER BY embedding distance     │
    └──────────┬──────────────────────┘
               │
               ▼
    ┌─────────────────────────────────┐
    │ Cohere reranking:               │
    │ Improve precision of top-50     │
    │ Return top-5 ranked chunks      │
    └──────────┬──────────────────────┘
               │
               ▼
    ┌─────────────────────────────────┐
    │ Claude synthesizes answer:      │
    │ "Based on lease pages 47-52,    │
    │ the tenant has 2x5-year renewal │
    │ options at market rates..."     │
    └──────────┬──────────────────────┘
               │
               ▼
    ┌─────────────────────────────────┐
    │ Format result with citations:   │
    │ - Source document & pages       │
    │ - Confidence score (95%)        │
    │ - Cache for 24 hours            │
    │ - Audit: log document access    │
    └──────────┬──────────────────────┘
               │
               ▼
          Return to user
```

---

## 6. Caching Strategy

### 6.1 Query Result Caching (Redis)
- **What:** Results of frequently asked queries
- **Where:** Redis (6GB cluster)
- **TTL:** 1 hour for real-time data (occupancy), 4 hours for financials
- **Hit rate target:** 40%
- **Validation:** Cache tags properties + query signature
- **Invalidation:** Manual admin control + automatic TTL expiry

### 6.2 Embedding Cache
- **What:** Query embeddings for semantic search
- **Where:** Redis in-memory
- **TTL:** 24 hours
- **Benefit:** Avoid re-embedding identical queries
- **Hit rate target:** 60% (users ask similar questions)

### 6.3 Snowflake Materialized Views
- **What:** Pre-computed KPIs (portfolio_kpi_summary, scorecard)
- **Where:** Snowflake persistent storage
- **Refresh:** Nightly after financial close
- **Benefit:** Eliminate expensive aggregations
- **Cost savings:** 80% reduction in query credits for KPI queries

---

## 7. Security Architecture

### 7.1 Tenant Isolation (Logical)
- Multiple clients share Snowflake warehouse
- Filtering via property_id in RBAC
- No hard database partition (cost optimization)
- Audit logs ensure no cross-tenant data leakage

### 7.2 Audit Logging
```sql
CREATE TABLE audit_logs (
  id UUID PRIMARY KEY,
  user_id VARCHAR,
  action VARCHAR,  -- 'query_executed', 'document_accessed'
  query_text VARCHAR,
  accessed_properties ARRAY,
  accessed_tables ARRAY,
  result_row_count INT,
  execution_time_ms INT,
  status VARCHAR,  -- 'success', 'error'
  timestamp TIMESTAMP,
  ip_address VARCHAR
);

-- Retention: 2 years
-- Query: 1-2 sec avg, cached for performance
```

### 7.3 PII Handling
- **Tenant names:** Visible to Property Manager, Broker, Finance
- **Tenant SSN/ID:** Visible only to Finance/Executive for credit
- **Payment methods:** Never visible (tokenized in external system)
- **Employee email:** Visible with redaction option
- **Contact phone:** Masked except last 4 digits for non-contacts

### 7.4 Data Encryption
- **In transit:** TLS 1.3 (Vercel → FastAPI → Snowflake)
- **At rest:** Snowflake AES-256 (default), Supabase PostgreSQL AES-256
- **API keys:** Stored in Vercel/AWS secrets manager, rotated quarterly

---

## 8. Deployment Architecture

### 8.1 Local Development
```
Developer machine:
├── Snowflake dev warehouse (separate account)
├── Supabase local (Docker + pgvector)
├── FastAPI server (localhost:8000)
├── Next.js dev server (localhost:3000)
├── Redis instance (Docker)
└── Mock Clerk + OpenAI API keys
```

### 8.2 Staging Environment
```
AWS/Vercel staging:
├── Snowflake staging warehouse (same cloud region)
├── Supabase staging (separate project)
├── FastAPI (2 instances, load balanced)
├── Next.js (Vercel preview deployment)
├── Redis 6GB (AWS ElastiCache)
└── Datadog monitoring (staging namespace)
```

### 8.3 Production Environment
```
Vercel (primary), AWS (backup):
├── Snowflake production warehouse (X-Large, auto-scaling)
├── Supabase production (HA replicas, 99.99% SLA)
├── FastAPI (3+ instances, auto-scaling)
├── Next.js (Vercel, global edge network)
├── Redis 6GB (AWS ElastiCache, Multi-AZ)
├── Datadog APM + uptime monitoring
├── CloudFlare DDoS protection
├── WAF (Mod Security rules)
└── SSL certificate (auto-renewal via cert manager)
```

---

## 9. Performance Considerations

### 9.1 Query Latency Targets
- **p50:** <1 second (simple queries with cache hits)
- **p95:** <5 seconds (complex joins, no cache)
- **p99:** <15 seconds (absolute worst case)

### 9.2 Scaling Strategy
- **Compute:** Snowflake auto-scaling warehouse (starts at XS, scales to XL)
- **Concurrency:** 10 Snowflake connections max per warehouse
- **If exceeded:** Queue queries, serve from cache for common queries
- **Database:** Supabase auto-scaling (PostgreSQL read replicas)
- **API:** Kubernetes HPA based on CPU % and request latency

### 9.3 Cost Optimization
- **Query costs:** Cache high-volume queries (50% cost reduction)
- **Embedding costs:** Batch processing (10x cost reduction)
- **Storage:** Archive old audit logs after 1 year (S3 Glacier)
- **Data transfer:** Snowflake ↔ FastAPI in same region (no egress fees)

---

## 10. Technology Selection Rationale

| Component | Selected | Alternatives | Rationale |
|-----------|----------|--------------|-----------|
| Data Warehouse | Snowflake | BigQuery, Redshift | Schema sharing, low concurrency cost, Supabase integration |
| LLM for Text-to-SQL | Claude Opus 4 | GPT-4 Turbo, open-source (LLama) | Longer context (60K), lower cost/token, prompt caching |
| Vector DB | Supabase pgvector | Pinecone, Weaviate, Milvus | Collocated with app tier, PostgreSQL familiarity, cost |
| Embedding Model | OpenAI embedding-3-large | OpenAI-small, open-source (Instructor) | 3072 dims, SotA retrieval quality, batch API pricing |
| Reranking | Cohere rerank-english-v3.0 | LlamaIndex, cross-encoders, in-house | Fast, accurate, low cost, specialized for English |
| API Framework | FastAPI | Flask, Django | Async support, auto OpenAPI docs, modern Python |
| Frontend | Next.js | React SPA, Vue, Svelte | SSR for SEO, API routes, Vercel deployment, adoption |
| Auth | Clerk | Auth0, Firebase Auth, AWS Cognito | Social login, user management dashboard, free tier for <500 users |
| Cache | Redis | Memcached, DynamoDB | Pub/sub for cache invalidation, TTL management, cost |
| Async Jobs | Trigger.dev | Celery, Bull, AWS Lambda | Hosted, serverless, trigger-based, dashboard |
| Workflow Automation | n8n | Zapier, Make, custom code | Self-hosted option, visual builder, Cost for volume |
| Monitoring | Datadog | New Relic, Grafana, Prometheus | APM + Logs + RUM, Snowflake integration, alerting |

---

## 11. Future Architecture Considerations

- **Phase 2:** Dedicated Snowflake warehouse per major customer (physical multi-tenancy)
- **Phase 3:** GraphQL API layer for mobile app flexibility
- **Phase 3:** Event streaming (Kafka) for real-time occupancy updates
- **Phase 3:** Feature store (Tecton) for predictive model inputs
- **Phase 4:** Federated search (multiple data warehouses per customer)

---

**Document Status:** Ready for implementation  
**Architecture Review Date:** 2026-03-11  
**Next Step:** Database schema design review
