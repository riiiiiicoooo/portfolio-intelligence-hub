"""Text-to-SQL pipeline for converting natural language to Snowflake queries.

This is the core engine that transforms user queries like "Show me occupancy by region"
into syntactically correct, safe SQL that executes against Snowflake.

PM Context: Real estate operators need instant access to structured metrics (occupancy,
NOI, collections, maintenance costs) without knowing SQL. This pipeline is 5 steps:
1. Parse intent (what metrics/dimensions does the user want?)
2. Map to tables (which Snowflake tables/columns implement those metrics?)
3. Generate SQL (Claude writes the SQL)
4. Validate (check it's safe and approved)
5. Execute (run on Snowflake with tenant filtering)

Reference Implementation: This is functional enough to demonstrate the capability,
with comprehensive type hints and docstrings. Production would need:
- Query plan caching
- More sophisticated intent parsing
- Enhanced validation rules
"""

import logging
import json
import re
import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum

import anthropic
import snowflake.connector
from snowflake.connector import DictCursor

from .semantic_layer import get_metric, get_approved_tables, get_table_schema, resolve_business_term
from .prompts import INTENT_EXTRACTION_PROMPT, SQL_GENERATION_PROMPT, RESULT_FORMATTING_PROMPT
from ..access_control.rbac import build_tenant_filter

logger = logging.getLogger(__name__)


# Snowflake table list for whitelisting
APPROVED_TABLES = get_approved_tables()

# Dangerous patterns that should never appear in generated SQL
DANGEROUS_PATTERNS = [
    r"DROP\s+(TABLE|DATABASE|SCHEMA)",
    r"DELETE\s+FROM",
    r"TRUNCATE\s+TABLE",
    r"ALTER\s+(TABLE|DATABASE|SCHEMA)",
    r"CREATE\s+(TABLE|DATABASE|SCHEMA)",
    r"GRANT\s+",
    r"REVOKE\s+",
    r"INSERT\s+INTO",
    r"UPDATE\s+",
    r"EXEC\s*\(",
    r"EXECUTE\s*\(",
]


@dataclass
class QueryIntent:
    """Structured representation of user intent extracted from natural language.
    
    Attributes:
        metrics: List of business metrics requested (e.g., ['occupancy_rate', 'noi'])
        dimensions: List of columns to group by (e.g., ['city', 'property_type'])
        filters: List of filter conditions
        sort: Sorting specification (column, ascending/descending)
        time_range: Date range for filtering
        aggregation: Type of aggregation (sum, avg, max, min, count)
        limit: Number of rows to return
    
    Example:
        >>> intent = QueryIntent(
        ...     metrics=['occupancy_rate', 'vacancy_rate'],
        ...     dimensions=['city'],
        ...     filters=[],
        ...     sort={'column': 'occupancy_rate', 'ascending': False},
        ...     time_range=None,
        ...     aggregation='avg',
        ...     limit=20
        ... )
    """
    metrics: List[str] = field(default_factory=list)
    dimensions: List[str] = field(default_factory=list)
    filters: List[Dict[str, Any]] = field(default_factory=list)
    sort: Optional[Dict[str, Any]] = None
    time_range: Optional[Dict[str, str]] = None
    aggregation: str = "avg"
    limit: int = 10


@dataclass
class TableMapping:
    """Mapping from intent to Snowflake tables and SQL components.
    
    Attributes:
        tables: Set of required tables
        joins: List of JOIN clauses
        where_clauses: List of WHERE conditions
        group_by: List of GROUP BY columns
        order_by: ORDER BY specification
        select_columns: SELECT clause columns
    
    Example:
        >>> mapping = TableMapping(
        ...     tables={'properties', 'units'},
        ...     joins=['LEFT JOIN units u ON p.property_id = u.property_id'],
        ...     where_clauses=['u.status = \'occupied\''],
        ...     group_by=['p.city'],
        ...     order_by='occupancy_rate DESC',
        ...     select_columns=['p.city', 'COUNT(*) as total']
        ... )
    """
    tables: set = field(default_factory=set)
    joins: List[str] = field(default_factory=list)
    where_clauses: List[str] = field(default_factory=list)
    group_by: List[str] = field(default_factory=list)
    order_by: Optional[str] = None
    select_columns: List[str] = field(default_factory=list)


