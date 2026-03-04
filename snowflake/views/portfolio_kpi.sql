-- ============================================================================
-- SNOWFLAKE VIEW: Portfolio KPI
-- Purpose: Portfolio-level key performance indicators aggregated by tenant
-- Strategy: Materialized view for fast queries on dashboard and executive reports
-- Refresh: Scheduled to refresh hourly/daily based on data update frequency
-- ============================================================================

CREATE OR REPLACE MATERIALIZED VIEW portfolio_kpi AS
SELECT
    t.tenant_id,
    t.company_name,
    t.subscription_tier,
    
    -- COUNT AND CAPACITY METRICS
    COUNT(DISTINCT p.property_id) AS property_count,
    SUM(p.units_total) AS units_total,
    COUNT(DISTINCT CASE WHEN u.status = 'occupied' THEN u.unit_id END) AS units_occupied,
    COUNT(DISTINCT CASE WHEN u.status = 'vacant' THEN u.unit_id END) AS units_vacant,
    
    -- OCCUPANCY RATE
    ROUND(
        (COUNT(DISTINCT CASE WHEN u.status = 'occupied' THEN u.unit_id END) * 100.0) /
        NULLIF(COUNT(DISTINCT u.unit_id), 0),
        2
    ) AS occupancy_percent,
    
    -- PROPERTY VALUATION
    SUM(p.current_valuation) AS portfolio_valuation,
    ROUND(AVG(p.current_valuation), 2) AS avg_property_valuation,
    
    -- FINANCIAL METRICS (from latest month)
    SUM(CASE WHEN f.period_month = DATE_TRUNC('month', CURRENT_DATE())
             THEN f.noi ELSE 0 END) AS total_noi_current_month,
    
    SUM(CASE WHEN f.period_month = DATE_TRUNC('month', CURRENT_DATE())
             THEN f.gross_rent ELSE 0 END) AS total_gross_rent_current_month,
    
    SUM(CASE WHEN f.period_month = DATE_TRUNC('month', CURRENT_DATE())
             THEN f.total_operating_expenses ELSE 0 END) AS total_opex_current_month,
    
    -- CAP RATE ANALYSIS
    ROUND(AVG(p.cap_rate), 2) AS avg_cap_rate,
    MAX(p.cap_rate) AS max_cap_rate,
    MIN(p.cap_rate) AS min_cap_rate,
    
    -- YEAR-TO-DATE MAINTENANCE COSTS
    SUM(CASE WHEN ml.log_date >= DATE_TRUNC('year', CURRENT_DATE())
             THEN COALESCE(ml.materials_cost, 0) + COALESCE(ml.labor_cost, 0)
             ELSE 0 END) AS ytd_maintenance_cost,
    
    -- OPEN WORK ORDERS
    COUNT(DISTINCT CASE WHEN wo.status IN ('Open', 'In Progress')
                        THEN wo.work_order_id END) AS open_work_orders_count,
    
    -- RENT COLLECTION HEALTH
    COUNT(DISTINCT CASE WHEN rc.status IN ('overdue', 'delinquent')
                        THEN rc.collection_id END) AS overdue_rent_collections,
    
    ROUND(
        COUNT(DISTINCT CASE WHEN rc.status = 'received' THEN rc.collection_id END) * 100.0 /
        NULLIF(COUNT(DISTINCT rc.collection_id), 0),
        2
    ) AS rent_collection_rate_percent,
    
    ROUND(AVG(CASE WHEN rc.days_overdue > 0 THEN rc.days_overdue END), 1) AS avg_days_overdue,
    
    -- TIMESTAMPS
    CURRENT_TIMESTAMP() AS last_updated,
    DATE_TRUNC('month', CURRENT_DATE()) AS reporting_month

