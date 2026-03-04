# Portfolio Intelligence Hub - Technical Decision Log

**Version:** 1.0  
**Status:** Active  
**Last Updated:** 2026-03-04  
**Owner:** Engineering Leadership  
**Purpose:** Record of major technical decisions, rationale, and outcomes

---

## Decision Template

```
## [Decision Title]
**Date:** YYYY-MM-DD  
**Status:** [DECIDED / PENDING / REVISIT]  
**Owner:** [Name]  
**Impact:** [CRITICAL / HIGH / MEDIUM]  

### Context
[Background on the problem and decision urgency]

### Options Considered
| Option | Pros | Cons | Cost | Effort |
|--------|------|------|------|--------|
| A | | | | |
| B | | | | |

### Decision
[What we decided and why]

### Consequences
[Short-term impacts, long-term implications, risks, reversibility]

### Follow-up
[Measurement plan, review date, contingencies]
```

---

## Decision 1: Data Warehouse Selection (Snowflake vs. BigQuery vs. Redshift)

**Date:** 2026-02-01  
**Status:** DECIDED  
**Owner:** Engineering Lead  
**Impact:** CRITICAL  

### Context
Portfolio Intelligence Hub requires a data warehouse that handles:
- Real estate operational data (87 properties, 3,665 units)
- Dynamic filtering for 45 users with property-level RBAC
- Text-to-SQL SQL generation with complex schema
- Real-time and batch queries mixed
- Multi-tenant logical isolation

All three major cloud data warehouses are viable; decision will lock us into specific technical patterns for 3-5 years.

### Options Considered

| Option | Pros | Cons | Cost Est. | Notes |
|--------|------|------|----------|--------|
| **Snowflake** | Excellent Text-to-SQL support (clear schema), Dynamic views for RBAC, Supabase integration via native API, Schema cloning, Native RBAC | Higher cost per query, Concurrency limits, No columnar compression on small tables | $5K/mo @ 100 queries/day | ✓ SELECTED |
| **BigQuery** | Lowest per-query cost, Excellent analytics, columnar compression | Less ideal for real-time OLTP, Complex RLS setup, Schema understanding harder for LLMs, No native vectors | $2K/mo but 10x latency | |
| **Redshift** | Good price/performance, Native support for complex queries | Older technology, Smaller ecosystem, Less support for RBAC, More ops-heavy | $3K/mo | |

### Decision
**Selected: Snowflake**

**Rationale:**
1. **Text-to-SQL Alignment:** Snowflake's clear, well-documented schema makes it easier for Claude Opus 4 to generate correct SQL. BigQuery's legacy SQL and array-heavy schema cause ~15% more errors in preliminary testing.

2. **RBAC Simplicity:** Snowflake's dynamic views (WHERE clause based on context) map perfectly to our user filtering model. BigQuery's RLS is more restrictive and BigQuery's query engine doesn't handle per-user table filtering as elegantly.

3. **Supabase Integration:** Supabase (PostgreSQL) integrates seamlessly with Snowflake via connectors. BigQuery integration requires more ETL plumbing.

4. **Schema Sharing:** For Fase 1, if we need to onboard 2nd customer, Snowflake's schema cloning makes logical multi-tenancy easier than BigQuery partitioning.

5. **Cost Tradeoff:** Snowflake is 2-3x cost per query but 10x faster, making total cost-per-answer comparable. For 100 queries/day × $5K/mo = $50/query credit cost acceptable for <5 sec p95 latency.

### Consequences

**Short-term:**
- Engineering team needs Snowflake training (1-2 weeks)
- Data migration from client's existing system (3 weeks)
- No vendor lock-in risk (standard SQL, easy to BigQuery migration if needed)

**Long-term:**
- Scalability: Can grow to 500+ queries/day without warehouse resizing until Phase 2
- Cost growth: Will scale with query volume (1-2K credits/mo at Phase 2 scale)
- Operational: Need to manage warehouse auto-scaling, monitor costs

**Risks & Mitigations:**
- Risk: Cost exceeds budget if query complexity increases
  - Mitigation: Implement query optimizer, materialized views, caching layer
- Risk: Vendor price increase (Snowflake raised prices 2024-2025)
  - Mitigation: Snowflake contract negotiation, 3-year lock-in discount

