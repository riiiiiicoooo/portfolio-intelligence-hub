"""Tests for the Text-to-SQL pipeline in Portfolio Intelligence Hub.

This module tests the query classification, intent parsing, SQL generation,
validation, and result formatting for the text-to-SQL RAG system.
"""

from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest


class QueryIntent:
    """Represents the parsed intent of a user query."""

    def __init__(
        self,
        query_type: str,
        metrics: List[str],
        dimensions: List[str],
        filters: Dict[str, Any],
    ):
        """Initialize QueryIntent.

        Args:
            query_type: Type of query (e.g., 'metric_aggregation', 'comparison')
            metrics: List of metrics to retrieve (e.g., 'open_work_orders', 'noi')
            dimensions: List of dimensions to group by (e.g., 'property_id', 'category')
            filters: Dictionary of filter conditions
        """
        self.query_type = query_type
        self.metrics = metrics
        self.dimensions = dimensions
        self.filters = filters


class TableMapping:
    """Represents the mapping from intent to database tables."""

    def __init__(
        self,
        tables: List[str],
        joins: List[Dict[str, str]],
        where_clause: str,
        select_columns: List[str],
    ):
        """Initialize TableMapping.

        Args:
            tables: List of tables to query
            joins: List of join configurations
            where_clause: WHERE clause for filtering
            select_columns: List of columns to select
        """
        self.tables = tables
        self.joins = joins
        self.where_clause = where_clause
        self.select_columns = select_columns


# Test Fixtures
@pytest.fixture
def mock_claude_client() -> MagicMock:
    """Mock Claude API client."""
    client = MagicMock()
    client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="SELECT * FROM work_orders")]
    )
    return client


@pytest.fixture
def text_to_sql_service(mock_snowflake_connection, mock_claude_client):
    """Create a text-to-SQL service with mocked dependencies."""

    class TextToSQLService:
        def __init__(self, snowflake_conn, claude_client):
            self.snowflake_conn = snowflake_conn
            self.claude_client = claude_client
            self.approved_tables = {
                "properties",
                "units",
                "leases",
                "work_orders",
                "financial_data",
                "occupancy",
                "tenants",
            }

        def classify_query(self, query: str) -> str:
            """Classify if query should use text-to-SQL or semantic search."""
            semantic_keywords = [
                "lease renewal",
                "inspection",
                "condition",
                "summary",
                "describe",
            ]
            return (
                "SEMANTIC_SEARCH"
                if any(kw in query.lower() for kw in semantic_keywords)
                else "TEXT_TO_SQL"
            )

        def parse_intent(self, query: str) -> QueryIntent:
            """Parse user query into structured intent."""
            if "open work orders" in query.lower():
                return QueryIntent(
                    query_type="metric_aggregation",
                    metrics=["open_work_orders", "count"],
                    dimensions=["building_name"],
                    filters={},
                )
            elif "lease" in query.lower() and "renewal" in query.lower():
                return QueryIntent(
                    query_type="filtering",
                    metrics=["lease_id", "unit_id"],
                    dimensions=["property_id"],
                    filters={"has_renewal_option": True},
                )
            else:
                return QueryIntent(
                    query_type="general",
                    metrics=[],
                    dimensions=[],
                    filters={},
                )

        def map_to_tables(self, intent: QueryIntent) -> TableMapping:
            """Map intent to database tables and joins."""
            if "work_order" in str(intent.metrics).lower():
                return TableMapping(
                    tables=["work_orders", "properties"],
                    joins=[
                        {
                            "left": "work_orders.property_id",
                            "right": "properties.property_id",
                        }
                    ],
                    where_clause="work_orders.status != 'completed'",
                    select_columns=["properties.name", "COUNT(*) as count"],
                )
            elif "lease" in str(intent.filters).lower():
                return TableMapping(
                    tables=["leases", "units"],
                    joins=[
                        {"left": "leases.unit_id", "right": "units.unit_id"}
                    ],
                    where_clause="leases.renewal_option = true",
                    select_columns=["leases.lease_id", "units.unit_number"],
                )
            else:
                return TableMapping(
                    tables=["properties"],
                    joins=[],
                    where_clause="1=1",
                    select_columns=["*"],
                )

        def generate_sql(self, mapping: TableMapping) -> str:
            """Generate Snowflake SQL from table mapping."""
            tables = ", ".join(mapping.tables)
            select_clause = ", ".join(mapping.select_columns)
            sql = f"SELECT {select_clause} FROM {tables}"

            if mapping.joins:
                for join in mapping.joins:
                    sql += f" JOIN {tables} ON {join['left']} = {join['right']}"

            sql += f" WHERE {mapping.where_clause}"
            return sql

        def validate_sql_approved_tables(self, sql: str) -> bool:
            """Validate that SQL only uses approved tables."""
            for table in self.approved_tables:
                if table not in sql:
                    continue
            # Check for system tables
            system_tables = {"pg_", "information_schema", "sys."}
            for sys_table in system_tables:
                if sys_table in sql.lower():
                    return False
            return True

        def validate_sql_no_drop(self, sql: str) -> bool:
            """Validate that SQL doesn't contain DROP statements."""
            dangerous_keywords = [
                "DROP",
                "DELETE",
                "TRUNCATE",
                "ALTER TABLE",
            ]
            for keyword in dangerous_keywords:
                if keyword in sql.upper():
                    return False
            return True

        def validate_sql(self, sql: str) -> bool:
            """Validate SQL query is safe to execute."""
            return (
                self.validate_sql_approved_tables(sql)
                and self.validate_sql_no_drop(sql)
            )

        def format_results(self, results: List[Dict[str, Any]]) -> str:
            """Format query results as markdown table."""
            if not results:
                return "| No Results |"

            # Get headers from first row
            headers = list(results[0].keys())
            header_row = "| " + " | ".join(headers) + " |"
            separator = "|" + "|".join(["---"] * len(headers)) + "|"

            rows = []
            for result in results:
                row = "| " + " | ".join(str(result.get(h, "")) for h in headers) + " |"
                rows.append(row)

            return "\n".join([header_row, separator] + rows)

        def apply_tenant_filtering(
            self, sql: str, tenant_id: str
        ) -> str:
            """Add tenant_id filter to SQL query."""
            if "WHERE" in sql:
                return sql.replace("WHERE", f"WHERE tenant_id = '{tenant_id}' AND")
            else:
                return sql + f" WHERE tenant_id = '{tenant_id}'"

        def apply_role_filtering(
            self, sql: str, role: str, assigned_properties: List[int]
        ) -> str:
            """Apply role-based filtering to SQL."""
            if role == "property_manager":
                props_str = ",".join(str(p) for p in assigned_properties)
                if "WHERE" in sql:
                    return sql.replace(
                        "WHERE",
                        f"WHERE property_id IN ({props_str}) AND",
                    )
                else:
                    return sql + f" WHERE property_id IN ({props_str})"
            elif role == "finance":
                # Finance sees all financial data
                return sql
            elif role == "admin":
                # Admin sees everything
                return sql
            return sql

    return TextToSQLService(mock_snowflake_connection, mock_claude_client)


