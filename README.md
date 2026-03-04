# Portfolio Intelligence Hub

**RAG-Powered Natural Language Analytics for Real Estate Portfolios — reducing report turnaround from 2-3 days to under 30 seconds across 87 properties and 4 user personas**

A natural language intelligence platform that sits on top of Snowflake, combining Text-to-SQL generation with semantic document search to let real estate operators query their portfolio data conversationally. Built for a mid-market operator managing 87 properties across 12 states, this system replaced a two-analyst bottleneck with self-service analytics — property managers, brokers, finance teams, and executives all ask questions in plain English and get answers in seconds.

---

## The Problem

A mid-market real estate operator manages a mixed-use portfolio of 87 properties (apartments, commercial office, retail, industrial) across 12 states with a $150M+ annual operating budget. Their data lives in Snowflake, but the operational reality is:

- **Two-analyst bottleneck** — Only 2 data analysts can write SQL. 45+ internal users (property managers, brokers, controllers, executives) submit ad-hoc requests via email and wait 24-48 hours for answers. Analysts spend 340+ hours/month fielding these requests instead of doing strategic analysis.

- **Scattered unstructured data** — Lease agreements, inspection reports, and maintenance logs are stored across Dropbox, email attachments, and shared drives. Finding "all leases with renewal options expiring in Q2" requires manually opening documents across 87 properties.

- **Inconsistent reporting** — Each property manager builds their own Excel reports with different formulas, time periods, and definitions of metrics like NOI or occupancy rate. Finance spends 3 days each month just reconciling these into a portfolio view.

- **Slow decisions** — The CIO wants to identify underperforming properties for disposition, but getting a comprehensive portfolio scorecard takes a week of analyst time. Market opportunities pass while the team waits for data.

- **No self-service** — Property managers can't check their own work order backlogs without emailing an analyst. Brokers can't pull available unit listings without calling each property individually. Every question, no matter how simple, goes through the same 24-48 hour queue.

## The Solution

A conversational analytics platform that combines two engines — **Text-to-SQL** for structured Snowflake queries and **RAG-based semantic search** for unstructured documents — behind a single natural language interface, with role-based access control ensuring each persona sees only their data.

**Core Capabilities:**

- **Text-to-SQL Generation** — Natural language questions are classified, mapped to Snowflake tables via a semantic business layer, and converted to valid SQL using Claude with few-shot prompting. "Which buildings have the most open work orders?" becomes a fully-formed Snowflake query in under 2 seconds.

- **Semantic Document Search** — Lease agreements, inspection reports, and maintenance logs are chunked at semantic boundaries (clause-level for leases, section-level for reports), embedded with OpenAI, and searched via hybrid BM25 + vector retrieval with Cohere reranking. "Show me all leases with early termination clauses" surfaces the exact clauses across 200+ documents.

- **Multi-Persona Access Control** — Property managers see only their assigned buildings. Brokers see leasing data across all properties. Finance sees complete financials. Executives see aggregated portfolio views. Enforced at both the Snowflake view level and Supabase RLS.

- **Business Metric Semantic Layer** — 15+ real estate KPIs (NOI, occupancy rate, cap rate, maintenance cost per unit, rent collection rate, budget variance) are defined once in the semantic layer, ensuring every query uses the same formula regardless of who's asking.

## Results