### Follow-up
- **Measurement:** Track average cost per query monthly (target <$0.10 by Phase 1)
- **Review Date:** 2026-08-01 (reassess if cost >$8K/mo)
- **Contingency:** BigQuery migration path documented (would delay 4-6 weeks if executed)

---

## Decision 2: LLM Selection for Text-to-SQL (Claude vs. GPT-4 vs. Open Source)

**Date:** 2026-02-05  
**Status:** DECIDED  
**Owner:** AI/ML Lead  
**Impact:** CRITICAL  

### Context
Text-to-SQL generation is the core intelligence feature. Accuracy directly impacts user trust and product adoption. Model choice affects cost, latency, and accuracy.

Preliminary testing on gold-standard query set (100 real estate queries):
- Claude Opus 4: 95.2% F1, 2.8s latency, $0.03/query
- GPT-4 Turbo: 93.8% F1, 1.9s latency, $0.04/query
- Llama-70B (self-hosted): 89.1% F1, 4.5s latency, $0 API cost but $8K/mo infra

### Options Considered

| Option | F1 Accuracy | Latency | Cost/Query | Context Window | Rationale |
|--------|-------------|---------|-----------|----------------|-----------|
| **Claude Opus 4** | 95.2% | 2.8s | $0.03 | 60K tokens | ✓ SELECTED |
| GPT-4 Turbo | 93.8% | 1.9s | $0.04 | 128K tokens | Close alternative |
| Llama-70B OSS | 89.1% | 4.5s | ~$0/API | 4K tokens | Cost trap (ops overhead) |
| Claude 3.5 Sonnet | 91.3% | 1.5s | $0.006 | 60K tokens | Lower accuracy, low cost |

### Decision
**Selected: Claude Opus 4**

**Rationale:**
1. **Accuracy is Primary Goal:** 95.2% F1 vs 93.8% (GPT-4) means 1.4pp better. On 100 queries/day, that's ~1 extra correct query per day. User trust and adoption depend on reliability; 1-2% error rate differential is material.

2. **Context Window:** 60K tokens sufficient for our Snowflake schema context + 10 in-context examples. GPT-4 Turbo's 128K is overkill; Claude's 60K gives us room for future expanded schema (9 tables → 20+ tables in Phase 3).

3. **Cost vs. Speed Tradeoff:** Claude is $0.01/query more expensive than Sonnet but 4pp more accurate. At 100 queries/day, +$1/day cost is acceptable for reliability.

4. **Latency Acceptable:** 2.8s Claude vs 1.9s GPT-4 = 0.9s difference. In 5s total latency budget, this is acceptable because SQL execution (1s) dominates.

5. **Prompt Caching:** Claude Opus 4 supports prompt caching; static schema context can be cached at 90% cost reduction on repeat queries.

### Consequences

**Short-term:**
- Anthropic API setup + rate limit increase (1 week)
- Fine-tune prompt for real estate domain (2 weeks)
- Build in-context learning framework for failed queries (1 week)

**Long-term:**
- Dependent on Anthropic API availability (not self-hosted)
- Cost will scale with query volume (~$3K/mo at 1,000 queries/day)
- Model updates may require re-tuning prompts (quarterly reviews needed)

**Risks & Mitigations:**
- Risk: Anthropic releases newer model (Opus 5+) and Opus 4 becomes deprecated
  - Mitigation: Anthropic has stated 18-month model support window; budget for testing/migration
- Risk: Prompt caching reduces cost but adds latency on first call
  - Mitigation: Cache schema once at startup, not per-query
- Risk: If accuracy drops below 93% in production, need emergency fallback
  - Mitigation: Maintain GPT-4 Turbo as backup (add conditional fallback logic)

### Follow-up
- **Measurement:** Weekly F1 tracking on gold-standard set
- **Review Date:** 2026-05-01 (reassess if F1 drops <94%)
- **Contingency:** GPT-4 Turbo fallback implemented for low-confidence queries (<0.7 confidence)

---

## Decision 3: Vector Database Selection (Supabase pgvector vs. Pinecone vs. Weaviate)

**Date:** 2026-02-08  
**Status:** DECIDED  
**Owner:** Data Engineering Lead  
**Impact:** CRITICAL  

### Context
Semantic search requires vector storage and similarity search for ~150K document chunks. Options differ in:
- Hosting model (managed vs. self-hosted)
- Cost structure (per-dimension, per-query, or per-storage)
- Integration complexity
- Vendor lock-in risk

