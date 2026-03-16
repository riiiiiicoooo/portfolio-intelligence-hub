# Portfolio Intelligence Hub - SLO Definitions

## SLO 1: Query Turnaround Time (Core Value Delivery)
**Target:** 95% of NL queries answered within 30 seconds
**Error Budget:** 5% of queries taking >30s per week
**Burn Rate Alert:** >40% of weekly error budget consumed in 24 hours

### Rationale
Portfolio Intelligence's core value is enabling real estate professionals to ask natural language questions about portfolio data and get instant answers (shift from 24-48 hour manual analysis). A 30-second SLO includes NLP inference (~2s) + SQL generation (~1s) + query execution (typical 5-20s, max 30s). This target is tight enough to deliver "instant insights" (users don't abandon) while loose enough to accommodate complex SQL (multi-table joins, aggregations). The 95% target allows 5% of complex queries (e.g., "compare portfolio composition across 50 properties") to take longer without breaking the SLA.

### Measurement
- Count: Query response time from user submit to answer delivery (sample: 100% of queries)
- Success: Response delivered in <30 seconds
- Failure: Response takes >30 seconds OR error returned
- Burn rate threshold: If >40% of weekly budget consumed in 24 hours, trigger infrastructure review (likely LLM latency spike)

---

## SLO 2: Query Classification Accuracy (Routing to Right Engine)
**Target:** 98% of queries classified correctly (routed to right execution path)
**Error Budget:** 2% of queries misclassified per week
**Burn rate Alert:** >30% of weekly classification error budget sustained >24 hours

### Rationale
NL queries must be classified into execution paths: simple keyword search, parameterized SQL, complex multi-table join, or "requires human review" (ambiguous query). Misclassification causes wrong answers (e.g., treating "portfolio risk" as keyword search instead of triggering portfolio-level analytics). A 98% accuracy target balances speed (can't spend 30s classifying) with correctness. The remaining 2% of misclassifications are acceptable if they're caught by answer validation (see SLO 3).

### Measurement
- Count: Classifier output vs. human-validated correct classification (weekly audit sample: 50 queries)
- Success: Classified query routed to correct execution engine
- Failure: Query classified to wrong engine; wrong answer or error returned
- Burn rate threshold: If >30% of weekly error budget sustained >24 hours, trigger classifier retraining

---

## SLO 3: Answer Validation & Safety (Preventing Bad Data to Users)
**Target:** 99% of NL answers are factually correct against ground truth data
**Error Budget:** 1% of answers hallucinating or wrong per week
**Burn rate Alert:** Any unvalidated answer reaching user triggers incident

### Rationale
Real estate investment decisions depend on accurate portfolio data. A single wrong answer ("You have 10 underperforming properties" when you have 3) could lead to million-dollar mistakes. A 99% correctness target is non-negotiable; the 1% error budget covers edge cases that validation misses. Unlike traditional SLOs with error budgets, answer correctness is asymmetric: answers must be validated before delivery. This SLO's burn rate alert is "any unvalidated answer" (zero tolerance), and every error requires root cause analysis.

### Measurement
- Count: Answer validation checks before user delivery (100% of answers checked)
- Success: Answer matches ground truth database within ±5% tolerance
- Validation layers: (1) SQL syntax check, (2) row count sanity check, (3) spot-check against raw data
- Burn rate threshold: Any failed validation = incident; escalate immediately

---

## SLO 4: LLM Inference Latency (Cost + User Experience)
**Target:** 95% of NLP inference completes in <3 seconds (includes model loading)
**Error Budget:** 5% of inferences taking >3s per day
**Burn rate Alert:** >50% of daily budget consumed in 4 hours

### Rationale
LLM inference (GPT-4, Claude) is the most expensive component (~$0.10-0.30 per query). Fast inference reduces cost/query and improves UX. A 3-second target is tight but achievable with model caching and prompt optimization. This SLO protects against cost explosion and user abandonment. Each second of inference latency = ~$0.02-0.05 added cost at scale.

### Measurement
- Count: Model inference time (tokenization → response generation) across all queries
- Success: Inference <3 seconds
- Failure: Inference >3 seconds (timeout, slow model endpoint)
- Burn rate threshold: If >50% of daily budget consumed in 4 hours, check: (1) LLM rate-limiting? (2) Prompt caching working? (3) Model endpoint availability?

---

## SLO 5: SQL Injection Prevention (Security/Safety)
**Target:** 100% of user-supplied SQL injection attempts blocked before execution
**Error Budget:** 0% tolerance for SQL injection vulnerabilities
**Burn rate Alert:** Any successful injection attempt triggers security incident

### Rationale
NL→SQL conversion creates a path for injection attacks ("Show me properties where owner='admin'; DROP TABLE properties; --'"). A 100% block rate (0% error budget) is mandatory for security. Unlike performance SLOs, this is a yes/no gate: either we prevent injection or we have a breach. This SLO's success is measured by security validation, not runtime exceptions.

### Measurement
- Count: SQL query validation before execution (100% of generated SQL checked)
- Success: Query passes syntax validation + parameterized query check; no literals from user input in WHERE clause
- Validation: Use prepared statements; strip/escape user input; run injection testing weekly
- Burn rate threshold: Any injection bypass = P1 security incident; immediate remediation

---

## Error Budget Governance
- **Review Cadence:** Daily check on query latency; weekly check on classification accuracy; monthly check on LLM cost
- **Escalation:** If turnaround SLO burns >40% budget by day 4, freeze new features; allocate optimization sprint
- **Classification retraining:** Weekly; if accuracy drops <98%, retrain on recent queries
- **Cost monitoring:** If cost/query exceeds $0.50, trigger prompt optimization or model downgrade (GPT-3.5 instead of GPT-4)
- **Security validation:** Monthly injection testing; continuous query validation in prod

