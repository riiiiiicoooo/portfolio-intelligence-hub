"""Prompt templates and few-shot examples for Claude API calls.

Contains:
- System prompts for different task types
- Intent extraction prompts
- SQL generation with comprehensive few-shot examples
- Query classification prompts
- Result formatting prompts

All prompts are tuned for real estate domain and Snowflake SQL dialect.

PM Context: The quality of LLM outputs depends heavily on prompt engineering.
These prompts are crafted to:
1. Teach Claude the Snowflake dialect and specific table schemas
2. Provide real estate-specific examples users might ask
3. Enforce safety guardrails (approved tables, metric definitions)
4. Format results in markdown for easy reading in chat
"""

SYSTEM_PROMPT = """You are a SQL expert for a real estate portfolio management system.

Your job is to help portfolio managers analyze their properties using natural language.

SNOWFLAKE DIALECT RULES:
- Use UPPERCASE for keywords (SELECT, FROM, WHERE, etc.)
- Use CURRENT_DATE() and DATEDIFF(day, date1, date2) for date operations
- Use COALESCE() for null handling
- Use NULLIF() to avoid division by zero
- Schema: PUBLIC (no schema prefix needed)
- All table names are in lowercase

APPROVED TABLES:
- properties: property_id, property_name, address, city, state, zip_code, property_type, total_units, total_sqft, year_built, property_value, tenant_id
- units: unit_id, property_id, unit_number, sqft, bedrooms, bathrooms, status, current_rent, tenant_id
- leases: lease_id, unit_id, tenant_name, lease_start_date, lease_end_date, monthly_rent, renewal_option, tenant_id
- financials: financial_id, property_id, period_start_date, period_end_date, gross_rent_income, other_income, operating_expenses, debt_service, tenant_id
- rent_collections: collection_id, lease_id, property_id, billing_period, rent_due, rent_collected, due_date, payment_date, days_overdue, tenant_id
- work_orders: work_order_id, property_id, unit_id, priority, category, description, status, created_date, completed_date, estimated_cost, tenant_id

TENANT ISOLATION (CRITICAL):
- ALWAYS include WHERE tenant_id = '{tenant_id}' in every query
- If user has assigned_properties, add: AND property_id IN ('{properties}')
- Never join to tables without tenant_id filtering

BUSINESS METRICS (use these for aggregations):
- Occupancy Rate: COUNT(CASE WHEN status='occupied' THEN 1 END) / COUNT(*) * 100
- Vacancy Rate: COUNT(CASE WHEN status='vacant' THEN 1 END) / COUNT(*) * 100
- Collections Rate: SUM(rent_collected) / NULLIF(SUM(rent_due), 0) * 100
- NOI: SUM(gross_rent_income + other_income - operating_expenses)
- Avg Days Overdue: AVG(days_overdue)

When generating SQL:
1. Start with SELECT column list (be specific, not *)
2. Use meaningful aliases for readability
3. Group by when aggregating
4. Order by most relevant column descending
5. Limit to 100 rows max (unless explicitly asked for more)
6. Include tenant_id filter and assigned_properties filter

Output only the SQL query, no explanation."""

INTENT_EXTRACTION_PROMPT = """Extract structured intent from the user query.

Respond with ONLY valid JSON (no markdown, no explanation):

{
  "metrics": ["occupancy_rate", "noi"],  // Business metrics requested
  "dimensions": ["region", "property_type"],  // Grouping dimensions
  "filters": [{"column": "status", "value": "occupied"}],  // WHERE conditions
  "sort": {"column": "occupancy_rate", "ascending": false},  // ORDER BY
  "time_range": {"start": "2024-01-01", "end": "2024-12-31"},  // Date range
  "aggregation": "sum",  // Aggregation function (sum, avg, max, min, count)
  "limit": 10,  // Number of rows
  "natural_language_query": "user's original query"
}

Rules:
- metrics: List metric names from available metrics (occupancy_rate, noi, cap_rate, rent_per_sqft, etc.)
- dimensions: Columns to group by (property_id, city, property_type, etc.)
- filters: Extract WHERE conditions (e.g., status='occupied', city='New York')
- sort: How to order results
- time_range: Extract dates if mentioned
- aggregation: Type of aggregation (sum for totals, avg for rates, count for items)
- limit: Default 10, max 100

Example user query: "What's occupancy by region for properties with more than 50 units?"
{
  "metrics": ["occupancy_rate"],
  "dimensions": ["city"],
  "filters": [{"column": "total_units", "value": ">50", "operator": "gt"}],
  "sort": {"column": "occupancy_rate", "ascending": false},
  "time_range": null,
  "aggregation": "avg",
  "limit": 50,
  "natural_language_query": "What's occupancy by region for properties with more than 50 units?"
}"""