### Options Considered

| Option | Cost/Mo | Latency | Integration | Vendor Lock-in | Notes |
|--------|---------|---------|-------------|---|---------|
| **Supabase pgvector** | $200-300 (included in DB) | <500ms | Native (PostgreSQL) | LOW | ✓ SELECTED |
| Pinecone | $0.25/1M vectors/mo | <100ms | HTTP API | MEDIUM | No HNSW control |
| Weaviate | $50-100 (self-hosted) | <300ms | GraphQL API | LOW | More ops burden |
| Chroma | Free (self-hosted) | <500ms | Python library | LOW | Less mature |

### Decision
**Selected: Supabase pgvector**

**Rationale:**
1. **Cost Efficiency:** Supabase pgvector is included in PostgreSQL storage cost (~$300/mo total for app layer) vs. Pinecone's vector-specific pricing ($0.25/1M vectors = $37.50/mo for 150K vectors, but requires separate vendor relationship).

2. **Collocated Storage:** Keeping vectors in PostgreSQL alongside document metadata (tables: documents, document_chunks) eliminates ETL between systems. Supabase is already app database; natural fit.

3. **RLS Integration:** Supabase RLS policies work natively with vector search. Pinecone has no RLS; would require application-layer filtering (complexity, performance overhead).

4. **No Vendor Lock-in:** pgvector is PostgreSQL native (open standard). Can migrate to Weaviate, Milvus, or self-hosted Postgres on any cloud if needed.

5. **Development Experience:** Supabase client library (JavaScript) makes vector queries simple:
   ```javascript
   const { data } = await supabase.rpc('match_documents', {
     query_embedding: embedding,
     match_threshold: 0.7
   })
   ```
   vs. Pinecone's separate API.

### Consequences

**Short-term:**
- Enable pgvector extension in Supabase (1 day)
- Create HNSW index on embeddings (1 week for 150K vectors)
- Implement similarity search functions (1 week)

**Long-term:**
- PostgreSQL HNSW is less mature than Pinecone's Rust implementation; expect ~2x slower latency
- Scaling beyond 10M vectors may require dedicated Postgres instance (Phase 3)
- Index maintenance overhead (5-10% query cost increase vs. Pinecone)

**Risks & Mitigations:**
- Risk: HNSW performance degrades with >500K vectors
  - Mitigation: Monitor index performance, evaluate dedicated vector DB at Phase 3 if needed
- Risk: PostgreSQL upgrade breaks pgvector compatibility
  - Mitigation: Test upgrades in staging first, maintain manual index backups
- Risk: Supabase outage takes down both app and vector search
  - Mitigation: Implement cache layer (Redis) for frequent searches, async fallback

### Follow-up
- **Measurement:** Track semantic search p95 latency monthly (target <500ms)
- **Review Date:** 2026-08-01 (if >1M vectors, revisit for dedicated vector DB)
- **Contingency:** Pinecone migration script documented (would take 2 weeks to execute)

---

## Decision 4: Document Chunking Strategy (Semantic vs. Fixed-Size)

**Date:** 2026-02-10  
**Status:** DECIDED (Phase 0 uses fixed-size, Phase 1 upgrades to semantic)  
**Owner:** ML Engineer  
**Impact:** MEDIUM  

### Context
Document ingestion splits PDFs into chunks for embedding. Chunk quality affects semantic search precision (NDCG@5).

Two approaches:
1. **Fixed-Size:** Split every 512 tokens (predictable, simple, fast)
2. **Semantic:** Split at sentence/clause boundaries (better context, slower, more complex)

Testing showed fixed-size NDCG@5 = 0.72, semantic NDCG@5 = 0.84 (+12 points).

### Options Considered

| Option | NDCG@5 | Chunking Time | Complexity | Cost |
|--------|--------|---------------|-----------|------|
| **Fixed-Size (512 tokens)** | 0.72 | <1 sec/doc | Simple | $0 |
| **Semantic (sentences)** | 0.84 | ~3 sec/doc | Medium | $0 |
| **LLM-based (Claude)** | 0.88 | ~30 sec/doc | Complex | $0.10/doc |

### Decision
**Phase 0:** Fixed-size chunking (for speed-to-launch)  
**Phase 1 (Week 10):** Upgrade to semantic chunking (NLTK sentence tokenizer)

