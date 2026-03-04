# Portfolio Intelligence Hub - Data Model

**Version:** 1.0  
**Status:** Active Development  
**Last Updated:** 2026-03-04  
**Owner:** Data Engineering  
**Audience:** Engineers, Data Analysts, DBA

---

## 1. Data Model Overview

The Portfolio Intelligence Hub combines **Snowflake** (structured operational data) and **Supabase PostgreSQL** (application layer with pgvector for semantic search).

### 1.1 Snowflake Schema (Data Warehouse)

```
                    SNOWFLAKE DATA WAREHOUSE
                     (Real Estate Operations)

    ┌────────────────┐
    │  PROPERTIES    │  (87 properties: apartments, commercial, retail)
    │  (master data) │
    └────────┬───────┘
             │ 1:N
             ▼
    ┌────────────────┐
    │     UNITS      │  (3,665 rentable units across portfolio)
    │   (per prop)   │
    └────────┬───────┘
             │ 1:N
             ├─────────────────┬────────────────┬──────────────────┐
             ▼                 ▼                ▼                  ▼
    ┌────────────┐   ┌───────────────┐   ┌─────────────┐   ┌──────────────┐
    │ TENANCIES  │   │    LEASES     │   │ WORK_ORDERS │   │  FINANCIALS  │
    │(current    │   │ (detailed     │   │ (maintenance│   │(per-unit     │
    │occupants)  │   │ terms)        │   │ & repairs)  │   │financials)   │
    └────────────┘   └───────────────┘   └─────────────┘   └──────────────┘
             │             │                    │                   │
             └─────────────┴────────────────────┴───────────────────┘
                           │
                           ▼
         ┌─────────────────────────────────┐
         │  MATERIALIZED VIEWS (KPIs)      │
         │  - portfolio_kpi_summary        │
         │  - property_performance_scorecard
         └─────────────────────────────────┘

    ┌─────────────────────────────────────┐
    │  RENTAL COLLECTIONS TRACKING        │
    │  - rent_collections                 │
    │  - occupancy_snapshots (point-in-time)
    └─────────────────────────────────────┘
```

### 1.2 Supabase Schema (App Layer + Semantic Search)

```
                    SUPABASE PostgreSQL
                 (Application + Vector Store)

    ┌──────────────────┐
    │      USERS       │  (45 internal users)
    │  (Clerk sync)    │
    └────────┬─────────┘
             │
    ┌────────┴──────────────┐
    ▼                       ▼
┌──────────────┐      ┌─────────────────────┐
│  DOCUMENTS   │      │  SAVED_QUERIES      │
│ (lease books,│      │  (parameterized)    │
│ reports)     │      └─────────────────────┘
└──────┬───────┘
       │ 1:N
       ▼
    ┌────────────────────────────────────┐
    │  DOCUMENT_CHUNKS (with pgvector)   │
    │  - 3072-dim OpenAI embeddings      │
    │  - HNSW index for similarity search│
    └────────────────────────────────────┘

    ┌────────────────────────────────────┐
    │  QUERY_HISTORY                     │
    │  (user queries, results, feedback) │
    └────────────────────────────────────┘

    ┌────────────────────────────────────┐
    │  ACCESS_LOGS (RLS enforcement)     │
    │  (audit trail for compliance)      │
    └────────────────────────────────────┘
```

---

## 2. Snowflake Tables

### 2.1 PROPERTIES Table

**Purpose:** Master data for all portfolio properties  
**Refresh:** Daily from source systems  
**Size:** 87 rows  

```sql
CREATE TABLE properties (
  property_id VARCHAR(50) PRIMARY KEY,
  property_name VARCHAR(255) NOT NULL,
  property_type ENUM ('APARTMENT', 'COMMERCIAL', 'RETAIL', 'INDUSTRIAL'),
  
  -- Location
  address VARCHAR(255),
  city VARCHAR(100),
  state VARCHAR(2),
  zip VARCHAR(10),
  county VARCHAR(100),
  msa VARCHAR(100),  -- Metropolitan Statistical Area
  latitude DECIMAL(10, 8),
  longitude DECIMAL(11, 8),
  
  -- Portfolio Classification
  cluster VARCHAR(100),  -- e.g., "Texas Cluster", "Northeast Cluster"
  asset_class VARCHAR(50),  -- e.g., "A", "B", "B+", "C"
  
  -- Property Metrics
  year_built INT,
  total_units INT,
  total_rentable_sf DECIMAL(12, 2),
  parking_ratio DECIMAL(5, 2),  -- spaces per 1000 sf
  
  -- Financials
  acquisition_date DATE,
  acquisition_price DECIMAL(15, 2),
  current_estimated_value DECIMAL(15, 2),
  annual_operating_budget DECIMAL(12, 2),
  
  -- Operations
  property_manager_id VARCHAR(50),  -- FK to USERS
  leasing_agent_id VARCHAR(50),
  status VARCHAR(50),  -- 'STABILIZED', 'VALUE_ADD', 'DEVELOPMENT', 'HOLD_FOR_SALE'
  
  -- Metadata
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  source_system VARCHAR(100)  -- e.g., 'RealPage', 'AppFolio'
);

-- Indexes
CREATE INDEX idx_properties_state ON properties(state);
CREATE INDEX idx_properties_cluster ON properties(cluster);
CREATE INDEX idx_properties_status ON properties(status);
```

