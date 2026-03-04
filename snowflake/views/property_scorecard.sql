-- ============================================================================
-- SNOWFLAKE VIEW: Property Scorecard
-- Purpose: Comprehensive property-level performance dashboard
-- Strategy: Materialized view for fast property health assessments
-- Usage: Powers property comparison and performance analytics
-- ============================================================================

CREATE OR REPLACE MATERIALIZED VIEW property_scorecard AS
SELECT
    p.property_id,
    p.tenant_id,
    p.property_name,
    p.property_address,
    p.city,
    p.state,
    p.zip_code,
    p.property_type,
    p.units_total,
    p.year_built,
    p.square_footage,
    p.current_valuation,
    
    -- OCCUPANCY METRICS
    COUNT(DISTINCT CASE WHEN u.status = 'occupied' THEN u.unit_id END) AS units_occupied,
    COUNT(DISTINCT CASE WHEN u.status = 'vacant' THEN u.unit_id END) AS units_vacant,
    
    ROUND(
        (COUNT(DISTINCT CASE WHEN u.status = 'occupied' THEN u.unit_id END) * 100.0) /
        NULLIF(p.units_total, 0),
        2
    ) AS occupancy_percent,
    
    ROUND(AVG(CASE WHEN u.status = 'occupied' THEN u.rent_current END), 2) AS avg_rent_occupied,
    
    -- FINANCIAL METRICS (Most Recent Month)
    f_latest.noi AS noi,
    f_latest.budget_noi AS budget_noi,
    f_latest.gross_rent AS gross_rent,
    f_latest.total_operating_expenses AS total_operating_expenses,
    f_latest.period_month AS latest_financial_period,
    
    -- NOI PERFORMANCE
    ROUND(
        ((f_latest.noi - f_latest.budget_noi) / NULLIF(f_latest.budget_noi, 0)) * 100,
        2
    ) AS noi_variance_percent,
    
    CASE
        WHEN f_latest.noi > f_latest.budget_noi THEN 'Above Budget'
        WHEN f_latest.noi < (f_latest.budget_noi * 0.95) THEN 'Below Budget'
        ELSE 'On Target'
    END AS noi_performance_status,
    
    -- RENT COLLECTION
    ROUND(
        COUNT(DISTINCT CASE WHEN rc.status = 'received' THEN rc.collection_id END) * 100.0 /
        NULLIF(COUNT(DISTINCT rc.collection_id), 0),
        2
    ) AS rent_collection_rate_percent,
    
    ROUND(AVG(CASE WHEN rc.days_overdue > 0 THEN rc.days_overdue END), 1) AS avg_days_overdue,
    
    COUNT(DISTINCT CASE WHEN rc.status IN ('overdue', 'delinquent')
                        THEN rc.collection_id END) AS delinquent_rent_count,
    
    ROUND(
        SUM(CASE WHEN rc.status IN ('overdue', 'delinquent')
                 THEN (rc.rent_due - rc.rent_received) ELSE 0 END),
        2
    ) AS delinquent_amount,
    
    -- MAINTENANCE & OPERATIONS
    COUNT(DISTINCT CASE WHEN wo.status IN ('Open', 'In Progress')
                        THEN wo.work_order_id END) AS open_work_orders,
    
    COUNT(DISTINCT CASE WHEN wo.status = 'Completed'
        AND wo.completed_date >= DATE_TRUNC('month', CURRENT_DATE())
        THEN wo.work_order_id END) AS completed_work_orders_month,
    
    ROUND(
        SUM(CASE WHEN wo.status = 'Completed'
                 THEN COALESCE(wo.actual_cost, 0) ELSE 0 END),
        2
    ) AS total_maintenance_cost,
    
    ROUND(
        SUM(CASE WHEN wo.status = 'Completed'
                 THEN COALESCE(wo.actual_cost, 0) ELSE 0 END) / NULLIF(p.units_total, 0),
        2
    ) AS maintenance_cost_per_unit,
    
    -- LEASE ANALYTICS
    COUNT(DISTINCT CASE WHEN l.status = 'active' THEN l.lease_id END) AS active_leases,
    
    COUNT(DISTINCT CASE WHEN l.lease_end_date <= DATE_TRUNC('month', CURRENT_DATE()) + INTERVAL '90 days'
                         AND l.lease_end_date > CURRENT_DATE()
                         AND l.status = 'active'
                        THEN l.lease_id END) AS leases_expiring_90_days,
    
    -- RISK SCORING (0-100, higher is worse)
    CASE
        WHEN ROUND(
            (COUNT(DISTINCT CASE WHEN u.status = 'occupied' THEN u.unit_id END) * 100.0) /
            NULLIF(p.units_total, 0),
            2) < 80 THEN 20
        ELSE 0
    END +
    CASE
        WHEN ROUND(AVG(CASE WHEN rc.days_overdue > 0 THEN rc.days_overdue END), 1) > 30 THEN 30
        WHEN ROUND(AVG(CASE WHEN rc.days_overdue > 0 THEN rc.days_overdue END), 1) > 15 THEN 15
        ELSE 0
    END +
    CASE
        WHEN COUNT(DISTINCT CASE WHEN wo.status IN ('Open', 'In Progress')
                                  THEN wo.work_order_id END) > 10 THEN 20
        WHEN COUNT(DISTINCT CASE WHEN wo.status IN ('Open', 'In Progress')
                                  THEN wo.work_order_id END) > 5 THEN 10
        ELSE 0
    END +
    CASE
        WHEN (f_latest.noi - f_latest.budget_noi) / NULLIF(f_latest.budget_noi, 0) < -0.15 THEN 15
        WHEN (f_latest.noi - f_latest.budget_noi) / NULLIF(f_latest.budget_noi, 0) < -0.05 THEN 10
        ELSE 0
    END AS health_risk_score,
    
    -- PROPERTY STATUS
    CASE
        WHEN COUNT(DISTINCT CASE WHEN wo.status IN ('Open', 'In Progress')
                                  THEN wo.work_order_id END) > 10
             AND ROUND(
                (COUNT(DISTINCT CASE WHEN u.status = 'occupied' THEN u.unit_id END) * 100.0) /
                NULLIF(p.units_total, 0),
                2) < 80
        THEN 'At Risk'
        WHEN ROUND(AVG(CASE WHEN rc.days_overdue > 0 THEN rc.days_overdue END), 1) > 30
        THEN 'At Risk'
        WHEN (f_latest.noi - f_latest.budget_noi) / NULLIF(f_latest.budget_noi, 0) < -0.15
        THEN 'At Risk'
        ELSE 'Healthy'
    END AS property_status,
    
    -- TIMESTAMPS
    CURRENT_TIMESTAMP() AS scorecard_updated,
    p.updated_at AS property_last_updated

