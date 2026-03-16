# Portfolio Intelligence Hub - Capacity Plan

## Executive Summary
Portfolio Intelligence Hub is an NLP-powered analytics engine for real estate portfolios. This plan quantifies infrastructure, LLM costs, and team capacity for current state, 2x growth, and 10x growth scenarios.

---

## Current State (Q1 2026)

### Usage Metrics
- **Active Users:** 120 (portfolio managers + analysts)
- **Queries/Day:** 4,200 (35 per user average)
- **Average Query Latency:** 24 seconds (target 30s)
- **LLM Cost/Query:** $0.18 (GPT-4 inference + token overhead)
- **Monthly Data Refresh Rate:** Daily (property metrics, financials, risk scores)

### Infrastructure
| Component | Current | Monthly Cost |
|-----------|---------|--------------|
| **API Servers** | 3 instances (t3.large) | $432 |
| **NLP Inference Service** | 2 instances (p3.2xlarge GPU) for model cache | $5,600 |
| **PostgreSQL Database** | db.r5.2xlarge (8 vCPU, 64 GB) | $3,600 |
| **Vector Store (Pinecone)** | 1.2M embeddings @ 50 dim | $150 |
| **LLM API Costs** | 4,200 queries × $0.18 = $756/day | $22,680 |
| **Query Cache (Redis)** | 10 GB cluster (similar queries cached) | $900 |
| **Object Storage (reports)** | 100 GB | $2.30 |
| **Monitoring/Logging** | CloudWatch + DataDog | $600 |
| **Total Monthly** | | **$33,965** |

**Monthly Breakdown by Function:**
- LLM API (core cost): 67%
- GPU inference: 17%
- Infrastructure: 16%

### Database Sizing
- **Fact Tables:** 2.5M property records, 50M transactions/year
- **Document Storage:** Portfolio summaries, market research (50 GB)
- **Time-Series:** Property value/performance history (180 days)
- **Daily Ingestion:** ~150 MB (market data, property updates, financial feeds)

### Team Capacity
| Role | Count | Utilization |
|------|-------|-------------|
| **Backend Engineers** | 2 | 80% |
| **ML/NLP Engineers** | 1.5 | 90% |
| **Data Engineer** | 1 | 75% |
| **SRE/DevOps** | 0.5 | 60% |
| **Product Manager** | 1 | 85% |

---

## 2x Growth Scenario (12 months forward)
**Assumption:** 240 users, 8,400 queries/day, avg latency 28s, $0.16/query (optimization savings)

### What Breaks First
1. **LLM Cost Explosion:** 8,400 queries × $0.18 = $45K/month (unsustainable; need prompt optimization or model downgrade)
2. **GPU Inference Throughput:** Single GPU can't handle peak load (9 AM spike); inferences queued, latency >60s
3. **Vector Search Latency:** Pinecone searches slow down with 2.4M embeddings; lookup takes 5+ seconds
4. **Query Classification Accuracy:** Classifier trained on 4K queries; at 8.4K/day, doesn't generalize well (misclassify complex queries)

### Required Infrastructure Changes
| Component | Current → 2x | Incremental Cost |
|-----------|--------------|-----------------|
| **GPU Inference** | 2 × p3.2xlarge → 4 × p3.2xlarge + auto-scaling | +$5,600/month |
| **API Servers** | 3 × t3.large → 5 × t3.large + ASG | +$288/month |
| **PostgreSQL** | r5.2xlarge → r6i.3xlarge + 1 read replica | +$3,200/month |
| **Vector Store** | Pinecone (2.4M embeddings) | +$100/month |
| **LLM API Costs** | 8.4K queries × $0.16 (optimized) = $40K/month instead of $50K | **-$10K/month** |
| **Query Cache** | 10 GB → 25 GB Redis cluster | +$450/month |
| **Monitoring** | DataDog scaling | +$300/month |
| **Total Monthly @ 2x** | | **$38,938** (+15%) |

**Key optimization at 2x scale:**
- Move from GPT-4 to GPT-3.5-turbo for simpler queries (60% of queries)
- Implement semantic caching (if same question asked twice in 24h, cache answer)
- Add prompt compression (reduce token count by 30% via summarization)

### LLM Cost Optimization Strategy
```
Current (4.2K queries/day):
- 70% of queries use GPT-4 ($0.15 + tokens): $0.24 avg cost
- 30% of queries use GPT-3.5 ($0.01 + tokens): $0.05 avg cost
- Blended: $0.18/query

At 2x (8.4K queries/day):
- 30% use GPT-4 (complex queries): $0.24 avg
- 70% use GPT-3.5 (simple, bulk): $0.05 avg
- Blended: $0.11/query (-39%)

Semantic caching (20% of queries are repeats):
- Cache hit: $0.001 (no LLM call)
- Effective blended: $0.088/query (-51%)
```

---

## 10x Growth Scenario (24 months forward)
**Assumption:** 1,200 users, 42K queries/day, avg latency 30s, $0.08/query (aggressive optimization)

### What Breaks First
1. **LLM Cost Becomes Prohibitive:** 42K queries × $0.18 = $7.5K/day; unsustainable without major optimization
2. **Model Generalization:** Query distribution changes dramatically; classifier needs continuous retraining
3. **Real-Time Data Sync:** Daily refresh can't keep up with 42K query demand; users get stale data
4. **Compliance/Data Privacy:** 1,200 users = regulatory oversight; need audit logs, data retention policies, multi-tenancy isolation

