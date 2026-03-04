/*
========================================
MACRO: Period-over-Period Analysis
========================================
Purpose:
  Reusable macro for calculating period-over-period (MoM, YoY) metrics using
  LAG window functions. Enables consistent trend analysis across multiple
  KPI models without duplicating window logic.

Parameters:
  - measure_col: Column name containing the metric to compare
  - partition_cols: List of columns to partition by (e.g., property_id)
  - order_cols: List of columns for ordering (e.g., reporting_period)
  - periods_back: Number of periods to lag (default 1 for MoM)

Returns:
  Two-column set with absolute change and percentage change

Usage:
  select
    property_id,
    reporting_period,
    noi,
    {{ period_over_period('noi', ['property_id'], ['reporting_period'], 1) }}
  from financials
========================================
*/

{% macro period_over_period(
  measure_col,
  partition_cols,
  order_cols,
  periods_back = 1
) %}

  -- Calculate absolute change
  {{ measure_col }} - 
  lag({{ measure_col }}) over (
    partition by {{ partition_cols | join(', ') }}
    order by {{ order_cols | join(', ') }}
    rows between {{ periods_back }} preceding and current row
  ) as {{ measure_col }}_change,
  
  -- Calculate percentage change
  case
    when lag({{ measure_col }}) over (
      partition by {{ partition_cols | join(', ') }}
      order by {{ order_cols | join(', ') }}
      rows between {{ periods_back }} preceding and current row
    ) != 0
    then ({{ measure_col }} - 
          lag({{ measure_col }}) over (
            partition by {{ partition_cols | join(', ') }}
            order by {{ order_cols | join(', ') }}
            rows between {{ periods_back }} preceding and current row
          )) / lag({{ measure_col }}) over (
      partition by {{ partition_cols | join(', ') }}
      order by {{ order_cols | join(', ') }}
      rows between {{ periods_back }} preceding and current row
    ) * 100
    else 0.00
  end as {{ measure_col }}_change_pct

{% endmacro %}