**Sample Data:**
```
property_id | property_name         | state | units | acq_price | current_value | status
------------|----------------------|-------|-------|-----------|----------------|----------
prop_001    | Riverside Plaza       | TX    | 450   | 45M       | 48.2M         | STABILIZED
prop_005    | Westwood Commons      | TX    | 280   | 28M       | 31.5M         | VALUE_ADD
prop_012    | Mountain View         | CA    | 320   | 52M       | 54.8M         | STABILIZED
...
```

---

### 2.2 UNITS Table

**Purpose:** Individual rental units within properties  
**Refresh:** Daily  
**Size:** 3,665 rows  

```sql
CREATE TABLE units (
  unit_id VARCHAR(50) PRIMARY KEY,
  property_id VARCHAR(50) NOT NULL,  -- FK
  unit_number VARCHAR(20),
  unit_type VARCHAR(50),  -- '1BR', '2BR', '3BR', 'COMMERCIAL_1000SF', etc.
  
  -- Physical Characteristics
  square_feet DECIMAL(8, 2),
  bedroom_count INT,
  bathroom_count DECIMAL(3, 1),
  floor_level INT,
  amenities ARRAY<VARCHAR(50)>,  -- ['BALCONY', 'FIREPLACE', 'AC', 'STAINLESS_APPLIANCES']
  
  -- Status
  occupancy_status VARCHAR(50),  -- 'OCCUPIED', 'VACANT', 'VACANT_READY', 'VACANT_NEEDS_REPAIR'
  
  -- Rental Details
  market_rent DECIMAL(10, 2),  -- Per month
  last_unit_type_change_date DATE,
  
  -- Utilities
  utilities_included BOOLEAN,
  
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

CREATE INDEX idx_units_property ON units(property_id);
CREATE INDEX idx_units_occupancy_status ON units(occupancy_status);
```

**Sample Data:**
```
unit_id    | property_id | unit_number | unit_type | market_rent | occupancy_status
-----------|-------------|-------------|-----------|-------------|-------------------
unit_001_1 | prop_001    | 101         | 1BR       | 1450        | OCCUPIED
unit_001_2 | prop_001    | 102         | 2BR       | 1850        | OCCUPIED
unit_001_3 | prop_001    | 103         | 1BR       | 1450        | VACANT_READY
...
```

---

### 2.3 TENANCIES Table

**Purpose:** Current occupancy records (who lives in which unit)  
**Refresh:** Real-time on move-in/out  
**Size:** ~3,400 rows (one per occupied unit)  

```sql
CREATE TABLE tenancies (
  tenancy_id VARCHAR(50) PRIMARY KEY,
  unit_id VARCHAR(50) NOT NULL,  -- FK
  property_id VARCHAR(50) NOT NULL,
  
  -- Tenant Information
  tenant_name VARCHAR(255),
  tenant_email VARCHAR(255),
  tenant_phone VARCHAR(20),
  
  -- Financial
  monthly_rent DECIMAL(10, 2),
  deposit_amount DECIMAL(10, 2),
  deposit_status VARCHAR(50),  -- 'HELD', 'RETURNED', 'FORFEITED'
  
  -- Dates
  move_in_date DATE,
  lease_expiration_date DATE,  -- Calculated from lease start + term
  is_renewal_option_available BOOLEAN,
  
  -- Payment Status
  rent_paid_status VARCHAR(50),  -- 'CURRENT', 'DELINQUENT', 'IN_PAYMENT_PLAN'
  days_delinquent INT,
  last_payment_date DATE,
  
  -- Lease Reference
  lease_id VARCHAR(50),  -- FK
  
  -- Metadata
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

CREATE INDEX idx_tenancies_property ON tenancies(property_id);
CREATE INDEX idx_tenancies_unit ON tenancies(unit_id);
CREATE INDEX idx_tenancies_lease_expiration ON tenancies(lease_expiration_date);
CREATE INDEX idx_tenancies_rent_paid_status ON tenancies(rent_paid_status);
```

---

### 2.4 LEASES Table

**Purpose:** Lease contract terms and details  
**Refresh:** Daily  
**Size:** ~1,200 rows (some units have multiple lease history)  

