/*
========================================
STAGING: Financials
========================================
Purpose:
  Standardize and clean property-level financial statements. This model
  processes income and expense data to calculate profitability metrics,
  budget variance, and operational efficiency ratios used in KPI analysis.

Key Transformations:
  - Type cast all monetary values to decimal(15,2)
  - Calculate NOI (Net Operating Income) from components
  - Compute NOI margin and budget variance percentages
  - Normalize revenue items (rents, fees, other income)
  - Categorize expense types for detailed analysis
  - Flag unusual variances for management review

Business Rules:
  - NOI = Gross Rental Income + Other Income - Vacancy Loss - Total Operating Expenses
  - NOI Margin = NOI / Effective Gross Income (EGI)
  - Budget Variance % = (Actual NOI - Budget NOI) / Budget NOI
  - Variance > 10% flagged for review
  - Period identified from financial reporting date
========================================
*/

with raw_financials as (
  select
    financial_id,
    property_id,
    reporting_period,
    gross_rental_income,
    other_income,
    vacancy_loss,
    total_operating_expenses,
    budget_noi,
    maintenance_expense,
    utilities_expense,
    management_expense,
    insurance_expense,
    property_tax_expense,
    created_at,
    updated_at
  from {{ source('raw', 'financials') }}
),

cleaned as (
  select
    -- Primary Key
    financial_id::varchar as financial_id,
    
    -- Foreign Key
    property_id::varchar as property_id,
    
    -- Period
    reporting_period::date as reporting_period,
    to_char(reporting_period, 'YYYY-MM') as period_key,
    created_at::timestamp as created_at,
    updated_at::timestamp as updated_at,
    
    -- Revenue Components
    coalesce(gross_rental_income::decimal(15,2), 0.00) as gross_rental_income,
    coalesce(other_income::decimal(15,2), 0.00) as other_income,
    coalesce(vacancy_loss::decimal(15,2), 0.00) as vacancy_loss,
    
    -- Effective Gross Income
    (coalesce(gross_rental_income::decimal(15,2), 0.00) + 
     coalesce(other_income::decimal(15,2), 0.00) - 
     coalesce(vacancy_loss::decimal(15,2), 0.00)) as effective_gross_income,
    
    -- Operating Expenses (by category)
    coalesce(total_operating_expenses::decimal(15,2), 0.00) as total_operating_expenses,
    coalesce(maintenance_expense::decimal(15,2), 0.00) as maintenance_expense,
    coalesce(utilities_expense::decimal(15,2), 0.00) as utilities_expense,
    coalesce(management_expense::decimal(15,2), 0.00) as management_expense,
    coalesce(insurance_expense::decimal(15,2), 0.00) as insurance_expense,
    coalesce(property_tax_expense::decimal(15,2), 0.00) as property_tax_expense,
    
    -- Budget Figures
    coalesce(budget_noi::decimal(15,2), 0.00) as budget_noi,
    
    -- Calculated NOI
    (coalesce(gross_rental_income::decimal(15,2), 0.00) + 
     coalesce(other_income::decimal(15,2), 0.00) - 
     coalesce(vacancy_loss::decimal(15,2), 0.00) - 
     coalesce(total_operating_expenses::decimal(15,2), 0.00)) as actual_noi,
    
    -- NOI Margin Calculation
    case
      when (coalesce(gross_rental_income::decimal(15,2), 0.00) + 
            coalesce(other_income::decimal(15,2), 0.00) - 
            coalesce(vacancy_loss::decimal(15,2), 0.00)) > 0
      then ((coalesce(gross_rental_income::decimal(15,2), 0.00) + 
             coalesce(other_income::decimal(15,2), 0.00) - 
             coalesce(vacancy_loss::decimal(15,2), 0.00) - 
             coalesce(total_operating_expenses::decimal(15,2), 0.00)) / 
            (coalesce(gross_rental_income::decimal(15,2), 0.00) + 
             coalesce(other_income::decimal(15,2), 0.00) - 
             coalesce(vacancy_loss::decimal(15,2), 0.00))) * 100
      else 0.00
    end as noi_margin_percent,
    
    -- Budget Variance
    case
      when coalesce(budget_noi::decimal(15,2), 0.00) != 0
      then (((coalesce(gross_rental_income::decimal(15,2), 0.00) + 
              coalesce(other_income::decimal(15,2), 0.00) - 
              coalesce(vacancy_loss::decimal(15,2), 0.00) - 
              coalesce(total_operating_expenses::decimal(15,2), 0.00)) - 
             coalesce(budget_noi::decimal(15,2), 0.00)) / 
            coalesce(budget_noi::decimal(15,2), 0.00)) * 100
      else 0.00
    end as budget_variance_pct,
    
    -- Variance Flag
    case
      when abs(((coalesce(gross_rental_income::decimal(15,2), 0.00) + 
                 coalesce(other_income::decimal(15,2), 0.00) - 
                 coalesce(vacancy_loss::decimal(15,2), 0.00) - 
                 coalesce(total_operating_expenses::decimal(15,2), 0.00)) - 
                coalesce(budget_noi::decimal(15,2), 0.00)) / 
               nullif(coalesce(budget_noi::decimal(15,2), 0.00), 0)) > 0.10
      then true
      else false
    end as variance_exceeds_threshold,
    
    current_date() as snapshot_date
    
  from raw_financials
  where property_id is not null
)

select * from cleaned
