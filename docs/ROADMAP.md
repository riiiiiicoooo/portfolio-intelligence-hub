# Portfolio Intelligence Hub - Product Roadmap

**Version:** 1.0  
**Status:** Active  
**Last Updated:** 2026-03-04  
**Owner:** Product Management  
**Timeline:** March 2026 - December 2026+ (36+ weeks)

---

## Product Roadmap Timeline

```
Week:     1   5   10   15   20   25   30   35   40   45   50
Phase 0 ▓▓▓▓▓▓▓▓  (MVP: Text-to-SQL basic, single document RAG)
        MVP Validation, Property Manager persona focus
                
                Phase 1 ▓▓▓▓▓▓▓▓  (Core: All personas, RBAC, batch upload)
                              Full product validation
                                     
                                     Phase 2 ▓▓▓▓▓▓▓▓  (Scale: Automation, analytics, 99.5% SLA)
                                                    Enterprise-grade reliability
                                                          
                                                          Phase 3 ▓▓▓▓▓▓▓▓▓  (Intelligence: Predictive, mobile, KPI builder)
                                                                         Market expansion phase

Key Milestones:
├─ W1:  Project kickoff, infrastructure setup
├─ W4:  Alpha release (internal testing)
├─ W8:  Phase 0 complete (pilot users go live)
├─ W12: Phase 1 UI/UX polish
├─ W16: Phase 1 complete (all 45 users onboarded)
├─ W20: Phase 2 performance targets hit
├─ W24: Phase 2 complete (production-grade)
├─ W32: Phase 3 begins (product expansion)
└─ W40: Phase 3 features launching
```

---

## Phase 0: MVP (Weeks 1-8)

**Goal:** Prove core Text-to-SQL value for Property Manager persona with minimal complexity.  
**Target Users:** 30-35 internal users (Property Managers + Finance pilot)  
**Success Threshold:** 20+ queries/day, 90%+ accuracy, <30 sec latency

### Objectives
1. Build foundational Text-to-SQL engine (Claude Opus 4 + Snowflake)
2. Implement basic single-document semantic search (lease documents)
3. Deliver MVP UI for Property Manager persona (chat + basic dashboard)
4. Establish RBAC foundation (role-based property access)
5. Achieve >95% SQL accuracy on gold-standard query set

### Deliverables

**Week 1-2: Infrastructure & Setup**
- [ ] Snowflake account setup (3-table schema: properties, units, occupancy_snapshots)
- [ ] Supabase PostgreSQL + pgvector extension enabled
- [ ] FastAPI skeleton + OpenAPI documentation
- [ ] Clerk authentication integration
- [ ] Datadog monitoring + logging pipeline
- [ ] GitHub Actions CI/CD setup

**Week 2-3: Text-to-SQL Engine**
- [ ] Claude Opus 4 integration + prompt engineering (in-context learning from 20 examples)
- [ ] SQL validation (syntax, permission, row limit checks)
- [ ] Snowflake query execution with 30s timeout
- [ ] Result formatting (tabular → narrative)
- [ ] Query audit logging
- [ ] Confidence scoring (0-100 for each generated query)

**Week 3-4: Semantic Search (Single Document)**
- [ ] PDF text extraction + fixed-size chunking (512 tokens)
- [ ] OpenAI embedding-3-large integration (batch processing)
- [ ] Supabase pgvector storage + HNSW indexing
- [ ] Vector similarity search + top-5 retrieval
- [ ] Document chunk display with page references

**Week 4-5: RBAC Foundation**
- [ ] User property access table (user → properties mapping)
- [ ] Dynamic Snowflake views (WHERE property_id IN user_accessible)
- [ ] Supabase RLS policies (row-level filtering)
- [ ] Audit logging (who accessed what, when)

**Week 5-6: UI/UX (MVP)**
- [ ] Next.js frontend boilerplate (Vercel deployment)
- [ ] Chat interface (text input + streaming responses)
- [ ] Property occupancy dashboard (simple table view)
- [ ] Query history (recent queries, user can re-run)
- [ ] Login/logout (Clerk integration)

**Week 6-7: Testing & Documentation**
- [ ] Gold-standard query set (100 real-world real estate queries)
- [ ] Automated F1 testing (weekly CI runs)
- [ ] Manual user acceptance testing (5 Property Managers)
- [ ] Runbooks (deployment, incident response)
- [ ] Data model documentation

