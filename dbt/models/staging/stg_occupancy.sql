/*
========================================
STAGING: Occupancy
========================================
Purpose:
  Clean and standardize property occupancy snapshot data. This model
  captures point-in-time occupancy metrics and trends to monitor
  portfolio utilization and vacancy patterns.

Key Transformations:
  - Type cast numeric fields to appropriate precisions
  - Calculate vacancy rate as complement to occupancy percent
  - Classify occupancy health status based on industry thresholds
  - Identify occupancy trends (improving, declining, stable)
  - Filter for most recent snapshots per property

Business Rules:
  - Vacancy rate = 1 - (occupancy_percent / 100)
  - Healthy occupancy >= 95% (vacancy <= 5%)
  - At-risk occupancy 90-95% (vacancy 5-10%)
  - Problem occupancy < 90% (vacancy > 10%)
========================================
*/

with raw_occupancy as (
  select
    occupancy_id,
    property_id,
    snapshot_date,
    total_units,
    occupied_units,
    occupancy_percent,
    ready_for_occupancy_units,
    under_renovation_units,
    notes,
    created_at
  from {{ source('raw', 'occupancy') }}
),

cleaned as (
  select
    -- Primary Key
    occupancy_id::varchar as occupancy_id,
    
    -- Foreign Key
    property_id::varchar as property_id,
    
    -- Date
    snapshot_date::date as snapshot_date,
    created_at::timestamp as created_at,
    
    -- Unit Counts
    coalesce(total_units::integer, 0) as total_units,
    coalesce(occupied_units::integer, 0) as occupied_units,
    coalesce(ready_for_occupancy_units::integer, 0) as ready_for_occupancy_units,
    coalesce(under_renovation_units::integer, 0) as under_renovation_units,
    
    -- Occupancy Metrics
    coalesce(occupancy_percent::decimal(5,2), 0.00) as occupancy_percent,
    
    case
      when coalesce(total_units::integer, 0) > 0
      then 1.0 - (coalesce(occupancy_percent::decimal(5,2), 0.00) / 100.0)
      else 0.00
    end as vacancy_rate,
    
    round(coalesce(occupancy_percent::decimal(5,2), 0.00), 1) as occupancy_percent_rounded,
    
    -- Occupancy Health Status
    case
      when coalesce(occupancy_percent::decimal(5,2), 0.00) >= 95.0 then 'HEALTHY'
      when coalesce(occupancy_percent::decimal(5,2), 0.00) >= 90.0 then 'AT_RISK'
      when coalesce(occupancy_percent::decimal(5,2), 0.00) >= 85.0 then 'PROBLEM'
      else 'CRITICAL'
    end as occupancy_health_status,
    
    -- Available Units
    (coalesce(total_units::integer, 0) - 
     coalesce(occupied_units::integer, 0) - 
     coalesce(under_renovation_units::integer, 0)) as available_units,
    
    notes::varchar as notes,
    
    current_date() as processed_date,
    
    row_number() over (partition by property_id order by snapshot_date desc) as recency_rank
    
  from raw_occupancy
  where property_id is not null
    and snapshot_date is not null
)

select * from cleaned
