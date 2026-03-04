-- ============================================================================
-- EXAMPLE SQL QUERIES FOR TEXT-TO-SQL ENGINE
-- Purpose: Reference queries that demonstrate Text-to-SQL generation patterns
-- Each query includes the natural language question that would generate it
-- Personas: Property Manager, Broker, Finance, Executive
-- ============================================================================

-- ============================================================================
-- QUERY 1: Which buildings have the most open work orders?
-- Natural Language: "Show me all properties with open maintenance work, ordered by urgency"
-- Persona: Property Manager / Facilities
-- ============================================================================
SELECT
    p.property_id,
    p.property_name,
    p.city,
    COUNT(DISTINCT CASE WHEN wo.status IN ('Open', 'In Progress') THEN wo.work_order_id END) AS open_work_orders,
    COUNT(DISTINCT CASE WHEN wo.priority = 'Critical' THEN wo.work_order_id END) AS critical_orders,
    COUNT(DISTINCT CASE WHEN wo.priority = 'High' THEN wo.work_order_id END) AS high_priority_orders,
    ROUND(SUM(CASE WHEN wo.status IN ('Open', 'In Progress') THEN COALESCE(wo.estimated_cost, 0) END), 2) AS estimated_cost,
    MIN(CASE WHEN wo.status = 'Open' THEN wo.requested_date END) AS oldest_open_request
FROM properties p
LEFT JOIN work_orders wo ON p.property_id = wo.property_id
WHERE p.status = 'active'
GROUP BY p.property_id, p.property_name, p.city
HAVING COUNT(DISTINCT CASE WHEN wo.status IN ('Open', 'In Progress') THEN wo.work_order_id END) > 0
ORDER BY open_work_orders DESC, critical_orders DESC
;

-- ============================================================================
-- QUERY 2: What available units are under $3k/month with recent renovations?
-- Natural Language: "Find vacant units under $3000 rent that were recently renovated"
-- Persona: Leasing Agent / Broker
-- ============================================================================
SELECT
    p.property_id,
    p.property_name,
    p.property_address,
    p.city,
    u.unit_id,
    u.unit_number,
    u.unit_type,
    u.square_footage,
    u.rent_current,
    u.bed_count,
    u.bath_count,
    u.amenities,
    u.last_renovation_date,
    DATEDIFF(day, u.last_renovation_date, CURRENT_DATE()) AS days_since_renovation
FROM properties p
JOIN units u ON p.property_id = u.property_id
WHERE p.status = 'active'
    AND u.status = 'vacant'
    AND u.rent_current < 3000
    AND u.last_renovation_date >= DATEADD(month, -12, CURRENT_DATE())
ORDER BY u.last_renovation_date DESC, u.rent_current ASC
;

-- ============================================================================
-- QUERY 3: What is the NOI trend year-over-year by region?
-- Natural Language: "Show me NOI trends for each state over the last 24 months"
-- Persona: Finance / Executive
-- ============================================================================
SELECT
    p.state,
    DATE_TRUNC('month', f.period_month)::DATE AS month,
    COUNT(DISTINCT p.property_id) AS property_count,
    SUM(f.gross_rent) AS total_gross_rent,
    SUM(f.total_operating_expenses) AS total_opex,
    SUM(f.noi) AS total_noi,
    ROUND(SUM(f.noi) / NULLIF(SUM(f.gross_rent), 0) * 100, 2) AS noi_margin_percent,
    LAG(SUM(f.noi)) OVER (PARTITION BY p.state ORDER BY DATE_TRUNC('month', f.period_month)) AS prior_month_noi,
    ROUND(
        ((SUM(f.noi) - LAG(SUM(f.noi)) OVER (PARTITION BY p.state ORDER BY DATE_TRUNC('month', f.period_month)))
         / NULLIF(LAG(SUM(f.noi)) OVER (PARTITION BY p.state ORDER BY DATE_TRUNC('month', f.period_month)), 0)) * 100,
        2
    ) AS month_over_month_change_percent