FROM tenants t
LEFT JOIN properties p ON t.tenant_id = p.tenant_id
LEFT JOIN units u ON p.property_id = u.property_id
LEFT JOIN financials f ON p.property_id = f.property_id
LEFT JOIN work_orders wo ON p.property_id = wo.property_id
LEFT JOIN maintenance_logs ml ON wo.work_order_id = ml.work_order_id
LEFT JOIN rent_collections rc ON p.property_id = rc.property_id

WHERE t.active = TRUE

GROUP BY
    t.tenant_id,
    t.company_name,
    t.subscription_tier

ORDER BY t.company_name

COMMENT = 'Portfolio-level KPIs aggregated by tenant including occupancy, financials, maintenance, and rent collection metrics'
;

-- ============================================================================
-- VIEW: Portfolio KPI Details by Property Type
-- Purpose: Break down portfolio metrics by property type for analysis
-- ============================================================================

CREATE OR REPLACE VIEW portfolio_kpi_by_property_type AS
SELECT
    t.tenant_id,
    t.company_name,
    p.property_type,
    
    COUNT(DISTINCT p.property_id) AS property_count,
    SUM(p.units_total) AS units_total,
    COUNT(DISTINCT CASE WHEN u.status = 'occupied' THEN u.unit_id END) AS units_occupied,
    
    ROUND(
        (COUNT(DISTINCT CASE WHEN u.status = 'occupied' THEN u.unit_id END) * 100.0) /
        NULLIF(SUM(p.units_total), 0),
        2
    ) AS occupancy_percent,
    
    SUM(p.current_valuation) AS property_type_valuation,
    ROUND(AVG(p.cap_rate), 2) AS avg_cap_rate,
    
    SUM(CASE WHEN f.period_month = DATE_TRUNC('month', CURRENT_DATE())
             THEN f.noi ELSE 0 END) AS total_noi_current_month,
    
    MAX(f.period_month) AS latest_financial_period

FROM tenants t
LEFT JOIN properties p ON t.tenant_id = p.tenant_id
LEFT JOIN units u ON p.property_id = u.property_id
LEFT JOIN financials f ON p.property_id = f.property_id

WHERE t.active = TRUE

GROUP BY
    t.tenant_id,
    t.company_name,
    p.property_type

ORDER BY t.company_name, property_count DESC

COMMENT = 'Portfolio KPI breakdown by property type for comparative analysis'
;

-- ============================================================================
-- VIEW: Portfolio Trend (Monthly)
-- Purpose: Track KPI trends over time for trajectory analysis
-- ============================================================================

CREATE OR REPLACE VIEW portfolio_kpi_trend AS
SELECT
    t.tenant_id,
    t.company_name,
    DATE_TRUNC('month', f.period_month)::DATE AS month,
    
    COUNT(DISTINCT p.property_id) AS property_count,
    ROUND(AVG(CASE WHEN u.status = 'occupied' THEN 1 ELSE 0 END) * 100, 2) AS occupancy_percent,
    
    SUM(f.gross_rent) AS total_gross_rent,
    SUM(f.total_operating_expenses) AS total_opex,
    SUM(f.noi) AS total_noi,
    
    ROUND(AVG(p.cap_rate), 2) AS avg_cap_rate,
    
    SUM(COALESCE(ml.materials_cost, 0) + COALESCE(ml.labor_cost, 0)) AS maintenance_cost

FROM tenants t
LEFT JOIN properties p ON t.tenant_id = p.tenant_id
LEFT JOIN units u ON p.property_id = u.property_id
LEFT JOIN financials f ON p.property_id = f.property_id
LEFT JOIN work_orders wo ON p.property_id = wo.property_id
LEFT JOIN maintenance_logs ml ON wo.work_order_id = ml.work_order_id
    AND DATE_TRUNC('month', ml.log_date) = DATE_TRUNC('month', f.period_month)

WHERE t.active = TRUE
  AND f.period_month IS NOT NULL

GROUP BY
    t.tenant_id,
    t.company_name,
    DATE_TRUNC('month', f.period_month)

ORDER BY t.company_name, month DESC

COMMENT = 'Monthly KPI trends for historical tracking and trajectory analysis'
;

