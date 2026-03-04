# Portfolio Intelligence Hub - Success Metrics & Measurement

**Version:** 1.0  
**Status:** Active  
**Last Updated:** 2026-03-04  
**Owner:** Product Management  
**Audience:** Executive stakeholders, product team

---

## 1. North Star Metric

### Time to Insight: From Question to Actionable Answer

**Definition:** Duration from user asks a question until they receive a complete, actionable answer.

| Phase | Metric | Current | Target | Improvement |
|-------|--------|---------|--------|------------|
| Phase 0 (MVP) | Time to Insight | 24-48 hours | < 30 seconds | 2,880-5,760x faster |
| Phase 1 (Full Platform) | Time to Insight | < 30 seconds | < 15 seconds | 2x improvement via caching |
| Phase 2 (Scale) | Time to Insight | < 15 seconds | < 5 seconds | 3x improvement via pre-computation |
| Phase 3+ (Intelligence) | Time to Insight | < 5 seconds | < 2 seconds | Predictive insights |

**Measurement:**
- Client-side timestamp on question submission
- Server-side timestamp on answer delivery
- Delta = Time to Insight
- Sample: all user queries logged automatically
- Reporting: daily dashboard showing p50, p95, p99 latency

**Success Threshold:** p95 < 5 seconds by end of Phase 1 (Week 16)

---

## 2. Input Metrics

### 2.1 Query Volume

**Definition:** Number of queries submitted to the platform per day

| Metric | Phase 0 Target | Phase 1 Target | Phase 2 Target |
|--------|--------|--------|--------|
| Queries/day | 20+ | 100+ | 500+ |
| Queries/user/week (avg) | 5-10 | 15-20 | 30-50 |
| Peak queries/hour | 10-15 | 30-50 | 100+ |

**Calculation:** COUNT(queries) WHERE created_at >= TODAY()

**Reporting:** Daily via Datadog dashboard

**Interpretation:**
- <20 queries/day = Low adoption (investigate barriers)
- 50-100 queries/day = Good adoption
- 200+ queries/day = Excellent adoption, approaching peak usage

### 2.2 Active Users

**Definition:** Users who submitted at least 1 query in the past 7 days

| Metric | Phase 0 Target | Phase 1 Target | Notes |
|--------|--------|--------|--------|
| Monthly Active Users (MAU) | 15-20 | 35-40 | Of 45 total users |
| Daily Active Users (DAU) | 5-10 | 20-25 | |
| MAU / Total Users | 35-45% | 78-89% | Adoption rate |

**Calculation:** COUNT(DISTINCT user_id) WHERE query_created_at >= CURRENT_DATE - 7

**Reporting:** Weekly executive dashboard

**Success Criteria:**
- Phase 0: 15+ MAU by week 8
- Phase 1: 40+ MAU by week 16 (89% adoption)

### 2.3 Document Ingestion Volume

**Definition:** Number of documents successfully indexed and searchable

| Metric | Phase 0 Target | Phase 1 Target | Notes |
|--------|--------|--------|--------|
| Total documents indexed | 10-20 | 200+ | Leases, reports, policies |
| Documents/week | 5-10 | 20-40 | Upload velocity |
| Document chunks | 3,000-6,000 | 60,000+ | Pages indexed |

**Calculation:** COUNT(DISTINCT document_id) WHERE status = 'indexed'

**Success Indicator:** Strong positive correlation between document availability and semantic search queries

### 2.4 Cache Hit Rate

**Definition:** Percentage of queries served from cache vs. executed fresh

| Metric | Phase 0 Target | Phase 1 Target | Phase 2 Target |
|--------|--------|--------|--------|
| Cache hit rate | 5-10% | 20-30% | 40%+ |

**Calculation:** cache_hits / (cache_hits + cache_misses) × 100

**Improvement Path:**
- Phase 0: Minimal caching (new queries, low volume)
- Phase 1: Identify top 50 queries, cache with 1-4 hour TTL
- Phase 2: Redis optimization, materialized views for KPIs

