/*
========================================
STAGING: Leases
========================================
Purpose:
  Clean and standardize lease agreement data. This model enriches lease
  records with calculated financial metrics and renewal risk indicators
  to support portfolio occupancy and revenue analysis.

Key Transformations:
  - Type cast dates and numeric fields
  - Calculate months remaining until lease expiration
  - Identify leases expiring within 90 days (renewal risk)
  - Compute rent per square foot (normalized pricing metric)
  - Calculate annual rent from monthly lease terms
  - Flag problematic leases (expired, high vacancy risk)

Business Rules:
  - Months remaining calculated from today to lease end date
  - Expiring soon = lease expires within 90 days
  - Rent PSF = monthly rent / total square feet / 12 months (annualized)
  - Only include active leases (status != 'EXPIRED' AND status != 'TERMINATED')
========================================
*/

with raw_leases as (
  select
    lease_id,
    property_id,
    unit_id,
    tenant_id,
    lease_start_date,
    lease_end_date,
    monthly_rent,
    deposit,
    status,
    lease_type,
    square_footage,
    created_at,
    updated_at
  from {{ source('raw', 'leases') }}
),

cleaned as (
  select
    -- Primary Key
    lease_id::varchar as lease_id,
    
    -- Foreign Keys
    property_id::varchar as property_id,
    unit_id::varchar as unit_id,
    tenant_id::varchar as tenant_id,
    
    -- Dates
    lease_start_date::date as lease_start_date,
    lease_end_date::date as lease_end_date,
    created_at::timestamp as created_at,
    updated_at::timestamp as updated_at,
    
    -- Financial Terms
    coalesce(monthly_rent::decimal(10,2), 0.00) as monthly_rent,
    coalesce(deposit::decimal(10,2), 0.00) as deposit,
    coalesce(square_footage::integer, 0) as square_footage,
    
    -- Lease Type and Status
    lease_type::varchar as lease_type,
    coalesce(status::varchar, 'UNKNOWN') as lease_status,
    
    -- Calculated Metrics
    datediff(month, current_date(), lease_end_date) as months_remaining,
    
    case
      when datediff(month, current_date(), lease_end_date) <= 0 then 'EXPIRED'
      when datediff(month, current_date(), lease_end_date) <= 3 then 'EXPIRING_SOON'
      when datediff(month, current_date(), lease_end_date) <= 6 then 'UPCOMING_RENEWAL'
      else 'CURRENT'
    end as renewal_status,
    
    case
      when datediff(day, current_date(), lease_end_date) <= 90 then true
      else false
    end as is_expiring_soon,
    
    case
      when square_footage > 0
      then (monthly_rent / square_footage) * 12
      else 0.00
    end as annual_rent_per_sqft,
    
    monthly_rent * 12 as annual_rent,
    
    case
      when lease_end_date < current_date() then 'RISK_HIGH'
      when datediff(day, current_date(), lease_end_date) <= 90 then 'RISK_MEDIUM'
      when datediff(day, current_date(), lease_end_date) <= 180 then 'RISK_LOW'
      else 'RISK_NONE'
    end as renewal_risk_category,
    
    current_date() as snapshot_date
    
  from raw_leases
  where status not in ('TERMINATED', 'CANCELLED')
    and lease_id is not null
)

select * from cleaned