| Metric | Before | After |
|---|---|---|
| Report turnaround (ad-hoc) | 24-48 hours | Under 30 seconds |
| Monthly analyst hours on ad-hoc queries | 340 hours | 45 hours |
| Time to portfolio KPI snapshot | 3-5 days | 30 seconds |
| SQL generation accuracy | N/A (manual only) | 89% F1 score |
| Document search relevance | Manual (hours) | NDCG@5 of 0.82 |
| Monthly active users (self-service) | 2 (analysts only) | 38 of 45 employees |
| Month-end close cycle | 10 business days | 3 business days |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER INTERFACES                               │
│  Next.js Dashboard        │  Query Interface    │  Document Viewer   │
│  - Persona-specific views │  - Natural language  │  - PDF viewer      │
│  - Suggested queries      │  - Results display   │  - Highlight match │
│  - Export controls        │  - Query history     │  - Source citation  │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
          ┌──────────────────────┐      ┌──────────────────────┐
          │   Query Router       │      │  Auth + RBAC         │
          │                      │      │  (Clerk + Supabase   │
          │ - Classify intent    │      │   RLS + Snowflake    │
          │ - Route to engine    │      │   views)             │
          │ - Check Redis cache  │      │                      │
          └──────────┬───────────┘      │  - Tenant isolation  │
                     │                  │  - Property scoping  │
          ┌──────────┼─────────────────┴─────────────────────┐
          │          │                                        │
          ▼          ▼                                        ▼
   ┌──────────────────┐  ┌───────────────────┐  ┌───────────────────┐
   │  TEXT-TO-SQL     │  │  SEMANTIC SEARCH  │  │  CACHE (Redis)    │
   │  ENGINE          │  │  ENGINE (RAG)     │  │                   │
   │                  │  │                   │  │  - Popular queries │
   │ 1. Parse intent  │  │ 1. Embed query    │  │  - Pre-aggregated │
   │ 2. Map tables    │  │ 2. BM25 keyword   │  │    portfolio KPIs │
   │ 3. Generate SQL  │  │ 3. Vector search  │  │  - 24hr TTL       │
   │ 4. Validate      │  │ 4. Cohere rerank  │  │                   │
   │ 5. Execute       │  │ 5. Synthesize     │  │                   │
   │ 6. Format        │  │    answer         │  │                   │
   └────────┬─────────┘  └────────┬──────────┘  └───────────────────┘
            │                     │
            ▼                     ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │                      DATA LAYER                                   │
   │                                                                   │
   │  ┌─────────────────────┐    ┌──────────────────────────────┐     │
   │  │   SNOWFLAKE          │    │  SUPABASE (PostgreSQL)       │     │
   │  │   (Structured Data)  │    │  (App Layer + Documents)     │     │
   │  │                      │    │                              │     │
   │  │ - Properties (87)    │    │  - pgvector embeddings       │     │
   │  │ - Units (3,665)      │    │  - Document chunks           │     │
   │  │ - Leases             │    │  - Query history             │     │
   │  │ - Financials (P&L)   │    │  - User sessions             │     │
   │  │ - Work orders        │    │  - Access logs               │     │
   │  │ - Occupancy          │    │  - RLS tenant isolation      │     │
   │  │ - Rent collections   │    │                              │     │
   │  │                      │    │  Hybrid search:              │     │
   │  │ Materialized views:  │    │  BM25 + pgvector + Cohere   │     │
   │  │ - Portfolio KPI      │    │                              │     │
   │  │ - Property scorecard │    │                              │     │
   │  └─────────────────────┘    └──────────────────────────────┘     │
   └──────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **Data Warehouse** | Snowflake | Semi-structured data support, CLUSTER BY optimization, role-based security, real estate industry standard for data lakes |
| **Text-to-SQL** | Claude API (primary), GPT-4 (fallback) | 200K context window handles full table schemas + metadata; structured JSON output for SQL generation; dual-model prevents SPOF |
| **Embeddings** | OpenAI text-embedding-3-large (3072-dim) | Best-in-class retrieval performance for domain-specific documents; cost-effective for real estate corpus (<1M chunks) |
| **Vector Search** | Supabase pgvector + HNSW indexes | Unified PostgreSQL stack eliminates data sync; RLS on documents in same DB; supports 50M+ vectors at scale |
| **Reranking** | Cohere Rerank API | 15-20% relevance improvement over raw vector similarity; handles domain-specific vocabulary well |
| **Semantic Layer** | Custom metric definitions + SQL views | Separates business logic from prompts; auditable KPI definitions; non-technical users can define custom metrics |
| **Backend** | FastAPI (Python) | Async support for concurrent queries; Pydantic validation; auto-generated OpenAPI docs |
| **Frontend** | Next.js + shadcn/ui | Persona-specific dashboards; server-side rendering for initial load; Tailwind for responsive design |
| **Auth** | Clerk (SSO/SAML) + Supabase RLS + Snowflake views | Three-layer enforcement: app-level role checks, database-level RLS, warehouse-level view filtering |
| **Async Jobs** | Trigger.dev | Document embedding batches (rate-limited), nightly MV refreshes, report generation; built-in retry + DLQ |
| **Workflows** | n8n | Visual workflow builder for document ingestion pipeline and query monitoring alerts; self-hosted for data sovereignty |
| **Email** | React Email + Resend | Component-based templates for query summaries and report notifications; TypeScript type safety |
| **Caching** | Redis | 24-hour TTL for popular queries; tenant-aware cache keys; eliminates redundant Snowflake compute |
| **Deployment** | Vercel (frontend) + Railway/Render (API) | Edge caching for static assets; serverless functions for API; preview deployments for PR review |

