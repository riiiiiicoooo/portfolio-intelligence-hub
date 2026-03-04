/*
========================================
CUSTOM DATA TEST: NOI Component Validation
========================================
Purpose:
  Data quality test that validates NOI calculations across the portfolio.
  Ensures that calculated NOI equals sum of income components minus expenses.

Test Logic:
  For each financial record, verify:
  actual_noi = gross_rental_income + other_income - vacancy_loss - total_operating_expenses
  
  Within tolerance of $1 to account for rounding differences

Scope:
  Tests against stg_financials model where data quality is verified

Pass Condition:
  Zero rows returned (no exceptions found)

Fail Condition:
  Returns financial records where NOI calculation variance > $1
========================================
*/

select
  property_id,
  reporting_period,
  gross_rental_income,
  other_income,
  vacancy_loss,
  total_operating_expenses,
  actual_noi,
  
  -- Calculate expected NOI
  (gross_rental_income + other_income - vacancy_loss - total_operating_expenses) as expected_noi,
  
  -- Calculate variance
  abs(actual_noi - (gross_rental_income + other_income - vacancy_loss - total_operating_expenses)) as noi_variance
  
from {{ ref('stg_financials') }}

where abs(actual_noi - (gross_rental_income + other_income - vacancy_loss - total_operating_expenses)) > 1.00
  and actual_noi is not null
  
order by noi_variance desc