FROM properties p
JOIN financials f ON p.property_id = f.property_id
WHERE p.status = 'active'
    AND f.period_month >= DATEADD(month, -24, DATE_TRUNC('month', CURRENT_DATE()))
GROUP BY p.state, DATE_TRUNC('month', f.period_month)
ORDER BY p.state, DATE_TRUNC('month', f.period_month) DESC
;

-- ============================================================================
-- QUERY 4: Which properties are underperforming vs budget?
-- Natural Language: "Show properties where NOI is more than 10% below budget"
-- Persona: Property Manager / Finance
-- ============================================================================
SELECT
    p.property_id,
    p.property_name,
    p.city,
    p.state,
    f.period_month,
    f.noi,
    f.budget_noi,
    f.noi - f.budget_noi AS noi_variance,
    ROUND(((f.noi - f.budget_noi) / NULLIF(f.budget_noi, 0)) * 100, 2) AS variance_percent,
    f.gross_rent,
    f.budget_gross_rent,
    f.total_operating_expenses,
    CASE
        WHEN ((f.noi - f.budget_noi) / NULLIF(f.budget_noi, 0)) < -0.20 THEN 'Critical'
        WHEN ((f.noi - f.budget_noi) / NULLIF(f.budget_noi, 0)) < -0.10 THEN 'Underperforming'
        ELSE 'On Track'
    END AS performance_status
FROM properties p
JOIN financials f ON p.property_id = f.property_id
WHERE p.status = 'active'
    AND f.period_month >= DATE_TRUNC('month', DATEADD(month, -3, CURRENT_DATE()))
    AND ((f.noi - f.budget_noi) / NULLIF(f.budget_noi, 0)) < -0.10
ORDER BY variance_percent ASC, p.property_name
;

-- ============================================================================
-- QUERY 5: What is the rent collection delinquency by region?
-- Natural Language: "Show delinquent rent by state with aging details"
-- Persona: Finance / Accounting
-- ============================================================================
SELECT
    p.state,
    p.city,
    p.property_name,
    COUNT(DISTINCT rc.collection_id) AS total_collections_expected,
    COUNT(DISTINCT CASE WHEN rc.status = 'received' THEN rc.collection_id END) AS received_count,
    COUNT(DISTINCT CASE WHEN rc.status IN ('overdue', 'delinquent') THEN rc.collection_id END) AS delinquent_count,
    ROUND(
        COUNT(DISTINCT CASE WHEN rc.status = 'received' THEN rc.collection_id END) * 100.0
        / NULLIF(COUNT(DISTINCT rc.collection_id), 0),
        2
    ) AS collection_rate_percent,
    ROUND(SUM(CASE WHEN rc.status IN ('overdue', 'delinquent') THEN rc.rent_due - rc.rent_received ELSE 0 END), 2) AS total_delinquent_amount,
    ROUND(AVG(CASE WHEN rc.days_overdue > 0 THEN rc.days_overdue END), 1) AS avg_days_overdue,
    MAX(CASE WHEN rc.days_overdue > 0 THEN rc.days_overdue END) AS max_days_overdue
FROM properties p
LEFT JOIN rent_collections rc ON p.property_id = rc.property_id
    AND rc.period_month >= DATE_TRUNC('month', DATEADD(month, -3, CURRENT_DATE()))
WHERE p.status = 'active'
GROUP BY p.state, p.city, p.property_name
HAVING COUNT(DISTINCT CASE WHEN rc.status IN ('overdue', 'delinquent') THEN rc.collection_id END) > 0
ORDER BY total_delinquent_amount DESC, p.state, p.property_name
;