**Cost Impact:** Each cache hit saves ~$0.05-0.10 in Snowflake credits

---

## 3. Quality Metrics

### 3.1 SQL Generation Accuracy (F1 Score)

**Definition:** Percentage of generated SQL queries that execute successfully and return correct results

**Measurement Methodology:**

1. **Gold-Standard Query Set:** 100 hand-verified queries representing each persona and complexity level
   - 30 simple queries (single table, basic WHERE)
   - 40 moderate queries (2-3 table joins, aggregations)
   - 20 complex queries (4+ tables, CTEs, window functions)
   - 10 edge cases (NULL handling, date math, currency formatting)

2. **F1 Calculation:**
   - Precision: # correct SQL / # total generated SQL
   - Recall: # correct SQL / # expected correct SQL
   - F1 = 2 × (Precision × Recall) / (Precision + Recall)

3. **Definition of "Correct":**
   - Syntactically valid Snowflake SQL
   - Executes without timeout or error
   - Returns expected row count (±5%)
   - Results match gold-standard within 0.1% numerical tolerance

| Phase | Target F1 | Current | Milestone |
|-------|-----------|---------|-----------|
| Phase 0 | >90% | TBD | Week 4 target |
| Phase 0 (end) | >95% | TBD | Week 8 target |
| Phase 1 | >97% | TBD | Week 12 target |
| Phase 2 | >98% | TBD | Week 20 target |

**Measurement:**
- Weekly test runs of gold-standard set
- Automated testing framework (CI/CD)
- Manual human verification for failures
- Feedback loop: failed queries used for model fine-tuning

**Example:**
```
Query: "Show me occupancy by property for last quarter"

Gold-standard SQL:
SELECT p.property_name, 
  COUNT(CASE WHEN os.occupied = TRUE THEN 1 END)::float /
  COUNT(*) * 100 as occupancy_pct
FROM occupancy_snapshots os
JOIN properties p ON os.property_id = p.property_id
WHERE os.snapshot_date >= DATE_TRUNC('QUARTER', CURRENT_DATE) - 3 MONTHS
GROUP BY p.property_name
ORDER BY occupancy_pct DESC;

Generated SQL: (evaluated as correct/incorrect)
- Did it execute? ✓
- Row count matches? ✓ (87 properties)
- Values match? ✓ (±0.1%)
→ Result: CORRECT (add to pass rate)
```

### 3.2 Answer Correctness (Human Evaluation)

**Definition:** Percentage of answers rated "correct and actionable" by human expert review

**Measurement Methodology:**

1. **Sample:** 20 queries/week from production (stratified by persona, complexity)
2. **Evaluation:** Domain expert (real estate PM or finance analyst) rates each answer:
   - **5 (Correct):** Answer fully addresses query, data accurate, actionable
   - **4 (Mostly Correct):** Minor omissions or formatting issues, still useful
   - **3 (Partially Correct):** Some data accuracy issues, requires user verification
   - **2 (Incorrect):** Major errors, contradicts facts
   - **1 (Hallucinatory):** Confidently incorrect, misleading

3. **Success Criterion:** Score ≥ 4 ("Correct or Mostly Correct")

| Phase | Target | Rationale |
|-------|--------|-----------|
| Phase 0 | >85% | Baseline acceptable (users expect some variability) |
| Phase 1 | >93% | High confidence (production-grade) |
| Phase 2 | >95% | Enterprise-grade reliability |

**Calculation:**
```
Correctness Score = (# answers rated 4-5) / (# evaluated) × 100
```

**Example Evaluation:**

Query: "What's our delinquent rent by property this month?"

Generated Answer: "Your portfolio has $47,300 in delinquent rent across 4 properties.
Westwood Commons ($18,200 from 2 tenants), Riverside Plaza ($12,400 from 1 tenant
in eviction), Mountain View ($9,800 from 3 tenants, 1 in payment plan), Downtown
Office ($6,900 from 1 tenant). Collections trend: 0.6% improvement vs. last year."