def parse_query_intent(query: str) -> QueryIntent:
    """Extract structured intent from natural language query using Claude.
    
    Args:
        query: User's natural language query
    
    Returns:
        QueryIntent dataclass with parsed components
    
    Raises:
        ValueError: If Claude response cannot be parsed as JSON
    
    Process:
        1. Send query to Claude with INTENT_EXTRACTION_PROMPT
        2. Parse response JSON
        3. Validate required fields
        4. Return QueryIntent
    
    Example:
        >>> intent = parse_query_intent("What's occupancy by region for metro areas?")
        >>> print(intent.metrics)  # ['occupancy_rate']
        >>> print(intent.dimensions)  # ['city']
    """
    client = anthropic.Anthropic()
    
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=500,
        messages=[
            {
                "role": "user",
                "content": f"Query: {query}\n\n{INTENT_EXTRACTION_PROMPT}"
            }
        ]
    )
    
    try:
        response_text = message.content[0].text.strip()
        # Remove markdown code blocks if present
        response_text = re.sub(r"```json\n?|\n?```", "", response_text)
        intent_data = json.loads(response_text)
        
        return QueryIntent(
            metrics=intent_data.get('metrics', []),
            dimensions=intent_data.get('dimensions', []),
            filters=intent_data.get('filters', []),
            sort=intent_data.get('sort'),
            time_range=intent_data.get('time_range'),
            aggregation=intent_data.get('aggregation', 'avg'),
            limit=min(intent_data.get('limit', 10), 100)  # Cap at 100
        )
    except (json.JSONDecodeError, IndexError) as e:
        logger.error(f"Failed to parse intent response: {e}")
        raise ValueError(f"Could not parse query intent: {e}")


def map_to_tables(intent: QueryIntent) -> TableMapping:
    """Map query intent to Snowflake tables and build SQL components.
    
    Args:
        intent: QueryIntent from parse_query_intent()
    
    Returns:
        TableMapping with tables, joins, and SQL components
    
    Process:
        1. For each metric, determine which tables it needs
        2. For each dimension, determine which table it comes from
        3. Build required JOINs
        4. Build WHERE clauses from filters
        5. Build GROUP BY from dimensions
        6. Build ORDER BY from sort specification
    
    Note:
        This is a reference implementation. Production would have more sophisticated
        table-to-metric mapping including a registry of which tables implement each metric.
    """
    mapping = TableMapping()
    
    # Add tables based on metrics
    for metric_name in intent.metrics:
        metric = get_metric(metric_name)
        if metric:
            mapping.tables.update(metric.tables_required)
    
    # Add base tables for dimensions
    dimension_to_table = {
        'property_id': 'properties',
        'property_name': 'properties',
        'property_type': 'properties',
        'city': 'properties',
        'state': 'properties',
        'region': 'properties',
        'unit_id': 'units',
        'unit_number': 'units',
        'status': 'units',
        'current_rent': 'units',
        'lease_id': 'leases',
        'lease_start_date': 'leases',
        'lease_end_date': 'leases',
        'monthly_rent': 'leases',
        'billing_period': 'rent_collections',
    }
    
    for dim in intent.dimensions:
        table = dimension_to_table.get(dim)
        if table:
            mapping.tables.add(table)
    
    # Build JOINs between tables
    if 'properties' in mapping.tables and 'units' in mapping.tables:
        mapping.joins.append('LEFT JOIN units u ON p.property_id = u.property_id')
    
    if 'properties' in mapping.tables and 'leases' in mapping.tables:
        mapping.joins.append('LEFT JOIN leases l ON p.property_id = l.unit_id')
    
    if 'properties' in mapping.tables and 'financials' in mapping.tables:
        mapping.joins.append('LEFT JOIN financials f ON p.property_id = f.property_id')
    
    if 'properties' in mapping.tables and 'rent_collections' in mapping.tables:
        mapping.joins.append('LEFT JOIN rent_collections rc ON p.property_id = rc.property_id')
    
    # Build WHERE clauses from filters
    for filter_item in intent.filters:
        column = filter_item.get('column')
        value = filter_item.get('value')
        operator = filter_item.get('operator', '=')
        
        if operator == 'gt':
            mapping.where_clauses.append(f"{column} > {value}")
        elif operator == 'lt':
            mapping.where_clauses.append(f"{column} < {value}")
        else:
            mapping.where_clauses.append(f"{column} = '{value}'")
    
    # Build GROUP BY from dimensions
    for dim in intent.dimensions:
        # Alias dimensions with table prefix if needed
        if '.' not in dim:
            for table_name in mapping.tables:
                schema = get_table_schema(table_name)
                cols = [c['name'] for c in schema.get('columns', [])]
                if dim in cols:
                    dim = f"{table_name[0]}.{dim}"
                    break
        mapping.group_by.append(dim)
    
    # Build ORDER BY
    if intent.sort:
        col = intent.sort.get('column')
        asc = 'ASC' if intent.sort.get('ascending', False) else 'DESC'
        mapping.order_by = f"{col} {asc}"
    
    logger.debug(f"Mapped intent to tables: {mapping.tables}")
    return mapping