```sql
CREATE TABLE leases (
  lease_id VARCHAR(50) PRIMARY KEY,
  property_id VARCHAR(50) NOT NULL,
  unit_id VARCHAR(50) NOT NULL,
  
  -- Party Information
  tenant_name VARCHAR(255),
  tenant_credit_rating VARCHAR(10),  -- 'AAA', 'AA', 'A', 'BBB', 'BB', 'B', 'CCC'
  
  -- Lease Terms
  lease_start_date DATE,
  lease_end_date DATE,
  lease_term_months INT,  -- Calculated
  
  -- Rent Terms
  base_rent DECIMAL(10, 2),  -- Monthly
  rent_escalation_pct DECIMAL(5, 2),  -- Annual escalation %
  
  -- Additional Charges
  cat_charges DECIMAL(10, 2),  -- Reimbursable charges
  cam_charges DECIMAL(10, 2),  -- Common area maintenance
  parking_charges DECIMAL(10, 2),
  
  -- Renewal Options
  renewal_option_1_term_months INT,
  renewal_option_1_rate_type VARCHAR(50),  -- 'FIXED', 'MARKET', 'INDEXED'
  renewal_option_1_fixed_rate DECIMAL(10, 2),
  renewal_option_2_term_months INT,
  renewal_option_2_rate_type VARCHAR(50),
  renewal_option_2_fixed_rate DECIMAL(10, 2),
  
  -- Lease Flexibility
  concessions VARCHAR(500),  -- e.g., "1 month free, $5K TI allowance"
  early_termination_allowed BOOLEAN,
  early_termination_penalty_pct INT,  -- % of remaining rent
  
  -- Status
  lease_status VARCHAR(50),  -- 'ACTIVE', 'EXPIRING_SOON', 'EXPIRED', 'TERMINATED'
  
  -- Document Reference
  lease_document_id VARCHAR(50),  -- FK to DOCUMENTS table
  
  -- Metadata
  lease_signed_date DATE,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

CREATE INDEX idx_leases_property ON leases(property_id);
CREATE INDEX idx_leases_tenant ON leases(tenant_name);
CREATE INDEX idx_leases_status ON leases(lease_status);
CREATE INDEX idx_leases_lease_end_date ON leases(lease_end_date);
```

---

### 2.5 WORK_ORDERS Table

**Purpose:** Maintenance, repairs, and capital improvement requests  
**Refresh:** Real-time  
**Size:** ~12,000 rows YTD  

```sql
CREATE TABLE work_orders (
  work_order_id VARCHAR(50) PRIMARY KEY,
  property_id VARCHAR(50) NOT NULL,
  unit_id VARCHAR(50),  -- NULL if property-wide
  
  -- Classification
  category VARCHAR(50),  -- 'HVAC', 'PLUMBING', 'ELECTRICAL', 'STRUCTURAL', 'COSMETIC', 'APPLIANCE'
  description VARCHAR(500),
  
  -- Request Details
  requested_by VARCHAR(255),  -- Property manager, tenant
  request_date DATE,
  
  -- Status Tracking
  status VARCHAR(50),  -- 'OPEN', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED'
  priority VARCHAR(20),  -- 'URGENT', 'HIGH', 'MEDIUM', 'LOW'
  
  -- Contractor & Cost
  contractor_name VARCHAR(255),
  estimated_cost DECIMAL(10, 2),
  actual_cost DECIMAL(10, 2),
  
  -- Scheduling
  scheduled_date DATE,
  completion_date DATE,
  response_time_hours INT,  -- Hours between request and scheduled date
  
  -- Follow-up
  is_recurring_issue BOOLEAN,
  notes VARCHAR(1000),
  
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

CREATE INDEX idx_work_orders_property ON work_orders(property_id);
CREATE INDEX idx_work_orders_category ON work_orders(category);
CREATE INDEX idx_work_orders_status ON work_orders(status);
CREATE INDEX idx_work_orders_completion_date ON work_orders(completion_date);
```

**Sample Data:**
```
work_order_id | property_id | category | status     | priority | actual_cost | completion_date
--------------|-------------|----------|-----------|----------|-------------|------------------
wo_001        | prop_001    | HVAC     | COMPLETED | HIGH     | 2400        | 2026-02-28
wo_002        | prop_001    | PLUMBING | OPEN      | URGENT   | NULL        | NULL
...
```

---

### 2.6 FINANCIALS Table

**Purpose:** Monthly operating financials per unit/property  
**Refresh:** Monthly after financial close (5th of month)  
**Size:** ~43,980 rows (3,665 units × 12 months historical)  

```sql
CREATE TABLE financials (
  financial_id VARCHAR(50) PRIMARY KEY,
  property_id VARCHAR(50) NOT NULL,
  unit_id VARCHAR(50),  -- NULL if property-level aggregate
  
  -- Period
  year_month DATE,  -- First day of month (e.g., 2026-03-01)
  
  -- Rental Income
  gross_potential_rent DECIMAL(12, 2),  -- What we could collect if 100% occupied
  collected_rent DECIMAL(12, 2),  -- What we actually collected
  vacancy_loss DECIMAL(12, 2),  -- GPR - collected
  concessions_granted DECIMAL(10, 2),  -- Rent abated for renewals, etc.
  
  -- Operating Expenses (annual allocation / 12)
  utilities DECIMAL(10, 2),  -- Gas, electric, water (if owner-paid)
  maintenance_repairs DECIMAL(10, 2),
  salaries_management DECIMAL(10, 2),  -- Property manager, staff
  insurance DECIMAL(10, 2),
  property_taxes DECIMAL(10, 2),
  hoa_fees DECIMAL(10, 2),
  
  -- Other Income
  pet_fees DECIMAL(10, 2),
  parking_income DECIMAL(10, 2),
  late_fees_collected DECIMAL(10, 2),
  
  -- Calculated Fields
  total_operating_expense DECIMAL(12, 2),  -- Sum of above
  net_operating_income DECIMAL(12, 2),  -- Collected rent - OpEx
  
  -- Budget Comparison
  budgeted_rent DECIMAL(12, 2),
  budgeted_opex DECIMAL(12, 2),
  rent_variance DECIMAL(12, 2),  -- Actual - budgeted
  opex_variance DECIMAL(12, 2),
  
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

CREATE INDEX idx_financials_property ON financials(property_id);
CREATE INDEX idx_financials_year_month ON financials(year_month);
```

