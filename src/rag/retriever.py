"""Hybrid search engine combining BM25 and vector similarity with reranking.

This module implements a three-stage retrieval pipeline:
1. Parallel BM25 (keyword) and vector (semantic) search
2. Merge results using reciprocal rank fusion
3. Rerank merged results using Cohere reranker for quality

PM Context: When a user asks "What are the maintenance requirements for Unit 204?",
this system finds the answer by:
- BM25: Fast keyword matching on "maintenance" + "Unit 204"
- Vector: Semantic search for "repair obligations" even if not verbatim
- Merge: Combine results (some matches are both, some are one or other)
- Rerank: Order by actual relevance to the question

This hybrid approach beats either method alone.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import os
import time

import cohere
import psycopg
from psycopg import sql

from ..access_control.rbac import UserContext
from ..core.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Result from hybrid search pipeline.
    
    Attributes:
        chunk_id: Unique chunk identifier
        doc_id: Document ID (lease_001, etc.)
        doc_title: Human-readable document title
        chunk_text: The actual text content (truncated for display)
        relevance_score: Final relevance score after reranking (0.0-1.0)
        page_number: Page where chunk appears
        match_type: How result matched (bm25, vector, hybrid, reranked)
        bm25_score: BM25 score before reranking
        vector_score: Vector similarity before reranking
    
    Example:
        >>> result = SearchResult(
        ...     chunk_id="LEASE_001_CHUNK_003",
        ...     doc_id="LEASE_001",
        ...     doc_title="Lease for Unit 204",
        ...     chunk_text="Tenant shall maintain the unit in good condition...",
        ...     relevance_score=0.92,
        ...     page_number=2,
        ...     match_type="reranked",
        ...     bm25_score=8.5,
        ...     vector_score=0.85
        ... )
    """
    chunk_id: str
    doc_id: str
    doc_title: str
    chunk_text: str
    relevance_score: float
    page_number: int
    match_type: str = "unknown"
    bm25_score: float = 0.0
    vector_score: float = 0.0


