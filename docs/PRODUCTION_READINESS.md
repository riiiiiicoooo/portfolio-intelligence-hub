# Production Readiness Checklist

Assessment of Portfolio Intelligence Hub's readiness for production deployment. Items marked `[x]` are implemented in the codebase. Items marked `[ ]` are not yet implemented and would be required before production use.

---

## Security

### Authentication and Authorization
- [x] JWT-based authentication via Clerk with RS256 signature verification (`src/api/auth.py`)
- [x] JWKS public key fetching from Clerk API with LRU caching (`get_clerk_public_key()`)
- [x] Role extraction and validation from JWT claims with default-to-viewer fallback (`verify_clerk_token()`)
- [x] FastAPI dependency injection for auth (`get_current_user`, `require_role`, `require_property_access`)
- [x] Role-based endpoint access control with allowed-role lists (`require_role()` factory)
- [x] Property-level access control with admin bypass (`require_property_access()`)
- [x] Optional authentication dependency for mixed-access endpoints (`get_optional_user()`)
- [x] Five-role RBAC model: Admin, Property Manager, Broker, Finance, Executive (`src/access_control/rbac.py`)
- [x] Permission matrix defining resource access, CRUD actions, and property scope per role (`ROLE_PERMISSIONS`)
- [ ] Clerk JWKS key rotation handling (currently uses `lru_cache(maxsize=1)` with no TTL)
- [ ] Token refresh and session management
- [ ] API key authentication for service-to-service calls
- [ ] OAuth2 scopes for fine-grained API permissions

### SQL Injection Prevention
- [x] sqlglot AST-based SQL validation with Snowflake dialect parsing (`validate_sql()` in `text_to_sql.py`)
- [x] Regex pre-check against 12 dangerous SQL patterns (`DANGEROUS_PATTERNS` list)
- [x] Approved table whitelist enforcement via AST table reference extraction (`APPROVED_TABLES`)
- [x] Single-statement enforcement (rejects multi-statement attacks)
- [x] SELECT-only enforcement (rejects INSERT, UPDATE, DELETE, DROP at AST level)
- [x] Subquery validation for unapproved table references
- [x] Mandatory TENANT_ID filter presence check in generated SQL
- [x] Parameterized queries with `%s` placeholders in Snowflake connector (`execute_with_tenant_filter()`)
- [x] Parameterized tenant filter builder returning SQL fragment and bind parameters (`build_tenant_filter()` in `rbac.py`)
- [ ] Query cost estimation to reject queries scanning >1M rows (noted in `main.py` docstring)
- [ ] SQL query execution timeout enforcement at Snowflake level (timeout parameter exists but not enforced)

### Tenant Isolation
- [x] Three-layer isolation: Clerk JWT + Supabase RLS + Snowflake views
- [x] Supabase RLS policies on all 7 tables filtering by `tenant_id` from JWT claims (`001_schema.sql`)
- [x] Role-specific Snowflake views with column masking (`snowflake_views.py`)
- [x] Tenant-scoped Redis cache keys preventing cross-tenant cache leakage (`_hash_query()`)
- [x] Tenant context injection middleware (`inject_tenant_context` in `main.py`)
- [x] Column masking per role (NULLing sensitive columns in Snowflake views)
- [ ] Snowflake Row Access Policies (RAP) as defense-in-depth layer (noted in `main.py` docstring)
- [ ] Per-tenant KMS keys for document encryption at rest (noted in `main.py` docstring)
- [ ] Tenant-scoped Snowflake warehouse isolation for compute separation

### Secrets Management
- [x] Environment variable-based configuration via pydantic-settings (`src/core/config.py`)
- [x] `.env` file support for local development
- [ ] AWS Secrets Manager or HashiCorp Vault integration for credential rotation
- [ ] Snowflake OAuth or key-pair authentication (currently uses static username/password)
- [ ] 90-day key rotation schedule (noted in `main.py` docstring)
- [ ] Secrets scanning in CI/CD pipeline

### Transport Security
- [ ] TLS termination configuration for API
- [ ] HTTPS enforcement (redirect HTTP to HTTPS)
- [ ] Certificate management and auto-renewal
- [ ] mTLS for service-to-service communication

---

## Reliability

### High Availability
- [x] Stateless API design (no in-process state beyond Redis and Snowflake connections)
- [x] Redis connection pool with configurable max connections (`max_connections=20`)
- [x] Graceful shutdown with connection cleanup in FastAPI lifespan handler
- [ ] Multi-instance deployment behind load balancer
- [ ] Health check endpoint used by load balancer (endpoint exists at `/api/health` but no LB config)
- [ ] Database connection pool with min/max sizing and health checks
- [ ] Snowflake connection pooling (currently creates new connections per query in `text_to_sql.py`)