---

### 2.7 RENT_COLLECTIONS Table

**Purpose:** Track individual rent payments and delinquencies  
**Refresh:** Real-time as payments received  
**Size:** ~450,000 rows YTD (monthly × units × years)  

```sql
CREATE TABLE rent_collections (
  collection_id VARCHAR(50) PRIMARY KEY,
  property_id VARCHAR(50) NOT NULL,
  unit_id VARCHAR(50) NOT NULL,
  tenancy_id VARCHAR(50) NOT NULL,
  lease_id VARCHAR(50) NOT NULL,
  
  -- Period
  due_date DATE,
  payment_date DATE,
  
  -- Amount
  rent_due DECIMAL(10, 2),
  amount_paid DECIMAL(10, 2),
  
  -- Status
  collection_status VARCHAR(50),  -- 'COLLECTED', 'PARTIAL', 'DELINQUENT', 'EVICTION'
  
  -- Delinquency Tracking
  days_delinquent INT,
  eviction_filed_date DATE,
  eviction_status VARCHAR(50),  -- 'FILED', 'FILED_AWAITING_HEARING', 'JUDGMENT', 'STAYED'
  
  -- Payment Plan
  is_payment_plan BOOLEAN,
  payment_plan_total DECIMAL(10, 2),
  payment_plan_balance DECIMAL(10, 2),
  
  -- Metadata
  payment_method VARCHAR(50),  -- 'ACH', 'CHECK', 'CREDIT_CARD', 'ONLINE'
  notes VARCHAR(500),
  
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

CREATE INDEX idx_rent_collections_property ON rent_collections(property_id);
CREATE INDEX idx_rent_collections_due_date ON rent_collections(due_date);
CREATE INDEX idx_rent_collections_status ON rent_collections(collection_status);
```

---

### 2.8 OCCUPANCY_SNAPSHOTS Table

**Purpose:** Historical occupancy snapshots for trend analysis  
**Refresh:** Daily (snapshot at 11:59 PM)  
**Size:** ~1.3M rows (3,665 units × 365 days × 1 year)  

```sql
CREATE TABLE occupancy_snapshots (
  snapshot_id VARCHAR(50) PRIMARY KEY,
  property_id VARCHAR(50) NOT NULL,
  unit_id VARCHAR(50) NOT NULL,
  
  snapshot_date DATE,
  occupied BOOLEAN,  -- true = occupied, false = vacant
  
  -- Unit State at Snapshot Time
  occupancy_status VARCHAR(50),  -- 'OCCUPIED', 'VACANT_READY', 'VACANT_REPAIR', 'NOTICE_GIVEN'
  tenant_name VARCHAR(255),
  
  -- Metadata
  created_at TIMESTAMP
);

CREATE INDEX idx_occupancy_snapshots_property ON occupancy_snapshots(property_id);
CREATE INDEX idx_occupancy_snapshots_date ON occupancy_snapshots(snapshot_date);
CREATE INDEX idx_occupancy_snapshots_property_date ON occupancy_snapshots(property_id, snapshot_date);
```

---

### 2.9 USER_PROPERTY_ACCESS Table

**Purpose:** RBAC mapping (which users can access which properties)  
**Refresh:** Real-time on user assignment changes  
**Size:** ~180 rows (45 users × avg 4 properties each)  

```sql
CREATE TABLE user_property_access (
  access_id VARCHAR(50) PRIMARY KEY,
  user_id VARCHAR(50) NOT NULL,
  property_id VARCHAR(50) NOT NULL,
  
  role VARCHAR(50),  -- 'PROPERTY_MANAGER', 'BROKER', 'FINANCE', 'EXECUTIVE'
  
  -- Data Restrictions (role-based)
  can_view_financials BOOLEAN,
  can_view_tenants BOOLEAN,
  can_view_leases BOOLEAN,
  can_edit_rent_terms BOOLEAN,
  
  -- Dates
  access_granted_date DATE,
  access_revoked_date DATE,  -- NULL if currently active
  
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  updated_by VARCHAR(50)  -- Admin who made change
);

CREATE INDEX idx_user_property_access_user ON user_property_access(user_id);
CREATE INDEX idx_user_property_access_property ON user_property_access(property_id);
```

---

## 3. Snowflake Materialized Views

### 3.1 portfolio_kpi_summary

**Purpose:** Pre-aggregated KPIs for portfolio performance dashboard  
**Refresh:** Nightly at 2 AM (after financial close)  
**Query Cost:** 80% reduction vs. on-demand aggregation  