**Rationale:**
1. **Phase 0 MVP:** Fixed-size is good enough (0.72 NDCG@5) for initial validation. Users won't notice if 3/5 retrieved documents are relevant vs. 4/5.

2. **Launch Speed:** Semantic chunking adds 2 weeks of development (NLP pipeline, unit tests). Fixed-size gets to MVP in time.

3. **Phase 1 Upgrade:** By week 10, we have production usage data showing semantic search gaps. Upgrade timing aligns with Cohere reranking integration (week 10 roadmap).

4. **LLM-based Rejected:** Using Claude to semantically chunk documents is overkill ($0.10/doc × 500 docs = $50 cost, 30 sec per doc too slow) for marginal NDCG@5 gain (0.84 → 0.88).

### Consequences

**Short-term (Phase 0):**
- Users may ask questions that fixed-size chunking answers poorly
- Mitigation: Confidence scoring + suggest document refinement

**Long-term (Phase 1):**
- NDCG@5 improves from 0.72 → 0.84, user satisfaction increases
- No customer friction because Phase 1 reranking makes relevance less critical
- Semantic chunking is reversible (re-chunk existing documents)

**Risks & Mitigations:**
- Risk: Semantic chunking with NLTK fails on formatted documents (tables, lists)
  - Mitigation: Fall back to fixed-size if tokenizer fails, manual curation for critical docs
- Risk: Sentence boundaries create chunks <100 tokens (too short for context)
  - Mitigation: Merge consecutive short chunks until >=200 tokens

### Follow-up
- **Measurement:** Track NDCG@5 before/after semantic chunking upgrade (target 0.84+)
- **Review Date:** 2026-05-01 (evaluate if semantic upgrade worth the complexity)
- **Contingency:** Revert to fixed-size if semantic chunking causes >5% error rate

---

## Decision 5: UI Architecture (Chat-First vs. Dashboard-First)

**Date:** 2026-02-12  
**Status:** DECIDED  
**Owner:** Product Lead + Frontend Lead  
**Impact:** MEDIUM (user experience critical for adoption)  

### Context
UI design determines user onboarding experience and discovery patterns.

Two UX patterns:
1. **Chat-First:** Conversational interface (ChatGPT-like)
2. **Dashboard-First:** Pre-built dashboards + query builder (Tableau-like)

User testing with 3 personas showed:
- Property Manager: Prefers chat (80%), dashboard second
- Finance: Prefers dashboard (70%), chat for ad-hoc
- Executive: Prefers dashboard (90%), wants summarization

### Options Considered

| Option | Property Mgr | Finance | Executive | Onboarding | Discovery | Notes |
|--------|---|---|---|---|---|---|
| **Chat-First** | 80% pref | 30% pref | 10% pref | Easy (1 question) | Low (user must know to ask) | ✓ SELECTED + HYBRID |
| Dashboard-First | 20% | 70% | 90% | Moderate (dashboard tour) | High (pre-built KPIs visible) | Too passive for PMs |
| Hybrid (Chat + Dashboard) | 90% | 85% | 95% | Moderate | High + Easy | Best compromise |

### Decision
**Selected: Hybrid (Dashboard + Chat)**

**Rationale:**
1. **Persona Diversity:** Single UI pattern (chat or dashboard) alienates 70-80% of users. Hybrid serves all personas.

2. **Onboarding:** Dashboards provide immediate value (Property Manager sees occupancy at a glance), reducing "why am I here?" skepticism. Chat is second-tier for power users.

3. **Discovery:** Dashboard shows available KPIs, helping users learn what's possible. Chat alone requires users to know what to ask.

4. **Fallback:** If user's question isn't understood, they can see pre-built dashboard for reference data.

5. **Development Parity:** Building both is ~1.2x development cost of single approach; hybrid splits time 60% dashboard / 40% chat.

### Consequences

**Short-term:**
- Build Next.js + React dashboard + chat components (3 weeks)
- Dashboard initial set: occupancy, collections, financials, work orders
- Chat handles ad-hoc questions beyond dashboard

**Long-term:**
- Maintenance burden (2 UX patterns), but offset by user satisfaction
- Mobile app (Phase 3) will be chat-first (dashboards less usable on phone)