**Week 7-8: Launch Prep & Stabilization**
- [ ] Performance tuning (target p95 <5s)
- [ ] Error handling + user-friendly messaging
- [ ] Security review (data encryption, RBAC testing)
- [ ] Pilot user onboarding (30-35 internal users)
- [ ] 24/7 on-call rotation begins

### Exit Criteria
- [ ] 20+ queries/day across pilot users
- [ ] SQL generation F1 score >95% on gold-standard set
- [ ] 30+ users actively using (>1 query/week each)
- [ ] Query latency p95 <10 seconds
- [ ] Zero unauthorized data access incidents
- [ ] NPS >30 from pilot group

### Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| SQL generation accuracy <90% | Medium | High | Aggressive prompt tuning, gold-standard testing, fallback to manual SQL |
| Snowflake data quality issues | Medium | Medium | Data validation layer, quality dashboards, user feedback loop |
| User adoption slower than expected | Medium | High | Executive mandate, champion program (identify 3-5 early adopters), training |
| Embedding cost exceeds budget | Low | Low | Batch processing, caching, smaller chunk sizes |
| Unplanned outage damages trust | Low | High | Redundant infrastructure, incident response runbook, SLA comms |

### Team & Dependencies

**Engineering Team:** 2 backend engineers, 1 frontend engineer, 1 ML engineer  
**Data:** 1 data engineer (Snowflake + Supabase setup)  
**Product:** 1 PM (requirements, prioritization)  
**Infrastructure:** Snowflake account, Supabase project, AWS (Redis, Datadog), Vercel  

**Critical Path Dependencies:**
1. Snowflake account setup (2 weeks before development) → blocks Text-to-SQL development
2. Client data migration (properties, units, leases) (3 weeks) → blocks testing with real data
3. Clerk authentication (1 week) → blocks MVP UI
4. Claude Opus 4 API access + rate limit increase (1 week) → blocks Text-to-SQL development

---

## Phase 1: Core Platform (Weeks 9-16)

**Goal:** Support all 4 personas with full RBAC, batch document upload, saved queries, Excel export.  
**Target Users:** 40/45 internal users (all personas onboarded)  
**Success Threshold:** 100+ queries/day, 94%+ accuracy, <5 sec latency, 40+ NPS

### Objectives
1. Expand schema to 9 tables (add leases, work_orders, financials, rent_collections, occupancy_snapshots)
2. Build persona-specific dashboards (Property Manager, Broker, Finance, Executive)
3. Implement document batch upload (10-50 docs/batch) with progress tracking
4. Enable saved queries (parameterized, reusable)
5. Export to Excel with formatting
6. Cohere reranking for semantic search precision (NDCG@5 0.82 → 0.88)
7. Confidence scoring + user feedback loop

### Deliverables

**Week 9-10: Schema Expansion & RBAC Enhancement**
- [ ] Expand Snowflake schema (9 core tables)
- [ ] Migrate full real estate data (87 properties, 3,665 units, 12 months history)
- [ ] RBAC enforcement in SQL (Finance cannot see tenant names, etc.)
- [ ] Data-type level permissions (view financial vs. operational data)

**Week 10-11: Persona Dashboards**
- [ ] Property Manager: Occupancy status, lease renewals, maintenance, collections
- [ ] Broker: Market availability, lease terms, disposition pipeline
- [ ] Finance: Budget variance, NOI analysis, collections tracking
- [ ] Executive: Portfolio scorecard, sub-market performance, KPI summary
- [ ] Drill-down capability (click property → details)

**Week 11-12: Document Batch Upload & Management**
- [ ] Document upload flow (web UI, progress bar)
- [ ] Batch processing (n8n or Trigger.dev orchestration)
- [ ] Semantic chunking (sentence boundaries, not fixed-size)
- [ ] Document versioning (old leases archived, new versions tracked)
- [ ] Access control per document (which roles can view)

**Week 12-13: Saved Queries & Parameterization**
- [ ] Saved query creation ("Save this query as template")
- [ ] Parameters (property_id, date_range as variables)
- [ ] Share saved queries with colleagues
- [ ] Query history with filtering (by persona, date, status)
- [ ] User feedback (rating each query result 1-5 stars)