-- ============================================================================
-- QUERY 6: Which lease renewals are coming up in the next 90 days?
-- Natural Language: "List all leases expiring in the next 3 months that need renewal action"
-- Persona: Leasing Agent / Property Manager
-- ============================================================================
SELECT
    l.lease_id,
    p.property_id,
    p.property_name,
    p.city,
    u.unit_number,
    u.unit_type,
    l.tenant_name,
    l.lease_end_date,
    DATEDIFF(day, CURRENT_DATE(), l.lease_end_date) AS days_until_expiration,
    l.rent_amount,
    l.lease_type,
    l.renewal_option,
    l.renewal_option_date,
    l.escalation_clause,
    l.escalation_percent,
    CASE
        WHEN DATEDIFF(day, CURRENT_DATE(), l.lease_end_date) <= 30 THEN 'Critical - Action Required'
        WHEN DATEDIFF(day, CURRENT_DATE(), l.lease_end_date) <= 60 THEN 'High Priority'
        ELSE 'Monitor'
    END AS renewal_urgency
FROM leases l
JOIN properties p ON l.property_id = p.property_id
JOIN units u ON l.unit_id = u.unit_id
WHERE p.status = 'active'
    AND l.status = 'active'
    AND l.lease_end_date > CURRENT_DATE()
    AND l.lease_end_date <= DATEADD(day, 90, CURRENT_DATE())
ORDER BY l.lease_end_date ASC, renewal_urgency DESC
;

-- ============================================================================
-- QUERY 7: What is the maintenance cost per unit by property?
-- Natural Language: "Calculate total maintenance spending divided by unit count for each building"
-- Persona: Property Manager / Facilities
-- ============================================================================
SELECT
    p.property_id,
    p.property_name,
    p.city,
    p.property_type,
    p.units_total,
    COUNT(DISTINCT wo.work_order_id) AS total_work_orders_completed,
    ROUND(SUM(COALESCE(wo.actual_cost, 0)), 2) AS total_maintenance_cost,
    ROUND(SUM(COALESCE(ml.materials_cost, 0)), 2) AS total_materials_cost,
    ROUND(SUM(COALESCE(ml.labor_cost, 0)), 2) AS total_labor_cost,
    ROUND(SUM(COALESCE(ml.hours_worked, 0)), 2) AS total_technician_hours,
    ROUND(
        SUM(COALESCE(wo.actual_cost, 0)) / NULLIF(p.units_total, 0),
        2
    ) AS maintenance_cost_per_unit,
    MIN(wo.completed_date) AS earliest_completion,
    MAX(wo.completed_date) AS most_recent_completion,
    DATE_TRUNC('month', CURRENT_DATE())::DATE AS reporting_month
FROM properties p
LEFT JOIN work_orders wo ON p.property_id = wo.property_id
    AND wo.status = 'Completed'
    AND wo.completed_date >= DATE_TRUNC('year', CURRENT_DATE())
LEFT JOIN maintenance_logs ml ON wo.work_order_id = ml.work_order_id
WHERE p.status = 'active'
GROUP BY p.property_id, p.property_name, p.city, p.property_type, p.units_total
HAVING COUNT(DISTINCT wo.work_order_id) > 0
ORDER BY maintenance_cost_per_unit DESC
;

-- ============================================================================
-- QUERY 8: What is the vacancy rate trend over 24 months?
-- Natural Language: "Show how occupancy rates have changed month-by-month across the portfolio"
-- Persona: Executive / Analytics
-- ============================================================================
SELECT
    os.snapshot_date,
    COUNT(DISTINCT os.property_id) AS property_count,
    SUM(os.units_total) AS total_units,
    SUM(os.units_occupied) AS total_occupied,
    SUM(os.units_vacant) AS total_vacant,
    ROUND(
        (SUM(os.units_occupied) * 100.0) / NULLIF(SUM(os.units_total), 0),
        2
    ) AS portfolio_occupancy_percent,
    ROUND(
        (SUM(os.units_vacant) * 100.0) / NULLIF(SUM(os.units_total), 0),
        2
    ) AS portfolio_vacancy_percent,
    LAG(ROUND((SUM(os.units_occupied) * 100.0) / NULLIF(SUM(os.units_total), 0), 2))
        OVER (ORDER BY os.snapshot_date) AS prior_month_occupancy_percent,
    ROUND(
        (SUM(os.units_occupied) * 100.0) / NULLIF(SUM(os.units_total), 0)
        - LAG(ROUND((SUM(os.units_occupied) * 100.0) / NULLIF(SUM(os.units_total), 0), 2))
        OVER (ORDER BY os.snapshot_date),
        2
    ) AS month_over_month_change