```sql
CREATE MATERIALIZED VIEW portfolio_kpi_summary AS
SELECT
  TRUNC(CURRENT_DATE, 'MONTH') as reporting_month,
  
  -- Portfolio-Level Metrics
  COUNT(DISTINCT p.property_id) as total_properties,
  SUM(u.market_rent) as gross_potential_rent,
  COUNT(CASE WHEN os.occupied = TRUE THEN 1 END) as occupied_units,
  COUNT(DISTINCT u.unit_id) as total_units,
  ROUND(100.0 * COUNT(CASE WHEN os.occupied = TRUE THEN 1 END) /
        COUNT(DISTINCT u.unit_id), 1) as portfolio_occupancy_pct,
  
  -- Collections Metrics
  SUM(f.collected_rent) as total_collected_rent,
  SUM(f.net_operating_income) as total_noi,
  ROUND(SUM(f.collected_rent) / SUM(f.gross_potential_rent) * 100, 1) as collection_rate_pct,
  
  -- Budget Variance
  SUM(f.collected_rent - f.budgeted_rent) as rent_variance,
  SUM(f.total_operating_expense - f.budgeted_opex) as opex_variance,
  
  -- Delinquency
  COUNT(CASE WHEN rc.collection_status IN ('DELINQUENT', 'EVICTION') THEN 1 END) 
    as delinquent_units,
  SUM(CASE WHEN rc.collection_status IN ('DELINQUENT', 'EVICTION') 
    THEN rc.rent_due - rc.amount_paid ELSE 0 END) as total_delinquent_amount,
  
  -- Average Rent
  ROUND(AVG(u.market_rent), 2) as avg_unit_rent

FROM properties p
LEFT JOIN units u ON p.property_id = u.property_id
LEFT JOIN occupancy_snapshots os ON u.unit_id = os.unit_id 
  AND os.snapshot_date = TRUNC(CURRENT_DATE) - 1
LEFT JOIN financials f ON p.property_id = f.property_id 
  AND f.year_month = TRUNC(CURRENT_DATE, 'MONTH')
LEFT JOIN rent_collections rc ON u.unit_id = rc.unit_id 
  AND rc.due_date >= TRUNC(CURRENT_DATE, 'MONTH')

GROUP BY reporting_month;

-- Refresh schedule
ALTER MATERIALIZED VIEW portfolio_kpi_summary SET CLUSTER REFRESH_MATERIALIZED_VIEW EVERY HOUR;
```

### 3.2 property_performance_scorecard

**Purpose:** Per-property performance metrics for comparison and benchmarking  
**Refresh:** Nightly  

```sql
CREATE MATERIALIZED VIEW property_performance_scorecard AS
SELECT
  p.property_id,
  p.property_name,
  p.cluster,
  p.property_type,
  
  -- Occupancy
  ROUND(100.0 * COUNT(CASE WHEN os.occupied = TRUE THEN 1 END) /
        COUNT(DISTINCT u.unit_id), 1) as occupancy_pct,
  
  -- Financial Performance
  ROUND(SUM(f.net_operating_income) / 
        SUM(f.gross_potential_rent) * 100, 1) as noi_margin_pct,
  ROUND(SUM(f.collected_rent) / SUM(f.gross_potential_rent) * 100, 1) 
    as collection_rate_pct,
  
  -- Comparisons
  ROUND(SUM(f.rent_variance), 2) as ytd_rent_variance,
  ROUND(SUM(f.opex_variance), 2) as ytd_opex_variance,
  
  -- Asset Quality
  COUNT(DISTINCT CASE WHEN l.tenant_credit_rating IN ('AAA', 'AA', 'A') 
    THEN l.lease_id END) as high_credit_tenant_count,
  COUNT(DISTINCT l.lease_id) as total_active_leases,
  
  -- Risk Indicators
  COUNT(CASE WHEN rc.collection_status = 'DELINQUENT' THEN 1 END) 
    as delinquent_count,
  COUNT(CASE WHEN DATEDIFF(DAY, CURRENT_DATE, t.lease_expiration_date) 
    BETWEEN 0 AND 90 THEN 1 END) as leases_expiring_90_days,

  -- Maintenance
  COUNT(CASE WHEN wo.status NOT IN ('COMPLETED', 'CANCELLED') THEN 1 END)
    as open_work_orders,
  SUM(CASE WHEN wo.status = 'COMPLETED' AND 
        DATE_TRUNC('MONTH', wo.completion_date) = TRUNC(CURRENT_DATE, 'MONTH')
      THEN wo.actual_cost ELSE 0 END) as mtd_maintenance_cost

FROM properties p
LEFT JOIN units u ON p.property_id = u.property_id
LEFT JOIN occupancy_snapshots os ON u.unit_id = os.unit_id 
  AND os.snapshot_date = TRUNC(CURRENT_DATE) - 1
LEFT JOIN financials f ON p.property_id = f.property_id 
  AND f.year_month >= DATE_TRUNC('YEAR', CURRENT_DATE)
LEFT JOIN leases l ON u.unit_id = l.unit_id AND l.lease_status = 'ACTIVE'
LEFT JOIN tenancies t ON u.unit_id = t.unit_id
LEFT JOIN rent_collections rc ON u.unit_id = rc.unit_id 
  AND rc.due_date >= DATE_TRUNC('MONTH', CURRENT_DATE)
LEFT JOIN work_orders wo ON p.property_id = wo.property_id

GROUP BY p.property_id, p.property_name, p.cluster, p.property_type;
```

---

## 4. Supabase Schema (Application Layer + Vector Search)

### 4.1 USERS Table

**Purpose:** User identity and role information (synced from Clerk)  
**Sync:** Real-time webhook from Clerk  
**Size:** 45 rows  