### Required Infrastructure Changes
| Component | Current → 10x | Incremental Cost |
|-----------|--------------|-----------------|
| **GPU Inference** | 2 × p3.2xlarge → 12 × p3.2xlarge + Kubernetes orchestration | +$16,800/month |
| **API Tier** | 3 × t3.large → 20 × t3.xlarge + multi-region | +$2,880/month |
| **PostgreSQL** | r5.2xlarge + 1 replica → r6i.4xlarge + 4 replicas + sharding (2 shards) | +$8,000/month |
| **Vector Store** | Pinecone → Dedicated Milvus/Weaviate cluster (12M embeddings) | +$1,200/month |
| **LLM API Costs** | 42K queries × $0.08 (heavily optimized) = $9,600/month | **-$13K/month** |
| **Fine-Tuned Models** | 0 → Custom fine-tuned model for portfolio domain | +$2,000/month (API cost) |
| **Data Warehouse** | 0 → BigQuery for analytics + historical trends | +$1,500/month |
| **Search Engine** | 0 → Elasticsearch for document search (property docs, reports) | +$1,000/month |
| **Real-Time Sync** | Batch → Kafka streams for near-real-time data | +$800/month |
| **Monitoring & Compliance** | DataDog Enterprise + audit logging | +$1,500/month |
| **Total Monthly @ 10x** | | **$33,480** (note: actually cheaper than 2x due to LLM cost reduction) |

### Architectural Changes @ 10x

**Multi-Tenant Isolation:**
- Current: Single shared database (fast but risky)
- At 10x: Separate schemas per customer (data isolation, compliance)
- Implementation: Row-level security + tenant ID in every query

**LLM Cost Reduction Strategy @ 10x:**
```
Techniques:
1. Fine-tuned model ($2K/month) reduces prompt tokens by 40%
2. Semantic caching (40% of queries are repeats): cache hit = $0.001
3. Query classifier pre-filters simple vs. complex (70% don't need LLM)
   - Simple: keyword search only ($0)
   - Complex: LLM-powered ($0.15)

At 10x:
- 40% simple queries (keyword search): $0
- 50% medium queries (GPT-3.5): $0.05
- 10% complex queries (fine-tuned GPT-4): $0.08
- Cache hits (40% of queries cached): $0.001 overhead
- Blended: $0.028/query (81% reduction from current $0.18)
```

**Real-Time Data Architecture:**
- Current: Batch daily refresh (data 24h stale)
- At 10x: Kafka event stream (property updates in <5min)
- Enables use cases: "Alert me when any property's risk score drops below X"

### Team Scaling
| Role | Current → 10x | Notes |
|---|---|---|
| **Backend Engineers** | 2 → 6 (3 query service, 2 data pipeline, 1 platform) | Multi-tenant isolation, compliance |
| **ML/NLP Engineers** | 1.5 → 5 (model training, fine-tuning, evaluation) | Custom models, continuous retraining |
| **Data Engineers** | 1 → 4 (real-time sync, data quality, warehouse) | Kafka, BigQuery, data governance |
| **SRE/DevOps** | 0.5 → 3 (multi-region, cost optimization, chaos) | Kubernetes, cost management |
| **Product Manager** | 1 → 1.5 (PM + domain specialist) | Deeper real estate expertise |
| **Data Science** | 0 → 2 (analytics, customer success metrics) | Predictive models, churn prediction |
| **Compliance Officer** | 0 → 0.5 (part-time) | Multi-tenant compliance, audit logs |
| **Total Cost** | ~$450K/year → ~$1.8M/year | +300% headcount for 10x user growth |

---

## Cost Optimization Timeline

### Phase 1: Immediate (Weeks 1-4)
1. **Prompt Compression:** Reduce token count by 20% (removes redundant context) → saves 15% LLM cost
2. **Semantic Caching:** Cache identical queries for 24h → saves 10-15% LLM cost
3. **Query Classification:** Route simple keyword queries away from LLM → saves 20% LLM cost
4. **Total savings:** 40% LLM cost reduction possible

### Phase 2: Medium-term (Months 2-6)
1. **Model Selection:** Downgrade simple queries to GPT-3.5 (from GPT-4) → saves 50% LLM cost on 60% of queries
2. **Fine-tuning:** Train domain-specific model for portfolio queries → saves 30% token overhead
3. **Infrastructure:** Move to GPU inference cluster (vs. API calls) for repetitive work → saves 70% on cached queries

### Phase 3: Long-term (Months 6-12)
1. **Custom Model:** Deploy fully fine-tuned model for portfolio domain → saves 80% LLM cost
2. **Real-Time Data:** Kafka-based updates eliminate stale data re-queries → saves 10% LLM cost
3. **Predictive Caching:** Pre-generate answers to likely queries (based on user behavior) → saves 20% LLM cost

---

## Monitoring & Decision Gates

### Weekly Metrics
- LLM cost/query: Alert if >$0.25 (baseline $0.18)
- Query classification accuracy: Alert if <97%
- Answer validation failures: Alert if >0.5%
- GPU utilization: Alert if >85% sustained

### Monthly Decision Gates
| Metric | Threshold | Action |
|--------|-----------|--------|
| LLM cost | >$25K/month | Implement semantic caching + model downgrade |
| Query latency | p95 >45s | Add GPU servers or optimize inference |
| Classification accuracy | <97% | Retrain classifier on recent queries |
| Cache hit ratio | <20% | Increase cache TTL or add semantic dedup |
| Answer validation failures | >5/month | Review model output; tighten validation |