**Week 13-14: Export & Reporting**
- [ ] Export to CSV (raw data)
- [ ] Export to Excel (formatted headers, currency, numbers)
- [ ] HTML email summaries (for board reports)
- [ ] Multi-query report bundles (5-10 related queries in one PDF)
- [ ] Scheduled report generation (weekly/monthly)

**Week 14-15: Semantic Search Optimization**
- [ ] Cohere reranking integration (top-50 candidates → top-5)
- [ ] Hybrid search (vector + keyword combined)
- [ ] Query expansion (synonyms: "cash inflow" = "rent collected")
- [ ] Re-rank evaluation (NDCG@5 testing on gold-standard)

**Week 15-16: Polish & Performance**
- [ ] Redis caching for popular queries (1-4 hr TTL)
- [ ] Query confidence scoring + low-confidence user review workflow
- [ ] Performance optimization (target p95 <5 sec)
- [ ] User onboarding improvements (in-app tutorials)
- [ ] End-to-end testing with all 4 personas

### Exit Criteria
- [ ] 100+ queries/day across all user types
- [ ] 40+ of 45 users active (monthly active users)
- [ ] SQL generation F1 >95%, answer correctness >93%
- [ ] Semantic search NDCG@5 >0.85 (with reranking)
- [ ] Query latency p95 <5 seconds
- [ ] Excel export working for 90%+ of queries
- [ ] NPS >40 from all 4 personas
- [ ] Zero unauthorized data access or security incidents

### Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Broker adoption low (hard to integrate into workflow) | Early broker testing (week 9), schedule focused training |
| RBAC bugs expose unauthorized data | Automated access control test suite, weekly audit log review |
| Document quality issues (poor OCR on old leases) | Manual correction workflow for critical docs, auto-skip low-confidence |
| Saved query parameter syntax confusing | Intuitive UI builder (not SQL syntax), clear examples |

### Team
- 2 backend engineers (schema, API)
- 1 frontend engineer (dashboards, UI)
- 1 ML engineer (semantic search, reranking)
- 1 data engineer (ETL, optimization)
- Support person (user training, feedback)

---

## Phase 2: Scale & Automation (Weeks 17-24)

**Goal:** Enable workflow automation, enterprise-grade reliability, advanced analytics.  
**Target Metrics:** 500+ queries/day, 99.5% uptime, <3 sec p95 latency, 45+ MAU

### Objectives
1. n8n workflow automation (automated reports, tenant comms, alerts)
2. Trigger.dev async jobs (document batch processing, scheduled reports)
3. Snowflake materialized views (portfolio_kpi_summary, property_scorecard)
4. Redis optimization (cache hit rate 40%+)
5. Analytics dashboard (queries/day, user engagement, cost tracking)
6. Advanced exports (multi-query bundles, HTML + PDF)
7. Scheduled report delivery (email, Slack)

### Deliverables

**Week 17-18: Materialized Views & Query Optimization**
- [ ] portfolio_kpi_summary (nightly refresh after financial close)
- [ ] property_performance_scorecard (all 87 properties, KPIs)
- [ ] Performance profiling (query execution plans, optimization)
- [ ] Indexing strategy review (B-tree, HNSW tuning)

**Week 18-19: n8n Workflow Automation**
- [ ] Monthly occupancy alert (email if <90%)
- [ ] Budget variance escalation (notify if >±5%)
- [ ] Collections report (daily delinquency summary)
- [ ] Maintenance issue tracking (recurring problems flagged)
- [ ] Workflow templates (50+ ready-to-use automations)

**Week 19-20: Trigger.dev Async Jobs**
- [ ] Document batch ingestion orchestration
- [ ] Scheduled report generation (weekly, monthly, quarterly)
- [ ] Email delivery (React Email + Resend templates)
- [ ] Retry logic (failed emails re-sent 3x)

**Week 20-21: Analytics & Admin Dashboard**
- [ ] Query volume tracking (queries/day, by persona)
- [ ] User engagement metrics (active users, query frequency)
- [ ] Cost analysis (Snowflake credits, API costs by feature)
- [ ] System health (uptime, error rates, latency)
- [ ] Feedback aggregation (user-reported query errors)

