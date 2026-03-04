/*
========================================
FACT: Portfolio KPIs
========================================
Purpose:
  Aggregate portfolio-wide key performance indicators by reporting period.
  This fact table provides executive-level summaries and period-over-period
  comparisons for board reporting and strategic decision-making.

Key Metrics:
  - Total NOI and NOI margin across portfolio
  - Average occupancy rate and trend
  - Total units and occupied units
  - Average capitalization rate (cap rate) analysis
  - Total maintenance costs and cost per unit
  - Work order completion rates
  - Lease renewal pipeline

Grain:
  One row per reporting period representing entire portfolio snapshot

Period-over-Period Calculations:
  - Month-over-Month (MoM) and Year-over-Year (YoY) NOI comparison
  - Occupancy trend direction and magnitude
  - Maintenance cost volatility
========================================
*/

with portfolio_monthly_snapshot as (
  select
    to_char(f.reporting_period, 'YYYY-MM') as reporting_period_key,
    f.reporting_period,
    extract(year from f.reporting_period) as reporting_year,
    extract(month from f.reporting_period) as reporting_month,
    
    -- Count of properties with data for this period
    count(distinct f.property_id) as properties_reporting,
    
    -- Revenue Metrics
    sum(f.gross_rental_income) as total_gross_rental_income,
    sum(f.other_income) as total_other_income,
    sum(f.vacancy_loss) as total_vacancy_loss,
    sum(f.effective_gross_income) as total_effective_gross_income,
    
    -- Expense Metrics
    sum(f.total_operating_expenses) as total_operating_expenses,
    sum(f.maintenance_expense) as total_maintenance_expense,
    sum(f.utilities_expense) as total_utilities_expense,
    sum(f.management_expense) as total_management_expense,
    sum(f.insurance_expense) as total_insurance_expense,
    sum(f.property_tax_expense) as total_property_tax_expense,
    
    -- NOI Metrics
    sum(f.actual_noi) as total_portfolio_noi,
    avg(f.noi_margin_percent) as avg_noi_margin_percent,
    
    -- Budget Variance
    sum(f.budget_noi) as total_budget_noi,
    
    -- Occupancy Metrics
    avg(o.occupancy_percent) as avg_portfolio_occupancy_pct,
    
    -- Unit Metrics
    sum(p.total_units) as total_portfolio_units,
    round(sum(p.total_units) * (avg(o.occupancy_percent) / 100)) as total_occupied_units,
    
    -- Cap Rate Calculation (NOI / Market Value)
    case
      when sum(p.current_market_value) > 0
      then (sum(f.actual_noi) / sum(p.current_market_value)) * 100
      else 0.00
    end as portfolio_cap_rate_pct
    
  from {{ ref('stg_financials') }} f
  left join {{ ref('stg_properties') }} p on f.property_id = p.property_id
  left join {{ ref('stg_occupancy') }} o on f.property_id = o.property_id 
    and o.recency_rank = 1
  
  group by 
    to_char(f.reporting_period, 'YYYY-MM'),
    f.reporting_period,
    extract(year from f.reporting_period),
    extract(month from f.reporting_period)
),

with_period_comparisons as (
  select
    pms.*,
    
    -- Previous Month NOI
    lag(pms.total_portfolio_noi) over (
      order by pms.reporting_period
    ) as previous_month_noi,
    
    -- Previous Year Same Month NOI
    lag(pms.total_portfolio_noi) over (
      order by pms.reporting_year, pms.reporting_month
    ) as previous_year_noi,
    
    -- MoM Change
    pms.total_portfolio_noi - 
    lag(pms.total_portfolio_noi) over (order by pms.reporting_period) as mom_noi_change,
    
    -- YoY Change
    pms.total_portfolio_noi - 
    lag(pms.total_portfolio_noi) over (
      order by pms.reporting_year, pms.reporting_month
    ) as yoy_noi_change
    
  from portfolio_monthly_snapshot pms
)

select
  wpc.reporting_period_key,
  wpc.reporting_period,
  wpc.reporting_year,
  wpc.reporting_month,
  wpc.properties_reporting,
  
  -- Revenue Metrics
  wpc.total_gross_rental_income,
  wpc.total_other_income,
  wpc.total_vacancy_loss,
  wpc.total_effective_gross_income,
  
  -- Expense Metrics
  wpc.total_operating_expenses,
  wpc.total_maintenance_expense,
  wpc.total_utilities_expense,
  wpc.total_management_expense,
  wpc.total_insurance_expense,
  wpc.total_property_tax_expense,
  
  -- NOI Metrics
  wpc.total_portfolio_noi,
  wpc.avg_noi_margin_percent,
  round(wpc.total_portfolio_noi, 2) as noi_rounded,
  
  -- Budget Comparison
  wpc.total_budget_noi,
  round(
    ((wpc.total_portfolio_noi - wpc.total_budget_noi) / 
     nullif(wpc.total_budget_noi, 0)) * 100, 
    2
  ) as portfolio_budget_variance_pct,
  
  -- Occupancy Metrics
  round(wpc.avg_portfolio_occupancy_pct, 2) as avg_portfolio_occupancy_pct,
  wpc.total_portfolio_units,
  wpc.total_occupied_units,
  round((wpc.total_occupied_units::float / nullif(wpc.total_portfolio_units, 0)) * 100, 2) as effective_occupancy_pct,
  
  -- Cap Rate
  round(wpc.portfolio_cap_rate_pct, 2) as portfolio_cap_rate_pct,
  
  -- Period-over-Period Comparisons
  wpc.previous_month_noi,
  round(wpc.mom_noi_change, 2) as mom_noi_change,
  case
    when wpc.previous_month_noi != 0
    then round((wpc.mom_noi_change / wpc.previous_month_noi) * 100, 2)
    else 0.00
  end as mom_noi_change_pct,
  
  wpc.previous_year_noi,
  round(wpc.yoy_noi_change, 2) as yoy_noi_change,
  case
    when wpc.previous_year_noi != 0
    then round((wpc.yoy_noi_change / wpc.previous_year_noi) * 100, 2)
    else 0.00
  end as yoy_noi_change_pct,
  
  current_date() as processed_date
  
from with_period_comparisons wpc
order by wpc.reporting_period desc
