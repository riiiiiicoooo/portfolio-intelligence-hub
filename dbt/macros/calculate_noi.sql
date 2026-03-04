/*
========================================
MACRO: Calculate NOI
========================================
Purpose:
  Reusable macro for Net Operating Income calculation standardized across
  all financial analyses. Encapsulates business logic for NOI computation
  to ensure consistency and enable easy maintenance of calculation rules.

Parameters:
  - gross_rent_col: Column name for gross rental income
  - other_income_col: Column name for other income
  - vacancy_loss_col: Column name for vacancy loss
  - operating_expense_col: Column name for total operating expenses

Returns:
  Numeric expression calculating NOI = Gross Rent + Other Income - Vacancy Loss - Operating Expenses

Usage:
  select
    property_id,
    {{ calculate_noi('gross_rent', 'other_revenue', 'vacancy_loss', 'opex') }} as calculated_noi
  from table
========================================
*/

{% macro calculate_noi(
  gross_rent_col,
  other_income_col,
  vacancy_loss_col,
  operating_expense_col
) %}

  coalesce({{ gross_rent_col }}::decimal(15,2), 0.00) +
  coalesce({{ other_income_col }}::decimal(15,2), 0.00) -
  coalesce({{ vacancy_loss_col }}::decimal(15,2), 0.00) -
  coalesce({{ operating_expense_col }}::decimal(15,2), 0.00)

{% endmacro %}