## Key Design Decisions

| Decision | Choice | Alternative Considered | Rationale |
|---|---|---|---|
| Data warehouse | Snowflake (not BigQuery or Redshift) | BigQuery (cheaper per-query), Redshift (AWS-native) | Snowflake's CLUSTER BY optimizes property-centric queries; role-based security simplifies RBAC; client's existing data lake was Snowflake |
| Chat-first vs dashboards | Chat interface with dynamic SQL | Pre-built dashboards (Tableau, Metabase) | Real estate questions are too diverse for static dashboards — "correlation between maintenance backlog and tenant turnover in Southeast" can't be pre-built; chat handles the long tail |
| Text-to-SQL approach | Claude + semantic layer + few-shot examples | Direct prompt-to-SQL, LangChain SQL agent, fine-tuned model | Semantic layer ensures metric consistency (everyone gets the same NOI formula); few-shot examples handle Snowflake dialect quirks; Claude's structured output reduces parsing errors |
| Vector DB | pgvector in Supabase (not Pinecone/Weaviate) | Pinecone (managed), Weaviate (self-hosted) | Documents and embeddings in same DB means RLS applies to vectors too; eliminates sync complexity; Supabase handles auth + storage + vectors in one platform |
| Document chunking | Semantic boundaries (clause-level for leases, section-level for reports) | Fixed-size 512-token chunks | Leases have natural clause boundaries — keeping "early termination" clauses intact preserves legal context; makes source attribution precise |
| Multi-tenancy | Logical isolation (tenant_id on all tables) | Physical isolation (separate Snowflake database per operator) | Logical isolation reduces ops overhead; shared materialized views reduce compute cost; fits SaaS pricing model at mid-market scale |
| Caching | Redis (24hr TTL) + Snowflake materialized views | No caching (always query Snowflake) | "Portfolio NOI" gets asked daily by 5+ people — cache eliminates redundant warehouse compute; MVs handle complex aggregations that would timeout as ad-hoc queries |

---

## Repository Structure