Evaluator Feedback:
- ✓ Numbers verified against rent_collections table
- ✓ Breakdown by property correct
- ✓ Includes context (eviction status, payment plans)
- ✓ Includes trend context
- Rating: 5 (Correct) ✓

### 3.3 Semantic Search NDCG@5

**Definition:** Normalized Discounted Cumulative Gain measuring ranking quality of document retrieval

**Methodology:**

1. **Test Queries:** 50 semantic search queries with known relevant documents
   - Example: "What are the renewal terms in our Westwood lease?"
   - Known relevant documents: Westwood Commons lease book (pages 47-52)

2. **NDCG@5 Calculation:**
   - Retrieval returns top-5 documents
   - Each document scored 0-3 by expert:
     - 3 = Highly relevant (directly answers query)
     - 2 = Relevant (contains useful context)
     - 1 = Marginally relevant
     - 0 = Not relevant
   - NDCG = CG@5 / IdealCG@5
   - Range: 0-1, higher is better

| Phase | Target NDCG@5 | Method |
|-------|---------|--------|
| Phase 0 | 0.75+ | Vector search only |
| Phase 1 | 0.85+ | + Cohere reranking |
| Phase 2 | 0.90+ | + Hybrid search (vector + keyword) |

**Measurement:**
- Weekly test set (50 queries)
- Manual evaluation by domain expert
- Track before/after reranking impact
- Identify low-scoring queries for training data

**Example:**

Query: "What are the renewal options for our commercial leases?"

Retrieval Results (before reranking):
1. [Score: 3] Westwood Commons lease book (renewal clause) - RELEVANT
2. [Score: 3] Downtown Office lease book (renewal terms) - RELEVANT
3. [Score: 2] Property management policy (renewal process) - MARGINALLY RELEVANT
4. [Score: 1] Riverside Plaza lease book (no renewal section) - NOT RELEVANT
5. [Score: 0] Maintenance report (unrelated) - NOT RELEVANT

CG@5 = 3 + 3 + 2 + 1 + 0 = 9
IdealCG@5 = 3 + 3 + 3 + 2 + 2 = 13 (theoretical perfect ranking)
NDCG@5 = 9 / 13 = 0.69 → Target improvement to 0.85+ with reranking

---

## 4. Business Metrics

### 4.1 User Adoption Rate

**Definition:** Percentage of internal users actively using platform

| Phase | Target | Notes |
|-------|--------|--------|
| Phase 0 (Week 8) | 30-35% (14 users) | Early adopters + pilot group |
| Phase 1 (Week 16) | 80%+ (36 users) | All personas onboarded |
| Phase 2 (Week 24) | 90%+ (40+ users) | Majority of eligible users |

**Calculation:** MAU (past 30 days) / Total eligible users × 100

**Measurement:** Monthly review

**Drivers of Adoption:**
- Executive sponsorship and mandate
- User training and support resources
- Integration with daily workflows
- Visible time savings vs. previous process

### 4.2 Net Promoter Score (NPS)

**Definition:** Customer satisfaction metric (likelihood to recommend to colleagues)

**Measurement:** Quarterly survey (in-app or email)

| Phase | Target | Scale |
|-------|--------|--------|
| Phase 0 | 25-35 | Early feedback |
| Phase 1 | 45-50 | Good adoption signal |
| Phase 2 | 55-65 | Strong satisfaction |

**Survey Questions:**
- "How likely would you recommend Portfolio Intelligence Hub to a colleague?" (0-10)
- "What's the biggest value you get from the platform?" (open-ended)
- "What's the #1 thing you'd improve?" (open-ended)

**NPS Calculation:** % Promoters (9-10) - % Detractors (0-6)

**Target Detractors:** <20% of users (improve support/features for this segment)

### 4.3 Hours Saved Per User Per Week

**Definition:** Time saved by avoiding analyst data requests