```sql
CREATE TABLE public.users (
  user_id UUID PRIMARY KEY,
  clerk_user_id VARCHAR(255) UNIQUE NOT NULL,
  email VARCHAR(255) NOT NULL,
  first_name VARCHAR(100),
  last_name VARCHAR(100),
  
  -- Role
  role VARCHAR(50) NOT NULL,  -- 'PROPERTY_MANAGER', 'BROKER', 'FINANCE', 'EXECUTIVE', 'ADMIN'
  
  -- Metadata
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  is_active BOOLEAN DEFAULT TRUE
);

-- Sync from Clerk via webhook
-- Clerk sends new user events → Trigger.dev job inserts to users table
```

### 4.2 DOCUMENTS Table

**Purpose:** Document library metadata  
**Size:** ~500 documents (leases, reports, policies)  

```sql
CREATE TABLE public.documents (
  document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  file_name VARCHAR(255) NOT NULL,
  file_type VARCHAR(20),  -- 'PDF', 'DOCX', 'PPTX', 'TXT'
  file_size_bytes INT,
  
  -- Classification
  document_type VARCHAR(50),  -- 'LEASE', 'OPERATING_REPORT', 'POLICY', 'FINANCIAL'
  property_id VARCHAR(50),  -- References Snowflake property
  
  -- Access Control
  accessible_to_roles TEXT[],  -- ['PROPERTY_MANAGER', 'FINANCE', 'EXECUTIVE']
  
  -- Versioning
  version INT DEFAULT 1,
  replaced_by_document_id UUID,  -- If superseded by newer version
  
  -- Metadata
  uploaded_by_user_id UUID NOT NULL,
  uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  FOREIGN KEY (uploaded_by_user_id) REFERENCES users(user_id),
  CHECK (file_type IN ('PDF', 'DOCX', 'PPTX', 'TXT', 'IMAGE'))
);

CREATE INDEX idx_documents_property ON documents(property_id);
CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_uploaded_at ON documents(uploaded_at DESC);
```

### 4.3 DOCUMENT_CHUNKS Table (with pgvector)

**Purpose:** Semantic chunks of documents for vector search  
**Size:** ~150,000 chunks (500 docs × 300 chunks/doc avg)  
**Vector Size:** 3,072 dimensions (OpenAI embedding-3-large)  

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE public.document_chunks (
  chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL,
  
  -- Chunk Metadata
  chunk_number INT NOT NULL,  -- Sequential: 0, 1, 2, ...
  page_number INT,
  section_title VARCHAR(255),  -- For structured docs
  
  -- Content
  content TEXT NOT NULL,  -- Actual chunk text (~400 words)
  content_token_count INT,  -- For cost tracking
  
  -- Vector Embedding (3,072-dim)
  embedding vector(3072) NOT NULL,
  
  -- RBAC
  property_id VARCHAR(50),  -- For filtering
  accessible_to_roles TEXT[],
  
  -- Metadata for better retrieval
  chunk_metadata JSONB,  -- {
                        -- "tenant": "Acme Corp",
                        -- "lease_term": "60 months",
                        -- "section": "Renewal Options"
                        -- }
  
  -- Audit
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  embedding_model VARCHAR(100),  -- 'openai-embedding-3-large'
  
  FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE
);