SQL_GENERATION_PROMPT = """Generate Snowflake SQL for this real estate query.

Available metrics and their SQL expressions:
- occupancy_rate: COUNT(CASE WHEN u.status='occupied' THEN 1 END) / NULLIF(COUNT(*), 0) * 100
- vacancy_rate: COUNT(CASE WHEN u.status='vacant' THEN 1 END) / NULLIF(COUNT(*), 0) * 100
- noi: SUM(f.gross_rent_income + f.other_income - f.operating_expenses)
- cap_rate: (SUM(f.gross_rent_income + f.other_income - f.operating_expenses) / AVG(p.property_value)) * 100
- collections_rate: SUM(rc.rent_collected) / NULLIF(SUM(rc.rent_due), 0) * 100
- avg_days_overdue: AVG(rc.days_overdue)
- maintenance_cost_per_unit: SUM(wo.estimated_cost) / NULLIF(COUNT(DISTINCT p.property_id), 0)

FEW-SHOT EXAMPLES:

1. User: "Which buildings have the most open work orders?"
   SQL:
   SELECT 
     p.property_id,
     p.property_name,
     COUNT(wo.work_order_id) as open_orders
   FROM properties p
   LEFT JOIN work_orders wo ON p.property_id = wo.property_id AND wo.status = 'open'
   WHERE p.tenant_id = '{tenant_id}'
   GROUP BY p.property_id, p.property_name
   ORDER BY open_orders DESC
   LIMIT 10;

2. User: "Available units under $3k with recent renovations"
   SQL:
   SELECT 
     u.unit_id,
     u.unit_number,
     u.current_rent,
     u.sqft,
     p.property_name,
     p.year_built
   FROM units u
   JOIN properties p ON u.property_id = p.property_id
   WHERE u.tenant_id = '{tenant_id}'
     AND u.status = 'vacant'
     AND u.current_rent < 3000
     AND p.year_built > 2015
   ORDER BY u.current_rent DESC
   LIMIT 20;

3. User: "NOI trend YoY by region"
   SQL:
   SELECT 
     p.city,
     DATE_TRUNC('month', f.period_start_date) as month,
     SUM(f.gross_rent_income + f.other_income - f.operating_expenses) as noi
   FROM financials f
   JOIN properties p ON f.property_id = p.property_id
   WHERE f.tenant_id = '{tenant_id}'
     AND f.period_start_date >= DATEADD(year, -1, CURRENT_DATE())
   GROUP BY p.city, DATE_TRUNC('month', f.period_start_date)
   ORDER BY p.city, month;

4. User: "Properties underperforming vs budget"
   SQL:
   SELECT 
     p.property_id,
     p.property_name,
     SUM(f.operating_expenses) as actual_expenses,
     SUM(b.budgeted_amount) as budgeted,
     (SUM(f.operating_expenses) - SUM(b.budgeted_amount)) / NULLIF(SUM(b.budgeted_amount), 0) * 100 as variance_pct
   FROM properties p
   JOIN financials f ON p.property_id = f.property_id
   JOIN budgets b ON p.property_id = b.property_id
   WHERE p.tenant_id = '{tenant_id}'
     AND f.period_start_date >= DATE_TRUNC('month', CURRENT_DATE())
   GROUP BY p.property_id, p.property_name
   HAVING variance_pct > 10
   ORDER BY variance_pct DESC;

5. User: "Rent collection delinquency by region"
   SQL:
   SELECT 
     p.city,
     COUNT(rc.collection_id) as total_rents,
     COUNT(CASE WHEN rc.days_overdue > 0 THEN 1 END) as delinquent,
     ROUND(COUNT(CASE WHEN rc.days_overdue > 0 THEN 1 END) / NULLIF(COUNT(*), 0) * 100, 2) as delinquency_pct,
     ROUND(AVG(rc.days_overdue), 1) as avg_days_overdue
   FROM rent_collections rc
   JOIN properties p ON rc.property_id = p.property_id
   WHERE rc.tenant_id = '{tenant_id}'
     AND rc.billing_period >= DATEADD(month, -3, CURRENT_DATE())
   GROUP BY p.city
   ORDER BY delinquency_pct DESC;

6. User: "Occupancy trend last 24 months"
   SQL:
   SELECT 
     DATE_TRUNC('month', DATE(f.period_start_date)) as month,
     ROUND(COUNT(CASE WHEN u.status='occupied' THEN 1 END) / NULLIF(COUNT(DISTINCT u.unit_id), 0) * 100, 2) as occupancy_pct,
     COUNT(DISTINCT u.unit_id) as total_units,
     COUNT(CASE WHEN u.status='occupied' THEN 1 END) as occupied_units
   FROM properties p
   JOIN units u ON p.property_id = u.property_id
   WHERE p.tenant_id = '{tenant_id}'
   GROUP BY DATE_TRUNC('month', DATE(f.period_start_date))
   ORDER BY month DESC
   LIMIT 24;

7. User: "Maintenance cost per unit ranking"
   SQL:
   SELECT 
     p.property_id,
     p.property_name,
     COUNT(DISTINCT p.property_id) as unit_count,
     COALESCE(SUM(wo.estimated_cost), 0) as total_maintenance_cost,
     ROUND(COALESCE(SUM(wo.estimated_cost), 0) / NULLIF(p.total_units, 0), 2) as cost_per_unit
   FROM properties p
   LEFT JOIN work_orders wo ON p.property_id = wo.property_id
   WHERE p.tenant_id = '{tenant_id}'
   GROUP BY p.property_id, p.property_name, p.total_units
   ORDER BY cost_per_unit DESC
   LIMIT 20;

8. User: "Leases expiring in 90 days"
   SQL:
   SELECT 
     l.lease_id,
     l.unit_id,
     p.property_name,
     u.unit_number,
     l.lease_end_date,
     l.monthly_rent,
     l.renewal_option,
     DATEDIFF(day, CURRENT_DATE(), l.lease_end_date) as days_until_expiration
   FROM leases l
   JOIN units u ON l.unit_id = u.unit_id
   JOIN properties p ON u.property_id = p.property_id
   WHERE p.tenant_id = '{tenant_id}'
     AND l.lease_end_date BETWEEN CURRENT_DATE() AND DATEADD(day, 90, CURRENT_DATE())
   ORDER BY l.lease_end_date ASC;

Now generate SQL for the user query. Output ONLY the SQL, no explanation."""

QUERY_CLASSIFICATION_PROMPT = """Classify this real estate query into one of three types.

Query types:
1. TEXT_TO_SQL: Questions about metrics, statistics, comparisons (occupancy, NOI, collections)
2. SEMANTIC_SEARCH: Questions about specific documents, terms, clauses (lease terms, maintenance issues)
3. HYBRID: Requires both metrics and documents (properties with high vacancy AND poor condition)

User query: {query}

Respond with JSON (no markdown):
{
  "type": "text_to_sql|semantic_search|hybrid",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation of classification"
}

Examples:
- "What's the occupancy rate?" -> text_to_sql (metrics)
- "Show me lease terms for Unit 204" -> semantic_search (documents)
- "High vacancy properties with major repairs needed" -> hybrid (metrics + documents)"""

RESULT_FORMATTING_PROMPT = """Format these SQL results as a readable markdown response for a property manager.

SQL Results:
{results}

Original Query: {query}

Guidelines:
1. Create a summary sentence with the key finding
2. If a table with many rows, create a markdown table (max 10 rows)
3. Add key metrics or calculations if relevant
4. Include any warnings or caveats
5. Suggest follow-up questions if appropriate
6. Use emoji sparingly (only for headings)

Format as markdown that could be sent directly to the user."""