**Measurement Methodology:**

1. **Baseline (Current State):**
   - Survey: "How many hours/week do you spend waiting for data from analysts?"
   - Result: Average 3-4 hours/week per Property Manager, Broker
   - Finance: 4-5 hours/week on budget variance reconciliation

2. **Post-Implementation:**
   - Track: How often users answer their own questions vs. requesting analyst help?
   - Survey: "How many hours/week saved by using Platform Intelligence Hub?"
   - Example: PM spends 10 minutes answering occupancy question themselves vs. 2-4 hour wait for analyst
     - Savings: 2-4 hours per question
     - If 5 questions/month: ~10-20 hours/month saved = 2.5-5 hours/week

| User Type | Phase 0 Target | Phase 1 Target | Phase 2 Target |
|-----------|--------|--------|--------|
| Property Manager | 1-2 hrs/week | 2-3 hrs/week | 3-4 hrs/week |
| Finance | 2-3 hrs/week | 3-4 hrs/week | 4-5 hrs/week |
| Broker | 1-2 hrs/week | 2-3 hrs/week | 2-3 hrs/week |
| Executive | 0.5-1 hrs/week | 1-2 hrs/week | 1-2 hrs/week |
| **Portfolio Average** | **1-1.5 hrs/week** | **2-2.5 hrs/week** | **2.5-3.5 hrs/week** |

**Business Impact:**
- 45 users × 2.5 hours saved/week = 112.5 analyst-hours/week freed
- At $75/hour burdened cost = $8,437/week = $438K/year analyst time redirected to analysis
- ROI: If platform cost $50K/year, payback in 5-6 weeks

### 4.4 Analyst Productivity Reallocation

**Definition:** Shift in analyst time from routine data pulls to strategic analysis

| Time Allocation | Current | Phase 1 Target | Phase 2 Target |
|-----------------|---------|--------|--------|
| Routine data pulls | 70% | 30% | 10% |
| Strategic analysis | 20% | 60% | 80% |
| Platform support | 10% | 10% | 10% |

**Measurement:**
- Quarterly time-tracking survey of 2 analysts
- What projects can they now tackle with freed time?
  - Lease economics analysis
  - Disposition readiness scoring
  - Rent optimization modeling
  - Custom reporting automation

---

## 5. Guardrail Metrics

These metrics define acceptable operational performance; exceeding thresholds trigger alerts.

### 5.1 System Uptime

**Definition:** Percentage of time platform is available (not in maintenance or errors)

| Target | Threshold | Notes |
|--------|-----------|--------|
| Phase 0 | 95% | Development phase acceptable |
| Phase 1+ | 99.5% | Production-grade (21.6 min/month downtime) |

**Measurement:**
- Synthetic monitoring (Datadog) pinging API every 60 seconds
- Client-side error tracking (Sentry)
- Database health checks

**Incident Response SLA:**
- Detection: <2 minutes (automated alert)
- Investigation: <5 minutes
- Mitigation: <15 minutes (either fix or failover)
- Post-mortem: <24 hours (root cause analysis)

### 5.2 Query Latency (p95)

**Definition:** 95th percentile query response time from question to answer

| Phase | Target | Includes |
|-------|--------|----------|
| Phase 0 | <10 seconds | SQL generation + execution + formatting |
| Phase 1 | <5 seconds | + Redis caching optimization |
| Phase 2 | <3 seconds | + Materialized views |

**Breakdown (typical query):**
```
SQL Generation:        2 sec  (Claude API)
SQL Execution:         1 sec  (Snowflake)
Result Formatting:     0.5 sec
Network latency:       0.5 sec
─────────────────────────────
Total (p95):          ~4 sec
```

**Tracking:**
- Automatic logging via FastAPI middleware
- Datadog APM traces
- Alert if p95 > 8 seconds for >5 minutes

### 5.3 Query Error Rate

**Definition:** Percentage of queries that fail or return partial results

