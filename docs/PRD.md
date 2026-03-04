# Portfolio Intelligence Hub - Product Requirements Document

**Version:** 1.0  
**Status:** Active Development  
**Last Updated:** 2026-03-04  
**Owner:** Product Management  
**Stakeholders:** Real Estate Operations, Finance, Brokers, Executive Leadership

---

## 1. Executive Summary

### Problem Statement
Mid-market real estate operators managing 50-200+ properties across multiple states face a critical data access bottleneck. The client operates 87 properties across 12 states (apartment, commercial, retail, industrial) with a $150M+ annual operating budget. With only 2 analysts supporting 45+ internal users, portfolio inquiries experience 24-48 hour turnaround times, delaying operational decisions.

**Current State Pain Points:**
- Property managers wait 24-48 hours for occupancy and maintenance queries
- Brokers cannot instantly access market availability or lease terms across portfolio
- Finance cannot quickly reconcile budget variance or collection status
- Executives lack real-time visibility into portfolio performance for disposition decisions
- Analysts spend 70% of their time on routine data pull requests rather than analysis
- Data inconsistencies due to manual SQL generation and copy-paste errors

### Product Vision
Portfolio Intelligence Hub is a RAG-based (Retrieval-Augmented Generation) natural language intelligence platform that enables real estate operators to ask any portfolio question in plain English and receive accurate, contextualized answers in under 30 seconds. The system combines:

1. **Text-to-SQL Engine** - Converts natural language queries to Snowflake SQL for structured data
2. **Semantic Search** - Retrieves contextual documents (leases, reports, policies) via vector embeddings
3. **Role-Based Access Control** - Enforces property-level and data-type permissions
4. **Intelligent Routing** - Determines whether to answer via SQL, documents, or hybrid approach

### Success Criteria
| Metric | Target | Current | Improvement |
|--------|--------|---------|------------|
| Query turnaround time | <30 seconds | 24-48 hours | 2,880-5,760x faster |
| User satisfaction (NPS) | >50 | N/A | Baseline |
| Query accuracy | >95% | ~70% (manual) | +25% |
| Daily active users | 40+ of 45 users | 8-10 (via analysts) | 400% increase in direct access |
| Analyst time on analysis | 70% | 30% | 2.3x increase in strategic work |
| Report generation time | <5 minutes | 2-3 days | 576-864x faster |

---

## 2. Personas & User Workflows

### Persona 1: Property Manager (Operations)
**Name:** Sarah Chen  
**Title:** Senior Property Manager  
**Experience:** 8 years managing apartment communities  
**Portfolio Size:** Manages 12 properties (450 units) across 3 states  
**Primary Goal:** Ensure on-time rent collection, respond to tenant maintenance requests, maintain occupancy

#### Daily Workflows
- **Morning standup (8:00am):** Check overnight maintenance requests, occupancy reports
- **Mid-morning (10:00am):** Prepare tenant communication, identify at-risk renewals
- **Afternoon (2:00pm):** Audit lease terms for renewals, review collections status
- **Ad-hoc:** Emergency maintenance budgeting, tenant dispute resolution

#### Pain Points
- Calls analyst about occupancy status "What's our current occupancy at Riverside Plaza?"
- Manually reviews spreadsheets to find lease renewal dates
- Waits to see if tenant rent is applied to correct lease and property
- Cannot quickly identify repeat maintenance issues (e.g., HVAC failures)
- Spends 3-4 hours/week asking analysts for routine data queries

#### Key Goals
1. Reduce time spent requesting data from analysts (from 3-4 hrs/week to <30 min/week)
2. Enable ad-hoc answering of tenant inquiries without analyst involvement
3. Identify operational trends and anomalies quickly

**Query Examples:**

**Query 1: Occupancy Status**
- **Context:** It's 8:30am Monday, Sarah needs occupancy numbers for the 12 properties she manages
- **Desired Output:** "Your portfolio is at 94.2% occupancy. Riverside Plaza: 96%, Westwood Commons: 91%, Mountain View: 87%. 3 vacant units - 2 market ready, 1 requires repairs (targeting turnover by 3/15)."
- **Current Workaround:** Email analyst, wait 2-4 hours, get spreadsheet attachment
- **Improvement:** Instant answer in chat interface, includes action items and exceptions

**Query 2: Lease Renewal Pipeline**
- **Context:** March 1st - need to plan renewal outreach for upcoming 60-day notices
- **Desired Output:** "37 leases expiring in next 90 days. 28 recommended for renewal (good tenants, market rate), 9 market test candidates. Top 5 by rent: Unit 405 Riverside ($2,850), Unit 301 Westwood ($2,650), Unit 201 Westwood ($2,495)..."
- **Current Workaround:** Manually filter lease database, identify expiration dates, consult move-out reports
- **Improvement:** Automated renewal pipeline with tenant risk scoring, recommended renewal rates

**Query 3: Maintenance Cost Analysis**
- **Context:** HVAC failures increasing - needs to identify patterns
- **Desired Output:** "HVAC work orders: 12 in past 90 days ($8,400 total). Concentrated in Building A (4 units, likely common system issue). Westwood Commons has 40% higher HVAC costs than comparable properties. Recommend whole-building assessment."
- **Current Workaround:** Pulls work order spreadsheet, manually categorizes by issue type
- **Improvement:** Automated anomaly detection, cross-property benchmarking, predictive maintenance alerts

