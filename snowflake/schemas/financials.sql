-- ============================================================================
-- SNOWFLAKE SCHEMA: Financials
-- Purpose: Financial tracking tables for properties and rent collection
-- Database: Snowflake (cloud data warehouse)
-- ============================================================================

-- ============================================================================
-- TABLE: financials
-- Description: Monthly/periodic financial statements for properties
-- Purpose: Track income, expenses, and profitability metrics at property level
-- ============================================================================
CREATE OR REPLACE TABLE financials (
    financial_id STRING NOT NULL PRIMARY KEY,
    property_id STRING NOT NULL,
    tenant_id STRING NOT NULL,
    
    -- Reporting period
    period_start_date DATE NOT NULL,
    period_end_date DATE NOT NULL,
    period_month DATE NOT NULL,
    -- period_month is set to the first day of the month for easy aggregation
    
    -- INCOME
    gross_rent DECIMAL(12,2) NOT NULL DEFAULT 0,
    -- Gross scheduled rent for the period
    
    other_income DECIMAL(12,2) DEFAULT 0,
    -- Parking fees, pet rent, utilities pass-through, etc.
    
    vacancy_loss DECIMAL(12,2) DEFAULT 0,
    -- Lost income due to vacant units
    
    effective_gross_income DECIMAL(12,2) NOT NULL,
    -- gross_rent + other_income - vacancy_loss
    
    -- OPERATING EXPENSES
    maintenance_repairs DECIMAL(12,2) DEFAULT 0,
    -- Regular maintenance and repairs
    
    utilities DECIMAL(12,2) DEFAULT 0,
    -- Electric, water, gas, sewer, trash
    
    insurance DECIMAL(12,2) DEFAULT 0,
    -- Property insurance and liability
    
    property_taxes DECIMAL(12,2) DEFAULT 0,
    -- Real estate property taxes
    
    management_fees DECIMAL(12,2) DEFAULT 0,
    -- Property management fees (% of rent or fixed)
    
    payroll DECIMAL(12,2) DEFAULT 0,
    -- Salaries for on-site staff
    
    marketing DECIMAL(12,2) DEFAULT 0,
    -- Leasing and marketing expenses
    
    other_operating_expense DECIMAL(12,2) DEFAULT 0,
    -- Miscellaneous operating expenses
    
    total_operating_expenses DECIMAL(12,2) NOT NULL,
    -- Sum of all operating expenses
    
    -- NOI (Net Operating Income)
    noi DECIMAL(12,2) NOT NULL,
    -- effective_gross_income - total_operating_expenses
    
    -- BOTTOM LINE
    debt_service DECIMAL(12,2) DEFAULT 0,
    -- Loan principal + interest payments
    
    net_income DECIMAL(12,2) NOT NULL,
    -- noi - debt_service (property-level net income)
    
    -- BUDGET VS ACTUAL
    budget_gross_rent DECIMAL(12,2),
    budget_noi DECIMAL(12,2),
    
    noi_variance DECIMAL(12,2),
    -- Actual NOI minus budgeted NOI (can be negative)
    
    noi_variance_percent DECIMAL(6,2),
    -- Variance as percentage of budget
    
    created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    
    FOREIGN KEY (property_id) REFERENCES properties(property_id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
    CONSTRAINT period_valid CHECK (period_end_date > period_start_date),
    CONSTRAINT income_positive CHECK (gross_rent >= 0 AND other_income >= 0 AND effective_gross_income >= 0),
    CONSTRAINT expense_positive CHECK (total_operating_expenses >= 0 AND debt_service >= 0)
)
CLUSTER BY (tenant_id, property_id, period_month)
COMMENT = 'Monthly financial statements including income, expenses, NOI, and budget variance'
;

-- ============================================================================
-- TABLE: rent_collections
-- Description: Individual rent payment tracking and delinquency monitoring
-- Purpose: Monitor payment status, track overdue amounts, identify problem units
-- ============================================================================
CREATE OR REPLACE TABLE rent_collections (
    collection_id STRING NOT NULL PRIMARY KEY,
    lease_id STRING NOT NULL,
    unit_id STRING NOT NULL,
    property_id STRING NOT NULL,
    tenant_id STRING NOT NULL,
    
    -- Billing period
    period_month DATE NOT NULL,
    -- First day of the month for which rent is due
    
    rent_due DECIMAL(10,2) NOT NULL,
    -- Scheduled rent amount for this unit
    
    rent_received DECIMAL(10,2) DEFAULT 0,
    -- Actual amount received from tenant
    
    received_date DATE,
    -- Date payment was received (NULL if not yet received)
    
    days_overdue NUMBER(4,0) DEFAULT 0,
    -- Number of days past due (calculated as current_date - due_date)
    
    status STRING NOT NULL DEFAULT 'pending',
    -- status values: 'pending', 'received', 'partially_received', 'overdue', 'delinquent', 'writeoff'
    
    notes STRING,
    -- Notes about the payment (e.g., payment plan, dispute, etc.)
    
    created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    
    FOREIGN KEY (lease_id) REFERENCES leases(lease_id),
    FOREIGN KEY (unit_id) REFERENCES units(unit_id),
    FOREIGN KEY (property_id) REFERENCES properties(property_id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
    CONSTRAINT rent_positive CHECK (rent_due > 0 AND rent_received >= 0),
    CONSTRAINT status_valid CHECK (status IN ('pending', 'received', 'partially_received', 'overdue', 'delinquent', 'writeoff'))
)
CLUSTER BY (tenant_id, property_id, period_month)
COMMENT = 'Individual rent payment tracking with delinquency monitoring and collection status'
;

-- ============================================================================
-- TABLE: occupancy_snapshots
-- Description: Point-in-time occupancy metrics for trending and reporting
-- Purpose: Track occupancy rate changes over time for reporting and forecasting
-- ============================================================================
CREATE OR REPLACE TABLE occupancy_snapshots (
    snapshot_id STRING NOT NULL PRIMARY KEY,
    property_id STRING NOT NULL,
    tenant_id STRING NOT NULL,
    
    snapshot_date DATE NOT NULL,
    -- The date of this occupancy snapshot
    
    units_total NUMBER(10,0) NOT NULL,
    -- Total units at the property as of this date
    
    units_occupied NUMBER(10,0) NOT NULL,
    -- Number of occupied units (status = 'occupied')
    
    units_vacant NUMBER(10,0) NOT NULL,
    -- Number of vacant units (units_total - units_occupied)
    
    occupancy_percent DECIMAL(5,2) NOT NULL,
    -- (units_occupied / units_total) * 100
    
    avg_rent_occupied DECIMAL(10,2),
    -- Average rent for occupied units
    
    days_to_lease_vacant NUMBER(5,0),
    -- Average days vacant units sit before being leased
    
    created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    
    FOREIGN KEY (property_id) REFERENCES properties(property_id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
    CONSTRAINT occupancy_valid CHECK (occupancy_percent >= 0 AND occupancy_percent <= 100),
    CONSTRAINT units_valid CHECK (units_occupied >= 0 AND units_vacant >= 0 AND units_total > 0)
)
CLUSTER BY (tenant_id, property_id, snapshot_date)
COMMENT = 'Occupancy snapshots for trend analysis and historical reporting'
;

-- ============================================================================
-- INDEXES for query optimization
-- ============================================================================
CREATE OR REPLACE INDEX idx_financials_property_period ON financials(property_id, period_month);
CREATE OR REPLACE INDEX idx_financials_tenant_period ON financials(tenant_id, period_month);
CREATE OR REPLACE INDEX idx_rent_collections_property ON rent_collections(property_id, period_month);
CREATE OR REPLACE INDEX idx_rent_collections_status ON rent_collections(status);
CREATE OR REPLACE INDEX idx_rent_collections_overdue ON rent_collections(days_overdue) WHERE days_overdue > 0;
CREATE OR REPLACE INDEX idx_occupancy_property_date ON occupancy_snapshots(property_id, snapshot_date);
CREATE OR REPLACE INDEX idx_occupancy_tenant_date ON occupancy_snapshots(tenant_id, snapshot_date);

-- ============================================================================
-- COMMENTS for Schema Documentation
-- ============================================================================
COMMENT ON COLUMN financials.period_month IS 'First day of the month for easy time-series aggregation and trending';
COMMENT ON COLUMN financials.noi IS 'Net Operating Income = Effective Gross Income - Operating Expenses (before debt service)';
COMMENT ON COLUMN financials.noi_variance_percent IS 'Percentage deviation from budget: ((Actual - Budget) / Budget) * 100';
COMMENT ON COLUMN rent_collections.days_overdue IS 'Number of days past the payment due date; updated daily';
COMMENT ON COLUMN rent_collections.status IS 'Current payment status: pending, received, overdue, delinquent, or written off';
COMMENT ON COLUMN occupancy_snapshots.occupancy_percent IS 'Current occupancy rate: (occupied_units / total_units) * 100';