| Phase | Target | Acceptable Causes |
|-------|--------|-------------------|
| Phase 0 | <5% | SQL syntax errors, model confusion |
| Phase 1 | <2% | Only timeout/execution errors (not generation) |
| Phase 2 | <1% | Extremely rare |

**Categories:**
- **SQL Generation Failure** (0.5%): Model can't understand query intent
  - Mitigation: Confidence scoring + human review suggestion
- **SQL Execution Failure** (0.5%): Query times out or hits row limits
  - Mitigation: Query queuing, aggregate function suggestions
- **Answer Synthesis Failure** (0.5%): Results can't be formatted to narrative
  - Mitigation: Return raw table if synthesis fails
- **Permission/RBAC Error** (0.3%): User doesn't have access
  - Mitigation: Clear error message + suggest escalation

**Alert Threshold:** If error rate > 2% in 1-hour window, page on-call engineer

### 5.4 Snowflake Query Cost Per Answer

**Definition:** Snowflake credits consumed per user query

| Metric | Phase 0 Target | Phase 1 Target | Phase 2 Target |
|--------|--------|--------|--------|
| Avg cost/query | $0.10-0.20 | $0.05-0.10 | <$0.05 |
| Cost per user/month | ~$5-10 | ~$3-5 | <$3 |

**Calculation:**
```
Cost/query = (Query credits used × $4 per credit) / queries

Example: 100 queries/day cost $20 in credits
Cost/query = $20 / 100 = $0.20
```

**Cost Reduction Path:**
- Phase 0: High cost (no caching, fresh executions)
- Phase 1: Redis caching (40% cost reduction)
- Phase 2: Materialized views for KPIs (80% cost reduction on KPI queries)

**Budget:** $5K/month Snowflake credits allocated for Phase 1-2 platform costs

---

## 6. Before & After Comparison

### 6.1 Quantified Impact Table

| Metric | Before | After | Improvement |
|--------|--------|-------|------------|
| **Speed** |
| Time for analyst to answer occupancy question | 2-4 hours | <30 sec | 240-480x |
| Time for finance to run budget variance report | 6 hours | <5 min | 72x |
| Time for exec to get portfolio scorecard | 1-2 days | <15 sec | 5,760-11,520x |
| **Efficiency** |
| Analyst time on routine data pulls | 70% of week | 30% | -40 pp |
| Users served per analyst | ~22 users | ~45+ users | 2x capacity |
| Queries/day the platform handles | 0 | 100+ | ∞ |
| **Quality** |
| Data accuracy (manual queries) | 70% | 98% | +28 pp |
| Audit trail of data access | None | 100% | Complete |
| **Adoption** |
| Users with direct data access | 2 (analysts) | 40+ (all roles) | 2,000% |
| Decision speed (wait for data) | 2-3 days | <30 sec | Immediate |

### 6.2 User Time Savings Calculation

**Scenario: Property Manager at Riverside Plaza**

Before Portfolio Intelligence Hub:
```
Daily Tasks:
- Check occupancy status:
  Email analyst @ 8 AM → Wait until 10 AM-12 PM → 2-4 hours
  
- Answer tenant question on lease renewal terms:
  Search for lease document, manually review → 1-2 hours
  
- Prepare move-out report for marketing:
  Pull vacant units list from analyst → 1-2 hours
  
Total time spent on data requests: ~4-8 hours/week
```

After Portfolio Intelligence Hub:
```
Same tasks:
- Check occupancy status:
  Ask "What's our occupancy?" in chat → 15 seconds instant
  
- Answer tenant question on lease renewal:
  Ask "Show renewal terms for Unit 405" → 20 seconds
  
- Prepare move-out report:
  Ask "List vacant units ready to lease" → 10 seconds
  
Total time spent on data requests: ~30 minutes/week

Savings: 3.5-7.5 hours/week per PM → $525-1,125/week × 12 PMs = $63-135K/year
```

---

## 7. Dashboard Mockup & KPIs