**Query 4: Collections Status by Tenant**
- **Context:** Month-end collections report - need to identify delinquent accounts
- **Desired Output:** "4 tenants with delinquent rent: $3,200 total outstanding. 2 partial payments, 1 payment-plan, 1 new lease default. Collections action: 2 require 3-day notices, 1 eviction proceeding in progress, 1 pending landlord contact."
- **Current Workaround:** Calls analyst, receives emailed summary
- **Improvement:** Real-time dashboard view with drill-down to specific tenant accounts and case history

---

### Persona 2: Broker / Leasing Agent
**Name:** Marcus Rodriguez  
**Title:** VP of Leasing & Dispositions  
**Experience:** 12 years commercial real estate, 5 years with current operator  
**Portfolio Size:** 35 commercial/retail properties  
**Primary Goal:** Maximize occupancy and rent rates, execute timely dispositions

#### Daily Workflows
- **Morning (9:00am):** Review market comps, pipeline deals, lease expirations
- **Mid-day (1:00pm):** Tenant negotiations, lease amendment requests
- **Afternoon (3:00pm):** Pipeline forecasting for Q2 revenue
- **Ad-hoc:** Disposition pricing, competitive bid evaluation

#### Pain Points
- Cannot instantly answer "What's available in our portfolio under $15/sf in the Southeast?"
- Manually compiles lease terms spreadsheet for tenant negotiation references
- Lacks visibility into upcoming availabilities and projected lease rates
- Misses market timing opportunities due to slow data access
- Competitors with instant market insights move faster on opportunities

#### Key Goals
1. Reduce time to answer market availability questions from 2-4 hours to <5 minutes
2. Enable data-driven lease rate recommendations
3. Improve forecasting accuracy for pipeline revenue

**Query Examples:**

**Query 1: Market Availability Snapshot**
- **Context:** Marketing executive asks "Show me all available retail space under $20/sf in Texas"
- **Desired Output:** "6 retail spaces available or soon-to-be: Dallas (2,400 sf @ $18/sf), Houston (1,800 sf @ $19/sf), Austin (1,200 sf @ $18.50/sf, move-in ready). 3 others require minimal TI. Map view with traffic patterns and demographics available."
- **Current Workaround:** Manually queries portfolio, pulls comps from external market data, 4-hour process
- **Improvement:** Instant results with visibility into TI requirements, market rates, and prospect fit scoring

**Query 2: Lease Term Consistency Check**
- **Context:** Negotiating new retail lease - want to ensure consistent terms
- **Desired Output:** "Similar 2,000-2,500 sf retail in Texas: 5-year avg term 60 months, typical renewal opt 2x5yr, CAM ranges $4-6/sf. Your current terms for Building C: 60 months, 2x5yr renewal, $5.25/sf CAM (median). Proposed tenant rate: market competitive for quality space."
- **Current Workaround:** Manually reviews 3-5 comparable leases, estimates averages
- **Improvement:** Automated benchmarking against entire portfolio, automatic flag if terms deviate >10%

**Query 3: Upcoming Dispositions Pipeline**
- **Context:** CEO wants to know which properties expire from portfolio in next 18 months
- **Desired Output:** "7 properties approaching end-of-hold period. 3 ready for market (stabilized, market rates trending +3%). 2 require 4-6 month value-add (pending capital improvements). 2 underperforming, recommend 1031 exchange or reposition. Projected disposition timeline: 3Q 2026 (2 props), 1Q 2027 (3 props), 2Q 2027 (2 props)."
- **Current Workaround:** Manual spreadsheet tracking disposition dates, performance metrics, timing forecasts
- **Improvement:** Automated disposition readiness scoring, market timing recommendations, revenue forecasting

**Query 4: Tenant Credit Quality Assessment**
- **Context:** Evaluating risk on portfolio before bank renewal
- **Desired Output:** "Tenant credit quality: 78% AAA/A-rated, 16% BBB, 6% below-investment-grade. 3 tenants under watch (30+ days late in past 12mo). Delinquency rate: 2.1% (vs. market avg 3.5%). Collections improving 0.3% YoY. Recommended reserve: $210K based on at-risk rent."
- **Current Workaround:** Manual credit rating compilation from tenant files
- **Improvement:** Automated credit scoring with collections trend analysis and reserve recommendations

---

### Persona 3: Finance Director / Controller
**Name:** Jennifer Park  
**Title:** Director of Financial Operations  
**Experience:** 10 years real estate accounting, CPA  
**Portfolio Size:** Oversees all 87 properties  
**Primary Goal:** Ensure accurate financial reporting, optimize cash flow, manage budget variance

#### Daily Workflows
- **Morning (8:30am):** Review previous day's collections, identify exceptions
- **10:00am:** Budget variance analysis for portfolio
- **1:00pm:** Tenant credit review for collections team
- **3:00pm:** Month-end financial close (varying periods)
- **Ad-hoc:** Audit requests, tax reporting, lender reporting

#### Pain Points
- Spends 6+ hours/month on budget variance reconciliation
- Cannot quickly answer "Why is NOI down 2% YoY in Q1?" requires SQL query
- Lacks real-time visibility into rent collections by property, unit, and tenant
- Manual spreadsheet updates create version control issues and audit risk
- Cannot quickly pull ad-hoc operating expense or capital improvement reports

