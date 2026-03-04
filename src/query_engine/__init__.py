"""Query engine for classification, routing, and execution of natural language queries.

Provides the core dispatch logic that:
1. Classifies incoming queries as TEXT_TO_SQL, SEMANTIC_SEARCH, CACHED, or HYBRID
2. Routes to appropriate backend (Snowflake, document search, or cache)
3. Returns structured results with execution metadata

PM Context: Property managers need sub-second responses to questions like "Show me
occupancy by region" or "Which leases expire in 90 days" without thinking about
whether the answer comes from metrics (SQL) or documents (search).
"""

from .router import QueryType, QueryResult, UserContext, classify_query, route_query
from .text_to_sql import QueryIntent, TableMapping, parse_query_intent, map_to_tables, generate_sql, validate_sql, execute_query, format_results
from .semantic_layer import MetricDefinition, get_metric, get_approved_tables, get_table_schema, resolve_business_term
from .prompts import SYSTEM_PROMPT, INTENT_EXTRACTION_PROMPT, SQL_GENERATION_PROMPT, QUERY_CLASSIFICATION_PROMPT, RESULT_FORMATTING_PROMPT

__all__ = [
    'QueryType',
    'QueryResult',
    'UserContext',
    'classify_query',
    'route_query',
    'QueryIntent',
    'TableMapping',
    'parse_query_intent',
    'map_to_tables',
    'generate_sql',
    'validate_sql',
    'execute_query',
    'format_results',
    'MetricDefinition',
    'get_metric',
    'get_approved_tables',
    'get_table_schema',
    'resolve_business_term',
    'SYSTEM_PROMPT',
    'INTENT_EXTRACTION_PROMPT',
    'SQL_GENERATION_PROMPT',
    'QUERY_CLASSIFICATION_PROMPT',
    'RESULT_FORMATTING_PROMPT',
]