**Risks & Mitigations:**
- Risk: Users confused by dual interfaces
  - Mitigation: Clear visual distinction, onboarding wizard explains both
- Risk: Dashboard maintenance burden grows (adding KPI requires coding)
  - Mitigation: Implement KPI builder for non-technical admins (Phase 3)

### Follow-up
- **Measurement:** Track NPS by UI preference (chat vs. dashboard users)
- **Review Date:** 2026-06-01 (evaluate if one pattern clearly dominant)
- **Contingency:** Deprecate chat-first or dashboard-first based on usage data

---

## Decision 6: Multi-Tenancy Model (Logical vs. Physical)

**Date:** 2026-02-15  
**Status:** DECIDED  
**Owner:** Engineering Lead  
**Impact:** HIGH  

### Context
Portfolio Intelligence Hub MVP is single-tenant (1 client). But planning for multi-tenant future (Phase 2+).

Two architectural models:
1. **Logical Multi-Tenancy:** All clients share Snowflake warehouse/schema, filtered by tenant_id in queries
2. **Physical Multi-Tenancy:** Each client has dedicated Snowflake warehouse and schema

### Options Considered

| Option | Initial Cost | Scaling Cost | Isolation | Complexity | Notes |
|--------|---|---|---|---|---|
| **Logical (Shared)** | $5K/mo | +$500/client | Medium (SQL filtering) | Low | ✓ SELECTED (Phase 0-1) |
| Physical (Dedicated) | $15K/mo | +$5K/client | High | High | Switch in Phase 2+ |

### Decision
**Phase 0-1:** Logical multi-tenancy (single shared warehouse)  
**Phase 2+:** Migrate to physical multi-tenancy per client (if customer count >3)

**Rationale:**
1. **Launch Speed:** Logical multi-tenancy has no tenant isolation plumbing. Data is filtered at query time, no data duplication.

2. **Cost:** Shared warehouse costs $5K/mo vs. $15K/mo for dedicated. For MVP with 1 customer, logical is 3x cheaper.

3. **Future Flexibility:** Logical multi-tenancy can grow to 5-10 small customers without issue. If we reach 10+ customers, switch to physical.

4. **Reversibility:** Can migrate from logical → physical (create separate warehouse, copy+filter data). Not the other way.

5. **Data Compliance:** Logical isolation is acceptable for real estate operator data (not PII-heavy like healthcare). If customers later require HIPAA-level isolation, we migrate to physical.

### Consequences

**Short-term (Phase 0-1):**
- Simpler data model (no tenant_id clutter)
- Lower ops burden
- Cost savings (~$10K/mo for 1 customer)

**Long-term (Phase 2+):**
- If customer count grows beyond 3, will need physical multi-tenancy migration
- Migration effort: 4-6 weeks (new warehouse, data cloning, testing)
- Cost increase when physical model kicks in (~$15K/mo per customer)

**Risks & Mitigations:**
- Risk: Customer 2 demands dedicated warehouse for data sovereignty
  - Mitigation: Physical multi-tenancy migration prepared; offer as premium tier
- Risk: Single warehouse downtime affects all customers
  - Mitigation: Implement Snowflake failover (HA setup, +$2K/mo cost)

### Follow-up
- **Measurement:** Track customer count (decision trigger at >3 customers)
- **Review Date:** 2026-09-01 (or when customer count = 3)
- **Contingency:** Physical multi-tenancy architecture documented; could execute in 4-6 weeks

---

## Decision 7: Caching Strategy (Redis for Queries, Materialized Views for KPIs)

**Date:** 2026-02-18  
**Status:** DECIDED  
**Owner:** DevOps Lead  
**Impact:** MEDIUM (performance optimization)  

### Context
Reducing latency requires caching. Three caching approaches:
1. **Query result caching (Redis):** Cache full SQL query results (top 50 queries)
2. **Materialized views (Snowflake):** Pre-compute aggregated KPIs (portfolio_kpi_summary)
3. **Both:** Hybrid approach

Testing showed:
- Most frequent queries (top 50 out of 500 unique) account for 40% of query volume
- KPI queries (occupancy, NOI, collections) repeat 3-5x daily
- Cache hit rate potential: 30-40%

### Options Considered

