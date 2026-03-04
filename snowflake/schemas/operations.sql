-- ============================================================================
-- SNOWFLAKE SCHEMA: Operations
-- Purpose: Maintenance, work order, and operational task tracking
-- Database: Snowflake (cloud data warehouse)
-- ============================================================================

-- ============================================================================
-- TABLE: work_orders
-- Description: Maintenance and repair work requests with lifecycle tracking
-- Purpose: Track all maintenance activities, costs, and completion status
-- ============================================================================
CREATE OR REPLACE TABLE work_orders (
    work_order_id STRING NOT NULL PRIMARY KEY,
    property_id STRING NOT NULL,
    unit_id STRING,
    tenant_id STRING NOT NULL,
    
    title STRING NOT NULL,
    description STRING,
    
    category STRING NOT NULL,
    -- category values: 'HVAC', 'Plumbing', 'Electrical', 'Structural', 'Cosmetic', 'Appliance', 'Other'
    
    priority STRING NOT NULL DEFAULT 'Medium',
    -- priority values: 'Critical', 'High', 'Medium', 'Low'
    
    status STRING NOT NULL DEFAULT 'Open',
    -- status values: 'Open', 'In Progress', 'Completed', 'Cancelled', 'On Hold'
    
    requested_date DATE NOT NULL,
    requested_by STRING,
    
    scheduled_date DATE,
    actual_start_date DATE,
    
    due_date DATE,
    completed_date DATE,
    
    -- Contractor/Technician assignment
    assigned_to STRING,
    assigned_date DATE,
    
    -- Cost tracking
    estimated_cost DECIMAL(10,2),
    actual_cost DECIMAL(10,2),
    
    -- Details and notes
    notes STRING,
    completion_notes STRING,
    
    created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    
    FOREIGN KEY (property_id) REFERENCES properties(property_id),
    FOREIGN KEY (unit_id) REFERENCES units(unit_id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
    CONSTRAINT category_valid CHECK (category IN ('HVAC', 'Plumbing', 'Electrical', 'Structural', 'Cosmetic', 'Appliance', 'Other')),
    CONSTRAINT priority_valid CHECK (priority IN ('Critical', 'High', 'Medium', 'Low')),
    CONSTRAINT status_valid CHECK (status IN ('Open', 'In Progress', 'Completed', 'Cancelled', 'On Hold')),
    CONSTRAINT cost_positive CHECK (estimated_cost IS NULL OR estimated_cost > 0) AND (actual_cost IS NULL OR actual_cost > 0),
    CONSTRAINT completion_date_after_requested CHECK (completed_date IS NULL OR completed_date >= requested_date)
)
CLUSTER BY (tenant_id, property_id)
COMMENT = 'Work orders for maintenance and repairs with priority, cost, and completion tracking'
;

-- ============================================================================
-- TABLE: maintenance_logs
-- Description: Detailed logs for work completed on maintenance tasks
-- Purpose: Create audit trail and record technician time/materials for billing
-- ============================================================================
CREATE OR REPLACE TABLE maintenance_logs (
    log_id STRING NOT NULL PRIMARY KEY,
    work_order_id STRING NOT NULL,
    property_id STRING NOT NULL,
    unit_id STRING,
    tenant_id STRING NOT NULL,
    
    log_date DATE NOT NULL,
    technician STRING NOT NULL,
    
    notes STRING,
    
    hours_worked DECIMAL(5,2),
    -- Technician time spent on this work
    
    materials_cost DECIMAL(10,2),
    -- Cost of materials used (parts, supplies, etc.)
    
    labor_cost DECIMAL(10,2),
    -- Labor cost calculated as hours_worked * hourly_rate
    
    created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    
    FOREIGN KEY (work_order_id) REFERENCES work_orders(work_order_id),
    FOREIGN KEY (property_id) REFERENCES properties(property_id),
    FOREIGN KEY (unit_id) REFERENCES units(unit_id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
    CONSTRAINT hours_positive CHECK (hours_worked > 0),
    CONSTRAINT materials_positive CHECK (materials_cost IS NULL OR materials_cost >= 0),
    CONSTRAINT labor_positive CHECK (labor_cost IS NULL OR labor_cost >= 0)
)
CLUSTER BY (tenant_id, property_id)
COMMENT = 'Detailed maintenance logs recording technician work, time, and materials for each work order'
;

-- ============================================================================
-- TABLE: preventive_maintenance_schedules
-- Description: Recurring maintenance tasks scheduled by property and system
-- Purpose: Track preventive maintenance requirements and compliance
-- ============================================================================
CREATE OR REPLACE TABLE preventive_maintenance_schedules (
    schedule_id STRING NOT NULL PRIMARY KEY,
    property_id STRING NOT NULL,
    tenant_id STRING NOT NULL,
    
    task_name STRING NOT NULL,
    description STRING,
    
    maintenance_category STRING,
    -- 'HVAC', 'Plumbing', 'Electrical', 'Structural', 'Appliance', 'Landscaping', 'Safety'
    
    frequency STRING NOT NULL,
    -- 'Daily', 'Weekly', 'Monthly', 'Quarterly', 'Semi-Annual', 'Annual', 'As-Needed'
    
    estimated_cost DECIMAL(10,2),
    
    is_active BOOLEAN DEFAULT TRUE,
    
    notes STRING,
    
    created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    
    FOREIGN KEY (property_id) REFERENCES properties(property_id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
)
CLUSTER BY (tenant_id, property_id)
COMMENT = 'Preventive maintenance schedules for recurring tasks by property'
;

-- ============================================================================
-- INDEXES for query optimization
-- ============================================================================
CREATE OR REPLACE INDEX idx_work_orders_property ON work_orders(property_id);
CREATE OR REPLACE INDEX idx_work_orders_status ON work_orders(status);
CREATE OR REPLACE INDEX idx_work_orders_priority_status ON work_orders(priority, status);
CREATE OR REPLACE INDEX idx_work_orders_dates ON work_orders(requested_date, completed_date);
CREATE OR REPLACE INDEX idx_work_orders_tenant ON work_orders(tenant_id);
CREATE OR REPLACE INDEX idx_maintenance_logs_wo ON maintenance_logs(work_order_id);
CREATE OR REPLACE INDEX idx_maintenance_logs_property ON maintenance_logs(property_id);
CREATE OR REPLACE INDEX idx_maintenance_logs_date ON maintenance_logs(log_date);
CREATE OR REPLACE INDEX idx_pm_schedule_property ON preventive_maintenance_schedules(property_id);

-- ============================================================================
-- COMMENTS for Schema Documentation
-- ============================================================================
COMMENT ON COLUMN work_orders.category IS 'Type of maintenance work: HVAC, Plumbing, Electrical, Structural, Cosmetic, Appliance, or Other';
COMMENT ON COLUMN work_orders.priority IS 'Urgency level: Critical (immediate), High (24-48hrs), Medium (1 week), Low (1+ months)';
COMMENT ON COLUMN work_orders.status IS 'Lifecycle status: Open, In Progress, Completed, Cancelled, or On Hold';
COMMENT ON COLUMN maintenance_logs.hours_worked IS 'Total technician hours spent on this log entry (can be partial day)';
COMMENT ON COLUMN maintenance_logs.labor_cost IS 'Labor cost = hours_worked * technician hourly rate';
COMMENT ON TABLE preventive_maintenance_schedules IS 'Schedule of recurring maintenance tasks for property systems and components';