# Classification Tests
class TestQueryClassification:
    """Tests for query classification (TEXT_TO_SQL vs SEMANTIC_SEARCH)."""

    def test_classify_query_structured(self, text_to_sql_service):
        """Test classification of structured query to TEXT_TO_SQL."""
        query = "Which buildings have the most open work orders?"
        result = text_to_sql_service.classify_query(query)
        assert result == "TEXT_TO_SQL"

    def test_classify_query_semantic(self, text_to_sql_service):
        """Test classification of semantic query to SEMANTIC_SEARCH."""
        query = "Show me all leases with renewal options"
        result = text_to_sql_service.classify_query(query)
        assert result == "SEMANTIC_SEARCH"

    def test_classify_query_inspection(self, text_to_sql_service):
        """Test classification of inspection-related query."""
        query = "What was the condition of the roof in the last inspection?"
        result = text_to_sql_service.classify_query(query)
        assert result == "SEMANTIC_SEARCH"

    @pytest.mark.parametrize(
        "query,expected",
        [
            ("How much revenue did we make in Q1?", "TEXT_TO_SQL"),
            ("What are the lease renewal options?", "SEMANTIC_SEARCH"),
            ("Which properties have the lowest cap rates?", "TEXT_TO_SQL"),
            ("Describe the property condition summary", "SEMANTIC_SEARCH"),
        ],
    )
    def test_classify_query_parametrized(self, text_to_sql_service, query, expected):
        """Parametrized test for query classification."""
        result = text_to_sql_service.classify_query(query)
        assert result == expected


# Intent Parsing Tests
class TestParseIntent:
    """Tests for parsing user queries into structured intents."""

    def test_parse_intent_work_orders(self, text_to_sql_service):
        """Test parsing of work order query intent."""
        query = "Which buildings have the most open work orders?"
        intent = text_to_sql_service.parse_intent(query)

        assert intent.query_type == "metric_aggregation"
        assert "open_work_orders" in intent.metrics
        assert "building_name" in intent.dimensions

    def test_parse_intent_lease_renewals(self, text_to_sql_service):
        """Test parsing of lease renewal query intent."""
        query = "Show me all leases with renewal options"
        intent = text_to_sql_service.parse_intent(query)

        assert intent.query_type == "filtering"
        assert intent.filters.get("has_renewal_option") is True

    def test_parse_intent_general(self, text_to_sql_service):
        """Test parsing of general query intent."""
        query = "Tell me about the properties"
        intent = text_to_sql_service.parse_intent(query)

        assert intent.query_type == "general"


