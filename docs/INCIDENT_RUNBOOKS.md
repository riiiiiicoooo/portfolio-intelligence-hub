# Portfolio Intelligence Hub - Incident Runbooks

---

## Incident 1: SQL Injection via Natural Language Query

### Context
A portfolio manager submits the query: "Show me properties where owner = 'abc'; DROP TABLE properties; -- ". The query classifier doesn't recognize the injection attempt. Generated SQL executes the DROP TABLE command, deleting 2,500 property records. Data is lost before backup recovery kicks in.

### Detection
- **Alert:** Database activity monitoring detects DROP/ALTER/TRUNCATE on prod tables
- **Symptoms:**
  - Property data suddenly missing from queries
  - Application errors: "Table not found"
  - CloudTrail shows unplanned DDL statement from application account

### Diagnosis (5 minutes)

**Step 1: Validate the breach**
```sql
-- Check table existence
SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='properties');
-- Result: FALSE (table deleted)

-- Check transaction logs
SELECT * FROM pg_stat_database_conflicts WHERE datname='portfolio_hub'
ORDER BY stats_reset DESC LIMIT 5;

-- Check when deletion happened
SELECT query, query_start, state
FROM pg_stat_activity
WHERE query LIKE '%DROP%' OR query LIKE '%DELETE%';
```

**Step 2: Identify injection vector**
```
Query that triggered injection:
Input: "Show me properties where owner = 'abc'; DROP TABLE properties; -- "

Generated SQL (BAD):
SELECT * FROM properties WHERE owner = 'abc'; DROP TABLE properties; --'

Why it happened:
- Input was concatenated directly into SQL (not parameterized)
- No input validation for SQL keywords (DROP, ALTER, TRUNCATE)
- Semicolon delimiter wasn't stripped
```

**Step 3: Assess data recovery**
```bash
# Check backup availability
aws rds describe-db-snapshots --db-instance-identifier portfolio-hub-db \
  --query 'DBSnapshots[0].[DBSnapshotIdentifier,SnapshotCreateTime,Status]'

# Check transaction logs (WAL retention)
ls -lh /var/lib/postgresql/data/pg_wal/ | tail -10
```

### Remediation

**Immediate (0-5 min): Restore from backup**
```bash
# Restore database from latest backup (taken 2 hours ago)
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier portfolio-hub-db-restored \
  --db-snapshot-identifier portfolio-hub-20260316-14-30

# Promote restored instance to primary (with brief downtime)
# Expected: 10-15 minutes to spin up new instance
```

**Short-term (5-30 min): Block injection attempts**
1. Implement parameterized queries:
   ```python
   # BAD:
   sql = f"SELECT * FROM properties WHERE owner = '{user_input}'"

   # GOOD:
   sql = "SELECT * FROM properties WHERE owner = %s"
   cursor.execute(sql, (user_input,))
   ```

2. Add input validation:
   ```python
   def validate_query_input(user_query):
       # Block SQL keywords in user input
       blocked_keywords = ['DROP', 'DELETE', 'ALTER', 'INSERT', 'TRUNCATE']
       for keyword in blocked_keywords:
           if keyword in user_query.upper():
               raise ValueError(f"Unsafe query contains '{keyword}'")
       return True
   ```

3. Implement prepared statements in query generator:
   ```python
   # Before generating SQL, validate that query doesn't contain SQL syntax
   safe_input = sanitize_nlp_output(user_query)
   sql = generate_parameterized_sql(safe_input)  # Uses placeholders, not string concat
   ```

**Root cause remediation (1-2 hours):**
1. **Add SQL injection testing to CI/CD:**
   ```python
   # Test suite: attempt 50 common injection patterns
   injection_tests = [
       "'; DROP TABLE properties; --",
       "' OR '1'='1",
       "'; UPDATE properties SET value=0; --",
       # ... more patterns
   ]
   for pattern in injection_tests:
       result = execute_safe_query(f"owner = '{pattern}'")
       assert result == []  # Should return empty, not execute injection
   ```

2. **Implement query validator:**
   ```python
   def validate_generated_sql(sql_string, user_input):
       # Parse SQL; ensure no user_input appears outside parameterized placeholders
       tree = sqlparse.parse(sql_string)[0]
       for token in tree.tokens:
           if user_input in str(token) and token.ttype not in (sqlparse.tokens.Placeholder,):
               raise ValueError("Injection detected: user input in non-parameterized clause")
       return True
   ```

