/*
========================================
DIMENSION: Properties
========================================
Purpose:
  Enriched property dimension table providing consistent property context
  for all fact tables. Contains slowly-changing dimension attributes
  (SCD Type 1) for property characteristics and management hierarchy.

Key Attributes:
  - Property identifiers and names
  - Location details (address, coordinates, geography)
  - Property characteristics (type, size, age, units)
  - Financial attributes (market value, purchase price)
  - Organizational hierarchy (owner, asset manager)
  - Data quality and lineage flags

Grain:
  One row per unique property with current attributes

Use Cases:
  - Filter fact tables by property characteristics
  - Drill-down from portfolio to property level
  - Property-level dimensional analysis
========================================
*/

with cleaned_properties as (
  select distinct
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
    property_age_years,
    acquisition_date,
    is_multifamily,
    current_market_value,
    purchase_price,
    owner_id,
    asset_manager_id,
    property_status,
    data_quality_flag,
    
    -- Geospatial Attributes
    case
      when state_province in ('CA', 'NY', 'TX', 'FL') then 'HIGH_VALUE_STATE'
      when state_province in ('IL', 'PA', 'OH', 'GA') then 'MID_TIER_STATE'
      else 'GROWTH_MARKET_STATE'
    end as market_tier,
    
    -- Property Lifecycle Stage
    case
      when property_age_years is null then 'UNKNOWN'
      when property_age_years < 5 then 'NEW'
      when property_age_years < 15 then 'STABILIZED'
      when property_age_years < 25 then 'MATURE'
      else 'LEGACY'
    end as property_lifecycle_stage,
    
    -- Investment Class
    case
      when property_type in ('Luxury', 'Premium') then 'CLASS_A'
      when property_type in ('Standard', 'Mid-Market') then 'CLASS_B'
      else 'CLASS_C'
    end as investment_class,
    
    -- Size Category
    case
      when total_units >= 200 then 'LARGE'
      when total_units >= 50 then 'MEDIUM'
      when total_units >= 20 then 'SMALL'
      else 'BOUTIQUE'
    end as property_size_category,
    
    row_number() over (partition by property_id order by updated_at desc) as recency_rank
    
  from {{ ref('stg_properties') }}
)

select
  property_id,
  property_name,
  property_type,
  investment_class,
  
  -- Location
  street_address,
  city,
  state_province,
  postal_code,
  country,
  latitude,
  longitude,
  market_tier,
  
  -- Physical Characteristics
  total_units,
  total_square_feet,
  property_size_category,
  year_built,
  property_age_years,
  property_lifecycle_stage,
  is_multifamily,
  
  -- Dates
  acquisition_date,
  
  -- Financial
  current_market_value,
  purchase_price,
  case
    when purchase_price > 0 and current_market_value > 0
    then round(((current_market_value - purchase_price) / purchase_price) * 100, 2)
    else 0.00
  end as appreciation_percent,
  
  -- Organizational
  owner_id,
  asset_manager_id,
  
  -- Status and Quality
  property_status,
  data_quality_flag,
  
  -- Metadata
  current_date() as dimension_date,
  'CURRENT' as record_type
  
from cleaned_properties
where recency_rank = 1
  and property_id is not null
  
order by property_name