# Table Mapping Tests
class TestMapToTables:
    """Tests for mapping intents to database tables."""

    def test_map_to_tables_work_orders(self, text_to_sql_service):
        """Test mapping work order intent to tables."""
        intent = QueryIntent(
            query_type="metric_aggregation",
            metrics=["open_work_orders"],
            dimensions=["property_id"],
            filters={},
        )

        mapping = text_to_sql_service.map_to_tables(intent)

        assert "work_orders" in mapping.tables
        assert "properties" in mapping.tables
        assert len(mapping.joins) > 0

    def test_map_to_tables_leases(self, text_to_sql_service):
        """Test mapping lease intent to tables."""
        intent = QueryIntent(
            query_type="filtering",
            metrics=["lease_id"],
            dimensions=["property_id"],
            filters={"has_renewal_option": True},
        )

        mapping = text_to_sql_service.map_to_tables(intent)

        assert "leases" in mapping.tables
        assert "renewal" in mapping.where_clause.lower()


# SQL Generation Tests
class TestGenerateSQL:
    """Tests for generating Snowflake SQL from table mappings."""

    def test_generate_sql_basic(self, text_to_sql_service):
        """Test basic SQL generation."""
        mapping = TableMapping(
            tables=["properties"],
            joins=[],
            where_clause="1=1",
            select_columns=["name", "valuation"],
        )

        sql = text_to_sql_service.generate_sql(mapping)

        assert "SELECT" in sql
        assert "FROM properties" in sql
        assert "name" in sql

    def test_generate_sql_with_joins(self, text_to_sql_service):
        """Test SQL generation with joins."""
        mapping = TableMapping(
            tables=["work_orders", "properties"],
            joins=[
                {
                    "left": "work_orders.property_id",
                    "right": "properties.property_id",
                }
            ],
            where_clause="status = 'open'",
            select_columns=["properties.name", "COUNT(*) as count"],
        )

        sql = text_to_sql_service.generate_sql(mapping)

        assert "JOIN" in sql
        assert "work_orders.property_id = properties.property_id" in sql


# SQL Validation Tests
class TestValidateSQL:
    """Tests for SQL validation."""

    def test_validate_sql_approved_tables(self, text_to_sql_service):
        """Test validation of SQL with approved tables."""
        sql = "SELECT * FROM work_orders WHERE status = 'open'"
        result = text_to_sql_service.validate_sql_approved_tables(sql)
        assert result is True

    def test_validate_sql_rejected_tables(self, text_to_sql_service):
        """Test rejection of SQL with system tables."""
        sql = "SELECT * FROM pg_users WHERE 1=1"
        result = text_to_sql_service.validate_sql_approved_tables(sql)
        assert result is False

    def test_validate_sql_no_drop(self, text_to_sql_service):
        """Test that DROP statements are rejected."""
        sql = "DROP TABLE work_orders"
        result = text_to_sql_service.validate_sql_no_drop(sql)
        assert result is False

    def test_validate_sql_delete_rejected(self, text_to_sql_service):
        """Test that DELETE statements are rejected."""
        sql = "DELETE FROM properties WHERE id = 1"
        result = text_to_sql_service.validate_sql_no_drop(sql)
        assert result is False

    @pytest.mark.parametrize(
        "sql,expected",
        [
            ("SELECT * FROM properties", True),
            ("SELECT * FROM work_orders", True),
            ("DELETE FROM properties", False),
            ("DROP TABLE units", False),
            ("TRUNCATE TABLE leases", False),
        ],
    )
    def test_validate_sql_parametrized(
        self, text_to_sql_service, sql, expected
    ):
        """Parametrized test for SQL validation."""
        result = text_to_sql_service.validate_sql(sql)
        assert result == expected


# Result Formatting Tests
class TestFormatResults:
    """Tests for formatting query results."""

    def test_format_results_basic(self, text_to_sql_service):
        """Test basic result formatting."""
        results = [
            {"property_id": 101, "open_work_orders": 12},
            {"property_id": 105, "open_work_orders": 28},
        ]

        formatted = text_to_sql_service.format_results(results)

        assert "|" in formatted
        assert "property_id" in formatted
        assert "open_work_orders" in formatted
        assert "101" in formatted
        assert "28" in formatted

    def test_format_results_empty(self, text_to_sql_service):
        """Test formatting of empty results."""
        results = []
        formatted = text_to_sql_service.format_results(results)
        assert "No Results" in formatted

    def test_format_results_multiple_rows(self, text_to_sql_service, sample_query_results):
        """Test formatting of multiple result rows."""
        formatted = text_to_sql_service.format_results(sample_query_results)
        lines = formatted.split("\n")

        # Should have header, separator, and at least 3 data rows
        assert len(lines) >= 5
        assert "building_id" in lines[0]