| Option | Cache Hit Rate | Latency Improvement | Complexity | Cost |
|--------|---|---|---|---|
| **Redis (Query Cache)** | 20-30% | 8s → 2s (cache miss), <100ms (hit) | Medium | $200/mo |
| **Materialized Views** | 60%+ (KPI queries) | 5s → <500ms | Medium | $100/mo (extra storage) |
| **Both (Hybrid)** | 40-50% overall | 8s → <500ms (avg) | High | $300/mo | ✓ SELECTED |

### Decision
**Selected: Hybrid (Redis + Materialized Views)**

**Rationale:**
1. **Query-Level Caching (Redis):** Cache results of frequently asked queries (e.g., "occupancy at Riverside Plaza"). TTL = 1-4 hours (depends on data freshness requirement).

2. **KPI Caching (Materialized Views):** Pre-compute expensive aggregations nightly (portfolio_kpi_summary, property_performance_scorecard). Updated 1x daily after financial close.

3. **Combined Benefits:** 
   - Chat queries (Q: "occupancy?") hit Redis cache (typical repeat)
   - Dashboard KPI tiles (portfolio scorecards) hit materialized views
   - Together = 40% cache hit rate, avg latency drops from 8s → 2-3s

4. **Cost Tradeoff:** +$100-200/mo for caching infrastructure, but saves ~$500/mo in Snowflake credits (query reduction). ROI: positive immediately.

### Consequences

**Short-term:**
- Build Redis cluster (AWS ElastiCache, $200/mo)
- Implement query cache middleware in FastAPI (2 weeks)
- Schedule materialized view refreshes (Snowflake tasks)

**Long-term:**
- Cache invalidation complexity (stale data risk)
- Redis failover ops (handle node failures)
- Monitor cache hit rates, adjust TTLs quarterly

**Risks & Mitigations:**
- Risk: Stale cache serves incorrect data (e.g., occupancy from 12 hours ago)
  - Mitigation: Manual cache invalidation button for admins, TTL = 1-4 hours based on data type
- Risk: Cache fills up, evicts important queries
  - Mitigation: Implement LRU eviction policy, monitor Redis memory

### Follow-up
- **Measurement:** Track cache hit rate weekly (target 40% by Phase 1)
- **Review Date:** 2026-06-01 (evaluate if Redis cost justified)
- **Contingency:** Disable Redis if hit rate <20% (cost exceeds benefit)

---

## Decision 8: Document Storage Approach (Supabase Blobs + External S3 vs. All-in-Supabase)

**Date:** 2026-02-20  
**Status:** DECIDED  
**Owner:** Backend Lead  
**Impact:** MEDIUM (storage architecture)  

### Context
Need to store ~500 documents (leases, reports) with retrieval speed requirements. Two models:
1. **All-in-Supabase:** Store PDFs in Supabase storage, chunks in pgvector
2. **Hybrid:** PDFs in S3, chunks + metadata in Supabase

### Options Considered

| Option | Cost | Latency | Compliance | Complexity | Notes |
|--------|---|---|---|---|---|
| **All-in-Supabase** | $500/mo (storage) | Medium (S3 redirect) | High (encrypted) | Low | Simple architecture |
| **Hybrid (S3 + Supabase)** | $50/mo (S3) + $200 (Supabase) | Low (pre-signed URL) | Very High | Medium | ✓ SELECTED |

### Decision
**Selected: Hybrid (S3 + Supabase)**

**Rationale:**
1. **Cost:** S3 ($0.023/GB) is 10x cheaper than Supabase storage ($0.25/GB) for PDFs.

2. **Latency:** Serve documents from S3 directly (pre-signed URLs in metadata), avoid Supabase bandwidth costs.

3. **Separation of Concerns:** 
   - Supabase: chunks + metadata + vectors
   - S3: original documents (immutable, versioned)

4. **Compliance:** S3 versioning + lifecycle policies support document archival (meet 2-year retention requirement).

5. **Scale:** For 500 docs (100MB total), Supabase is fine. But if scaling to 5,000 docs (1GB) in Phase 2, S3 avoids hitting Supabase limits.

### Consequences

**Short-term:**
- Set up S3 bucket with CORS + pre-signed URLs (1 week)
- Migrate storage layer metadata (document_url field) (1 week)
- Document retrieval: Supabase metadata → S3 pre-signed URL

**Long-term:**
- S3 versioning overhead (old versions clutter bucket)
- Lifecycle policy automation (delete old versions after 90 days)
- Cross-region replication if needed for disaster recovery

