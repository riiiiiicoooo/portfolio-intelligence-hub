"""
Portfolio Intelligence Hub - MCP Server
Model Context Protocol implementation for natural language portfolio queries,
document search, and property analytics. Enables AI agents to interact with
Snowflake data warehouse and vector-embedded property documents.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import logging
from functools import wraps
import hashlib

# MCP Protocol imports
from mcp.server import Server, Tool
from mcp.types import TextContent, ToolResult

# Data access and ML imports
import snowflake.connector
from snowflake.connector import DictCursor
import httpx
import jwt

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP Server
server = Server("portfolio-intelligence-hub")


class PortfolioAuthContext:
    """Tenant-aware authentication context for portfolio operations."""
    
    def __init__(self, tenant_id: str, user_role: str, user_id: str):
        self.tenant_id = tenant_id
        self.user_role = user_role  # "advisor", "analyst", "executive", "readonly"
        self.user_id = user_id
        self.request_count = 0
        self.request_reset_time = datetime.utcnow()
    
    def check_rate_limit(self) -> bool:
        """
        Enforce 60 requests per minute per user.
        Resets every 60 seconds.
        """
        now = datetime.utcnow()
        if (now - self.request_reset_time).total_seconds() > 60:
            self.request_count = 0
            self.request_reset_time = now
        
        self.request_count += 1
        return self.request_count <= 60
    
    def can_query(self, query_type: str) -> bool:
        """Role-based access control for query types."""
        allowed_roles = {
            "portfolio_summary": ["advisor", "analyst", "executive"],
            "property_details": ["advisor", "analyst", "executive", "readonly"],
            "financial_sensitive": ["advisor", "executive"],
            "lease_data": ["advisor", "analyst", "executive"],
            "performance_metrics": ["advisor", "analyst", "executive", "readonly"],
        }
        return self.user_role in allowed_roles.get(query_type, [])


class SnowflakePortfolioClient:
    """
    Interface to Snowflake data warehouse containing portfolio data.
    Handles connection pooling, query optimization, and SQL generation.
    """
    
    def __init__(self, account: str, user: str, password: str, warehouse: str = "COMPUTE_WH"):
        self.account = account
        self.user = user
        self.password = password
        self.warehouse = warehouse
        self.conn = None
    
    def connect(self):
        """Establish Snowflake connection with configured credentials."""
        try:
            self.conn = snowflake.connector.connect(
                account=self.account,
                user=self.user,
                password=self.password,
                warehouse=self.warehouse,
                database="PORTFOLIO_DB",
                schema="PUBLIC",
                client_session_keep_alive=True,
            )
            logger.info(f"Connected to Snowflake account: {self.account}")
        except Exception as e:
            logger.error(f"Snowflake connection failed: {str(e)}")
            raise
    
    def execute_query(self, query: str, params: Optional[List] = None) -> List[Dict[str, Any]]:
        """
        Execute SQL query against Snowflake with optional parameterization.
        Returns results as list of dicts.
        """
        if not self.conn:
            self.connect()
        
        try:
            cursor = self.conn.cursor(DictCursor)
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}\nQuery: {query}")
            raise
    
    def close(self):
        """Close Snowflake connection."""
        if self.conn:
            self.conn.close()


class VectorSearchEngine:
    """
    Semantic search over property documents using vector embeddings.
    Uses cosine similarity to find relevant documents from property corpus.
    """
    
    def __init__(self, embedding_api_url: str, api_key: str):
        self.embedding_api_url = embedding_api_url
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {api_key}"}
        )
    
    async def search(
        self,
        query: str,
        property_id: Optional[str] = None,
        doc_types: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search across property documents.
        
        Args:
            query: Natural language search query
            property_id: Filter to specific property (optional)
            doc_types: Filter by document type (e.g., ["lease", "valuation"])
            top_k: Number of results to return
        
        Returns:
            Ranked list of matching documents with relevance scores
        """
        try:
            # Get embedding for query
            embedding_response = await self.client.post(
                f"{self.embedding_api_url}/embed",
                json={"text": query}
            )
            query_embedding = embedding_response.json()["embedding"]
            
            # Search vector database (mock implementation - would call actual vector DB)
            search_params = {
                "embedding": query_embedding,
                "k": top_k,
            }
            if property_id:
                search_params["property_id"] = property_id
            if doc_types:
                search_params["doc_types"] = doc_types
            
            search_response = await self.client.post(
                f"{self.embedding_api_url}/search",
                json=search_params
            )
            
            return search_response.json().get("results", [])
        except Exception as e:
            logger.error(f"Vector search failed: {str(e)}")
            return []