```
portfolio-intelligence-hub/
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
├── .cursorrules                     # Cursor AI project context
├── .replit / replit.nix             # Replit instant-run config
├── Makefile                         # install, dev, test, deploy
├── requirements.txt                 # Python dependencies
├── docker-compose.yml               # Local dev (PostgreSQL + Redis)
├── vercel.json                      # Vercel deployment + cron
│
├── docs/
│   ├── PRD.md                       # Product requirements (4 personas, phased rollout)
│   ├── ARCHITECTURE.md              # System design with ASCII diagrams
│   ├── DATA_MODEL.md                # Snowflake + Supabase schemas
│   ├── METRICS.md                   # KPIs and success measurement
│   ├── DECISION_LOG.md              # 10 technical decisions with rationale
│   └── ROADMAP.md                   # 4-phase delivery plan (40 weeks)
│
├── src/
│   ├── query_engine/
│   │   ├── router.py                # Query classification + routing
│   │   ├── text_to_sql.py           # NL → Snowflake SQL (5-step pipeline)
│   │   ├── semantic_layer.py        # 15+ business metric definitions
│   │   └── prompts.py               # Few-shot SQL examples + system prompts
│   ├── rag/
│   │   ├── document_processor.py    # PDF/doc ingestion + semantic chunking
│   │   ├── embedder.py              # OpenAI embedding with rate limiting
│   │   ├── retriever.py             # Hybrid search (BM25 + vector + rerank)
│   │   └── llm_augmentation.py      # Claude answer synthesis with citations
│   ├── connectors/
│   │   └── snowflake_connector.py   # Connection pool + tenant filtering
│   ├── access_control/
│   │   ├── rbac.py                  # 5 roles, permission checks, audit logging
│   │   └── snowflake_views.py       # Role-based view DDL generators
│   └── api/
│       ├── main.py                  # FastAPI app + middleware
│       ├── auth.py                  # Clerk JWT verification
│       └── endpoints/
│           ├── queries.py           # POST /queries, GET /history
│           ├── documents.py         # Upload + semantic search
│           └── export.py            # Report generation (Excel/PDF/CSV)
│
├── snowflake/
│   ├── schemas/
│   │   ├── properties.sql           # Properties, units, tenancies, leases
│   │   ├── financials.sql           # P&L, rent collections, occupancy
│   │   └── operations.sql           # Work orders, maintenance logs
│   ├── views/
│   │   ├── portfolio_kpi.sql        # Nightly-refreshed KPI summary
│   │   └── property_scorecard.sql   # Monthly performance scorecard
│   └── sample_queries/
│       └── example_queries.sql      # 20 example Text-to-SQL outputs
│
├── supabase/
│   └── migrations/
│       └── 001_schema.sql           # App tables + pgvector + RLS
│
├── n8n/
│   ├── document_ingestion.json      # Upload → extract → embed → notify
│   └── query_monitoring.json        # Hourly error rate → alert
│
├── trigger-jobs/
│   ├── document_embedding.ts        # Batch embed with rate limiting
│   └── materialized_view_refresh.ts # Nightly Snowflake MV refresh
│
├── emails/
│   ├── query_summary.tsx            # Query results notification
│   └── report_ready.tsx             # Report download notification
│
├── tests/
│   ├── conftest.py                  # Shared fixtures
│   ├── test_text_to_sql.py          # Text-to-SQL pipeline tests
│   ├── test_semantic_search.py      # RAG pipeline tests
│   ├── test_rbac.py                 # Access control tests
│   └── test_api.py                  # API endpoint tests
│
├── demo/
│   ├── sample_data.json             # 10 properties, 200 units, 100 work orders
│   └── run_pipeline.py              # Demo: seed data + run 20 sample queries
│
└── dashboard/
    └── query_interface.jsx          # React query interface + results
```

## Modern Stack (Production Infrastructure)

### Data & Analytics
- **Snowflake** — Primary data warehouse with CLUSTER BY optimization, materialized views, and role-based views for RBAC
- **Supabase** — App layer PostgreSQL with pgvector (HNSW indexes), RLS policies, and storage buckets for documents
- **Redis** — Query caching with tenant-aware keys and 24-hour TTL

### AI & Search
- **Claude API** — Text-to-SQL generation with 200K context window for full schema injection and few-shot prompting
- **OpenAI Embeddings** — text-embedding-3-large (3072-dim) for document chunk embeddings
- **Cohere Rerank** — Cross-encoder reranking for hybrid search result optimization

### Async Processing
- **Trigger.dev** — Document embedding batches (rate-limited OpenAI calls), nightly materialized view refresh, report generation
- **n8n Workflows** — Document ingestion pipeline (upload → extract → embed → notify) and query monitoring (hourly error rate → alert)

### Authentication & Access Control
- **Clerk** — SSO/SAML authentication with organization management
- **Three-layer RBAC** — App-level role checks → Supabase RLS → Snowflake view filtering
- **5 roles** — Admin, Property Manager, Broker, Finance, Executive (each with scoped data access)