FROM properties p
LEFT JOIN units u ON p.property_id = u.property_id
LEFT JOIN financials f_latest ON p.property_id = f_latest.property_id
    AND f_latest.period_month = (
        SELECT MAX(period_month)
        FROM financials
        WHERE property_id = p.property_id
    )
LEFT JOIN rent_collections rc ON p.property_id = rc.property_id
LEFT JOIN work_orders wo ON p.property_id = wo.property_id
LEFT JOIN leases l ON p.property_id = l.property_id

WHERE p.status = 'active'

GROUP BY
    p.property_id,
    p.tenant_id,
    p.property_name,
    p.property_address,
    p.city,
    p.state,
    p.zip_code,
    p.property_type,
    p.units_total,
    p.year_built,
    p.square_footage,
    p.current_valuation,
    f_latest.noi,
    f_latest.budget_noi,
    f_latest.gross_rent,
    f_latest.total_operating_expenses,
    f_latest.period_month,
    p.updated_at

ORDER BY health_risk_score DESC, property_name

COMMENT = 'Property-level scorecard with occupancy, financial, operational, and health metrics for dashboard and analytics'
;

-- ============================================================================
-- VIEW: Property Performance Comparison
-- Purpose: Compare properties by metrics for benchmarking
-- ============================================================================

CREATE OR REPLACE VIEW property_performance_comparison AS
SELECT
    ps.property_id,
    ps.property_name,
    ps.property_type,
    ps.units_total,
    ps.occupancy_percent,
    ps.noi,
    ps.budget_noi,
    ps.noi_variance_percent,
    ps.rent_collection_rate_percent,
    ps.open_work_orders,
    ps.maintenance_cost_per_unit,
    ps.health_risk_score,
    
    -- Percentile rankings within property type
    PERCENT_RANK() OVER (
        PARTITION BY ps.property_type
        ORDER BY ps.occupancy_percent DESC
    ) AS occupancy_percentile,
    
    PERCENT_RANK() OVER (
        PARTITION BY ps.property_type
        ORDER BY ps.noi DESC
    ) AS noi_percentile,
    
    PERCENT_RANK() OVER (
        PARTITION BY ps.property_type
        ORDER BY ps.rent_collection_rate_percent DESC
    ) AS collection_percentile,
    
    PERCENT_RANK() OVER (
        PARTITION BY ps.property_type
        ORDER BY ps.health_risk_score ASC
    ) AS health_percentile

FROM property_scorecard ps

ORDER BY ps.property_type, ps.health_risk_score DESC

COMMENT = 'Property performance with percentile rankings for benchmarking within property type'
;