#### Key Goals
1. Reduce time on monthly financial reporting from 3-4 days to 1 day
2. Enable ad-hoc variance analysis without IT support
3. Improve audit trail and data accuracy

**Query Examples:**

**Query 1: Budget Variance Analysis**
- **Context:** March 1 - need to explain 2.3% NOI variance vs. budget
- **Desired Output:** "YTD NOI variance: -2.3% vs. budget (-$285K). Breakdown: Rent collections -$150K (-1.8%, driven by 0.4% lower occupancy), OpEx +$95K (utilities +$140K vs budget due to cold winter, offset by lower maintenance), CapEx +$40K (preventive HVAC work accelerated). Forecast Q2 recovery as occupancy rebounds."
- **Current Workaround:** Analyst runs multiple SQL queries, Finance manually consolidates in Excel, 6-8 hour process
- **Improvement:** Instant drill-down with variance waterfall, automatically flags root causes

**Query 2: Collections Status by Property**
- **Context:** Month-end close - need collections summary for financial statement
- **Desired Output:** "Total collected YTD: $8,247,500 (97.1% of billings). 2.9% delinquent or in collections. Top 3 delinquent properties: Westwood Commons ($18,200 from 2 tenants), Riverside Plaza ($12,400 from 1 tenant in eviction), Mountain View ($9,800 from 3 tenants, 1 in payment plan). Collections trend: 0.6% improvement vs. last year."
- **Current Workaround:** Accounting software pull + manual property-level aggregation, 2-3 hour process
- **Improvement:** Real-time dashboard with collections waterfall, automated delinquency reporting

**Query 3: Operating Expense Trend Analysis**
- **Context:** OpEx budget increased 3% YoY - need to validate legitimacy
- **Desired Output:** "Operating expenses trend (per-unit annual): 2024 $4,850, 2025 $4,995 (+3.0%). Breakdown: Utilities +5.2% (weather normalization suggests true cost +2.1%), Maintenance +1.8% (preventive focus), Management fees +2.1% (rent growth). Comparable market properties: +2.8% YoY. Assessment: your growth slightly high, likely due to winter utility costs."
- **Current Workaround:** Manual year-over-year comparison of GL accounts, external market research
- **Improvement:** Automated trend analysis with benchmarking and root cause decomposition

**Query 4: Capital Improvement Pipeline & Budget Tracking**
- **Context:** Preparing annual CapEx forecast and tracking Q1 spending
- **Desired Output:** "2026 CapEx plan: $1.2M authorized, $320K committed, $58K spent YTD. Phased by property: Riverside (roof - $400K, started 3/1), Westwood (parking lot - $350K, planning phase), Mountain View (HVAC replacement - $280K, Q3 start). Status: On budget and schedule. Risk: Westwood permit delays could push 60 days."
- **Current Workaround:** Manual tracking in CapEx spreadsheet, coordination with property managers
- **Improvement:** Integrated CapEx dashboard with real-time status, budget tracking, timeline visualization

---

### Persona 4: Executive / Chief Investment Officer
**Name:** David Thompson  
**Title:** Chief Investment Officer  
**Experience:** 18 years real estate investing, 3 years at current company  
**Portfolio Size:** Oversees investment strategy for all 87 properties  
**Primary Goal:** Optimize portfolio returns, execute strategic dispositions, identify growth opportunities

#### Daily Workflows
- **Morning (7:30am):** Review portfolio performance dashboard, key alerts
- **9:00am:** Board meeting prep or investor calls
- **1:00pm:** Disposition planning and market opportunity evaluation
- **3:00pm:** Strategy review and capital allocation decisions
- **Ad-hoc:** Investor reporting, lender calls, acquisition due diligence

#### Pain Points
- Cannot instantly answer "What's our portfolio IRR across all properties?" without IT support
- Lacks visibility into sub-market performance, tenant quality, and exit readiness
- Slow access to market comparables delays competitive decision-making
- Cannot perform ad-hoc sensitivity analysis on disposition timing or pricing
- Board reporting requires extensive manual compilation (2-3 analyst days)

#### Key Goals
1. Reduce time to answer strategic portfolio questions from 1-2 days to <5 minutes
2. Enable real-time portfolio performance visibility for decision-making
3. Automate quarterly board reporting and investor updates

**Query Examples:**

**Query 1: Portfolio Performance Scorecard**
- **Context:** Monthly board call - need 87-property performance summary
- **Desired Output:** "Portfolio Performance Scorecard: Avg occupancy 93.1% (+0.4% YoY), Avg rent/unit $2,180 (+2.8% YoY), Portfolio NOI $18.2M YTD (+1.9% YoY), Blended cap rate 5.2% (+8 bps), 87 properties tracked. Top performers: Austin cluster (6 props, 96% occ, 5.8% cap rate), Bottom: Midwestern industrial (3 props, 89% occ, 4.1% cap rate). Risk flags: 4 properties <85% occupancy, 2 requiring capital improvements."
- **Current Workaround:** Analyst builds custom Excel dashboard from Snowflake, 4-6 hours
- **Improvement:** Auto-refreshing dashboard, drill-down to individual property, immediate alerts on variance thresholds

