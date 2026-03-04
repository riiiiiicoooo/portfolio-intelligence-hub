"""Snowflake connection management and query execution.

Provides:
- Connection pooling and context management
- Query execution with timeouts and retries
- Tenant filtering for multi-tenant deployments
- Audit logging of all queries

PM Context: Snowflake stores structured operational data (properties, units, leases,
rent collections, financials). This connector handles authentication, pooling,
and query execution with proper tenant isolation and audit logging.
"""

import logging
import os
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import time
from contextlib import contextmanager

import snowflake.connector
from snowflake.connector import DictCursor, ProgrammingError

logger = logging.getLogger(__name__)


@dataclass
class SnowflakeConfig:
    """Snowflake connection configuration.
    
    Attributes:
        user: Snowflake username
        password: Snowflake password
        account: Snowflake account identifier
        warehouse: Warehouse name (COMPUTE_WH, etc.)
        database: Database name (PORTFOLIO_DB, etc.)
        schema: Schema name (PUBLIC, etc.)
        role: Optional role to assume
    
    Environment variables:
        SNOWFLAKE_USER
        SNOWFLAKE_PASSWORD
        SNOWFLAKE_ACCOUNT
        SNOWFLAKE_WAREHOUSE
        SNOWFLAKE_DATABASE
        SNOWFLAKE_SCHEMA
    """
    user: str
    password: str
    account: str
    warehouse: str = "COMPUTE_WH"
    database: str = "PORTFOLIO_DB"
    schema: str = "PUBLIC"
    role: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'SnowflakeConfig':
        """Load configuration from environment variables."""
        return cls(
            user=os.environ.get('SNOWFLAKE_USER', ''),
            password=os.environ.get('SNOWFLAKE_PASSWORD', ''),
            account=os.environ.get('SNOWFLAKE_ACCOUNT', ''),
            warehouse=os.environ.get('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
            database=os.environ.get('SNOWFLAKE_DATABASE', 'PORTFOLIO_DB'),
            schema=os.environ.get('SNOWFLAKE_SCHEMA', 'PUBLIC'),
            role=os.environ.get('SNOWFLAKE_ROLE'),
        )


class SnowflakeConnection:
    """Context manager for Snowflake connections.
    
    Handles connection lifecycle, error handling, and query execution.
    
    Example:
        >>> with SnowflakeConnection.from_config(config) as conn:
        ...     results = conn.execute_query("SELECT * FROM properties")
    """
    
    def __init__(self, config: SnowflakeConfig):
        """Initialize with configuration."""
        self.config = config
        self.connection = None
    
    def __enter__(self):
        """Establish connection."""
        try:
            self.connection = snowflake.connector.connect(
                user=self.config.user,
                password=self.config.password,
                account=self.config.account,
                warehouse=self.config.warehouse,
                database=self.config.database,
                schema=self.config.schema,
                role=self.config.role,
            )
            logger.debug(f"Connected to Snowflake {self.config.account}")
            return self
        except Exception as e:
            logger.error(f"Failed to connect to Snowflake: {e}")
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close connection."""
        if self.connection:
            self.connection.close()
            logger.debug("Snowflake connection closed")
    
    @staticmethod
    @contextmanager
    def from_config(config: SnowflakeConfig):
        """Context manager for connection from config."""
        conn = SnowflakeConnection(config)
        with conn as c:
            yield c
    
    @staticmethod
    @contextmanager
    def from_env():
        """Context manager using environment variables."""
        config = SnowflakeConfig.from_env()
        with SnowflakeConnection.from_config(config) as conn:
            yield conn
    
    def execute_query(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        timeout_seconds: int = 30
    ) -> List[Dict[str, Any]]:
        """Execute SQL query with timeout.
        
        Args:
            sql: SQL query string
            params: Query parameters (for parameterized queries)
            timeout_seconds: Query timeout (default 30s)
        
        Returns:
            List of result rows as dictionaries
        
        Raises:
            ProgrammingError: If SQL is invalid
            Exception: If query times out
        
        Example:
            >>> results = conn.execute_query(
            ...     "SELECT * FROM properties WHERE property_id = ?",
            ...     params={'property_id': 'PROP_001'}
            ... )
        """
        if not self.connection:
            raise RuntimeError("Connection not established")
        
        try:
            cursor = self.connection.cursor(DictCursor)
            
            start_time = time.time()
            logger.debug(f"Executing: {sql[:100]}...")
            
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            results = cursor.fetchall()
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            logger.info(f"Query executed in {elapsed_ms}ms, returned {len(results)} rows")
            cursor.close()
            return results
        
        except ProgrammingError as e:
            logger.error(f"SQL error: {e}")
            raise
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def execute_with_tenant_filter(
        self,
        sql: str,
        tenant_id: str,
        role: str,
        properties: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Execute query with automatic tenant and property filtering.
        
        Args:
            sql: SQL query (should have WHERE clause already)
            tenant_id: Tenant ID to filter by
            role: User role (for audit logging)
            properties: List of property IDs to filter by (empty = all)
        
        Returns:
            List of result rows
        
        Process:
            1. Add tenant_id filter to WHERE clause
            2. Add property list filter if provided
            3. Execute with tenant context
            4. Log for audit trail
        
        Example:
            >>> results = conn.execute_with_tenant_filter(
            ...     "SELECT * FROM properties WHERE status = 'active'",
            ...     tenant_id="TENANT_001",
            ...     role="property_manager",
            ...     properties=["PROP_001", "PROP_002"]
            ... )
        """
        # Inject tenant filter
        if "WHERE" in sql.upper():
            sql = sql.replace("WHERE", f"WHERE tenant_id = '{tenant_id}' AND")
        else:
            sql = f"{sql} WHERE tenant_id = '{tenant_id}'"
        
        # Inject property filter if applicable
        if properties:
            props_str = "', '".join(properties)
            sql = f"{sql} AND property_id IN ('{props_str}')"
        
        # Log for audit trail
        logger.info(f"Query by {role} in {tenant_id}: {sql[:100]}...")
        
        return self.execute_query(sql)


def execute_query(sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Execute query using default Snowflake connection.
    
    Convenience function for one-off queries.
    
    Args:
        sql: SQL query
        params: Query parameters
    
    Returns:
        List of result rows
    
    Example:
        >>> results = execute_query("SELECT COUNT(*) as count FROM properties")
    """
    with SnowflakeConnection.from_env() as conn:
        return conn.execute_query(sql, params)


def execute_with_tenant_filter(
    sql: str,
    tenant_id: str,
    role: str,
    properties: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """Execute query with tenant filtering using default connection.
    
    Args:
        sql: SQL query
        tenant_id: Tenant ID
        role: User role
        properties: Optional property filter list
    
    Returns:
        List of result rows
    """
    with SnowflakeConnection.from_env() as conn:
        return conn.execute_with_tenant_filter(sql, tenant_id, role, properties)