### 7.1 Executive Dashboard

```
┌──────────────────────────────────────────────────────────────┐
│ Portfolio Intelligence Hub - Executive Dashboard              │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│ ┌─────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│ │  ADOPTION       │  │  PERFORMANCE     │  │  GUARDRAILS  │ │
│ ├─────────────────┤  ├──────────────────┤  ├──────────────┤ │
│ │ MAU: 38/45      │  │ Avg latency      │  │ Uptime: 99.7%│
│ │ (84%)           │  │ p95: 4.2 sec     │  │ Error rate:  │
│ │ ↑ +8 from week  │  │ ✓ On target      │  │ 0.8% ✓       │
│ │                 │  │                  │  │              │
│ │ Query vol:      │  │ SQL accuracy     │  │ Query cost:  │
│ │ 156 today       │  │ F1: 96.2%        │  │ $0.08/query  │
│ │ ↑ +12% WoW      │  │ ✓ On target      │  │ ✓ Budget ok  │
│ │                 │  │                  │  │              │
│ │ NPS: 48         │  │ Answer correct   │  │ SLA Incidents│
│ │ ↑ from 42       │  │ 94.3%            │  │ 0 this week  │
│ │ ✓ Exceeding     │  │ ✓ High quality   │  │ ✓ Excellent  │
│ └─────────────────┘  └──────────────────┘  └──────────────┘
│
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ WEEKLY QUERY VOLUME                                      │ │
│ │                                                          │ │
│ │ 180  ┤     ╭─╮                                           │ │
│ │ 160  ┤     │ │  ╭─╮                                      │ │
│ │ 140  ┤     │ │  │ │  ╭─╮                                 │ │
│ │ 120  ┤  ╭─╮│ │  │ │  │ │                                 │ │
│ │ 100  ┤  │ ││ │  │ │  │ │  ╭─╮                            │ │
│ │  80  ┤  │ ││ │  │ │  │ │  │ │  ╭─╮                       │ │
│ │       └──────────────────────────────────────            │ │
│ │      W1  W2  W3  W4  W5  W6  W7  W8                      │ │
│ │      Phase 0 Progress (Target: 50+ by W8)                │ │
│ └──────────────────────────────────────────────────────────┘ │
│
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ PERSONA ENGAGEMENT (Phase 1 Target: 40+ users)           │ │
│ │                                                          │ │
│ │ Property Managers: 11/12 (92%) ████████████ [STRONG]    │ │
│ │ Brokers/Leasing:   4/8 (50%)  ██████ [NEEDS WORK]       │ │
│ │ Finance:           12/15 (80%) ██████████ [STRONG]      │ │
│ │ Executives:        11/10 (110%) ████████████ [LEADING] │ │
│ │                                                          │ │
│ └──────────────────────────────────────────────────────────┘ │
│
│ ⚠ Alerts: Broker adoption below target. Recommended action:  │
│           Schedule training session, identify pain points.    │
│
└──────────────────────────────────────────────────────────────┘
```

### 7.2 Product Team Dashboard