3. **Add security audit logging:**
   ```python
   def log_sql_generation(user_query, generated_sql, executed):
       audit_log.info({
           'user_query': user_query,
           'generated_sql': generated_sql,
           'executed': executed,
           'timestamp': now(),
           'user_id': current_user.id
       })
   ```

**Data Recovery:**
```bash
# Monitor restore progress
watch -n 5 'aws rds describe-db-instances --db-instance-identifier portfolio-hub-db-restored \
  --query "DBInstances[0].[DBInstanceStatus,PercentProgress]"'

# Once restored, verify data integrity
psql -h portfolio-hub-db-restored.xxx.rds.amazonaws.com -U admin -d portfolio_hub -c \
  "SELECT COUNT(*) FROM properties; SELECT COUNT(*) FROM transactions;"
```

### Communication Template

**Internal (Slack #security-incidents)**
```
CRITICAL: SQL Injection Attack - Data Loss
Severity: P1 (Data Integrity Breach)
Duration: [START] - [END]
Impact: 2,500 property records deleted from production

Root Cause: SQL injection via natural language query; user input not parameterized in generated SQL.

Actions:
1. Restored database from 2-hour-old backup
2. Implemented parameterized queries in codebase
3. Added SQL injection input validation
4. Deploying emergency fix (ETA 30 min)

Recovery: Data restored by 15:45 UTC. 2-hour data loss (queries between 13:45-15:45).

Assigned to: [SECURITY_LEAD], [DB_ADMIN]
```

**Customer (Email to affected users)**
```
Subject: Critical Security Incident - Portfolio Data Recovery

We identified a SQL injection vulnerability in our query system that resulted in data loss affecting your portfolio records. We've immediately:

1. Restored your data from a recent backup (2-hour recovery window)
2. Patched the vulnerability with parameterized SQL queries
3. Deployed emergency security fixes

What you need to do:
- Check your property list to confirm all records are present
- Contact support if any data is missing or inconsistent
- Update your password as a precaution

We sincerely apologize for this incident and take security very seriously. A detailed postmortem will follow.

Best regards,
[SECURITY_TEAM]
```

### Postmortem Questions
1. Why wasn't input validation in place for SQL injection?
2. Why did CI/CD not test against injection patterns?
3. Should we implement query signing (LLM output authenticated before execution)?
4. What's the backup RTO/RPO policy for critical data?

---

## Incident 2: LLM Inference Timeout (Degraded Query Latency)

### Context
On March 15 at 3 PM, portfolio managers report slow query responses (60-120+ seconds vs. 30s target). The LLM inference service is unresponsive. 80% of queries are timing out after 60s; only 20% receive answers. System slowly recovers over 2 hours.

### Detection
- **Alert:** Query latency p95 >60s sustained for >5 minutes OR error rate >10%
- **Symptoms:**
  - API returns "504 Gateway Timeout" to users
  - CloudWatch shows LLM inference latency spike to 45-60+ seconds
  - GPU utilization at 100% on all inference servers

### Diagnosis (10 minutes)

**Step 1: Check LLM endpoint health**
```bash
# Verify LLM API is responding
curl -X POST https://api.openai.com/v1/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{"model": "gpt-4", "prompt": "test", "max_tokens": 10}' \
  --max-time 5

# Check rate limiting status
grep -i "rate_limit\|429\|timeout" /var/log/inference_service.log | tail -20
```

**Step 2: Monitor GPU utilization**
```bash
# SSH to inference server
nvidia-smi

# Expected: <80% utilization, <60°C temperature
# Symptom: 100% utilization, queue backing up
```

**Step 3: Check inference queue depth**
```python
# Query Redis for queue depth
redis-cli LLEN inference_queue
# Expected: <100 jobs
# Symptom: 5,000+ jobs backed up
```

### Remediation

**Immediate (0-5 min): Shed load**
```bash
# Reduce batch size to prioritize in-flight requests
kubectl set env deployment/inference-service \
  BATCH_SIZE=2 \
  MAX_QUEUE_DEPTH=100 \
  TIMEOUT_SECONDS=30

# Scale down non-critical features (experimental queries)
curl -X POST http://localhost:8080/inference/pause \
  -d '{"reason": "High latency; pausing experimental queries"}'

# Restart inference service to clear stuck connections
kubectl rollout restart deployment/inference-service
```

**Short-term (5-30 min): Scale up**
```bash
# Add more inference servers
kubectl scale deployment inference-service --replicas=6 \
  (from 4 replicas)

# Route traffic to healthy replicas only
kubectl patch service inference-service -p \
  '{"spec":{"selector":{"status":"healthy"}}}'
```

**Root cause investigation (30 min - 2 hours):**

**If cause is LLM API rate limiting:**
```
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/account/rate_limits

Response: { "rpm_limit": 3500, "tpm_limit": 200000 }
Current usage: 3400 RPM (hitting limit!)
```
- Solution: Upgrade OpenAI account tier or implement queue-based throttling

**If cause is model endpoint overload:**
```
kubectl logs deployment/inference-service --tail=100 | grep -i "timeout\|queue\|backpressure"

Result: "Inference queue at 8,500 jobs; dropping oldest 20% of jobs"
```
- Solution: Enable auto-scaling on GPU cluster; reduce batch size

**If cause is query complexity spike:**
```sql
SELECT
  query_text,
  COUNT(*) as frequency,
  AVG(inference_time_ms) as avg_latency,
  MAX(inference_time_ms) as max_latency
FROM query_logs
WHERE created_at > NOW() - INTERVAL 1 HOUR
GROUP BY query_text
ORDER BY max_latency DESC
LIMIT 10;

Result: Complex queries asking for multi-table analysis taking 45+ seconds
```
- Solution: Classify complex queries separately; route to fallback (async/batch)

**Implement circuit breaker:**
```python
@circuit_breaker(
    failure_threshold=5,           # Fail 5 times
    recovery_timeout=30,            # Then open circuit for 30s
    expected_exception=TimeoutError
)
def call_llm_inference(query):
    # If circuit is open, return cached answer or error
    return inference_service.complete(query, timeout=30)
```

**Prevent recurrence:**
```python
# Add LLM inference latency monitoring
def monitor_inference_latency():
    if inference_time > 10_000:  # 10 seconds
        alert.warn("inference_slow", latency_ms=inference_time)
    if inference_time > 30_000:  # 30 seconds
        alert.error("inference_timeout", latency_ms=inference_time)
```

### Communication Template

**Internal (Slack #incidents)**
```
PORTFOLIO INTELLIGENCE INCIDENT: LLM Inference Timeout
Severity: P2 (Service Degradation - 80% queries affected)
Duration: 15:00-17:00 UTC (2 hours)

Root Cause: OpenAI API rate limit exceeded. Query surge at 3 PM exceeded contracted RPM limit.

Actions:
- Scaled inference replicas from 4 → 6
- Reduced batch size to shed load
- Restarted stalled connections
- Implemented circuit breaker for future timeouts

Resolution: 95% of queries responding within 30s by 17:00 UTC

ETA: Fully recovered by 17:30 UTC
Assigned to: [INFRASTRUCTURE_ENGINEER]
```

**Customer (In-app notification)**
```
Portfolio Intelligence Performance Notice

We experienced elevated query latency between 3:00-5:00 PM UTC. Service is now recovering. Some queries may still take 30-60 seconds to complete.

We're implementing improvements to prevent this in the future.

Thank you for your patience!
```

### Postmortem Questions
1. Did we have visibility into OpenAI rate limits? (Should add monitoring)
2. Can we implement query queuing + async responses?
3. Should we use multiple LLM providers as fallback?

---

## Incident 3: Query Classification Hallucination (Wrong Answer)

### Context
A user asks: "What's my portfolio risk score?" The classifier routes the query to keyword-search instead of analytics engine. Keyword search returns "Risk" from a property name ("Risk Properties LLC"), incorrectly claiming portfolio risk is "Properties LLC". User makes business decision based on wrong answer.

### Detection
- **Alert:** Answer validation detects factually incorrect results (manual review or automated checks)
- **Symptoms:**
  - User reports "Your answer is wrong"
  - Validation checks fail (answer doesn't match ground truth database)
  - Classifier confusion matrix shows >5% misclassification rate

### Diagnosis (15 minutes)

**Step 1: Reproduce the issue**
```
User query: "What's my portfolio risk score?"
Expected classification: analytics_engine (aggregate risk across portfolio)
Actual classification: keyword_search (matched "risk" keyword)
Generated SQL: SELECT name FROM properties WHERE name LIKE '%Risk%'
Returned: "Risk Properties LLC"
```

**Step 2: Review classifier confidence**
```python
# Check classifier output
classifier.predict("What's my portfolio risk score?")
# Result: {
#   "analytics": 0.35,
#   "keyword_search": 0.48,
#   "summary": 0.12,
#   "confidence": 0.48 (LOW)
# }

# Confidence below threshold (0.7)! Should have flagged as ambiguous
```

**Step 3: Test validation layer**
```python
# Validation should have caught this
answer = "Risk Properties LLC"
ground_truth = portfolio.risk_score  # float between 0-100

# Validation check: does answer match expected type?
assert isinstance(answer, float), "Risk score should be numeric, got string"
# FAIL: Answer is string, but should be float!
```

### Remediation

**Immediate (0-10 min): Suppress bad answer**
```python
# Prevent answer delivery to user
if classification_confidence < 0.6:
    return {
        "answer": None,
        "message": "I'm not confident in this answer. Please rephrase your question.",
        "suggestion": "Try: 'What is my portfolio's risk score?'"
    }
```

**Short-term (10-30 min): Improve classifier**
```python
# Add answer validation before returning to user
def validate_answer(query, answer):
    # Type validation
    if "risk score" in query.lower():
        assert isinstance(answer, float), "Risk score must be numeric"

    # Sanity check: is answer in reasonable range?
    if "risk" in query.lower() and isinstance(answer, float):
        assert 0 <= answer <= 100, "Risk score must be 0-100"

    return True
```

**Root cause remediation (30 min - 1 hour):**
1. **Improve classifier training data:**
   ```python
   # Add "risk score" as explicit training example
   training_data.add({
       "query": "What's my portfolio risk score?",
       "classification": "analytics",
       "expected_answer_type": "float",
       "confidence_threshold": 0.7
   })
   ```

2. **Implement answer type validation:**
   ```python
   def execute_query_with_validation(query, generated_sql, expected_type):
       answer = execute_sql(generated_sql)

       # Validate answer type matches expected
       if expected_type == "numeric":
           assert isinstance(answer, (int, float))
       elif expected_type == "aggregate":
           assert isinstance(answer, dict)  # {metric: value}

       return answer
   ```

3. **Add semantic similarity check:**
   ```python
   # Reject answers that don't semantically match query
   from sentence_transformers import SentenceTransformer

   similarity = model.similarity(query_embedding, answer_embedding)
   if similarity < 0.6:  # Low similarity
       raise ValueError("Answer doesn't match query intent")
   ```

4. **Weekly classifier retraining:**
   ```bash
   # Retrain classifier on recent queries + ground-truth answers
   python retrain_classifier.py \
     --training_data=last_week_queries.csv \
     --validation_data=last_week_validated_answers.csv \
     --minimum_confidence=0.75
   ```

### Communication Template

**Internal (Slack #incidents)**
```
PORTFOLIO INTELLIGENCE INCIDENT: Wrong Answer (Classification Failure)
Severity: P2 (Data Accuracy Impact)
Duration: Question at 14:23 UTC; caught in validation at 14:31 UTC
Affected: 1 user received incorrect answer

Root Cause: Classifier misrouted "portfolio risk score" to keyword search; returned property name instead of numeric score.

Actions:
- Immediately suppressed answer from delivery
- Improved classifier confidence threshold (0.6 → 0.7)
- Added answer type validation (numeric vs. string)
- Retraining classifier on risk/analytics queries

ETA: Fixed classifier deployed by 15:30 UTC
Assigned to: [ML_ENGINEER]
```

**Customer (Direct email)**
```
Subject: Answer Correction - Portfolio Risk Score

We identified an error in a response to your query "What's my portfolio risk score?"

The system incorrectly returned "Risk Properties LLC" (a property name) instead of your actual portfolio risk score.

Correct Answer: Your portfolio risk score is [ACTUAL_SCORE] on a scale of 0-100.

We've corrected our system to prevent this error in the future. If you'd like more details or have questions, please contact us.

Best regards,
[SUPPORT_TEAM]
```

### Postmortem Questions
1. Why didn't answer validation catch type mismatch?
2. How can we add stronger guardrails for numeric vs. text answers?
3. Should we require human approval for answers below confidence threshold?

---

## General Escalation Path
1. **P3 (Slow query, <5 users):** Assign to engineer; investigate root cause
2. **P2 (Wrong answer or 80%+ query failures):** Escalate to ML lead + product within 10 min
3. **P1 (Security: injection, data loss):** Page security team + VP engineering immediately
4. **All incidents with wrong answers:** Require postmortem + classifier retraining

