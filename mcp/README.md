# Portfolio Intelligence Hub - MCP Server

This MCP (Model Context Protocol) server enables AI agents and chat interfaces to query portfolio data, search documents, and retrieve property metrics through a standardized tool interface.

## Overview

The MCP server exposes 5 tools for portfolio analysis:
- **query_portfolio**: Natural language SQL queries over Snowflake data warehouse
- **search_documents**: Semantic search across property documents using vector embeddings
- **get_property_scorecard**: Fetch KPIs and metrics for individual properties
- **get_portfolio_summary**: Aggregate portfolio-level performance metrics
- **list_properties**: Browse portfolio with filters

## Installation

```bash
pip install mcp snowflake-connector-python httpx
```

## Environment Setup

Set these environment variables before running:

```bash
export SNOWFLAKE_ACCOUNT=xy12345.us-east-1
export SNOWFLAKE_USER=portfolio_user
export SNOWFLAKE_PASSWORD=secure_password
export EMBEDDING_API_URL=http://localhost:8000
export EMBEDDING_API_KEY=your_embedding_api_key
```

## Running the MCP Server

```bash
python mcp/server.py
```

The server will start on the default MCP transport (stdio). It's ready to accept tool calls from MCP clients.

## Integration with MCP Clients

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "portfolio-intelligence-hub": {
      "command": "python",
      "args": ["/path/to/mcp/server.py"]
    }
  }
}
```

### Cursor IDE

In Cursor settings, add as an MCP server pointing to the same script.

### Custom Client

Using the mcp-client SDK:

```python
from mcp.client import ClientSession
import asyncio

async def main():
    async with ClientSession() as session:
        # List available tools
        tools = await session.list_tools()
        
        # Call query_portfolio tool
        result = await session.call_tool(
            "query_portfolio",
            {
                "query": "Show me properties in California with > 90% occupancy",
                "persona_role": "analyst",
                "user_id": "user_123",
                "tenant_id": "tenant_456"
            }
        )
        print(result)

asyncio.run(main())
```

## Security & Access Control

### Role-Based Access Control (RBAC)
- **advisor**: Full access to all data and tools
- **analyst**: Query and reporting, limited financial data
- **executive**: High-level summaries and KPIs only
- **readonly**: View-only access to non-sensitive data

### Rate Limiting
- 60 requests per minute per user
- Enforced at the MCP server level before query execution

### Multi-Tenant Isolation
- All queries automatically filtered by tenant_id
- Snowflake row-level security (RLS) policies enforced
- User ID captured for audit logging

## Data Sources

### Snowflake Database
- **PORTFOLIO_DB.PROPERTIES**: Property master data
- **PORTFOLIO_DB.OCCUPANCY**: Current occupancy metrics
- **PORTFOLIO_DB.FINANCIALS**: Annual NOI, cap rates, valuations
- **PORTFOLIO_DB.LEASES**: Lease terms and expiration dates
- **PORTFOLIO_DB.TENANTS**: Tenant credit scores, defaults

### Vector Database
- Property documents indexed with OpenAI embeddings
- Supports semantic search across leases, appraisals, CAP statements
- Updated nightly with new documents

## Example Queries

```
"What is the total NOI in our Texas portfolio?"
"Show me properties with leases expiring within 12 months"
"List office buildings in California with occupancy < 80%"
"Find all lease amendments related to rent abatement"
"Compare cap rates across property types"
```

## Troubleshooting

### Snowflake Connection Failed
- Verify SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD
- Check that Snowflake warehouse is running
- Ensure IP is whitelisted in Snowflake account settings

### Vector Search Returning No Results
- Check EMBEDDING_API_URL and EMBEDDING_API_KEY
- Verify documents have been indexed (check logs)
- Try more general search terms

### Rate Limit Exceeded
- User has made > 60 requests in last minute
- Wait for rate limit window to reset or contact admin
