-- ============================================================================
-- SNOWFLAKE SCHEMA: Properties
-- Purpose: Core property management tables for the Portfolio Intelligence Hub
-- Database: Snowflake (cloud data warehouse)
-- ============================================================================

-- ============================================================================
-- TABLE: tenants
-- Description: Platform tenants - each operator/real estate firm using the system
-- ============================================================================
CREATE OR REPLACE TABLE tenants (
    tenant_id STRING NOT NULL PRIMARY KEY,
    company_name STRING NOT NULL,
    email_domain STRING NOT NULL UNIQUE,
    industry STRING,
    region STRING,
    phone_number STRING,
    mailing_address STRING,
    city STRING,
    state STRING,
    zip_code STRING,
    country STRING,
    subscription_tier STRING NOT NULL DEFAULT 'standard',
    properties_limit NUMBER(10,0),
    users_limit NUMBER(10,0),
    api_key_hash STRING,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY (tenant_id)
COMMENT = 'Platform tenants representing real estate operators using Portfolio Intelligence Hub'
;

-- ============================================================================
-- TABLE: properties
-- Description: Core property/building records with tenant relationships
-- ============================================================================
CREATE OR REPLACE TABLE properties (
    property_id STRING NOT NULL PRIMARY KEY,
    tenant_id STRING NOT NULL,
    property_name STRING NOT NULL,
    property_address STRING NOT NULL,
    city STRING NOT NULL,
    state STRING NOT NULL,
    zip_code STRING NOT NULL,
    country STRING DEFAULT 'USA',
    property_type STRING NOT NULL,
    -- property_type values: 'Apartment', 'Commercial', 'Retail', 'Industrial', 'Mixed-Use'
    
    units_total NUMBER(10,0) NOT NULL,
    year_built NUMBER(4,0),
    square_footage NUMBER(15,2),
    
    -- Financial metrics
    acquisition_date DATE,
    cap_rate DECIMAL(5,2),
    current_valuation DECIMAL(15,2),
    
    -- Status tracking
    status STRING NOT NULL DEFAULT 'active',
    -- status values: 'active', 'inactive', 'under_renovation', 'for_sale'
    
    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),
    
    property_manager_name STRING,
    property_manager_phone STRING,
    property_manager_email STRING,
    
    created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
    CONSTRAINT property_type_valid CHECK (property_type IN ('Apartment', 'Commercial', 'Retail', 'Industrial', 'Mixed-Use')),
    CONSTRAINT status_valid CHECK (status IN ('active', 'inactive', 'under_renovation', 'for_sale'))
)
CLUSTER BY (tenant_id, property_id)
COMMENT = 'Core property records with address, type, size, and valuation metrics'
;