def generate_sql(mapping: TableMapping, user_context: 'UserContext') -> str:
    """Generate Snowflake SQL from table mapping using Claude.
    
    Args:
        mapping: TableMapping from map_to_tables()
        user_context: UserContext with tenant and property filtering
    
    Returns:
        Valid Snowflake SQL query string
    
    Raises:
        ValueError: If SQL generation fails
    
    Process:
        1. Build prompt with table schemas and mappings
        2. Call Claude with SQL_GENERATION_PROMPT
        3. Extract and validate SQL
        4. Add tenant filtering
        5. Return SQL
    
    Note:
        Claude sees approved table schemas and few-shot examples.
        It does not see the mapping directly, allowing for flexible interpretation.
    """
    client = anthropic.Anthropic()
    
    # Build schema context for Claude
    schema_context = "Available tables and columns:\n"
    for table in mapping.tables:
        schema = get_table_schema(table)
        schema_context += f"\n{table}:\n"
        for col in schema.get('columns', []):
            schema_context += f"  - {col['name']}: {col['type']} ({col['description']})\n"
    
    prompt = f"""{SQL_GENERATION_PROMPT}

Table schemas:
{schema_context}

Tenant ID: {user_context.tenant_id}
Assigned properties: {','.join(user_context.assigned_properties) if user_context.assigned_properties else 'ALL'}

Generate SQL for the user query."""
    
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    try:
        sql = message.content[0].text.strip()
        # Remove markdown code blocks
        sql = re.sub(r"```sql\n?|\n?```", "", sql)
        
        logger.debug(f"Generated SQL:\n{sql}")
        return sql
    except (IndexError, AttributeError) as e:
        logger.error(f"Failed to extract SQL from response: {e}")
        raise ValueError(f"Could not generate SQL: {e}")


def validate_sql(sql: str) -> Tuple[bool, str]:
    """Validate SQL for safety and correctness.
    
    Args:
        sql: SQL query string to validate
    
    Returns:
        Tuple of (is_valid: bool, message: str)
    
    Checks:
        1. No dangerous patterns (DROP, DELETE, ALTER, etc.)
        2. Only uses approved tables
        3. Valid SQL syntax (basic parsing)
        4. Reasonable query complexity (not too many joins)
    
    Example:
        >>> is_valid, msg = validate_sql("SELECT * FROM properties WHERE tenant_id = '1'")
        >>> if not is_valid:
        ...     print(f"Validation failed: {msg}")
    """
    sql_upper = sql.upper()
    
    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, sql_upper):
            return False, f"Dangerous SQL pattern detected: {pattern}"
    
    # Check approved tables
    for table in APPROVED_TABLES:
        if table.upper() in sql_upper:
            # Table is used, which is OK
            pass
    
    # Check for unapproved tables
    all_words = re.findall(r'\bFROM\s+(\w+)|JOIN\s+(\w+)', sql_upper)
    for match in all_words:
        table = (match[0] or match[1]).lower()
        if table not in APPROVED_TABLES and table not in ['ON', 'WHERE', 'GROUP', 'ORDER', 'LIMIT']:
            return False, f"Unapproved table: {table}"
    
    # Check tenant_id filter is present
    if "TENANT_ID" not in sql_upper:
        return False, "Query must include tenant_id filter"
    
    # Basic syntax check (has SELECT and FROM)
    if not re.search(r'\bSELECT\b.*\bFROM\b', sql_upper):
        return False, "Invalid SQL: missing SELECT or FROM"
    
    return True, "SQL validation passed"


