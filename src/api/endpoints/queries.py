"""
Query Endpoints - Natural Language to SQL Query Execution

Provides endpoints for:
- Submitting natural language queries
- Retrieving query results
- Query history and management
- Saving queries for reuse
"""

import logging
from typing import Optional
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Query as FastAPIQuery
from pydantic import BaseModel, Field

from src.api.auth import get_current_user, UserContext, require_role
from src.core.exceptions import QueryExecutionError, ValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/queries")


# ============================================================================
# Request/Response Models
# ============================================================================

class QueryRequest(BaseModel):
    """Request model for submitting a new query."""
    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Natural language query text",
    )
    property_ids: Optional[list[str]] = Field(
        None,
        description="Optional list of property IDs to scope the query",
    )
    timeout_seconds: int = Field(
        30,
        ge=5,
        le=300,
        description="Query execution timeout",
    )


class QueryResultItem(BaseModel):
    """Single result item from query execution."""
    id: str = Field(..., description="Result item ID")
    data: dict = Field(..., description="Result data")
    relevance_score: Optional[float] = Field(
        None,
        description="Relevance score (0-1) for semantic results",
    )


class QueryResponse(BaseModel):
    """Response model for executed query."""
    query_id: str = Field(..., description="Unique query identifier")
    query: str = Field(..., description="Original query text")
    query_type: str = Field(..., description="Query type: sql, semantic, hybrid")
    status: str = Field(..., description="Status: completed, processing, failed")
    results: list[QueryResultItem] = Field(..., description="Query results")
    total_results: int = Field(..., description="Total number of results")
    execution_time_ms: int = Field(..., description="Query execution time in milliseconds")
    generated_sql: Optional[str] = Field(
        None,
        description="Generated SQL query (if applicable)",
    )
    follow_up_questions: list[str] = Field(
        default_factory=list,
        description="Suggested follow-up questions",
    )
    error: Optional[str] = Field(
        None,
        description="Error message if query failed",
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)


class QueryHistoryItem(BaseModel):
    """Query history item."""
    query_id: str
    query: str
    query_type: str
    status: str
    created_at: datetime
    execution_time_ms: Optional[int] = None
    result_count: int = 0


class QueryHistoryResponse(BaseModel):
    """Paginated query history response."""
    items: list[QueryHistoryItem]
    total: int
    page: int
    page_size: int


class SavedQuery(BaseModel):
    """Saved query for reuse."""
    id: str = Field(..., description="Saved query ID")
    name: str = Field(..., description="User-friendly name")
    description: Optional[str] = Field(None, description="Query description")
    query: str = Field(..., description="Query text")
    tags: list[str] = Field(default_factory=list, description="Query tags")
    created_at: datetime
    updated_at: datetime
    execution_count: int = Field(default=0, description="Number of times executed")


class SaveQueryRequest(BaseModel):
    """Request to save a query."""
    query_id: str = Field(..., description="Query ID to save")
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Friendly name for saved query",
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional description",
    )
    tags: list[str] = Field(default_factory=list, description="Optional tags")


class SavedQueryResponse(BaseModel):
    """Response after saving a query."""
    saved_query_id: str
    message: str


# ============================================================================
# Endpoints
# ============================================================================

@router.post(
    "",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit natural language query",
    description=(
        "Submit a natural language query against the property database. "
        "The system will classify the query type and execute appropriate SQL or semantic search."
    ),
)
async def submit_query(
    request: QueryRequest,
    user: UserContext = Depends(get_current_user),
) -> QueryResponse:
    """
    Submit a natural language query.
    
    The query is classified (SQL vs semantic) and executed against:
    - Snowflake data warehouse (for SQL queries)
    - Document embeddings (for semantic/document queries)
    - Hybrid search (combining both)
    
    Args:
        request: Query request with natural language query text
        user: Current authenticated user
        
    Returns:
        QueryResponse with results, metadata, and follow-up suggestions
        
    Raises:
        HTTPException: 400 if query validation fails
        HTTPException: 500 if execution fails
    """
    query_id = str(uuid4())
    
    try:
        # Validate query
        if not request.query.strip():
            raise ValidationError("Query cannot be empty")
        
        logger.info(
            f"[{query_id}] Submitting query from user {user.user_id}: {request.query[:100]}"
        )
        
        # In production, integrate with query router to:
        # 1. Classify query type (SQL, semantic, hybrid)
        # 2. Extract intent and entities
        # 3. Generate SQL if needed
        # 4. Execute and collect results
        # 5. Generate follow-up questions
        
        # Placeholder response
        execution_time_ms = 150
        
        return QueryResponse(
            query_id=query_id,
            query=request.query,
            query_type="hybrid",
            status="completed",
            results=[
                QueryResultItem(
                    id="result_1",
                    data={
                        "property_id": "prop_123",
                        "address": "123 Main St",
                        "value": "$1,250,000",
                    },
                    relevance_score=0.95,
                )
            ],
            total_results=1,
            execution_time_ms=execution_time_ms,
            generated_sql="SELECT * FROM properties WHERE address LIKE '%Main%'",
            follow_up_questions=[
                "What is the rental income for this property?",
                "Show me comparable properties in this area",
            ],
            created_at=datetime.utcnow(),
        )
        
    except QueryExecutionError as e:
        logger.error(f"[{query_id}] Query execution failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message,
        )
    except Exception as e:
        logger.error(f"[{query_id}] Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute query",
        )