-- ============================================================================
-- TABLE: units
-- Description: Individual units/spaces within properties
-- ============================================================================
CREATE OR REPLACE TABLE units (
    unit_id STRING NOT NULL PRIMARY KEY,
    property_id STRING NOT NULL,
    tenant_id STRING NOT NULL,
    unit_number STRING NOT NULL,
    unit_type STRING NOT NULL,
    -- unit_type values: 'Studio', '1BR', '2BR', '3BR', '4BR+', 'Office', 'Retail', 'Industrial'
    
    square_footage NUMBER(10,2),
    rent_current DECIMAL(10,2),
    bed_count NUMBER(2,0),
    bath_count DECIMAL(3,1),
    
    floor NUMBER(3,0),
    amenities ARRAY,
    -- amenities stored as JSON array: ['stainless_steel_appliances', 'granite_counters', 'in_unit_laundry', ...]
    
    last_renovation_date DATE,
    status STRING NOT NULL DEFAULT 'vacant',
    -- status values: 'vacant', 'occupied', 'reserved', 'maintenance'
    
    created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    
    FOREIGN KEY (property_id) REFERENCES properties(property_id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
    CONSTRAINT unit_type_valid CHECK (unit_type IN ('Studio', '1BR', '2BR', '3BR', '4BR+', 'Office', 'Retail', 'Industrial')),
    CONSTRAINT status_valid CHECK (status IN ('vacant', 'occupied', 'reserved', 'maintenance')),
    CONSTRAINT rent_positive CHECK (rent_current >= 0),
    CONSTRAINT beds_positive CHECK (bed_count >= 0),
    CONSTRAINT baths_positive CHECK (bath_count >= 0)
)
CLUSTER BY (property_id, unit_id)
COMMENT = 'Individual units/spaces within properties with type, size, and occupancy details'
;

-- ============================================================================
-- TABLE: leases
-- Description: Lease agreements for units with financial and renewal terms
-- ============================================================================
CREATE OR REPLACE TABLE leases (
    lease_id STRING NOT NULL PRIMARY KEY,
    property_id STRING NOT NULL,
    unit_id STRING NOT NULL,
    tenant_id STRING NOT NULL,
    
    tenant_name STRING NOT NULL,
    tenant_email STRING,
    tenant_phone STRING,
    
    lease_start_date DATE NOT NULL,
    lease_end_date DATE NOT NULL,
    
    rent_amount DECIMAL(10,2) NOT NULL,
    security_deposit DECIMAL(10,2),
    
    lease_type STRING DEFAULT 'fixed',
    -- lease_type values: 'fixed', 'variable', 'commercial', 'industrial'
    
    renewal_option STRING DEFAULT 'none',
    -- renewal_option values: 'none', 'automatic', 'optional_tenant', 'optional_landlord'
    renewal_option_date DATE,
    
    escalation_clause BOOLEAN DEFAULT FALSE,
    escalation_percent DECIMAL(5,2),
    escalation_frequency STRING,
    -- escalation_frequency values: 'annual', 'biennial', 'per_cpi'
    
    lease_document_url STRING,
    lease_document_hash STRING,
    
    status STRING NOT NULL DEFAULT 'active',
    -- status values: 'active', 'expired', 'terminated', 'pending_renewal'
    
    created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    
    FOREIGN KEY (property_id) REFERENCES properties(property_id),
    FOREIGN KEY (unit_id) REFERENCES units(unit_id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
    CONSTRAINT lease_date_valid CHECK (lease_end_date > lease_start_date),
    CONSTRAINT rent_positive CHECK (rent_amount > 0),
    CONSTRAINT escalation_valid CHECK (escalation_percent >= 0 AND escalation_percent <= 100),
    CONSTRAINT status_valid CHECK (status IN ('active', 'expired', 'terminated', 'pending_renewal'))
)
CLUSTER BY (tenant_id, property_id, unit_id)
COMMENT = 'Lease agreements with financial terms, renewal options, and escalation clauses'
;

-- ============================================================================
-- TABLE: tenancies
-- Description: Tenant occupancy records (who is in which unit and when)
-- ============================================================================
CREATE OR REPLACE TABLE tenancies (
    tenancy_id STRING NOT NULL PRIMARY KEY,
    unit_id STRING NOT NULL,
    property_id STRING NOT NULL,
    tenant_id STRING NOT NULL,
    lease_id STRING NOT NULL,
    
    tenant_name STRING NOT NULL,
    tenant_email STRING,
    tenant_phone STRING,
    
    move_in_date DATE NOT NULL,
    move_out_date DATE,
    
    status STRING NOT NULL DEFAULT 'active',
    -- status values: 'active', 'completed', 'evicted', 'pending'
    
    created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    
    FOREIGN KEY (unit_id) REFERENCES units(unit_id),
    FOREIGN KEY (property_id) REFERENCES properties(property_id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
    FOREIGN KEY (lease_id) REFERENCES leases(lease_id),
    CONSTRAINT moveout_after_movein CHECK (move_out_date IS NULL OR move_out_date > move_in_date),
    CONSTRAINT status_valid CHECK (status IN ('active', 'completed', 'evicted', 'pending'))
)
CLUSTER BY (tenant_id, property_id)
COMMENT = 'Tenant occupancy records tracking who lives in each unit and when'
;

-- ============================================================================
-- TABLE: user_property_access
-- Description: Fine-grained access control for users to properties
-- Purpose: Allows multi-tenant isolation and role-based property visibility
-- ============================================================================
CREATE OR REPLACE TABLE user_property_access (
    access_id STRING NOT NULL PRIMARY KEY,
    user_id STRING NOT NULL,
    tenant_id STRING NOT NULL,
    property_id STRING NOT NULL,
    
    role STRING NOT NULL,
    -- role values: 'owner', 'property_manager', 'leasing_agent', 'maintenance', 'accountant', 'viewer'
    
    access_level STRING NOT NULL DEFAULT 'read',
    -- access_level values: 'read', 'write', 'admin'
    
    granted_by STRING,
    granted_date TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    expires_at TIMESTAMP_NTZ,
    
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
    FOREIGN KEY (property_id) REFERENCES properties(property_id),
    CONSTRAINT role_valid CHECK (role IN ('owner', 'property_manager', 'leasing_agent', 'maintenance', 'accountant', 'viewer')),
    CONSTRAINT access_level_valid CHECK (access_level IN ('read', 'write', 'admin'))
)
CLUSTER BY (tenant_id, property_id)
COMMENT = 'Fine-grained access control mapping users to properties with specific roles and permissions'
;

-- ============================================================================
-- INDEXES for query optimization
-- ============================================================================
CREATE OR REPLACE INDEX idx_properties_tenant ON properties(tenant_id);
CREATE OR REPLACE INDEX idx_units_property ON units(property_id);
CREATE OR REPLACE INDEX idx_units_status ON units(status);
CREATE OR REPLACE INDEX idx_leases_property ON leases(property_id);
CREATE OR REPLACE INDEX idx_leases_unit ON leases(unit_id);
CREATE OR REPLACE INDEX idx_leases_dates ON leases(lease_start_date, lease_end_date);
CREATE OR REPLACE INDEX idx_tenancies_unit ON tenancies(unit_id);
CREATE OR REPLACE INDEX idx_tenancies_tenant ON tenancies(tenant_id);
CREATE OR REPLACE INDEX idx_access_tenant_user ON user_property_access(tenant_id, user_id);

-- ============================================================================
-- COMMENTS for Schema Documentation
-- ============================================================================
COMMENT ON COLUMN properties.property_type IS 'Type of property: Apartment, Commercial, Retail, Industrial, or Mixed-Use';
COMMENT ON COLUMN properties.cap_rate IS 'Capitalization rate: (Net Operating Income / Property Value) * 100';
COMMENT ON COLUMN units.amenities IS 'JSON array of unit amenities for search and filtering';
COMMENT ON COLUMN leases.escalation_clause IS 'Whether rent increases annually or based on CPI';
COMMENT ON COLUMN user_property_access.role IS 'Job role that determines default permissions and visibility';
COMMENT ON COLUMN user_property_access.access_level IS 'Granular permission level: read (view only), write (modify), or admin (full control)';