**Week 21-22: Advanced Reporting**
- [ ] Multi-query report builder (select 5-10 queries → combined report)
- [ ] Board-ready formatting (executive summary + visualizations)
- [ ] HTML + PDF export (pixel-perfect formatting)
- [ ] Scheduled delivery (email, Slack, S3 bucket)

**Week 22-23: Cache & Performance Optimization**
- [ ] Redis distributed caching (Redis cluster, 6GB)
- [ ] Cache invalidation strategy (TTL-based, event-based)
- [ ] Query result caching (top 50 queries, 30-40% hit rate target)
- [ ] CDN for static assets (Cloudflare)

**Week 23-24: Enterprise Reliability**
- [ ] 99.5% uptime SLA (monitoring, alerting, failover)
- [ ] Database replication (Supabase read replicas)
- [ ] Backup & disaster recovery (automated daily snapshots)
- [ ] Incident response automation (auto-remediation for common issues)

### Exit Criteria
- [ ] 500+ queries/day (2.5x Phase 1)
- [ ] 50 workflows active (n8n automations running)
- [ ] Cache hit rate 40%+ on queries
- [ ] Query latency p95 <3 seconds
- [ ] Uptime 99.5% (measured over 2 consecutive weeks)
- [ ] 45+ monthly active users
- [ ] Zero performance regressions

### Risk Factors
- Materialized view maintenance complexity
- n8n workflow error handling (prevent cascading failures)
- Cache invalidation bugs (stale data)
- Infrastructure scaling (concurrent query limits)

---

## Phase 3: Intelligence & Growth (Weeks 25-40+)

**Goal:** Expand to predictive analytics, market intelligence, custom analytics. Prepare for multi-customer scale.  
**Target Metrics:** 1,000+ queries/day, mobile app launch, revenue-generating features

### Objectives
1. Predictive models (occupancy forecasting, rent optimization, churn)
2. Market intelligence (CoStar/CoreLogic integration, comps)
3. Custom KPI builder (users define bespoke KPIs)
4. Mobile app (iOS/Android with push notifications)
5. Advanced RBAC (team-level permissions, temporary access)
6. Appraisal report automation
7. Investment thesis generation
8. Multi-customer support (physical multi-tenancy)

### Phase 3A: Predictive Analytics (Weeks 25-32)

**Week 25-27: Occupancy Forecasting Model**
- [ ] Historical occupancy data analysis (3 years)
- [ ] Seasonal decomposition (peak seasons, trends)
- [ ] Machine learning model (ARIMA, Prophet, or LSTM)
- [ ] Validation on holdout set (forecast accuracy >85%)
- [ ] Integration: "What will occupancy be next quarter?"

**Week 27-30: Rent Optimization Model**
- [ ] Comparable rent analysis by unit type, location
- [ ] Seasonal pricing optimization
- [ ] Tenant credit quality impact on rent (AAA vs. BBB)
- [ ] Recommendations: "Set rent to $1,850 for 2BR to maximize margin"

**Week 30-32: Churn Prediction Model**
- [ ] Tenant payment history + lease terms analysis
- [ ] Renewal likelihood scoring (% chance tenant stays)
- [ ] Early warning (flag at-risk renewals 6 months in advance)
- [ ] Intervention: "Unit 405 is at 60% renewal risk; consider concessions"

### Phase 3B: Market Intelligence (Weeks 32-36)

**Week 32-34: CoStar/CoreLogic Integration**
- [ ] API partnerships (data licensing agreements)
- [ ] Comparable property data import (neighboring properties, market rates)
- [ ] Sync pipeline (daily updates, validation)

**Week 34-36: Comparative Market Analysis (CMA)**
- [ ] Market comps retrieval ("Show rent for comparable properties in Austin")
- [ ] Appraisal automation ("Generate appraisal report for property disposition")
- [ ] Disposition pricing recommendations

### Phase 3C: Custom Analytics & Mobile (Weeks 36-40+)

**Week 36-38: Custom KPI Builder**
- [ ] UI for defining custom KPIs (drag-and-drop formula builder)
- [ ] Save KPIs to user dashboard
- [ ] Share KPIs with team
- [ ] Automated alerts (notify if KPI crosses threshold)

**Week 38-40: Mobile App (React Native)**
- [ ] Quick lookups (occupancy, collections status)
- [ ] Push notifications (critical alerts)
- [ ] Offline mode (cached data)
- [ ] Biometric auth (Touch ID, Face ID)

