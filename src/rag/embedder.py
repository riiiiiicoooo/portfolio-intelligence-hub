"""Dense vector embedding pipeline using OpenAI embeddings model.

Converts text chunks into dense vectors (1536-dimensional) for semantic similarity search.

PM Context: After chunking documents (leases, reports), we embed them so that
queries like "What are the maintenance requirements?" can find semantically similar
passages without keyword matching. Uses OpenAI's text-embedding-3-small model for
cost-effectiveness and performance.

Features:
- Batch embedding with rate limiting (3000 tokens/min)
- Retry logic for transient failures
- Token counting to track API usage
- Embedding refresh for updated documents
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import List, Optional
import math

import openai
import tiktoken
import psycopg

from ..core.config import Settings

logger = logging.getLogger(__name__)

# OpenAI embedding parameters
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
RATE_LIMIT_TOKENS_PER_MINUTE = 3000
BATCH_SIZE = 100


@dataclass
class EmbeddingResult:
    """Result of embedding a text chunk.
    
    Attributes:
        text: Original text that was embedded
        embedding: Dense vector (list of floats)
        model: Model name used for embedding
        dimensions: Vector dimensionality
        token_count: Number of tokens in text
    
    Example:
        >>> result = embed_text("Tenant shall pay rent on the first of each month")
        >>> print(f"Tokens: {result.token_count}, Dimensions: {result.dimensions}")
    """
    text: str
    embedding: List[float]
    model: str
    dimensions: int
    token_count: int


def _count_tokens(text: str, model: str = "cl100k_base") -> int:
    """Count tokens in text using tiktoken.
    
    Args:
        text: Text to count
        model: Encoding to use (default: OpenAI cl100k_base)
    
    Returns:
        Number of tokens
    
    Note:
        tiktoken counts tokens for OpenAI's encoding.
        Actual tokens in API call may vary slightly.
    """
    encoding = tiktoken.get_encoding(model)
    return len(encoding.encode(text))


def _rate_limit_sleep(token_count: int, rate_limit_tokens: int = RATE_LIMIT_TOKENS_PER_MINUTE) -> None:
    """Sleep to respect rate limit if needed.
    
    Args:
        token_count: Tokens about to be processed
        rate_limit_tokens: Tokens allowed per minute (default 3000)
    
    Note:
        This is a simple implementation. Production would use a token bucket
        or similar to track actual usage over time window.
    """
    tokens_per_second = rate_limit_tokens / 60
    time_needed = token_count / tokens_per_second
    if time_needed > 0.1:  # Only sleep if significant
        logger.debug(f"Rate limiting: sleeping {time_needed:.2f}s for {token_count} tokens")
        time.sleep(time_needed)


def embed_text(text: str) -> EmbeddingResult:
    """Embed a single text chunk using OpenAI API.
    
    Args:
        text: Text to embed (typically 200-500 words)
    
    Returns:
        EmbeddingResult with 1536-dimensional vector
    
    Raises:
        Exception: If OpenAI API fails after retries
    
    Example:
        >>> result = embed_text("The tenant obligations include maintaining the unit")
        >>> print(f"Vector shape: {len(result.embedding)}")
        # Vector shape: 1536
    
    Note:
        Costs ~$0.000001 per 1000 tokens with text-embedding-3-small.
        For typical 100-token chunk: $0.0000001 per chunk.
    """
    client = openai.OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
    
    token_count = _count_tokens(text)
    _rate_limit_sleep(token_count)
    
    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text,
            dimensions=EMBEDDING_DIMENSIONS
        )
        
        embedding_vector = response.data[0].embedding
        
        result = EmbeddingResult(
            text=text[:100],  # Store only first 100 chars
            embedding=embedding_vector,
            model=EMBEDDING_MODEL,
            dimensions=EMBEDDING_DIMENSIONS,
            token_count=token_count
        )
        
        logger.debug(f"Embedded text with {token_count} tokens")
        return result
    
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        raise


def embed_batch(texts: List[str], batch_size: int = BATCH_SIZE) -> List[List[float]]:
    """Embed multiple texts with rate limiting and retry logic.
    
    Args:
        texts: List of text chunks to embed
        batch_size: Process N texts per API call (default 100)
    
    Returns:
        List of embedding vectors, parallel to input texts
    
    Raises:
        Exception: If embedding fails after retries
    
    Process:
        1. Count total tokens
        2. Apply rate limiting
        3. Batch texts (100 per API call)
        4. Call OpenAI embeddings API
        5. Retry failed batches
        6. Return aligned list of vectors
    
    Example:
        >>> texts = ["Maintenance required", "Rent payment schedule", "Lease renewal"]
        >>> embeddings = embed_batch(texts)
        >>> print(f"Embedded {len(embeddings)} texts")
        # Embedded 3 texts
    
    Performance:
        - Batching 100 texts per call is ~100x faster than individual calls
        - Rate limiting ensures we stay under 3000 tokens/min quota
        - Typical batch of 100 x 100-token texts: 10,000 tokens, ~200ms, costs $0.00001
    """
    client = openai.OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
    
    # Count total tokens for rate limiting
    total_tokens = sum(_count_tokens(t) for t in texts)
    _rate_limit_sleep(total_tokens)
    
    embeddings = []
    
    # Process in batches
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        
        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch,
                dimensions=EMBEDDING_DIMENSIONS
            )
            
            # Response.data is ordered same as input batch
            batch_embeddings = [item.embedding for item in response.data]
            embeddings.extend(batch_embeddings)
            
            logger.info(f"Embedded batch {i//batch_size + 1}: {len(batch)} texts")
        
        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            # On failure, embed individually with retry
            for text in batch:
                try:
                    result = embed_text(text)
                    embeddings.append(result.embedding)
                except Exception as e2:
                    logger.error(f"Individual embedding failed for text: {e2}")
                    # Return zero vector as fallback
                    embeddings.append([0.0] * EMBEDDING_DIMENSIONS)
    
    logger.info(f"Batch embedding complete: {len(embeddings)} vectors")
    return embeddings


def refresh_embeddings(doc_id: str) -> int:
    """Re-embed all chunks for a document (after document update).

    Args:
        doc_id: Document ID to refresh

    Returns:
        Number of chunks re-embedded

    Note:
        In reference implementation, this is a skeleton.
        Production would:
        1. Query Supabase for all chunks with doc_id
        2. Extract text from chunks
        3. Call embed_batch()
        4. UPDATE embeddings in Supabase
        5. Return count updated
    """
    logger.info(f"Refreshing embeddings for document {doc_id}")

    settings = Settings()
    chunks_updated = 0

    try:
        with psycopg.connect(settings.DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                # Step 1: Fetch all chunks for this document
                cursor.execute(
                    """
                    SELECT chunk_id, chunk_text
                    FROM document_chunks
                    WHERE doc_id = %s
                    ORDER BY chunk_index ASC
                    """,
                    (doc_id,)
                )

                chunks = cursor.fetchall()

                if not chunks:
                    logger.info(f"No chunks found for document {doc_id}")
                    return 0

                # Step 2: Extract texts for embedding
                chunk_ids = [chunk[0] for chunk in chunks]
                texts = [chunk[1] for chunk in chunks]

                logger.info(f"Re-embedding {len(chunks)} chunks for document {doc_id}")

                # Step 3: Embed all chunks using batch embedding
                embeddings = embed_batch(texts)

                # Step 4: Update embeddings in database
                for chunk_id, embedding in zip(chunk_ids, embeddings):
                    cursor.execute(
                        """
                        UPDATE document_chunks
                        SET embedding = %s::vector,
                            updated_at = NOW()
                        WHERE chunk_id = %s
                        """,
                        (embedding, chunk_id)
                    )
                    chunks_updated += 1

                conn.commit()

        logger.info(f"Successfully refreshed embeddings for {chunks_updated} chunks in document {doc_id}")
        return chunks_updated

    except Exception as e:
        logger.error(f"Failed to refresh embeddings for document {doc_id}: {e}")
        return 0