**Query 2: Disposition Readiness Assessment**
- **Context:** Planning 2026 exit strategy - need to identify highest-return disposition targets
- **Desired Output:** "Disposition-ready portfolio: 12 properties meeting exit criteria (stabilized ops, no major capex needed). Top 3 by projected return: Industrial Complex #2 (acq price $18M, estimated exit $26.8M, 8.5% IRR), Retail Strip #7 ($12.5M acq, est. $17.2M exit, 7.8% IRR), Apartment #4 ($28M acq, est. $36.5M exit, 7.1% IRR). Market timing: Industrial strong (10% buyer demand above budget). Recommendation: Market #2 and #7 in Q2, #4 in Q3."
- **Current Workaround:** Manual assessment of property acquisition prices, current performance, market conditions
- **Improvement:** Automated disposition scoring with IRR modeling, market timing recommendations, broker shortlist suggestions

**Query 3: Sub-Market Performance Comparison**
- **Context:** Evaluating portfolio rebalancing - which markets underperforming?
- **Desired Output:** "Regional performance vs. targets (12 states, 4 clusters): Texas cluster (32 props, 94.2% occ, 5.4% cap rate, +12% YoY return) - STRONG. Southeast cluster (21 props, 92.1% occ, 4.9% cap rate, -3% YoY return) - MONITOR. Midwest cluster (18 props, 91.5% occ, 5.8% cap rate, +5% YoY return) - STABLE. Northeast cluster (16 props, 93.8% occ, 4.8% cap rate, +8% YoY return) - STRONG. Rebalancing recommendation: Reduce Southeast exposure, increase Texas/Northeast."
- **Current Workaround:** Manual compilation of market data, performance metrics by property
- **Improvement:** Automated market clustering, performance benchmarking, rebalancing recommendations

**Query 4: Investor Reporting Summary**
- **Context:** Preparing Q1 investor update for limited partners
- **Desired Output:** "Q1 2026 Performance Summary: Distributions $1.8M (+4% YoY), NOI $4.8M (+2.1% YoY), Occupancy 93.1% (+40 bps YoY), Cap rate 5.2% (stable), Portfolio value estimate $348M (+2.8% YoY). Key achievements: 12 tenant improvements completed, 1 major disposition closed ($26.8M, 8.5% IRR). Market outlook: Strong leasing activity in core markets, cautious on rising interest rates for future CapEx. Risk factors: 4 properties below stabilization metrics, 1 tenant concentration risk. Executive summary prepared for board distribution."
- **Current Workaround:** Analysts spend 2-3 days compiling reports from multiple sources
- **Improvement:** Auto-generated investor narrative with data visualization, board-ready formatting

---

## 3. Functional Requirements

### 3.1 Query Engine Requirements

| ID | Requirement | Priority | Notes |
|---|---|---|---|
| QE-1 | Accept natural language queries in English without syntax | P0 | Users should not need SQL knowledge |
| QE-2 | Generate syntactically correct Snowflake SQL for structured queries | P0 | Includes WHERE, JOIN, GROUP BY, ORDER BY logic |
| QE-3 | Support queries against minimum 9 table types in data warehouse | P0 | properties, units, tenancies, leases, work_orders, financials, rent_collections, occupancy_snapshots, user_property_access |
| QE-4 | Execute generated SQL queries against Snowflake with timeout (30s) | P0 | Prevent runaway queries from blocking users |
| QE-5 | Format SQL result sets into natural language answers | P0 | Convert tables to narrative prose, highlight key findings |
| QE-6 | Provide confidence score for each generated query (0-100) | P1 | Low confidence queries flagged for user verification |
| QE-7 | Support time-based queries (current, YTD, month-over-month, year-over-year) | P0 | Critical for finance and operations personas |
| QE-8 | Support aggregation queries (SUM, AVG, COUNT, GROUP BY) | P0 | Essential for KPI and trend analysis |
| QE-9 | Support ranking and comparison queries (TOP N, percentiles) | P1 | Required for property benchmarking and pipeline analysis |
| QE-10 | Maintain query audit log for compliance and debugging | P0 | Log query, user, timestamp, results, execution time |
| QE-11 | Cache frequently used queries to reduce latency | P1 | Improve response time for common queries from 8s to <2s |
| QE-12 | Support multiple parameter types (dates, numbers, text, currency) | P0 | Enable parameterized saved queries |

### 3.2 Semantic Search Requirements

| ID | Requirement | Priority | Notes |
|---|---|---|---|
| SS-1 | Ingest and index lease documents (PDF, DOCX) into Supabase pgvector | P0 | Support portfolio document library |
| SS-2 | Generate vector embeddings using OpenAI (3072-dim) for semantic search | P0 | Use OpenAI embedding-3-large model |
| SS-3 | Support hybrid search (vector + keyword) for document retrieval | P1 | Improve precision over pure vector search |
| SS-4 | Return top-5 contextual document chunks with similarity scores | P0 | Format with document name, chunk location, relevance score |
| SS-5 | Apply document-level access control during retrieval | P0 | Users only see documents they have permission to access |
| SS-6 | Support semantic chunking (sentence/clause boundary) for better context | P1 | Improve relevance over fixed-size chunking |
| SS-7 | Provide document upload workflow with progress tracking | P0 | Users can upload batch documents (10-50 docs/batch) |
| SS-8 | Re-rank retrieved documents using Cohere ranking model | P1 | Improve top-5 precision from 78% to 90%+ |
| SS-9 | Maintain document version history and update tracking | P1 | Support document lifecycle and audit trail |
| SS-10 | Cache popular search results for 24 hours | P1 | Reduce embedding API costs and latency |