### Email & Notifications
- **React Email** — TypeScript/JSX templates: query_summary.tsx (results notification), report_ready.tsx (download notification)
- **Resend** — Transactional email delivery

### Configuration & Deployment
- **.cursorrules** — Comprehensive Cursor AI context (architecture, personas, conventions)
- **.replit + replit.nix** — Replit cloud development with Python 3.11, Node 18, PostgreSQL, Redis
- **vercel.json** — Frontend deployment with cron jobs for MV refresh and cache warming
- **docker-compose.yml** — Local development environment (PostgreSQL + Redis + FastAPI)

---

## Product Documents

| Document | Description |
|---|---|
| [PRD](docs/PRD.md) | Full product requirements: 4 personas with workflows, functional requirements, phased rollout with exit criteria |
| [Architecture](docs/ARCHITECTURE.md) | System design: Text-to-SQL pipeline, RAG pipeline, RBAC architecture, data flow diagrams |
| [Data Model](docs/DATA_MODEL.md) | Snowflake schema (9 tables) + Supabase schema (6 tables) + materialized views + RLS policies |
| [Metrics](docs/METRICS.md) | Success measurement: Time to Insight north star, quality metrics, business metrics, before/after comparison |
| [Decision Log](docs/DECISION_LOG.md) | 10 technical decisions: Snowflake vs BigQuery, chat vs dashboards, chunking strategy, multi-tenancy model |
| [Roadmap](docs/ROADMAP.md) | 4-phase delivery plan: MVP (weeks 1-8) through Intelligence (weeks 25+) |

---

## Business Context

### Market Size
~4,200 mid-market real estate operators managing 50-500 properties in the US, with combined portfolio value exceeding $800B. These operators spend $2-4M/year on analytics, reporting, and business intelligence.

### Unit Economics

| Metric | Value |
|--------|-------|
| **Before** | |
| Monthly analyst hours on ad-hoc queries | 340 |
| Hourly analyst cost | $83 |
| Annual analyst cost | $340K |
| **After** | |
| Monthly analyst hours on ad-hoc queries | 45 |
| Hourly analyst cost | $83 |
| Annual analyst cost | $45K |
| Annual savings | $295K |
| **Decision speed improvement** | 24-48hr → <30sec |
| **Platform build cost** | **$230,000** |
| **Monthly run rate** | **$1,600** |
| **Payback period** | **10 months** |
| **3-year ROI** | **3.5x** |

### Pricing Model
If productized for real estate operators: $3,000-8,000/month based on property count and user seats, targeting $8-15M ARR at 300 operators.

---

## PM Perspective

The hardest decision was whether to use a semantic business layer (SQL views + metric mapping) or let the LLM generate raw SQL directly. Raw SQL was faster to ship — just inject the schema and let Claude generate queries. But the problem is consistency: two users asking "what's the occupancy rate?" would get different SQL depending on how the LLM interpreted it (some including pending leases, some not). The semantic layer guaranteed that "occupancy rate" always meant the same formula, regardless of who asked or how they phrased it. Added 3 weeks to Phase 2 but eliminated the "why do these numbers not match?" problem that kills trust in analytics tools.

Property managers didn't want dashboards — they wanted answers. We initially prototyped a Tableau-style dashboard with filters and drill-downs. In user testing, property managers ignored it entirely and typed questions in the search bar. They didn't want to learn a tool; they wanted to ask "which buildings have the most open work orders?" and get an answer in 10 seconds. This validated the chat-first approach and we killed the dashboard prototype entirely, redirecting that effort into improving query understanding and response formatting.

What I'd do differently: I would scope the document search (RAG) more narrowly in Phase 1. We tried to ingest everything — lease agreements, inspection reports, board minutes, vendor contracts, insurance policies — and the retrieval quality suffered. Too many document types with too little domain-specific chunking. Should have started with leases and inspection reports only (the two most-queried document types) and expanded once we had retrieval quality above 0.85 NDCG for those categories.

---

## Related Portfolio Projects