FROM occupancy_snapshots os
WHERE os.snapshot_date >= DATEADD(month, -24, CURRENT_DATE())
GROUP BY os.snapshot_date
ORDER BY os.snapshot_date DESC
;

-- ============================================================================
-- QUERY 9: Which operating expenses are exceeding budget by property?
-- Natural Language: "Show me properties where operating expenses are over budget"
-- Persona: Finance
-- ============================================================================
SELECT
    p.property_id,
    p.property_name,
    p.city,
    f.period_month,
    f.total_operating_expenses,
    f.total_operating_expenses - LAG(f.total_operating_expenses) OVER (PARTITION BY p.property_id ORDER BY f.period_month) AS month_over_month_increase,
    f.maintenance_repairs,
    f.utilities,
    f.insurance,
    f.property_taxes,
    f.management_fees,
    CASE
        WHEN f.maintenance_repairs > 5000 THEN 'High'
        WHEN f.maintenance_repairs > 2000 THEN 'Medium'
        ELSE 'Low'
    END AS maintenance_severity,
    CASE
        WHEN f.utilities > 3000 THEN 'Review Required'
        ELSE 'Normal'
    END AS utilities_status
FROM properties p
JOIN financials f ON p.property_id = f.property_id
WHERE p.status = 'active'
    AND f.period_month >= DATE_TRUNC('month', DATEADD(month, -6, CURRENT_DATE()))
ORDER BY f.period_month DESC, f.total_operating_expenses DESC
;

-- ============================================================================
-- QUERY 10: What is the average cap rate by property type and state?
-- Natural Language: "Compare cap rates across property types and regions"
-- Persona: Executive / Investment
-- ============================================================================
SELECT
    p.property_type,
    p.state,
    COUNT(DISTINCT p.property_id) AS property_count,
    ROUND(AVG(p.cap_rate), 2) AS avg_cap_rate,
    ROUND(MIN(p.cap_rate), 2) AS min_cap_rate,
    ROUND(MAX(p.cap_rate), 2) AS max_cap_rate,
    ROUND(STDDEV(p.cap_rate), 2) AS cap_rate_stddev,
    SUM(p.current_valuation) AS total_valuation,
    ROUND(AVG(p.current_valuation), 2) AS avg_property_valuation
FROM properties p
WHERE p.status = 'active'
GROUP BY p.property_type, p.state
ORDER BY p.property_type, avg_cap_rate DESC
;

-- ============================================================================
-- QUERY 11: Show me tenant payment history for the last tenant in each unit
-- Natural Language: "Who was in each unit and how did they pay their rent?"
-- Persona: Property Manager
-- ============================================================================
SELECT
    p.property_name,
    p.city,
    u.unit_number,
    t.tenant_name,
    t.move_in_date,
    t.move_out_date,
    l.lease_start_date,
    l.lease_end_date,
    l.rent_amount,
    COUNT(DISTINCT rc.collection_id) AS rent_payments_made,
    ROUND(
        COUNT(DISTINCT CASE WHEN rc.status = 'received' THEN rc.collection_id END) * 100.0
        / NULLIF(COUNT(DISTINCT rc.collection_id), 0),
        2
    ) AS payment_rate_percent,
    COUNT(DISTINCT CASE WHEN rc.status IN ('overdue', 'delinquent') THEN rc.collection_id END) AS late_payments,
    ROUND(AVG(rc.days_overdue), 1) AS avg_days_late