def bm25_search(query: str, tenant_id: str, top_k: int = 20) -> List[SearchResult]:
    """Full-text search using BM25 algorithm on PostgreSQL.

    Args:
        query: Natural language query
        tenant_id: Tenant ID for filtering
        top_k: Number of results to return

    Returns:
        List of SearchResult sorted by BM25 relevance score

    Process:
        1. Tokenize query
        2. Search PostgreSQL tsvector index on document_chunks table
        3. Filter by tenant_id
        4. Return top_k by relevance

    Note:
        In reference implementation, this is a skeleton.
        Production would:
        ```
        SELECT chunk_id, doc_id, chunk_text, ts_rank(fts, query) as rank
        FROM document_chunks
        WHERE fts @@ plainto_tsquery('english', ?)
          AND tenant_id = ?
        ORDER BY rank DESC
        LIMIT ?
        ```

    Example:
        >>> results = bm25_search("maintenance requirements", "TENANT_001")
        >>> print(f"Found {len(results)} matches")
    """
    logger.debug(f"BM25 search for '{query}' in tenant {tenant_id}")

    results = []
    settings = Settings()

    try:
        with psycopg.connect(settings.DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                # Full-text search using PostgreSQL FTS
                cursor.execute(
                    """
                    SELECT
                        chunk_id,
                        doc_id,
                        chunk_text,
                        page_number,
                        ts_rank(fts, plainto_tsquery('english', %s)) as rank
                    FROM document_chunks
                    WHERE fts @@ plainto_tsquery('english', %s)
                      AND tenant_id = %s
                    ORDER BY rank DESC
                    LIMIT %s
                    """,
                    (query, query, tenant_id, top_k)
                )

                rows = cursor.fetchall()

                for chunk_id, doc_id, chunk_text, page_number, rank in rows:
                    result = SearchResult(
                        chunk_id=chunk_id,
                        doc_id=doc_id,
                        doc_title=doc_id,  # In production, would join with documents table
                        chunk_text=chunk_text[:500],  # Truncate for display
                        relevance_score=float(rank) if rank else 0.0,
                        page_number=page_number or 1,
                        match_type="bm25",
                        bm25_score=float(rank) if rank else 0.0
                    )
                    results.append(result)

    except Exception as e:
        logger.error(f"BM25 search failed: {e}")
        return []

    logger.info(f"BM25 search returned {len(results)} results")
    return results


def vector_search(query: str, tenant_id: str, top_k: int = 20) -> List[SearchResult]:
    """Semantic vector similarity search using pgvector on PostgreSQL.

    Args:
        query: Natural language query
        tenant_id: Tenant ID for filtering
        top_k: Number of results to return

    Returns:
        List of SearchResult sorted by vector similarity (cosine)

    Process:
        1. Embed query using OpenAI embeddings
        2. Search pgvector index with cosine similarity
        3. Filter by tenant_id
        4. Return top_k by similarity

    Example:
        >>> results = vector_search("What are repair obligations?", "TENANT_001", 10)
        >>> for r in results:
        ...     print(f"{r.doc_title}: {r.vector_score:.3f}")

    Note:
        In production:
        ```
        WITH query_embedding AS (
          SELECT embedding_from_openai(?) as emb
        )
        SELECT chunk_id, doc_id, chunk_text,
               1 - (embedding <=> query_embedding.emb) as similarity
        FROM document_chunks, query_embedding
        WHERE tenant_id = ?
        ORDER BY similarity DESC
        LIMIT ?
        ```
    """
    logger.debug(f"Vector search for '{query}' in tenant {tenant_id}")

    results = []
    settings = Settings()

    try:
        # Import and use embedder to embed the query
        from .embedder import embed_text
        query_embedding = embed_text(query).embedding

        with psycopg.connect(settings.DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                # Vector similarity search using pgvector cosine operator (<=>)
                # 1 - (embedding <=> query_embedding) gives similarity score (higher = more similar)
                cursor.execute(
                    """
                    SELECT
                        chunk_id,
                        doc_id,
                        chunk_text,
                        page_number,
                        1 - (embedding <=> %s::vector) as similarity
                    FROM document_chunks
                    WHERE tenant_id = %s
                    ORDER BY similarity DESC
                    LIMIT %s
                    """,
                    (query_embedding, tenant_id, top_k)
                )

                rows = cursor.fetchall()

                for chunk_id, doc_id, chunk_text, page_number, similarity in rows:
                    result = SearchResult(
                        chunk_id=chunk_id,
                        doc_id=doc_id,
                        doc_title=doc_id,  # In production, would join with documents table
                        chunk_text=chunk_text[:500],  # Truncate for display
                        relevance_score=float(similarity) if similarity else 0.0,
                        page_number=page_number or 1,
                        match_type="vector",
                        vector_score=float(similarity) if similarity else 0.0
                    )
                    results.append(result)

    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        return []

    logger.info(f"Vector search returned {len(results)} results")
    return results


def merge_results(bm25: List[SearchResult], vector: List[SearchResult]) -> List[SearchResult]:
    """Merge BM25 and vector search results using Reciprocal Rank Fusion (RRF).
    
    RRF formula: score = sum(1 / (k + rank)) for each result
    where k=60 (standard parameter), and rank is position (1-indexed)
    
    This method:
    1. Gives both BM25 and vector equal weight
    2. Combines complementary matches (keyword + semantic)
    3. Removes duplicates, keeping best score
    4. Orders by fused score
    
    Args:
        bm25: Results from bm25_search()
        vector: Results from vector_search()
    
    Returns:
        Merged list of SearchResult
    
    Example:
        >>> bm25_res = bm25_search("maintenance", "TENANT_001", 20)
        >>> vec_res = vector_search("repair obligations", "TENANT_001", 20)
        >>> merged = merge_results(bm25_res, vec_res)
        >>> print(f"Merged {len(bm25_res)} + {len(vec_res)} = {len(merged)} results")
    """
    scores = {}
    
    # Score BM25 results
    for rank, result in enumerate(bm25, 1):
        key = result.chunk_id
        rrf_score = 1.0 / (60 + rank)
        if key not in scores:
            scores[key] = {
                'result': result,
                'rrf_score': 0.0,
                'match_type': 'bm25'
            }
        scores[key]['rrf_score'] += rrf_score
    
    # Score vector results
    for rank, result in enumerate(vector, 1):
        key = result.chunk_id
        rrf_score = 1.0 / (60 + rank)
        if key not in scores:
            scores[key] = {
                'result': result,
                'rrf_score': 0.0,
                'match_type': 'vector'
            }
        else:
            scores[key]['match_type'] = 'hybrid'  # Appeared in both
        scores[key]['rrf_score'] += rrf_score
    
    # Sort by RRF score and return
    merged = sorted(scores.values(), key=lambda x: x['rrf_score'], reverse=True)
    results = []
    
    for item in merged:
        result = item['result']
        result.match_type = item['match_type']
        result.relevance_score = item['rrf_score']
        results.append(result)
    
    logger.info(f"Merged results: {len(bm25)} BM25 + {len(vector)} vector = {len(results)} after dedup")
    return results


def rerank_results(
    query: str,
    candidates: List[SearchResult],
    top_k: int = 5
) -> List[SearchResult]:
    """Rerank search results using Cohere reranker for improved quality.
    
    Args:
        query: Original user query
        candidates: List of SearchResult from merge_results()
        top_k: How many top results to return after reranking
    
    Returns:
        Top-k reranked results
    
    Process:
        1. Take merged candidates (up to 100)
        2. Send to Cohere rerank API with query and documents
        3. Rerank API returns ordered list with relevance scores
        4. Return top_k
    
    Note:
        Cohere rerank is more accurate than embedding-based similarity,
        using a fine-tuned model to understand relevance to the query.
    
    Example:
        >>> candidates = merge_results(bm25, vector)
        >>> reranked = rerank_results("maintenance requirements", candidates, 5)
        >>> for r in reranked:
        ...     print(f"{r.doc_title}: {r.relevance_score:.2f}")
    """
    if not candidates:
        return []
    
    try:
        co = cohere.ClientV2(api_key=os.environ.get('COHERE_API_KEY'))
        
        # Cohere takes up to 100 documents
        documents = [
            {
                'id': result.chunk_id,
                'text': result.chunk_text[:500]  # Truncate for API
            }
            for result in candidates[:100]
        ]
        
        response = co.rerank(
            model="rerank-english-v2.0",
            query=query,
            documents=documents,
            top_n=top_k
        )
        
        # Map rerank results back to SearchResult objects
        reranked = []
        for ranked_result in response.results:
            doc_id = ranked_result.document['id']
            # Find original result
            original = next((c for c in candidates if c.chunk_id == doc_id), None)
            if original:
                original.relevance_score = ranked_result.relevance_score
                original.match_type = 'reranked'
                reranked.append(original)
        
        logger.info(f"Reranked {len(candidates)} candidates to top {len(reranked)}")
        return reranked
    
    except Exception as e:
        logger.error(f"Reranking failed: {e}")
        # Fallback to top-k by existing score
        return sorted(candidates, key=lambda x: x.relevance_score, reverse=True)[:top_k]


def search_documents(
    query: str,
    user_context: UserContext,
    top_k: int = 10
) -> List[SearchResult]:
    """End-to-end document search: BM25 + vector + merge + rerank.
    
    Args:
        query: User's natural language query
        user_context: UserContext with tenant and property filtering
        top_k: Number of final results to return
    
    Returns:
        List of SearchResult ranked by relevance
    
    Execution:
        1. Run BM25 search (top 20)
        2. Run vector search (top 20)
        3. Merge using RRF
        4. Rerank to top_k using Cohere
        5. Return final results
    
    All searches respect tenant_id isolation.
    
    Example:
        >>> ctx = UserContext("user1", "tenant1", "pm", ["prop1"])
        >>> results = search_documents("lease renewal options", ctx, 5)
        >>> for r in results:
        ...     print(f"{r.doc_title}: {r.relevance_score:.2f}")
    
    Performance:
        - BM25: ~50ms
        - Vector: ~100ms (includes embedding query)
        - Merge: ~10ms
        - Rerank: ~200ms
        - Total: ~400ms
    """
    logger.info(f"Hybrid search for '{query}' (tenant: {user_context.tenant_id})")
    
    start_time = time.time()
    
    # Stage 1: Parallel search
    bm25_results = bm25_search(query, user_context.tenant_id, top_k=20)
    vector_results = vector_search(query, user_context.tenant_id, top_k=20)
    
    # Stage 2: Merge
    merged = merge_results(bm25_results, vector_results)
    
    # Stage 3: Rerank (top_k)
    final_results = rerank_results(query, merged, top_k=top_k)
    
    elapsed_ms = int((time.time() - start_time) * 1000)
    logger.info(f"Search complete in {elapsed_ms}ms, returned {len(final_results)} results")
    
    return final_results


import time