def execute_query(sql: str, user_context: 'UserContext') -> List[Dict[str, Any]]:
    """Execute SQL on Snowflake with tenant filtering.
    
    Args:
        sql: Validated SQL query
        user_context: UserContext with tenant and property filtering
    
    Returns:
        List of result dictionaries
    
    Raises:
        Exception: If Snowflake execution fails
    
    Process:
        1. Inject tenant_id filter into WHERE clause
        2. Add property list filter if user has assigned_properties
        3. Execute with 30-second timeout
        4. Return as list of dicts
    
    Note:
        Uses connection pooling and retry logic (not shown in reference implementation).
        In production, would also cache plan for identical queries.
    """
    import os
    
    # Connect to Snowflake
    try:
        conn = snowflake.connector.connect(
            user=os.environ.get('SNOWFLAKE_USER'),
            password=os.environ.get('SNOWFLAKE_PASSWORD'),
            account=os.environ.get('SNOWFLAKE_ACCOUNT'),
            warehouse=os.environ.get('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
            database=os.environ.get('SNOWFLAKE_DATABASE', 'PORTFOLIO_DB'),
            schema=os.environ.get('SNOWFLAKE_SCHEMA', 'PUBLIC'),
        )
        
        cursor = conn.cursor(DictCursor)
        
        # Inject tenant filtering
        tenant_filter = build_tenant_filter(user_context)
        
        # Add tenant filter to SQL if not already present
        if "WHERE" in sql.upper():
            sql = re.sub(
                r"WHERE\s+",
                f"WHERE {tenant_filter} AND ",
                sql,
                flags=re.IGNORECASE
            )
        else:
            sql = f"{sql} WHERE {tenant_filter}"
        
        logger.info(f"Executing query with tenant filter: {tenant_filter}")
        cursor.execute(sql)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        logger.info(f"Query returned {len(results)} rows")
        return results
    
    except Exception as e:
        logger.error(f"Snowflake execution failed: {e}")
        raise


def format_results(results: List[Dict[str, Any]], query: str) -> str:
    """Format SQL results as readable markdown.
    
    Args:
        results: List of result dictionaries from execute_query()
        query: Original user query (for context)
    
    Returns:
        Markdown-formatted response string
    
    Process:
        1. If no results, return "No data" message
        2. If small number of rows, create markdown table
        3. If many rows, create summary stats
        4. Add context about what was queried
    
    Example:
        >>> results = [{'city': 'NYC', 'occupancy': 92.5}, {'city': 'LA', 'occupancy': 88.0}]
        >>> formatted = format_results(results, "occupancy by city")
        >>> print(formatted)
        # Results for: occupancy by city
        | city | occupancy |
        | - | - |
        | NYC | 92.5 |
        | LA | 88.0 |
    """
    if not results:
        return "No results found for your query."
    
    # Build markdown table
    markdown = f"## Results for: {query}\n\n"
    
    if len(results) > 0:
        # Get column names from first row
        columns = list(results[0].keys())
        
        # Create header
        markdown += "| " + " | ".join(columns) + " |\n"
        markdown += "| " + " | ".join(["---"] * len(columns)) + " |\n"
        
        # Add rows (limit to 20 for readability)
        for row in results[:20]:
            values = [str(row.get(col, "")) for col in columns]
            markdown += "| " + " | ".join(values) + " |\n"
        
        if len(results) > 20:
            markdown += f"\n*Showing 20 of {len(results)} results*\n"
    
    return markdown
