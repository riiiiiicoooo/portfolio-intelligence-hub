"""Business metric definitions and semantic layer for real estate operations.

This module defines the universe of "approved" metrics that users can query and
provides schema information to the LLM during SQL generation. Instead of letting
Claude generate arbitrary SQL, we provide a controlled semantic layer.

PM Context: Real estate operators think in business metrics (NOI, occupancy rate,
cap rate, rent per sqft) not database columns (monthly_revenue, unit_count, sqft).
This layer maps business terminology to underlying SQL expressions while preventing
access to sensitive columns like tenant SSN or explicit rent amounts.

Design Philosophy:
- Metrics are composable (e.g., NOI = Gross Income - Operating Expenses)
- Each metric has canonical SQL expression for Snowflake
- Tables and columns are whitelisted (APPROVED_TABLES)
- Business terms like "vacancy" resolve to actual columns
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class MetricDefinition:
    """Definition of a business metric available for querying.
    
    Attributes:
        name: Programmatic name (snake_case, used in API)
        display_name: User-friendly name for UI
        sql_expression: Snowflake SQL snippet (parameterized with {column} placeholders)
        tables_required: List of base tables needed for this metric
        description: User-facing description of what this metric means
        unit: Unit of measurement ('pct', 'usd', 'count', 'day', etc.)
        aggregation: Default aggregation for timeseries (avg, sum, max, etc.)
        formula: LaTeX or text explanation of the calculation
    
    Example:
        occupancy = MetricDefinition(
            name="occupancy_rate",
            display_name="Occupancy Rate",
            sql_expression="(COALESCE(occupied_units, 0) / NULLIF(total_units, 0)) * 100",
            tables_required=["properties", "units"],
            description="Percentage of units occupied",
            unit="pct",
            aggregation="avg",
            formula="Occupied Units / Total Units * 100"
        )
    """
    name: str
    display_name: str
    sql_expression: str
    tables_required: List[str]
    description: str
    unit: str
    aggregation: str = "avg"
    formula: str = ""


# Approved list of tables accessible through semantic layer
APPROVED_TABLES = [
    "properties",
    "units",
    "leases",
    "rent_collections",
    "work_orders",
    "maintenance",
    "financials",
    "budgets",
    "tenants",
]

# Metric registry: Comprehensive set of real estate KPIs
# Each metric is independently defined with full SQL expression and metadata
METRIC_REGISTRY: Dict[str, MetricDefinition] = {
    
    "noi": MetricDefinition(
        name="noi",
        display_name="Net Operating Income",
        sql_expression="(gross_rent_income + other_income) - operating_expenses",
        tables_required=["financials"],
        description="Total property revenue minus operating expenses, excluding debt service",
        unit="usd",
        aggregation="sum",
        formula="(Gross Rent Income + Other Income) - Operating Expenses"
    ),
    
    "occupancy_rate": MetricDefinition(
        name="occupancy_rate",
        display_name="Occupancy Rate",
        sql_expression="(COALESCE(occupied_units, 0) / NULLIF(total_units, 0)) * 100",
        tables_required=["properties", "units"],
        description="Percentage of units occupied vs total",
        unit="pct",
        aggregation="avg",
        formula="Occupied Units / Total Units * 100"
    ),
    
    "cap_rate": MetricDefinition(
        name="cap_rate",
        display_name="Capitalization Rate",
        sql_expression="(noi / property_value) * 100",
        tables_required=["financials", "properties"],
        description="Annual NOI divided by property value, metric for return on investment",
        unit="pct",
        aggregation="avg",
        formula="NOI / Property Value * 100"
    ),
    
    "rent_per_sqft": MetricDefinition(
        name="rent_per_sqft",
        display_name="Rent per Square Foot",
        sql_expression="COALESCE(annual_rent, 0) / NULLIF(total_sqft, 0)",
        tables_required=["properties", "leases"],
        description="Average annual rent divided by total rentable square feet",
        unit="usd",
        aggregation="avg",
        formula="Annual Rent / Total Square Feet"
    ),
    
    "maintenance_cost_per_unit": MetricDefinition(
        name="maintenance_cost_per_unit",
        display_name="Maintenance Cost Per Unit",
        sql_expression="maintenance_costs / NULLIF(total_units, 0)",
        tables_required=["maintenance", "properties"],
        description="Total maintenance spending divided by number of units",
        unit="usd",
        aggregation="sum",
        formula="Total Maintenance Costs / Total Units"
    ),
    
    "vacancy_rate": MetricDefinition(
        name="vacancy_rate",
        display_name="Vacancy Rate",
        sql_expression="(COALESCE(vacant_units, 0) / NULLIF(total_units, 0)) * 100",
        tables_required=["properties", "units"],
        description="Percentage of units unoccupied",
        unit="pct",
        aggregation="avg",
        formula="Vacant Units / Total Units * 100"
    ),
    
    "collections_rate": MetricDefinition(
        name="collections_rate",
        display_name="Rent Collections Rate",
        sql_expression="(rent_collected / NULLIF(rent_due, 0)) * 100",
        tables_required=["rent_collections"],
        description="Percentage of rent due that was actually collected",
        unit="pct",
        aggregation="avg",
        formula="Rent Collected / Rent Due * 100"
    ),
    
    "budget_variance": MetricDefinition(
        name="budget_variance",
        display_name="Budget Variance",
        sql_expression="((actual_expenses - budgeted_expenses) / NULLIF(budgeted_expenses, 0)) * 100",
        tables_required=["financials", "budgets"],
        description="Percentage difference between actual and budgeted expenses (negative is favorable)",
        unit="pct",
        aggregation="avg",
        formula="(Actual - Budgeted) / Budgeted * 100"
    ),
    
    "avg_days_overdue": MetricDefinition(
        name="avg_days_overdue",
        display_name="Average Days Rent Overdue",
        sql_expression="AVG(DATEDIFF(day, due_date, CURRENT_DATE()))",
        tables_required=["rent_collections"],
        description="Average number of days past due for delinquent rent accounts",
        unit="day",
        aggregation="avg",
        formula="Average(Current Date - Due Date)"
    ),
    
    "tenant_turnover": MetricDefinition(
        name="tenant_turnover",
        display_name="Tenant Turnover Rate",
        sql_expression="(lease_ends_this_period / NULLIF(avg_occupied_units, 0)) * 100",
        tables_required=["leases", "units"],
        description="Percentage of occupied units with leases ending",
        unit="pct",
        aggregation="sum",
        formula="Leases Ending This Period / Avg Occupied Units * 100"
    ),
    
    "renewal_rate": MetricDefinition(
        name="renewal_rate",
        display_name="Lease Renewal Rate",
        sql_expression="(renewed_leases / NULLIF(leases_expiring, 0)) * 100",
        tables_required=["leases"],
        description="Percentage of expiring leases that are renewed",
        unit="pct",
        aggregation="sum",
        formula="Renewed Leases / Leases Expiring * 100"
    ),
    
    "effective_gross_income": MetricDefinition(
        name="effective_gross_income",
        display_name="Effective Gross Income",
        sql_expression="(gross_rent_income * (collections_rate / 100)) + other_income",
        tables_required=["financials"],
        description="Gross rent income adjusted for actual collections plus other income",
        unit="usd",
        aggregation="sum",
        formula="(Gross Rent * Collections Rate%) + Other Income"
    ),
    
    "operating_expense_ratio": MetricDefinition(
        name="operating_expense_ratio",
        display_name="Operating Expense Ratio",
        sql_expression="(operating_expenses / gross_rent_income) * 100",
        tables_required=["financials"],
        description="Operating expenses as percentage of gross rent income",
        unit="pct",
        aggregation="avg",
        formula="Operating Expenses / Gross Rent Income * 100"
    ),
    
    "debt_coverage_ratio": MetricDefinition(
        name="debt_coverage_ratio",
        display_name="Debt Service Coverage Ratio",
        sql_expression="noi / debt_service",
        tables_required=["financials"],
        description="NOI divided by annual debt service, measures ability to service debt",
        unit="ratio",
        aggregation="avg",
        formula="NOI / Annual Debt Service"
    ),
    
    "gross_rent_multiplier": MetricDefinition(
        name="gross_rent_multiplier",
        display_name="Gross Rent Multiplier",
        sql_expression="property_value / annual_gross_rent",
        tables_required=["properties", "financials"],
        description="Property value divided by annual gross rent, valuation metric",
        unit="ratio",
        aggregation="avg",
        formula="Property Value / Annual Gross Rent"
    ),
}


def get_metric(name: str) -> Optional[MetricDefinition]:
    """Retrieve a metric definition by name.
    
    Args:
        name: Metric name (snake_case) from METRIC_REGISTRY keys
    
    Returns:
        MetricDefinition or None if not found
    
    Example:
        >>> metric = get_metric("occupancy_rate")
        >>> print(f"Formula: {metric.formula}")
        >>> print(f"SQL: {metric.sql_expression}")
    """
    metric = METRIC_REGISTRY.get(name)
    if not metric:
        logger.warning(f"Metric '{name}' not found in registry")
        return None
    return metric


def get_approved_tables() -> List[str]:
    """Get list of all Snowflake tables accessible through semantic layer.
    
    Returns:
        List of approved table names
    
    Note:
        Only these tables should appear in generated SQL. Acts as a whitelist
        to prevent queries accessing sensitive tables not in this list.
    
    Example:
        >>> tables = get_approved_tables()
        >>> assert all(t in tables for t in ["properties", "leases"])
    """
    return APPROVED_TABLES.copy()


def get_table_schema(table_name: str) -> Dict[str, Any]:
    """Get column schema for a Snowflake table.
    
    Used to populate Claude context during SQL generation.
    
    Args:
        table_name: Name of table in Snowflake
    
    Returns:
        Dict with schema info:
        {
            'table_name': str,
            'columns': [
                {
                    'name': str,
                    'type': str,
                    'description': str,
                    'nullable': bool,
                    'example': str
                },
                ...
            ]
        }
    
    Example:
        >>> schema = get_table_schema("properties")
        >>> for col in schema['columns']:
        ...     print(f"{col['name']}: {col['type']}")
    
    Note:
        This is hardcoded reference schema. In production, this would query
        Snowflake's INFORMATION_SCHEMA to stay in sync with actual schema.
    """
    schemas = {
        "properties": {
            "table_name": "properties",
            "columns": [
                {"name": "property_id", "type": "VARCHAR", "description": "Unique property identifier", "nullable": False, "example": "PROP_001"},
                {"name": "property_name", "type": "VARCHAR", "description": "Property display name", "nullable": False, "example": "Acme Plaza"},
                {"name": "address", "type": "VARCHAR", "description": "Street address", "nullable": False, "example": "123 Main St"},
                {"name": "city", "type": "VARCHAR", "description": "City", "nullable": False, "example": "New York"},
                {"name": "state", "type": "VARCHAR", "description": "State abbreviation", "nullable": False, "example": "NY"},
                {"name": "zip_code", "type": "VARCHAR", "description": "Zip code", "nullable": True, "example": "10001"},
                {"name": "property_type", "type": "VARCHAR", "description": "Type (Apartment, Office, Retail, etc.)", "nullable": False, "example": "Apartment"},
                {"name": "total_units", "type": "NUMBER", "description": "Total number of units", "nullable": False, "example": "50"},
                {"name": "total_sqft", "type": "NUMBER", "description": "Total rentable square feet", "nullable": False, "example": "50000"},
                {"name": "year_built", "type": "NUMBER", "description": "Year property was constructed", "nullable": True, "example": "1995"},
                {"name": "property_value", "type": "NUMBER", "description": "Current assessed/appraised value", "nullable": True, "example": "5000000"},
                {"name": "tenant_id", "type": "VARCHAR", "description": "Multi-tenant isolation key", "nullable": False, "example": "TENANT_001"},
            ]
        },
        "units": {
            "table_name": "units",
            "columns": [
                {"name": "unit_id", "type": "VARCHAR", "description": "Unique unit identifier", "nullable": False, "example": "PROP_001_101"},
                {"name": "property_id", "type": "VARCHAR", "description": "Parent property", "nullable": False, "example": "PROP_001"},
                {"name": "unit_number", "type": "VARCHAR", "description": "Unit number", "nullable": False, "example": "101"},
                {"name": "sqft", "type": "NUMBER", "description": "Square feet", "nullable": False, "example": "1200"},
                {"name": "bedrooms", "type": "NUMBER", "description": "Number of bedrooms", "nullable": True, "example": "2"},
                {"name": "bathrooms", "type": "NUMBER", "description": "Number of bathrooms", "nullable": True, "example": "1"},
                {"name": "status", "type": "VARCHAR", "description": "Status (vacant, occupied, maintenance)", "nullable": False, "example": "occupied"},
                {"name": "current_rent", "type": "NUMBER", "description": "Current monthly rent", "nullable": True, "example": "2500"},
                {"name": "tenant_id", "type": "VARCHAR", "description": "Multi-tenant isolation key", "nullable": False, "example": "TENANT_001"},
            ]
        },
        "leases": {
            "table_name": "leases",
            "columns": [
                {"name": "lease_id", "type": "VARCHAR", "description": "Unique lease identifier", "nullable": False, "example": "LEASE_001"},
                {"name": "unit_id", "type": "VARCHAR", "description": "Rented unit", "nullable": False, "example": "PROP_001_101"},
                {"name": "tenant_name", "type": "VARCHAR", "description": "Tenant name (PII - restricted)", "nullable": False, "example": "[RESTRICTED]"},
                {"name": "lease_start_date", "type": "DATE", "description": "Start date", "nullable": False, "example": "2023-01-01"},
                {"name": "lease_end_date", "type": "DATE", "description": "End date", "nullable": False, "example": "2024-12-31"},
                {"name": "monthly_rent", "type": "NUMBER", "description": "Monthly rent amount", "nullable": False, "example": "2500"},
                {"name": "renewal_option", "type": "BOOLEAN", "description": "Has renewal option", "nullable": True, "example": "true"},
                {"name": "tenant_id", "type": "VARCHAR", "description": "Multi-tenant isolation key", "nullable": False, "example": "TENANT_001"},
            ]
        },
        "financials": {
            "table_name": "financials",
            "columns": [
                {"name": "financial_id", "type": "VARCHAR", "description": "Unique record identifier", "nullable": False, "example": "FIN_001"},
                {"name": "property_id", "type": "VARCHAR", "description": "Property", "nullable": False, "example": "PROP_001"},
                {"name": "period_start_date", "type": "DATE", "description": "Start of reporting period", "nullable": False, "example": "2024-01-01"},
                {"name": "period_end_date", "type": "DATE", "description": "End of reporting period", "nullable": False, "example": "2024-01-31"},
                {"name": "gross_rent_income", "type": "NUMBER", "description": "Total rent billed", "nullable": False, "example": "125000"},
                {"name": "other_income", "type": "NUMBER", "description": "Parking, laundry, etc.", "nullable": True, "example": "5000"},
                {"name": "operating_expenses", "type": "NUMBER", "description": "Utilities, maintenance, management", "nullable": False, "example": "45000"},
                {"name": "debt_service", "type": "NUMBER", "description": "Loan payments", "nullable": True, "example": "20000"},
                {"name": "tenant_id", "type": "VARCHAR", "description": "Multi-tenant isolation key", "nullable": False, "example": "TENANT_001"},
            ]
        },
        "rent_collections": {
            "table_name": "rent_collections",
            "columns": [
                {"name": "collection_id", "type": "VARCHAR", "description": "Unique record identifier", "nullable": False, "example": "COL_001"},
                {"name": "lease_id", "type": "VARCHAR", "description": "Associated lease", "nullable": False, "example": "LEASE_001"},
                {"name": "property_id", "type": "VARCHAR", "description": "Property", "nullable": False, "example": "PROP_001"},
                {"name": "billing_period", "type": "DATE", "description": "Month for which rent is due", "nullable": False, "example": "2024-02-01"},
                {"name": "rent_due", "type": "NUMBER", "description": "Amount due", "nullable": False, "example": "2500"},
                {"name": "rent_collected", "type": "NUMBER", "description": "Amount received", "nullable": False, "example": "2500"},
                {"name": "due_date", "type": "DATE", "description": "Payment due date", "nullable": False, "example": "2024-02-01"},
                {"name": "payment_date", "type": "DATE", "description": "When payment received (null if not paid)", "nullable": True, "example": "2024-02-05"},
                {"name": "days_overdue", "type": "NUMBER", "description": "Days past due (0 if current)", "nullable": False, "example": "0"},
                {"name": "tenant_id", "type": "VARCHAR", "description": "Multi-tenant isolation key", "nullable": False, "example": "TENANT_001"},
            ]
        },
        "work_orders": {
            "table_name": "work_orders",
            "columns": [
                {"name": "work_order_id", "type": "VARCHAR", "description": "Unique identifier", "nullable": False, "example": "WO_001"},
                {"name": "property_id", "type": "VARCHAR", "description": "Property", "nullable": False, "example": "PROP_001"},
                {"name": "unit_id", "type": "VARCHAR", "description": "Unit (if applicable)", "nullable": True, "example": "PROP_001_101"},
                {"name": "priority", "type": "VARCHAR", "description": "Priority level", "nullable": False, "example": "High"},
                {"name": "category", "type": "VARCHAR", "description": "Category (Plumbing, Electrical, etc.)", "nullable": False, "example": "Plumbing"},
                {"name": "description", "type": "VARCHAR", "description": "Issue description", "nullable": False, "example": "Leaking faucet"},
                {"name": "status", "type": "VARCHAR", "description": "Status (open, in_progress, completed)", "nullable": False, "example": "open"},
                {"name": "created_date", "type": "DATE", "description": "When reported", "nullable": False, "example": "2024-02-01"},
                {"name": "completed_date", "type": "DATE", "description": "When completed", "nullable": True, "example": "2024-02-05"},
                {"name": "estimated_cost", "type": "NUMBER", "description": "Estimated repair cost", "nullable": True, "example": "500"},
                {"name": "tenant_id", "type": "VARCHAR", "description": "Multi-tenant isolation key", "nullable": False, "example": "TENANT_001"},
            ]
        },
    }
    
    return schemas.get(table_name, {"table_name": table_name, "columns": []})


def resolve_business_term(term: str) -> Optional[str]:
    """Map business language to database column name.
    
    Handles common variations that users might use.
    
    Args:
        term: User-facing business term
    
    Returns:
        SQL column name or None if not recognized
    
    Example:
        >>> col = resolve_business_term("occupancy")
        >>> print(col)  # "occupied_units" or similar
    
    Note:
        This enables fuzzy matching so users can say "vacancy" or "empty units"
        and get the right column without exact spelling.
    """
    term_lower = term.lower().strip()
    
    # Business term mappings
    mappings = {
        "occupancy": "occupied_units",
        "occupied": "occupied_units",
        "occupied units": "occupied_units",
        "vacancy": "vacant_units",
        "vacant": "vacant_units",
        "empty": "vacant_units",
        "open units": "vacant_units",
        "available units": "vacant_units",
        "noi": "noi",
        "net operating income": "noi",
        "rent": "monthly_rent",
        "monthly rent": "monthly_rent",
        "gross rent": "gross_rent_income",
        "income": "gross_rent_income",
        "revenue": "gross_rent_income",
        "expenses": "operating_expenses",
        "operating expenses": "operating_expenses",
        "opex": "operating_expenses",
        "maintenance": "maintenance_costs",
        "repairs": "maintenance_costs",
        "upkeep": "maintenance_costs",
        "units": "total_units",
        "total units": "total_units",
        "square feet": "total_sqft",
        "sqft": "total_sqft",
        "area": "total_sqft",
        "collections": "rent_collected",
        "collected": "rent_collected",
        "collected rent": "rent_collected",
        "delinquent": "days_overdue",
        "overdue": "days_overdue",
        "late": "days_overdue",
        "occupancy rate": "occupancy_rate",
        "cap rate": "cap_rate",
        "capitalization": "cap_rate",
        "collections rate": "collections_rate",
        "collection rate": "collections_rate",
        "turnover": "tenant_turnover",
        "renewal": "renewal_rate",
        "renewals": "renewal_rate",
    }
    
    return mappings.get(term_lower)