FROM tenancies t
JOIN units u ON t.unit_id = u.unit_id
JOIN properties p ON u.property_id = p.property_id
JOIN leases l ON t.lease_id = l.lease_id
LEFT JOIN rent_collections rc ON l.lease_id = rc.lease_id
WHERE t.status IN ('active', 'completed')
GROUP BY p.property_name, p.city, u.unit_number, t.tenant_name, t.move_in_date, t.move_out_date,
         l.lease_start_date, l.lease_end_date, l.rent_amount
ORDER BY p.property_name, u.unit_number, t.move_out_date DESC NULLS LAST
;

-- ============================================================================
-- QUERY 12: What maintenance categories are most frequent and expensive?
-- Natural Language: "Which types of maintenance repairs cost the most and happen most often?"
-- Persona: Facilities Manager
-- ============================================================================
SELECT
    wo.category,
    COUNT(DISTINCT wo.work_order_id) AS work_order_count,
    COUNT(DISTINCT CASE WHEN wo.status = 'Completed' THEN wo.work_order_id END) AS completed_count,
    COUNT(DISTINCT CASE WHEN wo.priority = 'Critical' THEN wo.work_order_id END) AS critical_count,
    ROUND(AVG(wo.estimated_cost), 2) AS avg_estimated_cost,
    ROUND(AVG(wo.actual_cost), 2) AS avg_actual_cost,
    ROUND(SUM(COALESCE(wo.actual_cost, 0)), 2) AS total_actual_cost,
    ROUND(AVG(ml.hours_worked), 2) AS avg_hours_per_job,
    COUNT(DISTINCT wo.assigned_to) AS unique_technicians
FROM work_orders wo
LEFT JOIN maintenance_logs ml ON wo.work_order_id = ml.work_order_id
WHERE wo.status = 'Completed'
    AND wo.completed_date >= DATE_TRUNC('year', CURRENT_DATE())
GROUP BY wo.category
ORDER BY total_actual_cost DESC, work_order_count DESC
;

-- ============================================================================
-- QUERY 13: Which units have the highest turnover (move-outs) recently?
-- Natural Language: "Show units with frequent tenant changes"
-- Persona: Leasing Agent
-- ============================================================================
SELECT
    p.property_id,
    p.property_name,
    u.unit_id,
    u.unit_number,
    u.unit_type,
    u.rent_current,
    COUNT(DISTINCT t.tenancy_id) AS total_tenants_24_months,
    COUNT(DISTINCT CASE WHEN t.move_out_date >= DATEADD(month, -12, CURRENT_DATE()) THEN t.tenancy_id END) AS moveouts_12_months,
    COUNT(DISTINCT CASE WHEN t.move_out_date >= DATEADD(month, -6, CURRENT_DATE()) THEN t.tenancy_id END) AS moveouts_6_months,
    AVG(DATEDIFF(day, t.move_in_date, t.move_out_date)) AS avg_tenancy_length_days,
    MAX(t.move_out_date) AS most_recent_moveout
FROM properties p
JOIN units u ON p.property_id = u.property_id
LEFT JOIN tenancies t ON u.unit_id = t.unit_id
WHERE p.status = 'active'
    AND t.move_out_date >= DATEADD(month, -24, CURRENT_DATE()) OR t.move_out_date IS NULL
GROUP BY p.property_id, p.property_name, u.unit_id, u.unit_number, u.unit_type, u.rent_current
HAVING COUNT(DISTINCT CASE WHEN t.move_out_date >= DATEADD(month, -12, CURRENT_DATE()) THEN t.tenancy_id END) >= 2
ORDER BY moveouts_12_months DESC, p.property_name, u.unit_number
;