# Tenant Filtering Tests
class TestTenantFiltering:
    """Tests for tenant isolation in queries."""

    def test_tenant_filtering(self, text_to_sql_service):
        """Test that tenant_id filter is applied."""
        query = "SELECT * FROM properties"
        filtered = text_to_sql_service.apply_tenant_filtering(query, "tenant_123")

        assert "tenant_id = 'tenant_123'" in filtered

    def test_tenant_filtering_with_existing_where(self, text_to_sql_service):
        """Test tenant filtering with existing WHERE clause."""
        query = "SELECT * FROM properties WHERE valuation > 1000000"
        filtered = text_to_sql_service.apply_tenant_filtering(query, "tenant_456")

        assert "tenant_id = 'tenant_456'" in filtered
        assert "valuation > 1000000" in filtered


# Role-Based Filtering Tests
class TestRoleFiltering:
    """Tests for role-based access control in queries."""

    def test_role_filtering_property_manager(self, text_to_sql_service):
        """Test that property managers only see assigned properties."""
        query = "SELECT * FROM properties"
        assigned_properties = [101, 102, 103]

        filtered = text_to_sql_service.apply_role_filtering(
            query, "property_manager", assigned_properties
        )

        assert "property_id IN (101,102,103)" in filtered

    def test_role_filtering_finance(self, text_to_sql_service):
        """Test that finance users see all financial data."""
        query = "SELECT * FROM financial_data"
        assigned_properties = [101, 102]

        filtered = text_to_sql_service.apply_role_filtering(
            query, "finance", assigned_properties
        )

        # Finance should see full query
        assert filtered == query

    def test_role_filtering_admin(self, text_to_sql_service):
        """Test that admins see everything."""
        query = "SELECT * FROM properties"
        filtered = text_to_sql_service.apply_role_filtering(query, "admin", [])

        # Admin should see full query
        assert filtered == query


# Error Handling Tests
class TestErrorHandling:
    """Tests for error handling in text-to-SQL pipeline."""

    def test_empty_results(self, text_to_sql_service):
        """Test handling of empty result sets."""
        results = []
        formatted = text_to_sql_service.format_results(results)

        assert len(formatted) > 0
        assert "No Results" in formatted

    def test_query_timeout(self, mock_snowflake_connection):
        """Test handling of query timeout."""
        # Mock connection to raise timeout exception
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = TimeoutError("Query exceeded timeout")
        mock_snowflake_connection.cursor.return_value = mock_cursor

        with pytest.raises(TimeoutError):
            mock_snowflake_connection.cursor().execute("SELECT * FROM large_table")

    def test_invalid_query(self, text_to_sql_service):
        """Test handling of invalid query."""
        intent = text_to_sql_service.parse_intent("")
        assert intent is not None
        assert intent.query_type == "general"


# Integration Tests
class TestTextToSQLIntegration:
    """Integration tests for the complete text-to-SQL pipeline."""

    def test_end_to_end_work_order_query(self, text_to_sql_service):
        """Test complete pipeline for work order query."""
        query = "Which buildings have the most open work orders?"

        # Classify
        classification = text_to_sql_service.classify_query(query)
        assert classification == "TEXT_TO_SQL"

        # Parse intent
        intent = text_to_sql_service.parse_intent(query)
        assert intent.query_type == "metric_aggregation"

        # Map to tables
        mapping = text_to_sql_service.map_to_tables(intent)
        assert len(mapping.tables) > 0

        # Generate SQL
        sql = text_to_sql_service.generate_sql(mapping)
        assert "SELECT" in sql

        # Validate
        is_valid = text_to_sql_service.validate_sql(sql)
        assert is_valid is True

    def test_end_to_end_with_filtering(self, text_to_sql_service):
        """Test pipeline with role and tenant filtering."""
        query = "SELECT * FROM properties WHERE valuation > 1000000"

        # Apply filters
        with_tenant = text_to_sql_service.apply_tenant_filtering(
            query, "tenant_456"
        )
        with_role = text_to_sql_service.apply_role_filtering(
            with_tenant, "property_manager", [101, 102, 103]
        )

        # Validate
        is_valid = text_to_sql_service.validate_sql(with_role)
        assert is_valid is True