@router.get(
    "/{query_id}",
    response_model=QueryResponse,
    summary="Get query result",
    description="Retrieve the result of a previously executed query by ID.",
)
async def get_query_result(
    query_id: str,
    user: UserContext = Depends(get_current_user),
) -> QueryResponse:
    """
    Retrieve a specific query result.
    
    Args:
        query_id: ID of the query to retrieve
        user: Current authenticated user
        
    Returns:
        QueryResponse with query details and results
        
    Raises:
        HTTPException: 404 if query not found
        HTTPException: 403 if user doesn't have access
    """
    try:
        logger.info(f"Retrieving query {query_id} for user {user.user_id}")
        
        # In production:
        # 1. Fetch query from database
        # 2. Check user has access (owned by tenant)
        # 3. Return with cached or computed results
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Query {query_id} not found",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving query {query_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve query",
        )


@router.get(
    "",
    response_model=QueryHistoryResponse,
    summary="Get query history",
    description="Retrieve paginated query history for the current user.",
)
async def get_query_history(
    page: int = FastAPIQuery(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = FastAPIQuery(
        20, ge=1, le=100, description="Results per page"
    ),
    status_filter: Optional[str] = FastAPIQuery(
        None,
        description="Filter by status: completed, processing, failed",
    ),
    user: UserContext = Depends(get_current_user),
) -> QueryHistoryResponse:
    """
    Get query history for current user.
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of results per page
        status_filter: Optional status filter
        user: Current authenticated user
        
    Returns:
        Paginated query history
    """
    try:
        logger.info(
            f"Fetching query history for user {user.user_id} "
            f"(page {page}, size {page_size})"
        )
        
        # In production:
        # 1. Query database with pagination
        # 2. Filter by tenant_id and user_id
        # 3. Apply status filter if provided
        # 4. Sort by created_at DESC
        
        return QueryHistoryResponse(
            items=[],
            total=0,
            page=page,
            page_size=page_size,
        )
        
    except Exception as e:
        logger.error(f"Error fetching query history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch query history",
        )


@router.post(
    "/save",
    response_model=SavedQueryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save query for reuse",
    description="Save a query with a friendly name and optional description for future reuse.",
)
async def save_query(
    request: SaveQueryRequest,
    user: UserContext = Depends(get_current_user),
) -> SavedQueryResponse:
    """
    Save a query for reuse.
    
    Args:
        request: Save query request with name, description, and tags
        user: Current authenticated user
        
    Returns:
        SavedQueryResponse with saved query ID
        
    Raises:
        HTTPException: 400 if validation fails
        HTTPException: 404 if query not found
    """
    saved_query_id = str(uuid4())
    
    try:
        logger.info(
            f"Saving query {request.query_id} as '{request.name}' "
            f"for user {user.user_id}"
        )
        
        # In production:
        # 1. Fetch original query
        # 2. Verify user has access
        # 3. Create saved_queries record
        # 4. Index for search
        
        return SavedQueryResponse(
            saved_query_id=saved_query_id,
            message=f"Query saved as '{request.name}'",
        )
        
    except Exception as e:
        logger.error(f"Error saving query: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save query",
        )


@router.get(
    "/saved",
    response_model=list[SavedQuery],
    summary="List saved queries",
    description="Retrieve all saved queries for the current user.",
)
async def get_saved_queries(
    user: UserContext = Depends(get_current_user),
) -> list[SavedQuery]:
    """
    Get all saved queries for current user.
    
    Args:
        user: Current authenticated user
        
    Returns:
        List of saved queries
    """
    try:
        logger.info(f"Fetching saved queries for user {user.user_id}")
        
        # In production:
        # Query database for saved_queries where tenant_id = user.tenant_id
        # and created_by_user_id = user.user_id (or shared with user)
        
        return []
        
    except Exception as e:
        logger.error(f"Error fetching saved queries: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch saved queries",
        )