### 3.3 Access Control Requirements

| ID | Requirement | Priority | Notes |
|---|---|---|---|
| AC-1 | Implement role-based access control (RBAC) with 4+ roles | P0 | Property Manager, Broker, Finance, Executive |
| AC-2 | Support property-level access restrictions | P0 | Users can only see queries/data for assigned properties |
| AC-3 | Support data-type restrictions (e.g., Finance sees financials, Property Manager doesn't) | P0 | Tenants hidden from executives, etc. |
| AC-4 | Implement Snowflake dynamic views filtered by user context | P0 | Queries automatically filtered to user's property/data scope |
| AC-5 | Use JWT tokens for stateless authentication | P0 | Integrate with Clerk for identity management |
| AC-6 | Enforce RLS (Row-Level Security) in Supabase for documents | P0 | Users only see documents assigned to their properties |
| AC-7 | Support document-level sharing permissions | P1 | Finance can share lease with Property Manager for specific property |
| AC-8 | Log all data access for audit compliance | P0 | Track who accessed what data, when, for how long |
| AC-9 | Implement PII masking for sensitive fields (SSN, payment info) | P1 | Comply with data privacy regulations |
| AC-10 | Support delegation of access (PM can grant admin to backup PM) | P2 | Nice-to-have for disaster recovery scenarios |

### 3.4 Export & Reporting Requirements

| ID | Requirement | Priority | Notes |
|---|---|---|---|
| EX-1 | Export query results to CSV format | P0 | Users can download structured data for further analysis |
| EX-2 | Export query results to Excel with formatting | P0 | Include headers, currency formatting, number precision |
| EX-3 | Generate email-ready summary reports (HTML + PDF) | P1 | Executive summaries for board distribution |
| EX-4 | Support scheduled report generation and delivery | P1 | Weekly/monthly automation for recurring reports |
| EX-5 | Include data refresh timestamp and source attribution | P0 | Transparency on data recency and lineage |
| EX-6 | Support multi-query report bundles (e.g., portfolio scorecard) | P1 | Combine 5-10 related queries into one report |

### 3.5 Admin & Management Requirements

| ID | Requirement | Priority | Notes |
|---|---|---|---|
| AD-1 | Admin dashboard showing system health (uptime, latency, error rates) | P1 | Proactive issue detection |
| AD-2 | Manage user roles and property access in UI | P0 | No direct database access required |
| AD-3 | View query performance metrics (execution time, Snowflake cost, API calls) | P1 | Cost attribution and optimization |
| AD-4 | Manage document library (upload, update, delete, archive) | P0 | Lifecycle management for documents |
| AD-5 | Review query audit logs with filtering and export | P1 | Compliance and debugging support |
| AD-6 | Manual query caching/invalidation controls | P2 | Override cache for stale data scenarios |
| AD-7 | Feedback mechanism for inaccurate query results | P0 | Continuous model training and improvement |

---

## 4. Non-Functional Requirements

| Category | Requirement | Target | Notes |
|---|---|---|---|
| **Performance** | Query response latency (p95) | <5 seconds | Includes SQL generation, execution, formatting |
| **Performance** | Document search latency (p95) | <3 seconds | Embedding retrieval + ranking |
| **Performance** | UI page load time | <2 seconds | Next.js optimized static+dynamic content |
| **Availability** | System uptime | 99.5% (21.6 min downtime/month) | Production environment |
| **Availability** | Query success rate | 98%+ | Only 2% of queries fail or require manual intervention |
| **Reliability** | Mean time to recovery (MTTR) | <15 minutes | Automated failover, incident response |
| **Scalability** | Concurrent users | 50+ simultaneous queries | Without degradation <5s p95 latency |
| **Scalability** | Document storage | 50,000+ pages indexed | Equivalent to 10-15 years of portfolio documents |
| **Security** | Encryption in transit | TLS 1.3 | All client-server communication |
| **Security** | Encryption at rest | AES-256 | Supabase + Snowflake default encryption |
| **Security** | API rate limiting | 100 requests/user/minute | Prevent abuse while supporting power users |
| **Security** | Query timeout | 30 seconds | Prevent runaway Snowflake queries |
| **Usability** | Time to first answer | <5 minutes for new users | Includes onboarding, first query |
| **Usability** | Query success w/o refinement | 80% | Users get acceptable answer on first try |
| **Data Quality** | SQL generation accuracy (F1) | >95% | Validated against gold-standard query set |
| **Data Quality** | Answer correctness (human eval) | >93% | Automated evaluation against human expert review |
| **Cost** | Snowflake query cost per answer | <$0.05 | Avoid BI tool economics |
| **Cost** | Embedding API cost per search | <$0.001 | Use batch processing and caching |

---

## 5. Technical Constraints & Assumptions

### 5.1 Snowflake Constraints
- **Query timeout:** 30 seconds maximum execution time
- **Concurrent connections:** 10 max per warehouse (partition queries across multiple warehouses if needed)
- **Data refresh:** Property data updated daily, financials updated nightly, occupancy near real-time
- **Row limit:** Queries must return <100k rows for performance (enforce in SQL generation)
- **Schema complexity:** 9 core tables + 2 materialized views; no external data integration in MVP

### 5.2 AI Model Constraints
- **Text-to-SQL model:** Claude Opus 4 (60K context window) or GPT-4-Turbo (128K context)
  - Cost: ~$0.01-0.03 per query (tokens in/out)
  - Accuracy: 95%+ on gold-standard query set
  - Latency: 2-4 seconds generation time
- **Embedding model:** OpenAI embedding-3-large (3072 dimensions)
  - Cost: $0.02 per 1M tokens
  - Batch processing to reduce per-query cost to <$0.0001
- **Reranking model:** Cohere rerank-english-v3.0
  - Cost: ~$0.001 per 100 documents ranked
  - Latency: <100ms for ranking 50 documents

### 5.3 Document Processing Constraints
- **Max document size:** 100MB per file
- **Supported formats:** PDF (with OCR), DOCX, PPTX, text
- **Chunking strategy:** Semantic (max 512 tokens per chunk) with 100-token overlap
- **Document ingestion SLA:** Upload → searchable within 5 minutes (for PDFs <20MB)
- **Batch processing:** Maximum 50 documents per batch upload job

### 5.4 Vector Database Constraints (Supabase pgvector)
- **Vector dimension:** 3,072 (OpenAI embedding-3-large)
- **Index type:** HNSW (Hierarchical Navigable Small Worlds)
- **Storage capacity:** 50,000+ documents = ~150GB vector index
- **Query latency:** <500ms for top-10 retrieval on full index
- **Backup strategy:** Daily snapshots, 30-day retention

### 5.5 Deployment Constraints
- **API latency requirement:** <5s p95 (includes all hops)
- **Cold start tolerance:** <3s for serverless compute
- **Database connection pooling:** Maximum 100 concurrent connections to Snowflake
- **Cache strategy:** Redis 6GB max (2,000 frequent queries)

---

## 6. Out of Scope (v1 Boundaries)

The following features are intentionally excluded from Phase 0-1 roadmap:

### 6.1 Advanced Features
- **Predictive analytics** (price forecasting, churn prediction) → Phase 3
- **Mobile app** (iOS/Android) → Phase 3+
- **Custom KPI builder** (user-defined metrics) → Phase 3
- **Market comps & acquisition targeting** → Phase 2+
- **Financial modeling & sensitivity analysis** → Phase 2+

### 6.2 Data Integration
- **Multi-source integration** (MLS, CoStar, Zillow APIs) → Phase 2+
- **Broker-managed data** (third-party property managers) → Phase 1.5+
- **External BI tool integration** (Tableau, Power BI embed) → Phase 2+

### 6.3 Automation Features
- **Workflow automation** (n8n integration) → Phase 2
- **Scheduled report delivery** (email, Slack) → Phase 2
- **Tenant communication workflows** → Phase 2+

### 6.4 Analysis Features
- **Comparative market analysis (CMA) generation** → Phase 2+
- **Investment thesis automation** → Phase 3+
- **Appraisal report generation** → Phase 3+

### 6.5 Compliance & Governance
- **HIPAA compliance** (not applicable to real estate ops) → No plans
- **SOC 2 Type II certification** → Future (currently Type I planned for Phase 1)
- **Audit workflow automation** → Phase 2+

### 6.6 Deployment Modes
- **On-premises deployment** → No plans (SaaS only)
- **Hybrid deployment** (customer Snowflake + our hosted app) → Phase 2+
- **White-label** (customer-branded UI) → Phase 3+

---

## 7. Phased Rollout & Delivery Plan

### Phase 0: MVP (Weeks 1-8)
**Goal:** Prove core Text-to-SQL value for Property Manager persona with 3-table schema  
**Exit Criteria:** 
- Property Manager can ask "What's my occupancy?" and get accurate answer
- 30+ internal users onboarded (test users + pilot PMs)
- System uptime >95% on internal staging
- SQL accuracy >90%

**Deliverables:**
- Text-to-SQL engine (properties, units, tenancies tables only)
- Single-document semantic search (leases)
- Basic RBAC (role assignment, no enforcement)
- Chat UI (Next.js) with query history
- Snowflake connection & data synchronization
- Audit logging (query + results)
- Admin user management interface
- Documentation & runbooks

**Key Decisions:**
- Claude Opus 4 for Text-to-SQL (vs. GPT-4 for cost/speed tradeoff)
- Fixed-size 512-token chunks for documents (vs. semantic chunking)
- Logical multi-tenancy (vs. physical) for faster deployment
- Dashboard-first UI (vs. chat-first) for data exploration accessibility

**Dependencies:**
- Snowflake account + initial schema (2 weeks)
- Client data migration (properties, units, leases) (3 weeks)
- Clerk authentication setup (1 week)

**Risks:**
- SQL generation accuracy <90% on complex properties → Mitigation: in-context learning from gold-standard queries
- Embedding API costs exceed budget → Mitigation: aggressive caching, smaller batch sizes
- Data quality issues in source systems → Mitigation: data validation dashboard, quality rules in SQL generation

---

### Phase 1: Core Platform (Weeks 9-16)
**Goal:** Support all 4 personas with full RBAC, batch document upload, saved queries, Excel export  
**Exit Criteria:**
- 40+ of 45 users actively using platform (>1 query/week)
- All 4 personas can answer their primary use cases
- RBAC enforcement verified in access logs (0 unauthorized data access)
- Query accuracy >94%
- <2% query error rate
- NPS >40

**Deliverables:**
- Expand schema to 9 tables (add leases, work_orders, financials, rent_collections, occupancy_snapshots)
- Broker/Leasing persona: market availability, lease term analysis, disposition pipeline
- Finance persona: budget variance, collections analysis, operating expense trends
- Executive persona: portfolio scorecard, sub-market performance, investor reporting
- RBAC property-level enforcement in Snowflake dynamic views
- Document batch upload (10-50 docs per job) with progress tracking
- Saved queries (user can save and re-run parameterized queries)
- Excel export with formatting (headers, currency, number precision)
- Document versioning and access audit logs
- Query performance dashboard (execution time, Snowflake cost)
- Improved semantic search with Cohere reranking
- Confidence scoring for generated queries
- User feedback mechanism for inaccurate results

**Technical Improvements:**
- Redis caching for popular queries
- Rate limiting (100 req/user/min)
- Improved prompt engineering (in-context examples from gold-standard set)
- Snowflake materialized views for common KPIs

**Dependencies:**
- Completion of Phase 0 feedback integration (1 week)
- Extended Snowflake schema & data migration (3 weeks)
- Additional document library ingestion (2 weeks)
- Beta user testing with all 4 personas (2 weeks)

**Risks:**
- RBAC complexity in Snowflake views → Mitigation: automated test suite for access control
- Document quality varies (poor OCR on old leases) → Mitigation: manual correction workflow for critical docs
- User adoption slower than expected → Mitigation: champion program with early adopters, training sessions

---

### Phase 2: Scale & Automation (Weeks 17-24)
**Goal:** Enable workflow automation, advanced analytics, enterprise-grade reliability  
**Exit Criteria:**
- n8n workflows running 50+ automations/day
- Materialized views reduce query latency by 60%
- Cache hit rate >40% on queries
- 99.5% uptime SLA met for 2 consecutive weeks
- Adoption rate >80% (36 of 45 users monthly active)

**Deliverables:**
- n8n workflow integration (automated report generation, tenant communications, maintenance alerts)
- Trigger.dev async jobs (document batch processing, report scheduling)
- Snowflake materialized views for portfolio_kpi_summary, property_performance_scorecard
- Enhanced Redis caching strategy with TTL management
- Analytics dashboard (queries/day, document views, user engagement)
- Advanced export: multi-query report bundles, HTML + PDF formatting
- Scheduled report delivery (email, Slack integration)
- Query performance optimization: indexing, cost analysis
- Admin controls: query caching/invalidation, document lifecycle management
- Enhanced semantic search: hybrid keyword+vector, query expansion

**Dependencies:**
- Snowflake architect review for materialized view design (1 week)
- n8n configuration & workflow templates (2 weeks)
- Trigger.dev setup & integration testing (2 weeks)
- Load testing and performance optimization (2 weeks)

**Risks:**
- Materialized view maintenance overhead → Mitigation: automated refresh scheduling, failure alerts
- Workflow automation errors cascade to users → Mitigation: comprehensive error handling, user notification
- Analytics impact query performance → Mitigation: separate analytics cluster or scheduled aggregation

---

### Phase 3: Intelligence & Growth (Weeks 25+)
**Goal:** Expand platform to predictive analytics, market intelligence, custom analytics  
**Exit Criteria:**
- Mobile app (iOS/Android) with >500 downloads
- Predictive models (occupancy, price, churn) with >85% accuracy
- Custom KPI builder used by >10 finance users
- Market comps integration providing actionable insights
- Revenue/margin contribution from premium features (est. +30% monetization)

**Deliverables:**
- Mobile app (React Native) with push notifications
- Predictive models: occupancy forecasting, rent rate optimization, tenant churn risk
- Custom KPI builder: users can define bespoke KPIs, save, share, alert on thresholds
- Market comps: integration with CoStar/CoreLogic APIs
- Investment thesis automation: AI-generated investment memos with market analysis
- Appraisal report generation: automated reports for refinance/disposition
- Advanced sensitivity analysis: "What if" modeling for different scenarios
- Enhanced RBAC: team-level permissions, temporary access grants
- Expanded integrations: Slack, Teams, Outlook for notifications

**Dependencies:**
- External market data partnerships (CoStar, CoreLogic agreements) (4-8 weeks)
- Mobile app development (8-12 weeks)
- Data science team to develop/train predictive models (6-8 weeks)
- Advanced UI/UX for custom analytics (6-8 weeks)

**Risks:**
- Market data accuracy and recency → Mitigation: multi-source triangulation
- Predictive model performance degrades over time → Mitigation: continuous retraining, drift detection
- Mobile app cannibilizes web usage → Mitigation: complementary feature set (mobile alerts, quick lookups)

---

## 8. Risks & Mitigation Strategies

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| SQL generation accuracy <90% on complex properties | Medium | High | In-context learning from gold-standard queries, aggressive testing, human feedback loop |
| Snowflake schema complexity exceeds AI model's reasoning capacity | Medium | High | Start with 3 tables (Phase 0), expand gradually; use chain-of-thought prompting |
| Data quality issues prevent accurate queries (missing property data, stale leases) | High | Medium | Data validation dashboard, quality rules in SQL generation, user feedback on bad answers |
| Users request data access they don't have (exceeds RBAC design) | Medium | Medium | Early design review with Finance/Legal, comprehensive access audit logs, dynamic RLS testing |
| Embedding API costs exceed budget ($500/month target) | Low | Medium | Aggressive caching, batch processing, smaller chunk sizes, re-rank only top-50 |
| Cold start latency >3s breaks user experience on first query | Medium | Medium | Prompt caching, warm Snowflake warehouse, lazy load UI components |
| Document OCR quality poor for old leases (pre-2015) | Medium | Low | Manual transcription for critical docs, skip poor-quality PDFs, human curation layer |
| User adoption slower than target (30/45 users target by end of Phase 1) | Medium | High | Champion program, executive sponsorship, usage dashboards, training/support resources |
| Concurrent query overload during month-end close (100+ queries/hour) | Medium | Medium | Query queuing, Snowflake scaling, aggressive caching of month-end reports |
| Unplanned downtime during Phase 0-1 (impact trust) | Low | High | Automated failover, incident response runbooks, 2 Snowflake warehouse setup, Redis persistence |
| Model output hallucinations (confidently wrong answers) | Medium | High | Confidence scoring, human review for low-confidence queries, comprehensive testing framework |
| Regulatory/compliance issues (data privacy, audit trail) | Low | High | Legal review early (SOC 2 scope), comprehensive audit logging, PII masking, access control testing |

---

## 9. Dependencies & Critical Path

| Dependency | Owner | Est. Duration | Critical Path Impact |
|---|---|---|---|
| Snowflake account setup + initial schema | Infrastructure | 2 weeks | Blocks Phase 0 development |
| Client data migration (properties, units, leases, financials) | Operations | 3 weeks | Blocks Phase 0 testing |
| Clerk authentication integration | Engineering | 1 week | Blocks MVP user testing |
| Claude API access + rate limit increase | Anthropic | 1 week | Enables Text-to-SQL development |
| Supabase account + pgvector extension | Infrastructure | 1 week | Enables semantic search development |
| Extended Snowflake schema (9 tables) | Data Engineering | 3 weeks | Blocks Phase 1 personas |
| Document library ingestion (50+ leases) | Operations | 2 weeks | Blocks Phase 1 semantic search |
| n8n & Trigger.dev setup | Engineering | 2 weeks | Blocks Phase 2 automation |
| Load testing environment | QA | 2 weeks | Blocks Phase 2 SLA validation |
| External market data API agreements | Operations/Legal | 4-8 weeks | Blocks Phase 3 market features |
| Mobile app development | Engineering | 8-12 weeks | Blocks Phase 3 launch |

---

## 10. Success Metrics & Measurement

**North Star Metric:** Time to Insight (from question to actionable answer)
- **Current:** 24-48 hours
- **Phase 0 Target:** <30 seconds
- **Phase 1 Target:** <15 seconds (with caching/materialized views)

**Input Metrics:**
- Queries per day (target: 50+ by end of Phase 1)
- Documents ingested (target: 200+ by end of Phase 1)
- Active users (target: 40+/45 by end of Phase 1)
- Query types distribution (structured SQL vs. document search vs. hybrid)

**Quality Metrics:**
- SQL generation F1 score (target: >95%)
- Answer correctness (human eval) (target: >93%)
- Semantic search NDCG@5 (target: >0.85)
- User satisfaction on individual answers (1-5 scale target: 4.2+)

**Business Metrics:**
- User adoption rate (target: >80% monthly active by Phase 1)
- NPS score (target: >50 by end of Phase 1)
- Hours saved per user per week (est. 2-3 hours by Phase 1)
- ROI: Analyst time freed up for strategic analysis (est. $150K/year value)

**Guardrail Metrics:**
- System uptime (target: 99.5%)
- p95 query latency (target: <5 seconds)
- Error rate (target: <2% queries fail/require manual intervention)
- Security: 0 unauthorized data access incidents

**Measurement Methodology:**
- Query performance: Automatic logging of execution time, Snowflake cost, API calls
- User adoption: Login tracking, query frequency per user
- Answer quality: Automated F1 evaluation on gold-standard set + sample human review (5% of queries)
- Satisfaction: Post-query rating prompts + monthly NPS survey
- Uptime: Synthetic monitoring, database health checks every 60 seconds

---

## 11. Appendix: Glossary & Terms

- **RAG (Retrieval-Augmented Generation):** Combining document retrieval with language model generation for contextual answers
- **Text-to-SQL:** Natural language → structured SQL query translation
- **Semantic search:** Vector-based similarity search instead of keyword matching
- **Embedding:** Dense vector representation of text (3072 dimensions in our case)
- **Materialized view:** Pre-computed Snowflake table that refreshes on schedule
- **HNSW:** Hierarchical Navigable Small Worlds index for vector similarity search
- **pgvector:** PostgreSQL/Supabase extension for vector similarity operations
- **RBAC:** Role-Based Access Control (Property Manager, Broker, Finance, Executive)
- **RLS:** Row-Level Security in Supabase (database-level filtering)
- **Cold start:** First request to serverless function (higher latency)
- **Confidence score:** 0-100 score for generated query accuracy
- **F1 score:** Harmonic mean of precision and recall for classification accuracy
- **NDCG@5:** Normalized Discounted Cumulative Gain @ top-5 results (relevance ranking quality)

---

**Document Status:** Ready for stakeholder review  
**Next Steps:** Design review with engineering team, data migration planning, Snowflake account setup  
**Review Date:** 2026-03-11
