/*
========================================
STAGING: Work Orders
========================================
Purpose:
  Standardize and clean work order maintenance data. This model tracks
  maintenance activities across the portfolio and calculates operational
  efficiency metrics like time-to-completion and priority scoring.

Key Transformations:
  - Type cast date and numeric fields
  - Standardize priority levels to numeric scores for analytics
  - Calculate days open (time from request to completion/current date)
  - Filter active and in-progress work orders
  - Compute cost per day of work

Business Rules:
  - Priority scoring: Critical=4, High=3, Medium=2, Low=1
  - Days open calculated to current date if not yet completed
  - Only include non-cancelled work orders
  - Cost estimates are in USD
========================================
*/

with raw_work_orders as (
  select
    work_order_id,
    property_id,
    requested_date,
    completed_date,
    priority_level,
    category,
    description,
    estimated_cost,
    actual_cost,
    assigned_to_id,
    status,
    notes,
    created_at,
    updated_at
  from {{ source('raw', 'work_orders') }}
),

cleaned as (
  select
    -- Primary Key
    work_order_id::varchar as work_order_id,
    
    -- Foreign Keys
    property_id::varchar as property_id,
    assigned_to_id::varchar as assigned_to_id,
    
    -- Dates
    requested_date::date as requested_date,
    completed_date::date as completed_date,
    created_at::timestamp as created_at,
    updated_at::timestamp as updated_at,
    
    -- Category and Status
    category::varchar as category,
    coalesce(status::varchar, 'UNKNOWN') as work_order_status,
    
    -- Description
    description::varchar as description,
    notes::varchar as notes,
    
    -- Financial Attributes
    coalesce(estimated_cost::decimal(10,2), 0.00) as estimated_cost,
    coalesce(actual_cost::decimal(10,2), 0.00) as actual_cost,
    
    -- Priority Scoring
    case
      when upper(priority_level) = 'CRITICAL' then 4
      when upper(priority_level) = 'HIGH' then 3
      when upper(priority_level) = 'MEDIUM' then 2
      when upper(priority_level) = 'LOW' then 1
      else 0
    end as priority_score,
    
    upper(priority_level) as priority_level,
    
    -- Operational Metrics
    datediff(day, requested_date, coalesce(completed_date, current_date())) as days_open,
    
    case
      when actual_cost > 0 and datediff(day, requested_date, coalesce(completed_date, current_date())) > 0
      then actual_cost / datediff(day, requested_date, coalesce(completed_date, current_date()))
      else 0.00
    end as cost_per_day,
    
    case
      when completed_date is not null and datediff(day, requested_date, completed_date) <= 7 then true
      else false
    end as was_completed_timely,
    
    current_date() as snapshot_date
    
  from raw_work_orders
  where status not in ('CANCELLED', 'DELETED')
    and work_order_id is not null
)

select * from cleaned