**Risks & Mitigations:**
- Risk: S3 bucket becomes public (security incident)
  - Mitigation: CloudFront OAI (Origin Access Identity), no direct S3 access
- Risk: Pre-signed URL expires, document becomes inaccessible
  - Mitigation: URL validity 24 hours, refresh on access

### Follow-up
- **Measurement:** Track S3 storage size growth monthly
- **Review Date:** 2026-06-01 (if >2GB, evaluate archival strategy)
- **Contingency:** Switch to all-Supabase if S3 complexity becomes burden

---

## Decision 9: Embedding Model Selection (OpenAI embedding-3-large vs. Open Source)

**Date:** 2026-02-22  
**Status:** DECIDED  
**Owner:** ML Lead  
**Impact:** HIGH (semantic search quality)  

### Context
Document semantic search quality depends on embedding model. Two candidates:
1. **OpenAI embedding-3-large:** 3,072 dimensions, SOTA retrieval, $0.02/1M tokens
2. **Open-source (Instructor, BGE):** 384-768 dims, free/cheap, less accurate

Testing on 100 semantic search queries:
- OpenAI embedding-3-large: NDCG@5 = 0.82 (before reranking)
- Instructor XL: NDCG@5 = 0.64
- BGE-large: NDCG@5 = 0.75

### Options Considered

| Option | NDCG@5 | Cost/Month | Latency | Hosting | Notes |
|--------|--------|-----------|---------|---------|--------|
| **OpenAI embedding-3-large** | 0.82 | $0.30 (500 docs × $0.0003) | 100ms | API | ✓ SELECTED |
| Instructor XL | 0.64 | $0 (self-hosted) | 500ms | Hugging Face | 12 pp worse quality |
| BGE-large | 0.75 | $0 (self-hosted) | 300ms | Hugging Face | 7 pp worse quality |

### Decision
**Selected: OpenAI embedding-3-large**

**Rationale:**
1. **Quality is Non-Negotiable:** Semantic search failures directly reduce user trust. 0.82 NDCG@5 (80% of retrieved docs relevant) vs. 0.75 (75% relevant) is material difference.

2. **Cost is Minimal:** $0.30/mo for all document embeddings is rounding error vs. $5K/mo Snowflake cost. Cost/doc = $0.0006 (negligible).

3. **Latency Acceptable:** 100ms embedding latency is fast; self-hosted would add 300-500ms overhead, unacceptable for user experience.

4. **Batch Processing:** For 500 docs, batch embedding to further reduce per-doc cost (50% savings). Only new docs trigger real-time embedding.

5. **Dimension Advantage:** 3,072 dims allow finer-grained similarity than 768-dim models. Overkill now but valuable headroom for Phase 3 (market comps, custom embeddings).

### Consequences

**Short-term:**
- Minimal setup (OpenAI API key)
- Batch embedding pipeline (import 500 existing leases)
- Cost: ~$0.30/mo embedding cost

**Long-term:**
- Dependent on OpenAI pricing (could increase)
- Model updates may require re-embedding (major operation for 1M+ vectors at scale)
- SLA: OpenAI uptime (99.99%), not within our control

**Risks & Mitigations:**
- Risk: OpenAI deprecates embedding-3-large
  - Mitigation: OpenAI has 2+ year support window; budget for migration if needed
- Risk: Cost increases with volume (1,000 docs → $0.60/mo)
  - Mitigation: Acceptable cost scaling; even at Phase 3 scale (10K docs = $6/mo)

### Follow-up
- **Measurement:** Track embedding cost monthly (budget $5/mo for Phase 2)
- **Review Date:** 2026-09-01 (if cost >$2/mo, explore batch processing optimizations)
- **Contingency:** BGE-large fallback if OpenAI API becomes unreliable

---

## Decision 10: Reranking Strategy (Cohere vs. Cross-Encoder vs. None)

**Date:** 2026-02-25  
**Status:** DECIDED (Phase 0 = none, Phase 1 = Cohere)  
**Owner:** ML Lead  
**Impact:** MEDIUM (semantic search optimization)  