### Failover and Resilience
- [x] Redis unavailability fallback (queries execute without caching if Redis is down)
- [x] Cohere reranker fallback to score-based ordering if API fails (`retriever.py`)
- [x] PDF extraction fallback from Docling to Azure OCR (`document_processor.py`)
- [x] Embedding batch retry with individual fallback on batch failure (`embedder.py`)
- [x] Zero-vector fallback for failed individual embeddings
- [x] Generic exception handler returning structured error responses (`main.py`)
- [ ] Circuit breaker pattern for external API calls (Claude, OpenAI, Cohere, Snowflake)
- [ ] Retry with exponential backoff for transient failures
- [ ] Dead letter queue for failed async jobs
- [ ] Dual-model LLM failover (Claude primary, GPT-4 fallback -- noted in README but not implemented)

### Backups and Recovery
- [x] PostgreSQL data volume persistence via Docker volume (`docker-compose.yml`)
- [x] Redis append-only file (AOF) persistence enabled (`redis-server --appendonly yes`)
- [ ] Automated database backup schedule
- [ ] Point-in-time recovery configuration
- [ ] Disaster recovery runbook
- [ ] Backup restoration testing

---

## Observability

### Logging
- [x] Structured logging with timestamp, logger name, level, and message (`main.py`)
- [x] Request ID generation and propagation via middleware (`add_request_id` middleware)
- [x] Request/response logging with method, path, status code, and duration in milliseconds
- [x] Request ID in response headers (`X-Request-ID`)
- [x] Query execution logging with row counts and timing (`snowflake_connector.py`, `router.py`)
- [x] Authentication event logging (token verification success/failure with user and tenant)
- [x] Access control audit logging (`audit_log()` in `rbac.py`)
- [x] Error logging with exception info (`exc_info=True`) for unexpected errors
- [ ] Structured JSON logging format (currently uses text format)
- [ ] Log aggregation service (ELK, Datadog, CloudWatch)
- [ ] PII scrubbing in logs (tenant names, email addresses)
- [ ] Log retention policy configuration

### Metrics
- [x] Query execution time tracking in milliseconds (`QueryResult.execution_time_ms`)
- [x] Query classification confidence scores (`QueryResult.confidence`)
- [x] Search result relevance scores (`SearchResult.relevance_score`)
- [x] Health check endpoint reporting service status for Redis, Snowflake, OpenAI (`/api/health`)
- [ ] Prometheus/OpenTelemetry metrics exposition
- [ ] Request latency histograms (p50, p95, p99)
- [ ] Cache hit/miss ratio tracking
- [ ] LLM token usage and cost tracking
- [ ] Snowflake query cost tracking
- [ ] Active user and query volume dashboards

### Tracing
- [x] Request ID propagation through middleware for request correlation
- [x] Query pipeline stage logging (classify, route, execute, cache)
- [ ] Distributed tracing (OpenTelemetry, Jaeger, or Datadog APM)
- [ ] LLM call tracing with prompt and response metadata
- [ ] Cross-service trace context propagation

### Alerting
- [x] n8n workflow for hourly query error rate monitoring (`n8n/query_monitoring.json`)
- [x] Resend email integration for alert delivery (`RESEND_API_KEY`, `ALERT_EMAIL` in config)
- [x] Slack webhook integration for notifications (`SLACK_WEBHOOK_ID` in config)
- [ ] PagerDuty or Opsgenie integration for on-call escalation
- [ ] SLA-based alerting (e.g., >5% error rate, >3s p99 latency)
- [ ] Snowflake credit usage alerts
- [ ] LLM API budget threshold alerts

---

## Performance

### Caching
- [x] Redis query result caching with configurable TTL (default 3600s) (`router.py`)
- [x] Tenant-scoped cache keys to prevent cross-tenant leakage
- [x] Cache bypass when Redis is unavailable
- [x] Failed query exclusion from cache
- [x] Clerk JWKS public key caching via `lru_cache` (`auth.py`)
- [ ] Cache warming for frequently-asked portfolio KPI queries
- [ ] Cache invalidation on data refresh (currently TTL-based only)
- [ ] Maximum TTL enforcement of 15 minutes for operational data (noted in `main.py` docstring)
- [ ] Redis cluster mode for horizontal scaling

### Connection Pooling
- [x] Redis async connection pool with configurable max connections (`main.py`)
- [x] Snowflake connection context manager with proper cleanup (`snowflake_connector.py`)
- [ ] Snowflake connection pool (currently opens/closes per query in `text_to_sql.py`)
- [ ] Supabase connection pooling via PgBouncer
- [ ] Connection pool health monitoring and auto-recovery

### Query Optimization
- [x] Query result row limit cap at 100 (`parse_query_intent()` caps `limit` at 100)
- [x] Snowflake materialized views for portfolio KPI and property scorecard (`snowflake/views/`)
- [x] HNSW index on pgvector embeddings for efficient vector search (`001_schema.sql`)
- [x] GIN indexes on document full-text search (`to_tsvector`) and tags
- [x] Composite indexes on tenant_id + role, tenant_id + created_at (`001_schema.sql`)
- [x] Embedding batch processing (100 per API call) for efficient bulk operations (`embedder.py`)
- [x] Rate limiting on embedding API calls to stay within token quotas
- [ ] Snowflake CLUSTER BY optimization on frequently queried columns
- [ ] Query plan analysis and slow query detection
- [ ] Materialized view refresh scheduling (Trigger.dev job defined but not integrated end-to-end)

