/*
========================================
INTERMEDIATE: Property Performance
========================================
Purpose:
  Aggregate property-level operational and financial metrics into a
  comprehensive performance view. This model joins staging tables to create
  a single enriched dataset used by downstream mart models.

Key Transformations:
  - Join properties with latest financial and occupancy snapshots
  - Calculate composite performance score from normalized metrics
  - Aggregate work order metrics by property
  - Calculate period-over-period changes for trending
  - Flag properties requiring management attention

Business Logic:
  - Performance score: (NOI_health * 0.40) + (Occupancy_health * 0.35) + (Maintenance_health * 0.25)
  - All components normalized to 0-100 scale
  - Latest records identified via row_number() window functions
========================================
*/

with property_base as (
  select distinct
    p.property_id,
    p.property_name,
    p.property_type,
    p.city,
    p.state_province,
    p.total_units,
    p.total_square_feet,
    p.is_multifamily,
    p.property_age_years,
    p.current_market_value,
    p.owner_id,
    p.asset_manager_id
  from {{ ref('stg_properties') }} p
),

latest_financials as (
  select
    property_id,
    reporting_period,
    gross_rental_income,
    actual_noi,
    noi_margin_percent,
    budget_variance_pct,
    total_operating_expenses,
    row_number() over (partition by property_id order by reporting_period desc) as fin_rank
  from {{ ref('stg_financials') }}
  where actual_noi is not null
),

latest_occupancy as (
  select
    property_id,
    snapshot_date,
    occupancy_percent,
    vacancy_rate,
    occupancy_health_status,
    row_number() over (partition by property_id order by snapshot_date desc) as occ_rank
  from {{ ref('stg_occupancy') }}
),

work_order_summary as (
  select
    property_id,
    count(*) as total_open_work_orders,
    count(case when priority_score = 4 then 1 end) as critical_work_orders,
    avg(days_open) as avg_days_to_complete,
    sum(actual_cost) as total_maintenance_cost
  from {{ ref('stg_work_orders') }}
  where work_order_status in ('OPEN', 'IN_PROGRESS')
  group by property_id
),

lease_summary as (
  select
    property_id,
    count(*) as total_active_leases,
    count(case when is_expiring_soon then 1 end) as leases_expiring_soon,
    count(case when renewal_risk_category = 'RISK_HIGH' then 1 end) as high_risk_renewals,
    avg(monthly_rent) as avg_monthly_rent
  from {{ ref('stg_leases') }}
  where lease_status in ('ACTIVE', 'CURRENT')
  group by property_id
),

performance_scoring as (
  select
    pb.property_id,
    pb.property_name,
    pb.property_type,
    pb.city,
    pb.state_province,
    pb.total_units,
    pb.total_square_feet,
    pb.is_multifamily,
    pb.property_age_years,
    pb.current_market_value,
    pb.owner_id,
    pb.asset_manager_id,
    
    -- Financial Metrics
    lf.reporting_period as latest_financial_period,
    lf.gross_rental_income,
    lf.actual_noi,
    lf.noi_margin_percent,
    lf.budget_variance_pct,
    lf.total_operating_expenses,
    
    -- NOI Health Score (0-100)
    case
      when lf.noi_margin_percent >= 40 then 100
      when lf.noi_margin_percent >= 35 then 85
      when lf.noi_margin_percent >= 30 then 70
      when lf.noi_margin_percent >= 25 then 55
      when lf.noi_margin_percent >= 20 then 40
      else 25
    end as noi_health_score,
    
    -- Occupancy Metrics
    lo.snapshot_date as latest_occupancy_date,
    lo.occupancy_percent,
    lo.vacancy_rate,
    lo.occupancy_health_status,
    
    -- Occupancy Health Score (0-100)
    case
      when lo.occupancy_percent >= 98 then 100
      when lo.occupancy_percent >= 95 then 85
      when lo.occupancy_percent >= 90 then 70
      when lo.occupancy_percent >= 85 then 50
      else 30
    end as occupancy_health_score,
    
    -- Work Order Metrics
    coalesce(wo.total_open_work_orders, 0) as total_open_work_orders,
    coalesce(wo.critical_work_orders, 0) as critical_work_orders,
    coalesce(wo.avg_days_to_complete, 0) as avg_days_to_complete,
    coalesce(wo.total_maintenance_cost, 0.00) as total_maintenance_cost,
    
    -- Maintenance Health Score (0-100)
    case
      when coalesce(wo.critical_work_orders, 0) > 0 then 40
      when coalesce(wo.total_open_work_orders, 0) = 0 then 100
      when coalesce(wo.total_open_work_orders, 0) <= 2 then 85
      when coalesce(wo.total_open_work_orders, 0) <= 5 then 70
      else 50
    end as maintenance_health_score,
    
    -- Lease Metrics
    coalesce(ls.total_active_leases, 0) as total_active_leases,
    coalesce(ls.leases_expiring_soon, 0) as leases_expiring_soon,
    coalesce(ls.high_risk_renewals, 0) as high_risk_renewals,
    coalesce(ls.avg_monthly_rent, 0.00) as avg_monthly_rent,
    
    current_date() as processed_date
    
  from property_base pb
  left join latest_financials lf on pb.property_id = lf.property_id and lf.fin_rank = 1
  left join latest_occupancy lo on pb.property_id = lo.property_id and lo.occ_rank = 1
  left join work_order_summary wo on pb.property_id = wo.property_id
  left join lease_summary ls on pb.property_id = ls.property_id
)

select
  *,
  -- Composite Performance Score
  round(
    (noi_health_score * 0.40) + 
    (occupancy_health_score * 0.35) + 
    (maintenance_health_score * 0.25),
    1
  ) as composite_performance_score,
  
  -- Performance Tier
  case
    when round((noi_health_score * 0.40) + (occupancy_health_score * 0.35) + (maintenance_health_score * 0.25), 1) >= 85 then 'EXCELLENT'
    when round((noi_health_score * 0.40) + (occupancy_health_score * 0.35) + (maintenance_health_score * 0.25), 1) >= 70 then 'GOOD'
    when round((noi_health_score * 0.40) + (occupancy_health_score * 0.35) + (maintenance_health_score * 0.25), 1) >= 55 then 'FAIR'
    else 'POOR'
  end as performance_tier
  
from performance_scoring