### Context
Vector retrieval returns top-50 candidates. Need to rerank to top-5 for user display. Two approaches:
1. **No Reranking:** Return top-5 from vector similarity (NDCG@5 = 0.82)
2. **Cohere Rerank:** Use specialized ranking model (NDCG@5 = 0.88, +6pp improvement)
3. **Cross-Encoder:** Self-hosted transformer model (NDCG@5 = 0.87, similar cost/performance as Cohere)

### Options Considered

| Option | NDCG@5 Improvement | Cost | Latency | Complexity | Notes |
|--------|---|---|---|---|---|
| **No Reranking** | Baseline (0.82) | $0 | <100ms | None | Okay for MVP |
| **Cohere rerank-english-v3.0** | 0.88 (+6pp) | $0.001/100 docs | 200ms | Low | ✓ SELECTED (Phase 1) |
| **Cross-Encoder (BGE)** | 0.87 (+5pp) | $0 (self-hosted) | 1000ms | High | Self-hosting overhead |

### Decision
**Phase 0:** No reranking (launch faster, NDCG@5 = 0.82 acceptable)  
**Phase 1 (Week 10):** Add Cohere reranking (improve NDCG@5 → 0.88)

**Rationale:**
1. **Phase 0 MVP:** 0.82 NDCG@5 is good enough for POV. Reranking adds 200ms latency and complexity; not critical for launch.

2. **Phase 1 Upgrade:** By week 10, have production data showing user satisfaction gaps. Cohere reranking is quick (2-day integration) and measurable (test on gold-standard set).

3. **Cost:** $0.001/100 docs = $0.001 per query (for 100 candidate documents). Negligible cost for 6pp quality improvement.

4. **Latency Acceptable:** 200ms reranking latency + 300ms embedding latency = 500ms total for semantic search (within 5s overall budget).

5. **Cross-Encoder Rejected:** Self-hosted cross-encoder would require 1000ms latency (ML inference on GPU), not worth it vs. Cohere's 200ms for identical accuracy.

### Consequences

**Short-term (Phase 0):**
- Users might see one less-relevant document in top-5
- Mitigation: Phase 1 reranking fixes this; monitor satisfaction

**Long-term (Phase 1+):**
- Cohere reranking adds $50/mo cost (if 1K semantic queries/day)
- Scalable cost (per-query billing)
- Optional optimization (can disable if cost becomes concern)

**Risks & Mitigations:**
- Risk: Cohere reranking model biases certain document types
  - Mitigation: A/B test reranking on sample of users
- Risk: Cohere API downtime impacts semantic search
  - Mitigation: Fallback to non-reranked results if Cohere unavailable

### Follow-up
- **Measurement:** Track NDCG@5 improvement Phase 0 → Phase 1 (target 0.82 → 0.88)
- **Review Date:** 2026-05-01 (evaluate if 6pp improvement worth $50/mo cost)
- **Contingency:** Disable reranking if NDCG@5 doesn't improve as expected

---

## Summary of Decisions

| Decision | Phase 0 | Phase 1+ | Reversible | Cost Impact |
|----------|---------|----------|-----------|------------|
| 1. Snowflake | ✓ Selected | ✓ Locked | No (high cost) | +$5K/mo |
| 2. Claude Opus 4 | ✓ Selected | ✓ Locked | Yes (effort-heavy) | +$3K/mo @ scale |
| 3. Supabase pgvector | ✓ Selected | ✓ Locked | Yes (medium effort) | Included in DB |
| 4. Fixed-size chunking | ✓ Selected | ✗ Upgrade (W10) | Yes (low cost) | $0 |
| 5. Dashboard + Chat | ✓ Selected | ✓ Locked | No (refactor) | +1 week dev |
| 6. Logical multi-tenancy | ✓ Selected | ✗ Upgrade (Phase 2) | Yes (4-6 weeks) | -$10K/mo now |
| 7. Redis + Materialized Views | - | ✓ Selected (W8) | Yes (disable) | +$300/mo |
| 8. S3 + Supabase hybrid | - | ✓ Selected (W8) | Yes (refactor) | +$50/mo |
| 9. OpenAI embedding-3-large | - | ✓ Selected | Yes (re-embed all) | +$0.30/mo |
| 10. Cohere reranking | - | ✓ Selected (W10) | Yes (optional) | +$50/mo |

---

**Document Status:** Active decision tracking  
**Review Cadence:** Add new decisions as they arise, review existing decisions quarterly  
**Next Review Date:** 2026-06-04
