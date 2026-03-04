/*
========================================
STAGING: Properties
========================================
Purpose:
  Clean and standardize raw property data from the source system. This model
  performs data validation, type casting, and column naming conventions to
  prepare property records for downstream analytics models.

Key Transformations:
  - Rename columns to snake_case for consistency
  - Cast numeric and date fields to appropriate types
  - Handle NULL values and apply business logic defaults
  - Filter out deleted and archived records
  - Compute derived attributes: property age and multifamily classification
  - Add data quality flags for monitoring data lineage

Business Rules:
  - Only include active properties (status != 'ARCHIVED' AND status != 'DELETED')
  - Property age calculated as years since acquisition
  - Multifamily flag based on unit count and property type
  - Revenue is in USD; standardized to cents where appropriate
========================================
*/

with raw_properties as (
  select
    property_id,
    property_name,
    property_type,
    street_address,
    city,
    state_province,
    postal_code,
    country,
    latitude,
    longitude,
    total_units,
    total_square_feet,
    year_built,
    acquisition_date,
    status,
    owner_id,
    asset_manager_id,
    current_market_value,
    purchase_price,
    created_at,
    updated_at
  from {{ source('raw', 'properties') }}
),

cleaned as (
  select
    -- Primary Key
    property_id::varchar as property_id,
    
    -- Property Identifiers
    property_name::varchar as property_name,
    property_type::varchar as property_type,
    
    -- Location Attributes
    street_address::varchar as street_address,
    city::varchar as city,
    state_province::varchar as state_province,
    postal_code::varchar as postal_code,
    country::varchar as country,
    coalesce(latitude::float, 0.0) as latitude,
    coalesce(longitude::float, 0.0) as longitude,
    
    -- Property Dimensions
    coalesce(total_units::integer, 0) as total_units,
    coalesce(total_square_feet::integer, 0) as total_square_feet,
    coalesce(year_built::integer, null) as year_built,
    
    -- Dates
    acquisition_date::date as acquisition_date,
    created_at::timestamp as created_at,
    updated_at::timestamp as updated_at,
    
    -- Financial Attributes
    coalesce(current_market_value::decimal(15,2), 0.00) as current_market_value,
    coalesce(purchase_price::decimal(15,2), 0.00) as purchase_price,
    
    -- Foreign Keys
    owner_id::varchar as owner_id,
    asset_manager_id::varchar as asset_manager_id,
    
    -- Status
    coalesce(status::varchar, 'UNKNOWN') as property_status,
    
    -- Derived Attributes
    case 
      when acquisition_date is not null 
      then datediff(year, acquisition_date, current_date())
      else null
    end as property_age_years,
    
    case 
      when coalesce(total_units, 0) >= 5 and property_type in ('Apartment', 'Multifamily', 'Townhome')
      then true
      else false
    end as is_multifamily,
    
    -- Data Quality Flag
    case
      when property_id is null or property_name is null then 'INVALID'
      when total_units <= 0 or total_square_feet <= 0 then 'INCOMPLETE'
      else 'VALID'
    end as data_quality_flag
    
  from raw_properties
  where status not in ('ARCHIVED', 'DELETED')
    and property_id is not null
)

select * from cleaned