-- ============================================================================
-- QUERY 14: Portfolio summary for executive dashboard
-- Natural Language: "Give me a quick overview of the entire portfolio performance"
-- Persona: Executive
-- ============================================================================
SELECT
    COUNT(DISTINCT p.property_id) AS total_properties,
    SUM(p.units_total) AS total_units,
    COUNT(DISTINCT CASE WHEN u.status = 'occupied' THEN u.unit_id END) AS occupied_units,
    ROUND(
        (COUNT(DISTINCT CASE WHEN u.status = 'occupied' THEN u.unit_id END) * 100.0)
        / NULLIF(SUM(p.units_total), 0),
        2
    ) AS occupancy_rate_percent,
    SUM(p.current_valuation) AS portfolio_valuation,
    ROUND(AVG(p.cap_rate), 2) AS avg_cap_rate,
    SUM(CASE WHEN f.period_month = DATE_TRUNC('month', CURRENT_DATE()) THEN f.noi ELSE 0 END) AS current_month_noi,
    SUM(CASE WHEN f.period_month = DATE_TRUNC('month', CURRENT_DATE()) THEN f.budget_noi ELSE 0 END) AS current_month_budget_noi,
    COUNT(DISTINCT CASE WHEN wo.status IN ('Open', 'In Progress') THEN wo.work_order_id END) AS open_work_orders,
    ROUND(
        COUNT(DISTINCT CASE WHEN rc.status = 'received' THEN rc.collection_id END) * 100.0
        / NULLIF(COUNT(DISTINCT rc.collection_id), 0),
        2
    ) AS rent_collection_rate_percent,
    COUNT(DISTINCT CASE WHEN rc.status IN ('overdue', 'delinquent') THEN rc.collection_id END) AS overdue_accounts
FROM properties p
LEFT JOIN units u ON p.property_id = u.property_id
LEFT JOIN financials f ON p.property_id = f.property_id
LEFT JOIN work_orders wo ON p.property_id = wo.property_id
LEFT JOIN rent_collections rc ON p.property_id = rc.property_id
WHERE p.status = 'active'
;

-- ============================================================================
-- QUERY 15: Show the top 10 revenue-generating properties
-- Natural Language: "Which buildings are generating the most rental income?"
-- Persona: Finance / Executive
-- ============================================================================
SELECT
    p.property_id,
    p.property_name,
    p.city,
    p.state,
    p.property_type,
    p.units_total,
    SUM(CASE WHEN f.period_month >= DATE_TRUNC('month', DATEADD(month, -12, CURRENT_DATE()))
             THEN f.gross_rent ELSE 0 END) AS gross_rent_12_months,
    SUM(CASE WHEN f.period_month >= DATE_TRUNC('month', DATEADD(month, -12, CURRENT_DATE()))
             THEN f.noi ELSE 0 END) AS noi_12_months,
    ROUND(
        SUM(CASE WHEN f.period_month >= DATE_TRUNC('month', DATEADD(month, -12, CURRENT_DATE()))
                 THEN f.noi ELSE 0 END) /
        NULLIF(SUM(CASE WHEN f.period_month >= DATE_TRUNC('month', DATEADD(month, -12, CURRENT_DATE()))
                        THEN f.gross_rent ELSE 0 END), 0) * 100,
        2
    ) AS noi_margin_percent_12m,
    ROUND(
        SUM(CASE WHEN f.period_month >= DATE_TRUNC('month', DATEADD(month, -12, CURRENT_DATE()))
                 THEN f.gross_rent ELSE 0 END) / NULLIF(p.units_total, 0),
        2
    ) AS revenue_per_unit_12m
FROM properties p
LEFT JOIN financials f ON p.property_id = f.property_id
WHERE p.status = 'active'
GROUP BY p.property_id, p.property_name, p.city, p.state, p.property_type, p.units_total
ORDER BY gross_rent_12_months DESC
LIMIT 10
;

