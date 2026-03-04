/*
========================================
FACT: Property Scorecard
========================================
Purpose:
  Comprehensive per-property scorecard combining financial, operational,
  and maintenance metrics into a single analytical view. Enables detailed
  property-level performance analysis and ranking against peers.

Key Metrics:
  - Financial: NOI, NOI margin, budget variance, cap rate
  - Occupancy: Current rate, vacancy, lease renewals at risk
  - Maintenance: Open work orders, completion rates, costs
  - Health: Composite scoring and quartile ranking
  - Alerts: Flags for properties requiring immediate attention

Grain:
  One row per property with most recent financial and occupancy data

Quartile Ranking:
  Properties ranked within their peer group (similar size/type) for
  comparative performance analysis and management focus allocation
========================================
*/

with property_metrics as (
  select
    ip.property_id,
    ip.property_name,
    ip.property_type,
    ip.city,
    ip.state_province,
    ip.total_units,
    ip.total_square_feet,
    ip.is_multifamily,
    ip.current_market_value,
    ip.owner_id,
    ip.asset_manager_id,
    
    -- Latest Financial Data
    ip.latest_financial_period,
    ip.gross_rental_income,
    ip.actual_noi,
    ip.noi_margin_percent,
    ip.budget_variance_pct,
    ip.total_operating_expenses,
    
    -- Financial Health Score
    ip.noi_health_score,
    
    -- Latest Occupancy Data
    ip.latest_occupancy_date,
    ip.occupancy_percent,
    ip.vacancy_rate,
    ip.occupancy_health_status,
    
    -- Occupancy Health Score
    ip.occupancy_health_score,
    
    -- Maintenance Data
    ip.total_open_work_orders,
    ip.critical_work_orders,
    ip.avg_days_to_complete,
    ip.total_maintenance_cost,
    
    -- Maintenance Health Score
    ip.maintenance_health_score,
    
    -- Lease Data
    ip.total_active_leases,
    ip.leases_expiring_soon,
    ip.high_risk_renewals,
    ip.avg_monthly_rent,
    
    -- Composite Score
    ip.composite_performance_score,
    ip.performance_tier,
    
    -- Cost per Unit Metrics
    case
      when ip.total_units > 0
      then ip.total_maintenance_cost / ip.total_units
      else 0.00
    end as maintenance_cost_per_unit,
    
    case
      when ip.total_units > 0
      then ip.actual_noi / ip.total_units
      else 0.00
    end as noi_per_unit,
    
    -- Work Order Metrics
    case
      when ip.total_open_work_orders > 0
      then round((ip.avg_days_to_complete), 1)
      else 0.0
    end as avg_work_order_resolution_days
    
  from {{ ref('int_property_performance') }} ip
),

with_peer_ranking as (
  select
    pm.*,
    
    -- Rank within property type
    dense_rank() over (
      partition by pm.property_type 
      order by pm.composite_performance_score desc
    ) as rank_within_type,
    
    -- Quartile ranking
    ntile(4) over (
      partition by pm.property_type 
      order by pm.composite_performance_score desc
    ) as performance_quartile,
    
    -- Count in peer group
    count(*) over (partition by pm.property_type) as peer_group_size
    
  from property_metrics pm
),

with_flags as (
  select
    wr.*,
    
    -- Alert Flags
    case
      when wr.total_open_work_orders > 5 then true
      else false
    end as flag_high_maintenance_burden,
    
    case
      when wr.critical_work_orders > 0 then true
      else false
    end as flag_critical_work_orders,
    
    case
      when wr.high_risk_renewals > 0 then true
      else false
    end as flag_lease_renewal_risk,
    
    case
      when wr.noi_margin_percent < 25 then true
      else false
    end as flag_low_profitability,
    
    case
      when wr.occupancy_percent < 90 then true
      else false
    end as flag_occupancy_concern,
    
    case
      when wr.budget_variance_pct < -10 then true
      else false
    end as flag_budget_miss,
    
    case
      when wr.performance_quartile = 4 then true
      else false
    end as flag_underperformer,
    
    current_date() as processed_date
    
  from with_peer_ranking wr
)

select
  property_id,
  property_name,
  property_type,
  city,
  state_province,
  total_units,
  total_square_feet,
  is_multifamily,
  current_market_value,
  owner_id,
  asset_manager_id,
  
  -- Financial Metrics
  latest_financial_period,
  round(gross_rental_income, 2) as gross_rental_income,
  round(actual_noi, 2) as actual_noi,
  round(noi_margin_percent, 2) as noi_margin_percent,
  round(budget_variance_pct, 2) as budget_variance_pct,
  round(total_operating_expenses, 2) as total_operating_expenses,
  round(noi_per_unit, 2) as noi_per_unit,
  
  -- Financial Health
  noi_health_score,
  
  -- Occupancy Metrics
  latest_occupancy_date,
  round(occupancy_percent, 2) as occupancy_percent,
  round(vacancy_rate, 4) as vacancy_rate,
  occupancy_health_status,
  
  -- Occupancy Health
  occupancy_health_score,
  
  -- Maintenance Metrics
  total_open_work_orders,
  critical_work_orders,
  avg_work_order_resolution_days,
  round(total_maintenance_cost, 2) as total_maintenance_cost,
  round(maintenance_cost_per_unit, 2) as maintenance_cost_per_unit,
  
  -- Maintenance Health
  maintenance_health_score,
  
  -- Lease Metrics
  total_active_leases,
  leases_expiring_soon,
  high_risk_renewals,
  round(avg_monthly_rent, 2) as avg_monthly_rent,
  
  -- Composite Score and Tier
  round(composite_performance_score, 1) as composite_performance_score,
  performance_tier,
  
  -- Peer Comparison
  rank_within_type,
  performance_quartile,
  peer_group_size,
  
  case
    when performance_quartile = 1 then 'TOP_QUARTILE'
    when performance_quartile = 2 then 'SECOND_QUARTILE'
    when performance_quartile = 3 then 'THIRD_QUARTILE'
    else 'BOTTOM_QUARTILE'
  end as quartile_label,
  
  -- Alert Flags
  flag_high_maintenance_burden,
  flag_critical_work_orders,
  flag_lease_renewal_risk,
  flag_low_profitability,
  flag_occupancy_concern,
  flag_budget_miss,
  flag_underperformer,
  
  -- Alert Count
  (flag_high_maintenance_burden::int +
   flag_critical_work_orders::int +
   flag_lease_renewal_risk::int +
   flag_low_profitability::int +
   flag_occupancy_concern::int +
   flag_budget_miss::int +
   flag_underperformer::int) as alert_count,
  
  processed_date
  
from with_flags
order by composite_performance_score desc