-- HNSW index for vector similarity (from pgvector)
CREATE INDEX idx_document_chunks_embedding ON document_chunks 
  USING HNSW (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- Traditional indexes
CREATE INDEX idx_document_chunks_property ON document_chunks(property_id);
CREATE INDEX idx_document_chunks_document ON document_chunks(document_id);

-- Row-Level Security (RLS)
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;

CREATE POLICY document_chunks_select_policy ON document_chunks FOR SELECT
  USING (
    -- User can see chunk if:
    -- 1. Chunk is marked for their role
    -- 2. User has access to the property
    accessible_to_roles @> ARRAY[
      (SELECT role FROM users WHERE user_id = auth.uid())
    ]::text[]
    OR
    property_id IN (
      SELECT property_id FROM public.user_property_access 
      WHERE user_id = auth.uid()
    )
  );
```

### 4.4 QUERY_HISTORY Table

**Purpose:** Track user queries for analytics and model improvement  
**Size:** ~50,000 rows (100 queries/day × 500 days)  

```sql
CREATE TABLE public.query_history (
  query_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  user_id UUID NOT NULL,
  query_text VARCHAR(2000) NOT NULL,
  
  -- Query Type
  query_type VARCHAR(50),  -- 'TEXT_TO_SQL', 'SEMANTIC_SEARCH', 'HYBRID'
  
  -- Results
  result_status VARCHAR(50),  -- 'SUCCESS', 'PARTIAL', 'ERROR', 'LOW_CONFIDENCE'
  result_summary VARCHAR(1000),  -- First 1000 chars of answer
  
  -- Performance
  execution_time_ms INT,
  snowflake_cost_credits DECIMAL(10, 6),
  
  -- Generated SQL (for Text-to-SQL)
  generated_sql TEXT,
  sql_confidence_score DECIMAL(3, 2),  -- 0.0-1.0
  
  -- Retrieved Documents (for semantic search)
  retrieved_documents JSONB,  -- [{document_id, chunk_id, score}]
  
  -- User Feedback
  user_rating INT,  -- 1-5 stars
  user_feedback VARCHAR(500),
  
  -- Session
  session_id VARCHAR(100),
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE INDEX idx_query_history_user ON query_history(user_id);
CREATE INDEX idx_query_history_timestamp ON query_history(timestamp DESC);
CREATE INDEX idx_query_history_type ON query_history(query_type);
```

### 4.5 SAVED_QUERIES Table

**Purpose:** User-saved parameterized queries for reuse  
**Size:** ~50 queries (avg 1 saved per user)  

```sql
CREATE TABLE public.saved_queries (
  saved_query_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  created_by_user_id UUID NOT NULL,
  query_name VARCHAR(255) NOT NULL,
  query_description VARCHAR(500),
  
  -- Query Definition
  query_text VARCHAR(2000),  -- May contain parameter placeholders: {property_id}, {date_range}
  query_type VARCHAR(50),  -- 'TEXT_TO_SQL', 'SEMANTIC_SEARCH'
  
  -- Parameters
  parameters JSONB,  -- {
                     -- "property_id": {type: "string", required: true},
                     -- "date_range": {type: "date_range", required: false, default: "ytd"}
                     -- }
  
  -- Sharing
  is_shared BOOLEAN DEFAULT FALSE,
  shared_with_users UUID[],
  shared_with_roles TEXT[],
  
  -- Usage
  last_executed_at TIMESTAMP,
  execution_count INT DEFAULT 0,
  
  -- Metadata
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  FOREIGN KEY (created_by_user_id) REFERENCES users(user_id)
);

CREATE INDEX idx_saved_queries_user ON saved_queries(created_by_user_id);
CREATE INDEX idx_saved_queries_shared ON saved_queries(is_shared);
```

### 4.6 ACCESS_LOGS Table (Audit Trail)

**Purpose:** Compliance and security audit logging  
**Retention:** 2 years  
**Size:** ~100,000 rows (200 access events/day)  

```sql
CREATE TABLE public.access_logs (
  log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- User & Session
  user_id UUID NOT NULL,
  session_id VARCHAR(100),
  
  -- Access Details
  action VARCHAR(50),  -- 'QUERY_EXECUTED', 'DOCUMENT_VIEWED', 'DATA_EXPORTED'
  resource_type VARCHAR(50),  -- 'PROPERTY', 'UNIT', 'LEASE', 'FINANCIAL'
  accessed_property_ids TEXT[],  -- Array of property IDs accessed
  accessed_tables TEXT[],  -- Snowflake tables queried
  
  -- Request Details
  query_or_document_id VARCHAR(255),
  result_row_count INT,
  
  -- Security & Performance
  request_ip VARCHAR(45),
  user_agent VARCHAR(500),
  execution_time_ms INT,
  
  -- PII Access
  sensitive_fields_accessed TEXT[],  -- ['SSN', 'PAYMENT_METHOD']
  
  -- Status
  success BOOLEAN,
  error_message VARCHAR(500),
  
  -- Timestamp
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_access_logs_user ON access_logs(user_id);
CREATE INDEX idx_access_logs_timestamp ON access_logs(created_at DESC);
CREATE INDEX idx_access_logs_action ON access_logs(action);

-- Retention policy (if using TimescaleDB)
-- SELECT add_retention_policy('access_logs', INTERVAL '2 years');
```

---

## 5. RLS Policies for Supabase Tables

```sql
-- DOCUMENTS Table RLS
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY documents_select_policy ON documents FOR SELECT
  USING (
    accessible_to_roles @> ARRAY[(SELECT role FROM users WHERE user_id = auth.uid())]::text[]
  );

-- Only admins can insert/update documents
CREATE POLICY documents_insert_policy ON documents FOR INSERT
  WITH CHECK (
    (SELECT role FROM users WHERE user_id = auth.uid()) = 'ADMIN'
  );

-- DOCUMENT_CHUNKS Table RLS (already defined above)

-- QUERY_HISTORY Table RLS
ALTER TABLE query_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY query_history_select_policy ON query_history FOR SELECT
  USING (user_id = auth.uid());  -- Users only see their own queries

CREATE POLICY query_history_insert_policy ON query_history FOR INSERT
  WITH CHECK (user_id = auth.uid());

-- ACCESS_LOGS Table RLS
ALTER TABLE access_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY access_logs_select_policy ON access_logs FOR SELECT
  USING (
    -- Only admins can view full access logs
    (SELECT role FROM users WHERE user_id = auth.uid()) = 'ADMIN'
    OR
    -- Users can see their own access logs
    user_id = auth.uid()
  );

CREATE POLICY access_logs_insert_policy ON access_logs FOR INSERT
  WITH CHECK (user_id = auth.uid());
```

---

## 6. Indexing Strategy

### 6.1 Snowflake Indexes

| Table | Index | Purpose | Estimated Improvement |
|-------|-------|---------|----------------------|
| properties | cluster, status | Filter by cluster for regional queries | 10x faster cluster analysis |
| units | property_id, occupancy_status | Common filtering | 20x faster occupancy queries |
| tenancies | lease_expiration_date, rent_paid_status | Renewal pipeline, collections | 15x faster renewal forecasting |
| leases | lease_end_date, tenant_credit_rating | Expiration tracking, credit analysis | 8x faster lease pipeline |
| occupancy_snapshots | property_id + snapshot_date | Historical occupancy trends | 30x faster historical analysis |
| financials | property_id + year_month, variance reporting | Budget vs. actual analysis | 25x faster variance queries |
| work_orders | property_id + category + status | Maintenance tracking | 5x faster maintenance reports |
| rent_collections | property_id + due_date + status | Collections dashboards | 12x faster delinquency reporting |

### 6.2 Supabase Indexes

| Table | Index Type | Purpose |
|-------|-----------|---------|
| document_chunks | HNSW (vector) | Semantic search (pgvector) |
| document_chunks | B-tree (property_id) | RLS filtering |
| query_history | B-tree (user_id, timestamp) | User query history retrieval |
| access_logs | B-tree (created_at DESC) | Compliance audit retrieval |

### 6.3 Clustering Strategy

**Snowflake:** Cluster properties table by state (12 states) for geographic isolation
**Supabase:** Cluster document_chunks by property_id for RLS performance

---

## 7. Sample Data Overview

The demo dataset includes:

**Properties:** 87 real estate properties across 12 states
- 45 apartment/multifamily properties
- 20 commercial office properties
- 15 retail properties
- 7 industrial properties

**Units:** 3,665 total rentable units
- Unit types: 1BR, 2BR, 3BR, commercial spaces, industrial bays
- Market rents: $1,200-$4,500/month (apartments), $12-25/sf (commercial)

**Tenancies:** ~3,400 active occupancies (93% occupancy on average)
- Mix of individual, corporate, government, non-profit tenants
- Credit ratings: 70% A-rated+, 20% BBB, 10% below-investment-grade

**Leases:** ~1,200 active leases with varying terms
- Lease terms: 6 months to 5+ years
- Rent escalations: 2-4% annual average
- Renewal options: 70% of leases include 1-2 renewal options

**Financials:** 12 months history per property
- YTD Portfolio NOI: $18.2M
- Average NOI margin: 42-48% (varies by property type)
- Budget variance: typical ±3% YTD

**Work Orders:** 12,000+ YTD work orders
- HVAC (30%), Plumbing (20%), Electrical (15%), Other (35%)
- Average cost: $650 per order
- Average response time: 4.2 hours

---

## 8. Query Patterns by Persona

### Property Manager Queries
```sql
-- Occupancy status by property
SELECT property_name, COUNT(CASE WHEN occupied THEN 1 END)::float / 
  COUNT(*) * 100 as occupancy_pct
FROM occupancy_snapshots os
JOIN properties p ON os.property_id = p.property_id
WHERE p.property_id IN (user_accessible_properties)
AND os.snapshot_date = CURRENT_DATE
GROUP BY property_name;

-- Lease renewals due in 90 days
SELECT t.tenant_name, u.unit_number, t.lease_expiration_date, 
  l.base_rent, l.renewal_option_1_rate_type
FROM tenancies t
JOIN units u ON t.unit_id = u.unit_id
JOIN leases l ON t.lease_id = l.lease_id
WHERE DATEDIFF(DAY, CURRENT_DATE, t.lease_expiration_date) BETWEEN 0 AND 90
AND u.property_id IN (user_accessible_properties)
ORDER BY t.lease_expiration_date;
```

### Finance Queries
```sql
-- Monthly NOI variance analysis
SELECT p.property_name,
  f.collected_rent as actual_rent,
  f.budgeted_rent,
  f.collected_rent - f.budgeted_rent as rent_variance,
  f.total_operating_expense as actual_opex,
  f.budgeted_opex,
  f.net_operating_income
FROM financials f
JOIN properties p ON f.property_id = p.property_id
WHERE f.year_month >= DATE_TRUNC('YEAR', CURRENT_DATE)
ORDER BY f.collected_rent - f.budgeted_rent DESC;

-- Collections status
SELECT p.property_name, 
  COUNT(CASE WHEN rc.collection_status = 'COLLECTED' THEN 1 END) as collected,
  COUNT(CASE WHEN rc.collection_status = 'DELINQUENT' THEN 1 END) as delinquent,
  SUM(CASE WHEN rc.collection_status = 'DELINQUENT' THEN rc.rent_due ELSE 0 END)
FROM rent_collections rc
JOIN properties p ON rc.property_id = p.property_id
WHERE rc.due_date >= DATE_TRUNC('MONTH', CURRENT_DATE)
GROUP BY p.property_name;
```

### Executive Queries
```sql
-- Portfolio performance scorecard (uses materialized view)
SELECT * FROM property_performance_scorecard
WHERE cluster IN ('Texas Cluster', 'Northeast Cluster')
ORDER BY occupancy_pct DESC, noi_margin_pct DESC;

-- Sub-market performance comparison
SELECT p.cluster, 
  AVG(ps.occupancy_pct) as avg_occupancy,
  AVG(ps.noi_margin_pct) as avg_noi_margin,
  COUNT(*) as property_count,
  AVG(ps.high_credit_tenant_count)::float / 
    AVG(ps.total_active_leases) as high_credit_ratio
FROM property_performance_scorecard ps
JOIN properties p ON ps.property_id = p.property_id
GROUP BY p.cluster
ORDER BY avg_noi_margin_pct DESC;
```

---

**Document Status:** Ready for database deployment  
**Next Steps:** Schema validation in development environment, data migration planning  
**Review Date:** 2026-03-11