```
┌──────────────────────────────────────────────────────────────┐
│ Portfolio Intelligence Hub - Product Analytics                │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│ QUALITY METRICS                                               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ SQL Generation F1 Score: 96.2%   Target: >95%          │ │
│ │ ██████████████████████████ (96.2%)  ✓ ON TARGET        │ │
│ │                                                          │ │
│ │ Answer Correctness: 94.3%          Target: >93%        │ │
│ │ ██████████████████████████ (94.3%)  ✓ EXCEEDING         │ │
│ │                                                          │ │
│ │ Semantic Search NDCG@5: 0.82       Target: >0.85 (P1)  │ │
│ │ ████████████████████ (0.82)         ⚠ BELOW TARGET     │
│ │ Action: Implement Cohere reranking (scheduled W10)     │ │
│ └─────────────────────────────────────────────────────────┘ │
│
│ OPERATIONAL METRICS                                           │
│ ┌──────────────────┬──────────────────┬──────────────────┐ │
│ │ Metric           │ Current          │ Target           │ │
│ ├──────────────────┼──────────────────┼──────────────────┤ │
│ │ Cache Hit Rate   │ 8.2% (up from 5%)│ 20% by W10       │ │
│ │ P95 Latency      │ 4.8 sec          │ <5 sec by W12    │ │
│ │ Error Rate       │ 1.2%             │ <2% by W8        │ │
│ │ Query Cost/unit  │ $0.12            │ <$0.10 by W12    │ │
│ └──────────────────┴──────────────────┴──────────────────┘ │
│
│ TOP QUERIES (By Volume)                                      │
│ 1. "Show occupancy at [property]" - 28 queries/day          │
│ 2. "What's delinquent rent?" - 12 queries/day               │
│ 3. "Renewal pipeline [property]" - 8 queries/day            │
│ 4. "Budget variance [property]" - 7 queries/day             │
│ 5. "Show work orders [category]" - 5 queries/day            │
│                                                               │
│ Recommendation: Create saved queries for #1, #2, #5 (high   │
│ reuse potential, further cache opportunity)                  │
│
│ ERROR RATE TREND                                             │
│ ┌──────────────────────────────────────────────────────┐   │
│ │                                                      │   │
│ │ 2.5% ┤  ╭──╮                                         │   │
│ │      ┤  │  │ ╭──╮                                    │   │
│ │ 1.5% ┤  │  ╰─╯  ╰──╮ ╭──╮                           │   │
│ │      ┤           │ ╰─╯                              │   │
│ │ 0.5% ┤                ╭──╮ ╭──╮ ╭──╮              │   │
│ │      └────────────────────────────────────────────   │   │
│ │      W1  W2  W3  W4  W5  W6  W7  W8                 │   │
│ │                                                      │   │
│ │ Trend: ↓ Improving (good quality assurance)         │   │
│ └──────────────────────────────────────────────────────┘   │
│
└──────────────────────────────────────────────────────────────┘
```

---

## 8. Measurement Methodology by Metric

### 8.1 Automated Measurement (Real-time)
- Query latency: Datadog APM
- Error rate: Sentry + custom logging
- Uptime: Synthetic monitoring
- Cache hit rate: Redis metrics
- Query volume: Application logs
- User adoption: Clerk + application tracking

### 8.2 Manual Measurement (Weekly/Monthly)
- SQL accuracy (F1): Automated test suite on gold-standard set
- Answer correctness: Manual expert review (5% sample)
- Semantic search NDCG: Weekly evaluation
- Hours saved: Quarterly survey

### 8.3 Incident Response & Tracking
```
When metric exceeds guardrail:
1. Automatic alert triggered (Datadog)
2. On-call engineer pages in if no auto-remediation
3. Post-mortem within 24 hours
4. Root cause analysis + preventive action
5. Metric improvement tracked in next week's dashboard
```

---

## 9. Success Criteria Summary

| Phase | Key Metrics | Go/No-Go Decision Point |
|-------|-----------|------------------------|
| Phase 0 (MVP) | Uptime >95%, F1 >90%, 20+ queries/day, 15+ MAU | Week 8 review |
| Phase 1 (Core) | Uptime 99.5%, F1 >95%, 100+ queries/day, 40+ MAU, NPS >40 | Week 16 review |
| Phase 2 (Scale) | 500+ queries/day, 45+ MAU, Cache hit 40%+, p95 <3s | Week 24 review |
| Phase 3+ | Revenue/monetization, 2x user expansion | Quarterly |

**Exit Criteria for Phase 0 → Phase 1 Transition:**
- All metrics green
- No critical bugs in production
- Pilot users report positive feedback
- Executive sign-off on roadmap

---

**Document Status:** Active measurement plan  
**Review Cadence:** Weekly executive review, monthly deep-dive  
**Next Review Date:** 2026-03-11