### API Performance
- [x] Async FastAPI endpoints for concurrent request handling
- [x] CORS configuration with specific allowed origins (`main.py`)
- [x] Per-user rate limiting via Redis (100 req/min standard, 500 premium)
- [x] Pydantic model validation with field constraints (max_length, min_length, ge, le)
- [ ] Response compression (gzip/brotli)
- [ ] API response pagination for large result sets (models defined but not fully implemented)
- [ ] Request payload size limits

---

## Compliance

### Tenant Data Isolation
- [x] Logical tenant isolation via tenant_id on all tables
- [x] Supabase RLS policies enforcing tenant boundaries on all 7 tables
- [x] Role-specific Snowflake views with column masking
- [x] Tenant-scoped cache keys in Redis
- [x] Tenant filtering in all Snowflake queries via parameterized WHERE clauses
- [ ] Tenant data deletion capability (right to erasure)
- [ ] Cross-tenant data access reporting for compliance audits

### Audit Logging
- [x] Access log table schema with user, action, resource, IP, status, and timestamp (`001_schema.sql`)
- [x] `record_access_log()` PostgreSQL function for structured audit trail insertion
- [x] Application-level audit logging function (`audit_log()` in `rbac.py`)
- [x] Query history table with user, tenant, query text, generated SQL, and execution time
- [x] User feedback collection (1-5 star rating, comments) on query results
- [ ] Audit log immutability (append-only, no DELETE/UPDATE)
- [ ] Audit log export for compliance reporting
- [ ] Audit log retention policy (e.g., 7 years for financial data)

### Data Retention
- [x] Soft delete for documents (metadata preserved for audit, `is_deleted` flag)
- [x] Notification expiration (30-day default TTL on notifications table)
- [ ] Configurable data retention policies per data type
- [ ] Automated data archival for aged records
- [ ] PII anonymization for expired records
- [ ] Data export for portability (GDPR/CCPA)

### Data Protection
- [x] PII column masking per role (tenant names hidden from brokers, salaries from finance)
- [x] File type validation on document uploads (PDF, DOCX, TXT only)
- [x] File size limits on uploads (50MB max)
- [ ] Encryption at rest for documents in S3 (SSE-KMS with per-tenant keys, noted in `main.py` docstring)
- [ ] Encryption at rest for PostgreSQL database
- [ ] Data classification and labeling
- [ ] Privacy impact assessment documentation

---

## Deployment

### Containerization
- [x] Docker Compose for local development with PostgreSQL, Redis, and FastAPI services
- [x] Health checks on PostgreSQL and Redis containers with retry configuration
- [x] Persistent volumes for PostgreSQL and Redis data
- [x] Service dependency ordering (FastAPI depends on healthy PostgreSQL and Redis)
- [x] Network isolation via Docker bridge network
- [ ] Production Dockerfile (referenced in `docker-compose.yml` but file not present)
- [ ] Multi-stage Docker build for minimal production image
- [ ] Container vulnerability scanning

### CI/CD
- [x] Test suite with pytest covering text-to-SQL, RBAC, semantic search, and API endpoints
- [x] SQL injection bypass test suite (8 attack vectors in `TestSQLInjectionBypass`)
- [x] Mock fixtures for Snowflake, Supabase, and OpenAI dependencies (`conftest.py`)
- [x] Evaluation framework: promptfoo for SQL generation, RAGAS for RAG quality (`evals/`)
- [ ] CI pipeline (GitHub Actions, GitLab CI, etc.)
- [ ] Automated test execution on pull requests
- [ ] Code coverage requirements and reporting
- [ ] Linting and type checking enforcement (mypy, ruff)
- [ ] Security scanning (Snyk, Dependabot)

### Deployment Strategy
- [x] Vercel configuration for frontend deployment with cron jobs (`vercel.json`)
- [x] Trigger.dev integration for async job execution (document embedding, MV refresh)
- [x] n8n workflows for document ingestion and query monitoring
- [ ] Blue-green or canary deployment strategy for API
- [ ] Rollback procedure and automation
- [ ] Database migration strategy and tooling (Supabase migrations exist but no orchestration)
- [ ] Feature flags for gradual rollout
- [ ] Preview environments for pull request review

### Infrastructure as Code
- [ ] Terraform, Pulumi, or CloudFormation for infrastructure provisioning
- [ ] Snowflake resource management (warehouses, databases, roles) as code
- [ ] Redis cluster configuration as code
- [ ] DNS and CDN configuration

### Monitoring in Production
- [ ] Uptime monitoring (Pingdom, Better Uptime, etc.)
- [ ] Error tracking service (Sentry, Bugsnag)
- [ ] Synthetic monitoring for critical user flows
- [ ] Capacity planning and auto-scaling rules
- [ ] Cost monitoring for Snowflake compute credits and LLM API usage