-- ============================================================================
-- QUERY 16: Identify units below market rent for the property type
-- Natural Language: "Which units are rented below the property average?"
-- Persona: Leasing Agent / Broker
-- ============================================================================
SELECT
    p.property_id,
    p.property_name,
    p.city,
    u.unit_id,
    u.unit_number,
    u.unit_type,
    u.rent_current,
    ROUND(AVG(u_avg.rent_current) OVER (PARTITION BY p.property_id), 2) AS property_avg_rent,
    u.rent_current - ROUND(AVG(u_avg.rent_current) OVER (PARTITION BY p.property_id), 2) AS rent_difference,
    ROUND(
        ((u.rent_current - ROUND(AVG(u_avg.rent_current) OVER (PARTITION BY p.property_id), 2))
         / NULLIF(ROUND(AVG(u_avg.rent_current) OVER (PARTITION BY p.property_id), 2), 0)) * 100,
        2
    ) AS rent_difference_percent
FROM properties p
JOIN units u ON p.property_id = u.property_id
JOIN units u_avg ON p.property_id = u_avg.property_id
WHERE p.status = 'active'
    AND u.status = 'occupied'
    AND u.rent_current < ROUND(AVG(u_avg.rent_current) OVER (PARTITION BY p.property_id), 2) * 0.95
GROUP BY p.property_id, p.property_name, p.city, u.unit_id, u.unit_number, u.unit_type, u.rent_current
ORDER BY p.property_name, rent_difference
;

-- ============================================================================
-- QUERY 17: Year-to-date budget vs actual comparison
-- Natural Language: "How are we performing against YTD budget across income and expenses?"
-- Persona: Finance / Controller
-- ============================================================================
SELECT
    DATE_TRUNC('month', f.period_month)::DATE AS month,
    COUNT(DISTINCT p.property_id) AS property_count,
    
    SUM(f.gross_rent) AS actual_gross_rent,
    SUM(f.budget_gross_rent) AS budget_gross_rent,
    SUM(f.gross_rent) - SUM(f.budget_gross_rent) AS gross_rent_variance,
    
    SUM(f.total_operating_expenses) AS actual_opex,
    SUM(f.total_operating_expenses) AS budget_opex,
    
    SUM(f.noi) AS actual_noi,
    SUM(f.budget_noi) AS budget_noi,
    SUM(f.noi) - SUM(f.budget_noi) AS noi_variance,
    
    ROUND(
        ((SUM(f.noi) - SUM(f.budget_noi)) / NULLIF(SUM(f.budget_noi), 0)) * 100,
        2
    ) AS noi_variance_percent,
    
    CASE
        WHEN ((SUM(f.noi) - SUM(f.budget_noi)) / NULLIF(SUM(f.budget_noi), 0)) > 0.05 THEN 'Favorable'
        WHEN ((SUM(f.noi) - SUM(f.budget_noi)) / NULLIF(SUM(f.budget_noi), 0)) < -0.05 THEN 'Unfavorable'
        ELSE 'On Target'
    END AS variance_status

FROM properties p
JOIN financials f ON p.property_id = f.property_id

WHERE p.status = 'active'
    AND f.period_month >= DATE_TRUNC('year', CURRENT_DATE())

GROUP BY DATE_TRUNC('month', f.period_month)
ORDER BY DATE_TRUNC('month', f.period_month) DESC
;

-- ============================================================================
-- QUERY 18: Properties approaching lease expirations (renewal risk)
-- Natural Language: "Which properties have multiple units with expiring leases soon?"
-- Persona: Property Manager
-- ============================================================================
SELECT
    p.property_id,
    p.property_name,
    p.city,
    p.units_total,
    COUNT(DISTINCT CASE WHEN l.lease_end_date <= DATEADD(day, 90, CURRENT_DATE())
                         AND l.lease_end_date > CURRENT_DATE()
                         AND l.status = 'active'
                        THEN l.lease_id END) AS leases_expiring_90_days,
    ROUND(
        (COUNT(DISTINCT CASE WHEN l.lease_end_date <= DATEADD(day, 90, CURRENT_DATE())
                             AND l.lease_end_date > CURRENT_DATE()
                             AND l.status = 'active'
                            THEN l.lease_id END) * 100.0) / NULLIF(p.units_total, 0),
        2
    ) AS lease_expiration_rate_percent,
    SUM(CASE WHEN l.lease_end_date <= DATEADD(day, 90, CURRENT_DATE())
             AND l.lease_end_date > CURRENT_DATE()
             AND l.status = 'active'
            THEN l.rent_amount ELSE 0 END) AS at_risk_monthly_rent,
    MIN(CASE WHEN l.lease_end_date > CURRENT_DATE() AND l.status = 'active'
             THEN l.lease_end_date END) AS next_expiration_date