| Project | Domain | Focus |
|---|---|---|
| [AI Data Ops Platform](../ai-data-ops-platform) | ML/AI | Training data quality and annotation management |
| [Contract Intelligence Platform](../contract-intelligence-platform) | Legal/M&A | AI-powered contract analysis with multi-model orchestration |
| [Engagement & Personalization Engine](../engagement-personalization-engine) | Consumer | ML-driven personalization with experimentation platform |
| [Fintech Operations Platform](../fintech-operations-platform) | Fintech | Payment routing, settlement, and reconciliation |
| [GenAI Governance](../genai-governance) | Compliance | Enterprise guardrails and compliance for LLM deployment |
| [Infrastructure Automation Platform](../infrastructure-automation-platform) | DevOps | Self-service IaC provisioning with policy enforcement |
| [Integration Health Monitor](../integration-health-monitor) | Fintech | Multi-API health monitoring with predictive alerting |
| [Review Prep Engine](../review-prep-engine) | Wealth Management | Automated review briefing assembly |
| [Scope Tracker](../scope-tracker) | Professional Services | Scope drift detection for fixed-fee engagements |
| [Verified Services Marketplace](../verified-services-marketplace) | Marketplace | Two-sided marketplace with provider verification |

---

## Engagement & Budget

### Team & Timeline

| Role | Allocation | Duration |
|------|-----------|----------|
| Lead PM (Jacob) | 20 hrs/week | 16 weeks |
| Lead Developer (US) | 40 hrs/week | 16 weeks |
| Offshore Developer(s) | 2 × 35 hrs/week | 16 weeks |
| QA Engineer | 20 hrs/week | 16 weeks |

**Timeline:** 16 weeks total across 3 phases
- **Phase 1: Discovery & Design** (3 weeks) — Snowflake schema mapping, query pattern analysis, semantic business layer design, persona-based access control, document corpus inventory
- **Phase 2: Core Build** (9 weeks) — Text-to-SQL engine (few-shot + schema injection), RAG pipeline (hybrid BM25 + vector + Cohere rerank), property scorecard, multi-persona dashboards
- **Phase 3: Integration & Launch** (4 weeks) — Snowflake production connection, document ingestion pipeline, evaluation suite (F1 + NDCG), user pilot (property managers → finance → executives), query refinement based on production usage

### Budget Summary

| Category | Cost | Notes |
|----------|------|-------|
| PM & Strategy | $59,200 | Discovery, specs, stakeholder management |
| Development (Lead + Offshore) | $159,360 | Core platform build |
| QA Engineer | $11,200 | Testing and quality assurance |
| AI/LLM Token Budget | $9,280/total | Claude Sonnet ($320/mo), Voyage embeddings ($40/mo), Cohere Rerank ($120/mo), Haiku summarization ($100/mo) × 16 weeks |
| Infrastructure | $13,120/total | Supabase Pro ($25/mo), Snowflake ($400/mo incremental), Vercel ($20/mo), Redis ($65/mo), AWS compute ($150/mo), n8n ($50/mo), Trigger.dev ($25/mo), misc ($85/mo) × 16 weeks |
| **Total Engagement** | **$230,000** | Fixed-price, phases billed at milestones |
| **Ongoing Run Rate** | **$1,600/month** | Infrastructure + AI tokens + support |

---

## About This Project

Built as a product management engagement for a mid-market real estate operator managing 87 properties across 12 states ($150M+ annual operating budget) where only 2 analysts could access Snowflake data, creating a 24-48 hour bottleneck for every ad-hoc question. I led discovery across four personas (property managers, brokers, finance, executives) to map query patterns and information needs. Designed the Text-to-SQL engine with semantic business layer ensuring metric consistency across all personas. Made technology decisions on hybrid search architecture (BM25 + vector + Cohere rerank) and Snowflake integration. Established evaluation framework measuring SQL generation accuracy (F1), document relevance (NDCG@5), and user adoption.

**Note:** Client-identifying details have been anonymized. Code represents the architecture and design decisions I drove; production deployments were managed by client engineering teams.
