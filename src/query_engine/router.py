"""Main query classification and routing engine for Portfolio Intelligence Hub.

This module handles:
1. Classifying user queries into types (TEXT_TO_SQL, SEMANTIC_SEARCH, CACHED, HYBRID)
2. Routing queries to appropriate backends
3. Checking Redis cache for previously-answered queries
4. Aggregating results from multiple sources

PM Context: Property managers ask heterogeneous questions:
- "What's the occupancy rate?" (TEXT_TO_SQL - structured metrics)
- "Find lease terms for Unit 204" (SEMANTIC_SEARCH - unstructured docs)
- "Show properties with high vacancy and repair needs" (HYBRID - both)

This router automatically detects the right combination and returns unified results
without the user needing to choose a tool.

Reference Implementation Notes:
- Uses Claude for zero-shot classification (no ML training required)
- Redis caching reduces unnecessary processing
- Comprehensive error handling with fallback strategies
- All results include execution metadata for debugging
"""

import logging
import time
import json
import os
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import hashlib

import anthropic
import redis

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Classification of query intent and routing destination.
    
    TEXT_TO_SQL: Structured query about metrics (occupancy, NOI, rent, etc.)
                 Routes to Snowflake via text-to-SQL pipeline.
    
    SEMANTIC_SEARCH: Unstructured query about documents (leases, reports, etc.)
                     Routes to vector + BM25 search.
    
    CACHED: Previously-answered query found in Redis cache within TTL.
           Returns cached result without recomputation.
    
    HYBRID: Query requires both structured and unstructured data.
           Routes to both pipelines and merges results.
    """
    TEXT_TO_SQL = "text_to_sql"
    SEMANTIC_SEARCH = "semantic_search"
    CACHED = "cached"
    HYBRID = "hybrid"


@dataclass
class QueryResult:
    """Unified result container returned by route_query().
    
    Attributes:
        query_id: Unique identifier for this query (for caching and audit)
        query_type: Classification from QueryType enum
        results: Main result data (varies by type)
                - TEXT_TO_SQL: list of dicts from SQL
                - SEMANTIC_SEARCH: list of SearchResult dicts
                - HYBRID: dict with 'sql_results' and 'search_results' keys
        execution_time_ms: Total wall-clock time for query execution
        generated_sql: Generated SQL (for TEXT_TO_SQL and HYBRID only)
        source_documents: Document metadata for SEMANTIC_SEARCH and HYBRID
        error: Exception message if query failed (None on success)
        confidence: Confidence score in classification (0.0-1.0)
    
    Example:
        >>> result = route_query("occupancy by region", user_context)
        >>> print(f"Query type: {result.query_type.value}")
        >>> print(f"Execution: {result.execution_time_ms}ms")
        >>> for row in result.results:
        ...     print(f"{row['region']}: {row['occupancy_pct']}%")
    """
    query_id: str
    query_type: QueryType
    results: Any
    execution_time_ms: int
    generated_sql: Optional[str] = None
    source_documents: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class UserContext:
    """Authentication and authorization context for query execution.
    
    Used to enforce RBAC, tenant isolation, and audit logging.
    
    Attributes:
        user_id: Unique user identifier
        tenant_id: Multi-tenant isolation key (company/portfolio)
        role: User's role (admin, property_manager, broker, finance, executive)
        assigned_properties: List of property IDs this user can access
                           (empty list means all properties accessible)
    
    Example:
        >>> ctx = UserContext(
        ...     user_id="pm_john_123",
        ...     tenant_id="portfolio_acme",
        ...     role="property_manager",
        ...     assigned_properties=["prop_001", "prop_002"]
        ... )
    """
    user_id: str
    tenant_id: str
    role: str
    assigned_properties: List[str] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        """Validate user context on creation."""
        if not self.user_id or not self.tenant_id:
            raise ValueError("user_id and tenant_id are required")
        logger.debug(
            f"Created UserContext for {self.user_id} in tenant {self.tenant_id} "
            f"with role {self.role}"
        )


def _get_redis_client() -> Optional[redis.Redis]:
    """Get Redis client for caching, with graceful fallback if unavailable.
    
    Returns:
        redis.Redis client or None if Redis is unavailable.
        If None is returned, queries will skip caching and execute normally.
    
    Note:
        Environment variables:
        - REDIS_URL: Redis connection URL (default: redis://localhost:6379/0)
        - CACHE_ENABLED: Set to "false" to disable caching entirely
    """
    if os.environ.get("CACHE_ENABLED", "true").lower() == "false":
        return None
    
    try:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        client = redis.from_url(redis_url, decode_responses=True, socket_timeout=2)
        client.ping()
        return client
    except Exception as e:
        logger.warning(f"Redis unavailable, caching disabled: {e}")
        return None


def _hash_query(query: str, user_context: UserContext) -> str:
    """Generate deterministic cache key for query + context.
    
    Args:
        query: User query string
        user_context: UserContext (tenant_id and assigned_properties included)
    
    Returns:
        hex digest suitable for Redis key
    
    Note:
        Different tenants and property assignments generate different keys
        even if the query text is identical, ensuring no cross-tenant leakage.
    """
    key_input = f"{query}#{user_context.tenant_id}#{','.join(sorted(user_context.assigned_properties))}"
    return hashlib.sha256(key_input.encode()).hexdigest()


def _get_cached_result(
    query: str,
    user_context: UserContext,
    redis_client: Optional[redis.Redis],
    ttl_seconds: int = 3600
) -> Optional[QueryResult]:
    """Check Redis cache for previously-executed query.
    
    Args:
        query: User query string
        user_context: UserContext with tenant info
        redis_client: Redis client (if None, returns None)
        ttl_seconds: Cache expiration time in seconds (default 1 hour)
    
    Returns:
        QueryResult from cache or None if not found or expired
    
    Note:
        Cache key includes tenant_id and assigned_properties to prevent
        cross-tenant data leakage.
    """
    if not redis_client:
        return None
    
    try:
        cache_key = f"query:{_hash_query(query, user_context)}"
        cached_json = redis_client.get(cache_key)
        if not cached_json:
            return None
        
        cached_data = json.loads(cached_json)
        logger.info(f"Cache HIT for query: {query[:50]}...")
        
        # Reconstruct QueryResult from JSON
        result = QueryResult(
            query_id=cached_data['query_id'],
            query_type=QueryType(cached_data['query_type']),
            results=cached_data['results'],
            execution_time_ms=0,  # Cache hits are instant
            generated_sql=cached_data.get('generated_sql'),
            source_documents=cached_data.get('source_documents', []),
            confidence=cached_data.get('confidence', 1.0)
        )
        return result
    except Exception as e:
        logger.warning(f"Cache lookup failed: {e}")
        return None


def _cache_result(
    query_result: QueryResult,
    user_context: UserContext,
    redis_client: Optional[redis.Redis],
    ttl_seconds: int = 3600
) -> None:
    """Store query result in Redis cache.
    
    Args:
        query_result: QueryResult to cache
        user_context: UserContext with tenant info
        redis_client: Redis client (if None, does nothing)
        ttl_seconds: Cache expiration time
    
    Note:
        Only caches successful results (error is None).
    """
    if not redis_client or query_result.error:
        return
    
    try:
        cache_key = f"query:{_hash_query(query_result.query_id, user_context)}"
        cache_data = {
            'query_id': query_result.query_id,
            'query_type': query_result.query_type.value,
            'results': query_result.results,
            'generated_sql': query_result.generated_sql,
            'source_documents': query_result.source_documents,
            'confidence': query_result.confidence,
        }
        redis_client.setex(cache_key, ttl_seconds, json.dumps(cache_data))
        logger.debug(f"Cached query result (TTL {ttl_seconds}s)")
    except Exception as e:
        logger.warning(f"Failed to cache result: {e}")


def classify_query(query: str) -> tuple[QueryType, float]:
    """Classify query intent using Claude API (zero-shot).
    
    Args:
        query: Natural language query from user
    
    Returns:
        Tuple of (QueryType enum, confidence score 0.0-1.0)
    
    Raises:
        ValueError: If Claude API call fails
    
    Classification Rules:
        TEXT_TO_SQL: Questions about metrics, aggregations, comparisons
                    Examples: "occupancy by region", "top 10 properties by NOI",
                             "rent collection rate this month"
        
        SEMANTIC_SEARCH: Questions about specific documents, terms, clauses
                        Examples: "lease terms for unit 204", "what are the
                                 maintenance obligations", "find leases with
                                 renewal options"
        
        HYBRID: Requires both metrics and documents to answer fully
               Examples: "properties with high vacancy and poor condition",
                        "portfolio performance vs maintenance needs"
    
    Note:
        Uses Claude 3 for robust zero-shot classification without fine-tuning.
        Returns confidence from 0.0 (uncertain) to 1.0 (very confident).
        Defaults to HYBRID if uncertain to maximize information returned.
    
    Example:
        >>> query_type, confidence = classify_query("What's the occupancy rate?")
        >>> print(f"Type: {query_type.value}, Confidence: {confidence}")
        # Type: text_to_sql, Confidence: 0.95
    """
    client = anthropic.Anthropic()
    
    system_prompt = """You are a query classification system for a real estate portfolio platform.
    
Classify the user query into one of these categories:
1. TEXT_TO_SQL: Questions about metrics, statistics, comparisons, aggregations
   - "What's occupancy by region?"
   - "Top 5 properties by NOI"
   - "Rent collection rate this month"

2. SEMANTIC_SEARCH: Questions about specific documents, terms, or clauses
   - "What are the lease terms for Unit 204?"
   - "Find properties with maintenance issues"
   - "Show me lease renewal options"

3. HYBRID: Requires both metrics and documents
   - "Properties with high vacancy and repair needs"
   - "Compare occupancy trends vs maintenance costs"

Respond with JSON: {"type": "text_to_sql|semantic_search|hybrid", "confidence": 0.0-1.0, "reasoning": "..."}"""
    
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=200,
        system=system_prompt,
        messages=[
            {"role": "user", "content": query}
        ]
    )
    
    try:
        response_text = message.content[0].text
        result = json.loads(response_text)
        query_type = QueryType(result['type'])
        confidence = float(result.get('confidence', 0.8))
        logger.info(f"Classified '{query[:50]}...' as {query_type.value} (confidence: {confidence})")
        return query_type, confidence
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Failed to parse classification response: {e}")
        # Default to HYBRID to be safe
        return QueryType.HYBRID, 0.5


def route_query(
    query: str,
    user_context: UserContext,
    cache_ttl_seconds: int = 3600
) -> QueryResult:
    """Main entry point: classify, check cache, route, and execute query.
    
    Args:
        query: Natural language query from user
        user_context: UserContext with auth and tenant info
        cache_ttl_seconds: Redis cache TTL in seconds (default 1 hour)
    
    Returns:
        QueryResult with results, execution metadata, and error status
    
    Execution Flow:
        1. Check Redis cache for identical query + user context
           -> Return CACHED result if hit
        2. Classify query using Claude
        3. Route to appropriate backend(s):
           - TEXT_TO_SQL: via text_to_sql.generate_sql()
           - SEMANTIC_SEARCH: via retriever.search_documents()
           - HYBRID: execute both and merge
        4. Cache result in Redis
        5. Return unified QueryResult
    
    Example:
        >>> ctx = UserContext("user1", "tenant1", "property_manager", ["prop1"])
        >>> result = route_query("Show me occupancy by region", ctx)
        >>> if result.query_type == QueryType.TEXT_TO_SQL:
        ...     for row in result.results:
        ...         print(f"{row['region']}: {row['occupancy']}%")
    
    Note:
        - All errors are caught and returned in QueryResult.error field
        - Execution time includes classification, routing, and SQL/search time
        - Generated SQL is returned for TEXT_TO_SQL and HYBRID for transparency
        - Source documents are populated for SEMANTIC_SEARCH and HYBRID
    """
    start_time = time.time()
    query_id = _hash_query(query, user_context)[:16]
    redis_client = _get_redis_client()
    
    try:
        # Step 1: Check cache
        cached = _get_cached_result(query, user_context, redis_client, cache_ttl_seconds)
        if cached:
            cached.query_id = query_id
            return cached
        
        # Step 2: Classify query
        query_type, confidence = classify_query(query)
        
        # Step 3: Route and execute
        if query_type == QueryType.TEXT_TO_SQL:
            logger.info(f"Routing to TEXT_TO_SQL pipeline")
            # Import here to avoid circular dependencies
            from .text_to_sql import generate_sql, execute_query, format_results, parse_query_intent, map_to_tables
            
            intent = parse_query_intent(query)
            table_mapping = map_to_tables(intent)
            generated_sql = generate_sql(table_mapping, user_context)
            results = execute_query(generated_sql, user_context)
            formatted = format_results(results, query)
            
            result = QueryResult(
                query_id=query_id,
                query_type=QueryType.TEXT_TO_SQL,
                results=results,
                generated_sql=generated_sql,
                execution_time_ms=int((time.time() - start_time) * 1000),
                confidence=confidence
            )
        
        elif query_type == QueryType.SEMANTIC_SEARCH:
            logger.info(f"Routing to SEMANTIC_SEARCH pipeline")
            from .retriever import search_documents
            
            search_results = search_documents(query, user_context)
            source_docs = [
                {
                    'chunk_id': r.chunk_id,
                    'doc_id': r.doc_id,
                    'title': r.doc_title,
                    'relevance': r.relevance_score
                }
                for r in search_results
            ]
            
            result = QueryResult(
                query_id=query_id,
                query_type=QueryType.SEMANTIC_SEARCH,
                results=[r.__dict__ for r in search_results],
                source_documents=source_docs,
                execution_time_ms=int((time.time() - start_time) * 1000),
                confidence=confidence
            )
        
        else:  # HYBRID
            logger.info(f"Routing to HYBRID pipeline")
            from .text_to_sql import generate_sql, execute_query, parse_query_intent, map_to_tables
            from .retriever import search_documents
            
            # Execute SQL
            intent = parse_query_intent(query)
            table_mapping = map_to_tables(intent)
            generated_sql = generate_sql(table_mapping, user_context)
            sql_results = execute_query(generated_sql, user_context)
            
            # Search documents
            search_results = search_documents(query, user_context)
            source_docs = [
                {
                    'chunk_id': r.chunk_id,
                    'doc_id': r.doc_id,
                    'title': r.doc_title,
                    'relevance': r.relevance_score
                }
                for r in search_results
            ]
            
            result = QueryResult(
                query_id=query_id,
                query_type=QueryType.HYBRID,
                results={
                    'sql_results': sql_results,
                    'search_results': [r.__dict__ for r in search_results]
                },
                generated_sql=generated_sql,
                source_documents=source_docs,
                execution_time_ms=int((time.time() - start_time) * 1000),
                confidence=confidence
            )
        
        # Step 4: Cache result
        _cache_result(result, user_context, redis_client, cache_ttl_seconds)
        logger.info(f"Query completed successfully in {result.execution_time_ms}ms")
        return result
    
    except Exception as e:
        logger.error(f"Query routing failed: {e}", exc_info=True)
        return QueryResult(
            query_id=query_id,
            query_type=QueryType.HYBRID,  # Unknown
            results=[],
            execution_time_ms=int((time.time() - start_time) * 1000),
            error=str(e),
            confidence=0.0
        )