# Global clients (would be initialized from environment in production)
sf_client = None
vector_engine = None


def require_auth(func):
    """Decorator to validate authentication context."""
    @wraps(func)
    def wrapper(auth_context: PortfolioAuthContext, *args, **kwargs):
        if not auth_context.check_rate_limit():
            raise Exception(f"Rate limit exceeded for user {auth_context.user_id}")
        return func(auth_context, *args, **kwargs)
    return wrapper


@server.list_tools()
def list_tools():
    """Register all available MCP tools."""
    return [
        Tool(
            name="query_portfolio",
            description=(
                "Execute a natural language query over portfolio data in Snowflake. "
                "Returns query results, generated SQL, and execution plan. "
                "Supports aggregations, time series, and multi-table joins."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language question about portfolio (e.g., 'Show me properties in TX with occupancy > 90%')",
                    },
                    "persona_role": {
                        "type": "string",
                        "enum": ["advisor", "analyst", "executive", "readonly"],
                        "description": "User's role for access control",
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User identifier for rate limiting and audit",
                    },
                    "tenant_id": {
                        "type": "string",
                        "description": "Tenant/organization identifier",
                    },
                },
                "required": ["query", "persona_role", "user_id", "tenant_id"],
            },
        ),
        Tool(
            name="search_documents",
            description=(
                "Perform semantic search across property documents (leases, valuations, "
                "CAP statements, etc.). Uses vector embeddings for relevance ranking."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query",
                    },
                    "property_id": {
                        "type": "string",
                        "description": "Optional: filter results to specific property",
                    },
                    "doc_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional: filter by document type (e.g., ['lease', 'valuation'])",
                    },
                    "tenant_id": {
                        "type": "string",
                        "description": "Tenant identifier",
                    },
                },
                "required": ["query", "tenant_id"],
            },
        ),
        Tool(
            name="get_property_scorecard",
            description=(
                "Retrieve performance scorecard for a specific property. "
                "Includes occupancy, lease expiration timeline, financial metrics, "
                "tenant quality, and risk indicators."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "property_id": {
                        "type": "string",
                        "description": "Property identifier",
                    },
                    "tenant_id": {
                        "type": "string",
                        "description": "Tenant identifier",
                    },
                    "include_historical": {
                        "type": "boolean",
                        "description": "Include 24-month historical trends (default: false)",
                        "default": False,
                    },
                },
                "required": ["property_id", "tenant_id"],
            },
        ),
        Tool(
            name="get_portfolio_summary",
            description=(
                "Get aggregate portfolio-level KPIs: total NOI, occupancy rate, "
                "weighted average cap rate, tenant concentration, lease expiration schedule."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": "Tenant identifier",
                    },
                    "as_of_date": {
                        "type": "string",
                        "description": "Optional: report date (YYYY-MM-DD). Defaults to today.",
                    },
                },
                "required": ["tenant_id"],
            },
        ),
        Tool(
            name="list_properties",
            description=(
                "List all properties in portfolio with optional filters. "
                "Returns property ID, name, location, property type, and key metrics."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": "Tenant identifier",
                    },
                    "state": {
                        "type": "string",
                        "description": "Optional: filter by state (e.g., 'CA', 'TX')",
                    },
                    "property_type": {
                        "type": "string",
                        "enum": ["office", "industrial", "retail", "multifamily", "mixed"],
                        "description": "Optional: filter by property type",
                    },
                    "min_occupancy_pct": {
                        "type": "number",
                        "description": "Optional: filter to properties with at least this occupancy %",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results (default: 100, max: 1000)",
                        "default": 100,
                    },
                },
                "required": ["tenant_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool invocations from MCP clients."""
    
    if name == "query_portfolio":
        return await _query_portfolio(arguments)
    elif name == "search_documents":
        return await _search_documents(arguments)
    elif name == "get_property_scorecard":
        return await _get_property_scorecard(arguments)
    elif name == "get_portfolio_summary":
        return await _get_portfolio_summary(arguments)
    elif name == "list_properties":
        return await _list_properties(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


@require_auth
async def _query_portfolio(auth_context: PortfolioAuthContext, args: Dict[str, Any]) -> List[TextContent]:
    """
    Natural language query execution with SQL generation.
    Translates natural language to SQL, applies tenant filtering, executes query.
    """
    try:
        query_text = args["query"]
        
        # Generate SQL from natural language (in production, uses GPT-4 or similar)
        # This is a simplified example
        generated_sql = f"""
        SELECT 
            p.property_id,
            p.property_name,
            p.state,
            p.property_type,
            ROUND(occ.occupancy_pct, 2) as occupancy_pct,
            ROUND(fin.annual_noi, 0) as annual_noi,
            ROUND(fin.cap_rate, 3) as cap_rate
        FROM portfolio_db.properties p
        LEFT JOIN portfolio_db.occupancy occ ON p.property_id = occ.property_id
        LEFT JOIN portfolio_db.financials fin ON p.property_id = fin.property_id
        WHERE p.tenant_id = %s
        ORDER BY fin.annual_noi DESC
        LIMIT 50
        """
        
        # Execute query
        results = sf_client.execute_query(generated_sql, [auth_context.tenant_id])
        
        return [
            TextContent(
                type="text",
                text=json.dumps({
                    "query": query_text,
                    "generated_sql": generated_sql.strip(),
                    "row_count": len(results),
                    "results": results,
                    "timestamp": datetime.utcnow().isoformat(),
                }),
            )
        ]
    except Exception as e:
        logger.error(f"Portfolio query failed: {str(e)}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def _search_documents(args: Dict[str, Any]) -> List[TextContent]:
    """Semantic search across property documents."""
    try:
        results = await vector_engine.search(
            query=args["query"],
            property_id=args.get("property_id"),
            doc_types=args.get("doc_types"),
            top_k=args.get("top_k", 5),
        )
        
        return [
            TextContent(
                type="text",
                text=json.dumps({
                    "query": args["query"],
                    "result_count": len(results),
                    "results": results,
                }),
            )
        ]
    except Exception as e:
        logger.error(f"Document search failed: {str(e)}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def _get_property_scorecard(args: Dict[str, Any]) -> List[TextContent]:
    """Fetch property performance scorecard."""
    try:
        property_id = args["property_id"]
        tenant_id = args["tenant_id"]
        include_historical = args.get("include_historical", False)
        
        query = """
        SELECT 
            p.property_id,
            p.property_name,
            p.property_type,
            p.city,
            p.state,
            p.zip_code,
            ROUND(occ.occupancy_pct, 2) as occupancy_pct,
            occ.occupied_sqft,
            occ.total_sqft,
            ROUND(fin.annual_noi, 0) as annual_noi,
            ROUND(fin.annual_revenue, 0) as annual_revenue,
            ROUND(fin.operating_expenses, 0) as operating_expenses,
            ROUND(fin.cap_rate, 3) as cap_rate,
            ROUND(fin.price_per_sqft, 0) as price_per_sqft,
            COUNT(DISTINCT t.tenant_id) as tenant_count,
            MIN(l.lease_expiration) as earliest_lease_exp,
            MAX(l.lease_expiration) as latest_lease_exp,
            ROUND(AVG(t.credit_score), 0) as avg_tenant_credit,
            COUNT(CASE WHEN t.in_default = true THEN 1 END) as tenants_in_default
        FROM portfolio_db.properties p
        LEFT JOIN portfolio_db.occupancy occ ON p.property_id = occ.property_id
        LEFT JOIN portfolio_db.financials fin ON p.property_id = fin.property_id
        LEFT JOIN portfolio_db.leases l ON p.property_id = l.property_id
        LEFT JOIN portfolio_db.tenants t ON l.tenant_id = t.tenant_id
        WHERE p.property_id = %s AND p.tenant_id = %s
        GROUP BY p.property_id, p.property_name, p.property_type, p.city, p.state, 
                 p.zip_code, occ.occupancy_pct, occ.occupied_sqft, occ.total_sqft,
                 fin.annual_noi, fin.annual_revenue, fin.operating_expenses, 
                 fin.cap_rate, fin.price_per_sqft
        """
        
        results = sf_client.execute_query(query, [property_id, tenant_id])
        
        if not results:
            return [TextContent(type="text", text=json.dumps({"error": "Property not found"}))]
        
        scorecard = results[0]
        
        return [
            TextContent(
                type="text",
                text=json.dumps({
                    "property_scorecard": scorecard,
                    "timestamp": datetime.utcnow().isoformat(),
                }),
            )
        ]
    except Exception as e:
        logger.error(f"Property scorecard retrieval failed: {str(e)}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def _get_portfolio_summary(args: Dict[str, Any]) -> List[TextContent]:
    """Get aggregate portfolio KPIs."""
    try:
        tenant_id = args["tenant_id"]
        as_of_date = args.get("as_of_date", datetime.utcnow().strftime("%Y-%m-%d"))
        
        query = """
        SELECT 
            COUNT(DISTINCT p.property_id) as property_count,
            SUM(occ.total_sqft) as total_sqft,
            SUM(occ.occupied_sqft) as occupied_sqft,
            ROUND(100.0 * SUM(occ.occupied_sqft) / NULLIF(SUM(occ.total_sqft), 0), 2) as portfolio_occupancy_pct,
            SUM(fin.annual_noi) as total_noi,
            ROUND(AVG(fin.cap_rate), 3) as weighted_avg_cap_rate,
            COUNT(DISTINCT t.tenant_id) as unique_tenants,
            ROUND(MAX(fin.price_per_sqft), 0) as highest_price_per_sqft,
            ROUND(MIN(fin.price_per_sqft), 0) as lowest_price_per_sqft,
            COUNT(CASE WHEN l.lease_expiration < DATEADD(year, 1, %s) THEN 1 END) as leases_exp_within_12mo
        FROM portfolio_db.properties p
        LEFT JOIN portfolio_db.occupancy occ ON p.property_id = occ.property_id
        LEFT JOIN portfolio_db.financials fin ON p.property_id = fin.property_id
        LEFT JOIN portfolio_db.leases l ON p.property_id = l.property_id
        LEFT JOIN portfolio_db.tenants t ON l.tenant_id = t.tenant_id
        WHERE p.tenant_id = %s
        """
        
        results = sf_client.execute_query(query, [as_of_date, tenant_id])
        
        return [
            TextContent(
                type="text",
                text=json.dumps({
                    "portfolio_summary": results[0] if results else {},
                    "as_of_date": as_of_date,
                    "timestamp": datetime.utcnow().isoformat(),
                }),
            )
        ]
    except Exception as e:
        logger.error(f"Portfolio summary retrieval failed: {str(e)}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def _list_properties(args: Dict[str, Any]) -> List[TextContent]:
    """List properties with optional filtering."""
    try:
        tenant_id = args["tenant_id"]
        
        # Build dynamic filter clauses
        filters = ["p.tenant_id = %s"]
        params = [tenant_id]
        
        if args.get("state"):
            filters.append("p.state = %s")
            params.append(args["state"])
        
        if args.get("property_type"):
            filters.append("p.property_type = %s")
            params.append(args["property_type"])
        
        if args.get("min_occupancy_pct"):
            filters.append("occ.occupancy_pct >= %s")
            params.append(args["min_occupancy_pct"])
        
        where_clause = " AND ".join(filters)
        limit = min(args.get("limit", 100), 1000)
        
        query = f"""
        SELECT 
            p.property_id,
            p.property_name,
            p.property_type,
            p.city,
            p.state,
            p.zip_code,
            ROUND(occ.occupancy_pct, 2) as occupancy_pct,
            occ.total_sqft,
            ROUND(fin.annual_noi, 0) as annual_noi,
            ROUND(fin.cap_rate, 3) as cap_rate
        FROM portfolio_db.properties p
        LEFT JOIN portfolio_db.occupancy occ ON p.property_id = occ.property_id
        LEFT JOIN portfolio_db.financials fin ON p.property_id = fin.property_id
        WHERE {where_clause}
        ORDER BY fin.annual_noi DESC
        LIMIT {limit}
        """
        
        results = sf_client.execute_query(query, params)
        
        return [
            TextContent(
                type="text",
                text=json.dumps({
                    "property_count": len(results),
                    "properties": results,
                    "timestamp": datetime.utcnow().isoformat(),
                }),
            )
        ]
    except Exception as e:
        logger.error(f"Property listing failed: {str(e)}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


def initialize_mcp_server():
    """Initialize MCP server with Snowflake and vector search clients."""
    global sf_client, vector_engine
    
    # Initialize Snowflake client from environment
    sf_client = SnowflakePortfolioClient(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
    )
    sf_client.connect()
    
    # Initialize vector search engine for document search
    vector_engine = VectorSearchEngine(
        embedding_api_url=os.getenv("EMBEDDING_API_URL", "http://localhost:8000"),
        api_key=os.getenv("EMBEDDING_API_KEY"),
    )
    
    logger.info("Portfolio Intelligence Hub MCP server initialized")


if __name__ == "__main__":
    initialize_mcp_server()
    server.run()