**Week 40+: Advanced RBAC & Multi-Tenancy**
- [ ] Team-level permissions (group users by team)
- [ ] Temporary access grants (share data for 24 hours)
- [ ] Physical multi-tenancy (dedicated warehouse per customer)
- [ ] Customer admin portal (manage users, permissions)

### Phase 3 Exit Criteria
- [ ] 1,000+ queries/day (across all customers if multi-tenant)
- [ ] 3 predictive models in production (accuracy >80% each)
- [ ] Mobile app with 500+ downloads (iOS + Android)
- [ ] Custom KPI builder used by 10+ finance users
- [ ] Market comps integration live
- [ ] Revenue from premium features (est. 30% monetization lift)

---

## Dependency & Team Planning

### Critical Path (Phase 0-1)
```
Snowflake setup (2w)
    ↓
Data migration (3w) ───→ Phase 0 Text-to-SQL development (4w)
    ↓
Schema expansion (2w) ───→ Phase 1 persona dashboards (3w)
```

### Team Scaling
- **Phase 0:** 5 people (2 BE, 1 FE, 1 ML, 1 DE)
- **Phase 1:** 6 people (+1 support)
- **Phase 2:** 8 people (+1 DevOps, +1 QA)
- **Phase 3:** 10+ people (+data scientist, +product, +customer success)

---

## Success Metrics by Phase

| Phase | MAU | Queries/Day | Latency p95 | Uptime | NPS | SQL F1 |
|-------|-----|------------|------------|--------|-----|--------|
| Phase 0 | 30+ | 20+ | <10s | >95% | 30+ | >95% |
| Phase 1 | 40+ | 100+ | <5s | 99.5% | 40+ | >95% |
| Phase 2 | 45+ | 500+ | <3s | 99.5% | 50+ | >97% |
| Phase 3 | 100+ | 1,000+ | <2s | 99.9% | 55+ | >97% |

---

## Budget & Resource Allocation

**Infrastructure Costs (Annual)**
| Component | Phase 0-1 | Phase 2 | Phase 3 |
|-----------|----------|---------|---------|
| Snowflake | $60K | $120K | $250K+ |
| Supabase | $2.4K | $5K | $20K |
| AWS (Redis, ElastiCache) | $2.4K | $5K | $10K |
| Vercel (Next.js hosting) | $1.2K | $2.4K | $5K |
| API costs (Claude, OpenAI, Cohere) | $3.6K | $10K | $30K |
| **Total** | **$69.6K** | **$142.4K** | **$315K+** |

**Engineering Costs (Annual)**
| Role | Phase 0-1 (FTE months) | Cost |
|------|--------|------|
| Backend Engineers (2) | 16 | $240K |
| Frontend Engineer (1) | 8 | $120K |
| ML Engineer (1) | 8 | $120K |
| Data Engineer (1) | 8 | $120K |
| DevOps (Phase 2+) | 4 | $60K |
| Support/CS (Phase 1+) | 4 | $60K |
| **Total** | | **$720K** |

**ROI Estimate**
- Cost: ~$790K (infra + team, Year 1)
- Value: 2 analysts × $150K × 40% time saved = $120K saved
- Additional value: User productivity gains = $438K/year (from PRD)
- **Total Year 1 value: ~$560K**
- **Payback period: ~17 months**
- **Phase 3 scale-up:** Multi-customer model, license SaaS version

---

## Go/No-Go Decision Gates

| Phase | Gate | Decision Criteria | Stakeholders |
|-------|------|------------------|--------------|
| Phase 0 → 1 | Week 8 | 20+ queries/day, F1 >95%, NPS >30 | CEO, CIO, PM |
| Phase 1 → 2 | Week 16 | 100+ queries/day, 40+ MAU, NPS >40 | CEO, CFO, all heads |
| Phase 2 → 3 | Week 24 | 500+ queries/day, 99.5% uptime achieved | Board, CEO |
| Pricing (if SaaS) | Week 32 | 3+ predictive models validated, market readiness | CEO, board |

---

**Document Status:** Active roadmap (updated weekly)  
**Next Planning Review:** 2026-03-11 (Phase 0 week 1 review)  
**Final Review Before Launch:** 2026-03-25 (final Phase 0 prep)