FROM properties p
LEFT JOIN leases l ON p.property_id = l.property_id
WHERE p.status = 'active'
GROUP BY p.property_id, p.property_name, p.city, p.units_total
HAVING COUNT(DISTINCT CASE WHEN l.lease_end_date <= DATEADD(day, 90, CURRENT_DATE())
                            AND l.lease_end_date > CURRENT_DATE()
                            AND l.status = 'active'
                           THEN l.lease_id END) > 0
ORDER BY leases_expiring_90_days DESC, p.property_name
;

-- ============================================================================
-- QUERY 19: Insurance and tax burden by property
-- Natural Language: "Show insurance and tax costs as percentage of revenue by building"
-- Persona: Finance
-- ============================================================================
SELECT
    p.property_id,
    p.property_name,
    p.city,
    p.property_type,
    ROUND(AVG(f.gross_rent), 2) AS avg_monthly_gross_rent,
    ROUND(AVG(f.insurance), 2) AS avg_monthly_insurance,
    ROUND(AVG(f.property_taxes), 2) AS avg_monthly_property_taxes,
    ROUND(AVG(f.insurance + f.property_taxes), 2) AS avg_monthly_fixed_charges,
    ROUND(
        (AVG(f.insurance + f.property_taxes) / NULLIF(AVG(f.gross_rent), 0)) * 100,
        2
    ) AS fixed_charges_percent_of_revenue,
    COUNT(DISTINCT f.period_month) AS months_in_sample
FROM properties p
JOIN financials f ON p.property_id = f.property_id
WHERE p.status = 'active'
    AND f.period_month >= DATE_TRUNC('month', DATEADD(month, -12, CURRENT_DATE()))
GROUP BY p.property_id, p.property_name, p.city, p.property_type
ORDER BY fixed_charges_percent_of_revenue DESC
;

-- ============================================================================
-- QUERY 20: Technician productivity and cost analysis
-- Natural Language: "Show which technicians complete the most work at lowest cost"
-- Persona: Facilities Manager
-- ============================================================================
SELECT
    ml.technician,
    COUNT(DISTINCT wo.work_order_id) AS jobs_completed,
    ROUND(SUM(ml.hours_worked), 1) AS total_hours,
    ROUND(SUM(COALESCE(ml.materials_cost, 0)), 2) AS total_materials_cost,
    ROUND(SUM(COALESCE(ml.labor_cost, 0)), 2) AS total_labor_cost,
    ROUND(
        SUM(COALESCE(ml.materials_cost, 0) + COALESCE(ml.labor_cost, 0)),
        2
    ) AS total_cost,
    ROUND(
        SUM(COALESCE(ml.materials_cost, 0) + COALESCE(ml.labor_cost, 0)) / NULLIF(COUNT(DISTINCT wo.work_order_id), 0),
        2
    ) AS avg_cost_per_job,
    ROUND(SUM(ml.hours_worked) / NULLIF(COUNT(DISTINCT wo.work_order_id), 0), 2) AS avg_hours_per_job,
    ROUND(
        SUM(COALESCE(ml.labor_cost, 0)) / NULLIF(SUM(ml.hours_worked), 0),
        2
    ) AS implied_hourly_rate
FROM maintenance_logs ml
JOIN work_orders wo ON ml.work_order_id = wo.work_order_id
WHERE wo.completed_date >= DATE_TRUNC('month', DATEADD(month, -6, CURRENT_DATE()))
GROUP BY ml.technician
HAVING COUNT(DISTINCT wo.work_order_id) >= 5
ORDER BY total_cost DESC, jobs_completed DESC
;

