"""Database and service connectors for Portfolio Intelligence Hub.

Provides abstracted connections to:
- Snowflake: Structured operational and financial data
- Supabase (PostgreSQL + pgvector): Document storage and embeddings
- External APIs: Azure Document Intelligence, Cohere, Anthropic Claude

PM Context: This layer abstracts away connection details, pooling, retry logic,
and authentication so that higher-level modules can focus on business logic.
"""

from .snowflake_connector import SnowflakeConfig, SnowflakeConnection, execute_query, execute_with_tenant_filter

__all__ = [
    'SnowflakeConfig',
    'SnowflakeConnection',
    'execute_query',
    'execute_with_tenant_filter',
]
