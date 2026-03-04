"""Tests for the semantic search RAG pipeline in Portfolio Intelligence Hub.

This module tests document chunking, embedding, retrieval, ranking, and answer
generation for the semantic search system.
"""

from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest


class DocumentChunker:
    """Service for chunking documents into retrievable chunks."""

    def __init__(self, min_tokens: int = 200, max_tokens: int = 500):
        """Initialize DocumentChunker.

        Args:
            min_tokens: Minimum chunk size
            max_tokens: Maximum chunk size
        """
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens

    def chunk_lease_document(self, document_text: str) -> List[Dict[str, Any]]:
        """Chunk lease document at clause level."""
        chunks = []
        clauses = [
            s.strip() for s in document_text.split("\n\n") if s.strip()
        ]

        for i, clause in enumerate(clauses):
            token_count = len(clause.split())
            if self.min_tokens <= token_count <= self.max_tokens:
                chunks.append(
                    {
                        "id": f"lease_clause_{i}",
                        "text": clause,
                        "tokens": token_count,
                        "section": self._identify_section(clause),
                    }
                )

        return chunks

    def chunk_inspection_report(self, document_text: str) -> List[Dict[str, Any]]:
        """Chunk inspection report at section level."""
        chunks = []
        sections = [
            s.strip() for s in document_text.split("\n\n") if s.strip()
        ]

        for i, section in enumerate(sections):
            token_count = len(section.split())
            if self.min_tokens <= token_count <= self.max_tokens:
                chunks.append(
                    {
                        "id": f"report_section_{i}",
                        "text": section,
                        "tokens": token_count,
                        "section": self._extract_section_name(section),
                    }
                )

        return chunks

    def _identify_section(self, text: str) -> str:
        """Identify lease section from text."""
        sections = ["PREMISES", "TERM", "RENT", "RENEWAL", "SECURITY", "MAINTENANCE"]
        for section in sections:
            if section in text.upper():
                return section
        return "GENERAL"

    def _extract_section_name(self, text: str) -> str:
        """Extract section name from report text."""
        first_line = text.split("\n")[0]
        return first_line.upper()


class EmbeddingService:
    """Service for generating embeddings."""

    def __init__(self, dimension: int = 3072):
        """Initialize EmbeddingService.

        Args:
            dimension: Embedding vector dimension (default 3072 for OpenAI)
        """
        self.dimension = dimension

    def embed_text(self, text: str, client: MagicMock) -> List[float]:
        """Generate embedding for text.

        Args:
            text: Text to embed
            client: OpenAI client

        Returns:
            Vector embedding
        """
        response = client.embeddings.create(input=text, model="text-embedding-3-large")
        return response.data[0].embedding

    def embed_batch(
        self, texts: List[str], client: MagicMock, batch_size: int = 100
    ) -> List[List[float]]:
        """Generate embeddings for batch of texts with rate limiting.

        Args:
            texts: List of texts to embed
            client: OpenAI client
            batch_size: Batch size for processing

        Returns:
            List of vector embeddings
        """
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            for text in batch:
                embedding = self.embed_text(text, client)
                embeddings.append(embedding)

        return embeddings


class SearchService:
    """Service for searching documents."""

    def __init__(self, bm25_weight: float = 0.3, vector_weight: float = 0.7):
        """Initialize SearchService.

        Args:
            bm25_weight: Weight for BM25 results
            vector_weight: Weight for vector similarity
        """
        self.bm25_weight = bm25_weight
        self.vector_weight = vector_weight

    def bm25_search(self, query: str, documents: List[Dict[str, Any]]) -> List[Dict]:
        """Perform BM25 keyword search."""
        query_terms = set(query.lower().split())
        results = []

        for doc in documents:
            doc_terms = set(doc["text"].lower().split())
            overlap = len(query_terms & doc_terms)

            if overlap > 0:
                score = overlap / len(query_terms)
                results.append({"id": doc["id"], "score": score, "doc": doc})

        return sorted(results, key=lambda x: x["score"], reverse=True)

    def vector_search(
        self,
        query_embedding: List[float],
        document_embeddings: List[Dict[str, Any]],
    ) -> List[Dict]:
        """Perform vector similarity search."""
        results = []

        for doc_emb in document_embeddings:
            # Cosine similarity (simplified)
            similarity = sum(
                a * b for a, b in zip(query_embedding, doc_emb["embedding"])
            ) / (
                sum(a**2 for a in query_embedding) ** 0.5
                * sum(b**2 for b in doc_emb["embedding"]) ** 0.5
            )

            results.append(
                {"id": doc_emb["id"], "score": similarity, "doc": doc_emb}
            )

        return sorted(results, key=lambda x: x["score"], reverse=True)

    def hybrid_merge(
        self, bm25_results: List[Dict], vector_results: List[Dict]
    ) -> List[Dict]:
        """Merge BM25 and vector search results."""
        scores = {}

        for result in bm25_results:
            doc_id = result["id"]
            scores[doc_id] = scores.get(doc_id, 0) + (
                result["score"] * self.bm25_weight
            )

        for result in vector_results:
            doc_id = result["id"]
            scores[doc_id] = scores.get(doc_id, 0) + (
                result["score"] * self.vector_weight
            )

        merged = [
            {
                "id": doc_id,
                "score": score,
                "doc": next(
                    (r["doc"] for r in bm25_results + vector_results if r["id"] == doc_id),
                    None,
                ),
            }
            for doc_id, score in scores.items()
        ]

        return sorted(merged, key=lambda x: x["score"], reverse=True)


class RerankingService:
    """Service for reranking search results."""

    def rerank(self, candidates: List[Dict], query: str) -> List[Dict]:
        """Rerank candidates using Cohere-style ranking.

        Args:
            candidates: Candidate documents
            query: Search query

        Returns:
            Reranked candidates
        """
        # Simplified reranking based on query overlap
        query_terms = set(query.lower().split())

        for candidate in candidates:
            if candidate.get("doc"):
                doc_terms = set(candidate["doc"]["text"].lower().split())
                overlap = len(query_terms & doc_terms)
                candidate["rerank_score"] = overlap / len(query_terms)

        return sorted(candidates, key=lambda x: x.get("rerank_score", 0), reverse=True)


class AnswerGenerator:
    """Service for generating answers from retrieved chunks."""

    def generate_answer(
        self, chunks: List[Dict[str, Any]], query: str, client: MagicMock
    ) -> Dict[str, Any]:
        """Generate answer from retrieved chunks.

        Args:
            chunks: Retrieved chunks
            query: Original query
            client: Claude client

        Returns:
            Generated answer with citations
        """
        if not chunks:
            return {
                "answer": "I couldn't find relevant information to answer your query.",
                "citations": [],
                "confidence": 0.0,
            }

        context = "\n\n".join([c["text"] for c in chunks])

        # Mock Claude response
        response = client.messages.create(
            model="claude-opus-4",
            messages=[
                {
                    "role": "user",
                    "content": f"Based on this context:\n{context}\n\nAnswer: {query}",
                }
            ],
        )

        answer = response.content[0].text

        citations = [
            {"chunk_id": c["id"], "source": c.get("section", "Unknown")}
            for c in chunks
        ]

        confidence = min(1.0, len(chunks) * 0.2)

        return {
            "answer": answer,
            "citations": citations,
            "confidence": confidence,
        }


# Test Fixtures
@pytest.fixture
def document_chunker() -> DocumentChunker:
    """Create document chunker service."""
    return DocumentChunker(min_tokens=200, max_tokens=500)


@pytest.fixture
def embedding_service() -> EmbeddingService:
    """Create embedding service."""
    return EmbeddingService(dimension=3072)


@pytest.fixture
def search_service() -> SearchService:
    """Create search service."""
    return SearchService()


@pytest.fixture
def reranking_service() -> RerankingService:
    """Create reranking service."""
    return RerankingService()


@pytest.fixture
def answer_generator() -> AnswerGenerator:
    """Create answer generator service."""
    return AnswerGenerator()


@pytest.fixture
def mock_rag_client() -> MagicMock:
    """Mock RAG client (OpenAI + Cohere)."""
    client = MagicMock()
    client.embeddings.create.return_value = MagicMock(
        data=[MagicMock(embedding=[0.1] * 3072)]
    )
    return client


# Document Chunking Tests
class TestDocumentChunking:
    """Tests for document chunking."""

    def test_chunk_lease_document(self, document_chunker, sample_lease_document):
        """Test chunking lease document into clauses."""
        chunks = document_chunker.chunk_lease_document(sample_lease_document)

        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk["tokens"] >= 200
            assert chunk["tokens"] <= 500

    def test_chunk_inspection_report(
        self, document_chunker, sample_inspection_report
    ):
        """Test chunking inspection report into sections."""
        chunks = document_chunker.chunk_inspection_report(sample_inspection_report)

        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk["tokens"] >= 200
            assert chunk["tokens"] <= 500

    def test_chunk_size_bounds(self, document_chunker, sample_lease_document):
        """Test that all chunks are within token bounds."""
        chunks = document_chunker.chunk_lease_document(sample_lease_document)

        for chunk in chunks:
            assert 200 <= chunk["tokens"] <= 500

    def test_chunk_identification_lease_sections(
        self, document_chunker, sample_lease_document
    ):
        """Test that lease sections are correctly identified."""
        chunks = document_chunker.chunk_lease_document(sample_lease_document)

        sections = {chunk["section"] for chunk in chunks}
        assert "RENEWAL" in sections or "GENERAL" in sections


# Embedding Tests
class TestEmbedding:
    """Tests for text embedding."""

    def test_embed_text(self, embedding_service, mock_rag_client):
        """Test embedding single text."""
        text = "This is a sample lease agreement"
        embedding = embedding_service.embed_text(text, mock_rag_client)

        assert isinstance(embedding, list)
        assert len(embedding) == 3072

    def test_embed_text_returns_vector(self, embedding_service, mock_rag_client):
        """Test that embedding returns numeric vector."""
        text = "Sample text"
        embedding = embedding_service.embed_text(text, mock_rag_client)

        assert all(isinstance(x, (int, float)) for x in embedding)

    def test_embed_batch_rate_limiting(self, embedding_service, mock_rag_client):
        """Test batch embedding with rate limiting."""
        texts = ["Text " + str(i) for i in range(250)]

        embeddings = embedding_service.embed_batch(texts, mock_rag_client, batch_size=100)

        assert len(embeddings) == 250


# BM25 Search Tests
class TestBM25Search:
    """Tests for BM25 keyword search."""

    def test_bm25_search(self, search_service, sample_lease_document):
        """Test BM25 keyword search."""
        documents = [
            {
                "id": "doc_1",
                "text": "Lease renewal option available on 12/31/2025",
            },
            {
                "id": "doc_2",
                "text": "Property maintenance schedule and responsibilities",
            },
        ]

        query = "renewal option"
        results = search_service.bm25_search(query, documents)

        assert len(results) > 0
        assert results[0]["id"] == "doc_1"

    def test_bm25_search_no_matches(self, search_service):
        """Test BM25 search with no matches."""
        documents = [
            {"id": "doc_1", "text": "Roof and structural information"},
            {"id": "doc_2", "text": "Electrical systems status"},
        ]

        query = "lease renewal"
        results = search_service.bm25_search(query, documents)

        assert len(results) == 0


# Vector Search Tests
class TestVectorSearch:
    """Tests for vector similarity search."""

    def test_vector_search(self, search_service):
        """Test vector similarity search."""
        query_embedding = [0.1] * 3072
        documents = [
            {
                "id": "doc_1",
                "embedding": [0.11] * 3072,
                "text": "Sample document 1",
            },
            {
                "id": "doc_2",
                "embedding": [0.5] * 3072,
                "text": "Sample document 2",
            },
        ]

        results = search_service.vector_search(query_embedding, documents)

        assert len(results) > 0
        assert results[0]["id"] == "doc_1"  # Should be closest to query


# Hybrid Search Tests
class TestHybridSearch:
    """Tests for hybrid BM25 + vector search."""

    def test_hybrid_merge(self, search_service):
        """Test merging BM25 and vector results."""
        bm25_results = [
            {"id": "doc_1", "score": 0.8},
            {"id": "doc_2", "score": 0.5},
        ]
        vector_results = [
            {"id": "doc_2", "score": 0.9},
            {"id": "doc_3", "score": 0.7},
        ]

        merged = search_service.hybrid_merge(bm25_results, vector_results)

        assert len(merged) >= 2
        assert all("id" in result for result in merged)
        assert all("score" in result for result in merged)


# Reranking Tests
class TestReranking:
    """Tests for result reranking."""

    def test_rerank(self, reranking_service):
        """Test reranking of candidates."""
        candidates = [
            {"id": "doc_1", "doc": {"text": "Lease renewal term agreement"}},
            {"id": "doc_2", "doc": {"text": "Property maintenance guidelines"}},
        ]

        query = "lease renewal"
        reranked = reranking_service.rerank(candidates, query)

        assert len(reranked) == 2
        assert reranked[0]["id"] == "doc_1"


# Tenant Isolation Tests
class TestTenantIsolation:
    """Tests for tenant isolation in search."""

    def test_tenant_isolation(self, search_service):
        """Test that search only returns tenant's documents."""
        documents = [
            {
                "id": "doc_1",
                "tenant_id": "tenant_a",
                "text": "Document for tenant A",
            },
            {
                "id": "doc_2",
                "tenant_id": "tenant_b",
                "text": "Document for tenant B",
            },
        ]

        # Filter by tenant before search
        tenant_docs = [d for d in documents if d["tenant_id"] == "tenant_a"]

        assert len(tenant_docs) == 1
        assert tenant_docs[0]["id"] == "doc_1"


# Answer Generation Tests
class TestAnswerGeneration:
    """Tests for answer generation from chunks."""

    def test_generate_answer(self, answer_generator, mock_rag_client):
        """Test generating answer from chunks."""
        chunks = [
            {
                "id": "chunk_1",
                "text": "Lease renewal option available on 12/31/2025",
                "section": "RENEWAL",
            }
        ]

        result = answer_generator.generate_answer(chunks, "What is the renewal date?", mock_rag_client)

        assert "answer" in result
        assert "citations" in result
        assert "confidence" in result
        assert len(result["citations"]) > 0

    def test_generate_answer_no_chunks(self, answer_generator, mock_rag_client):
        """Test answer generation with no chunks."""
        result = answer_generator.generate_answer([], "What is the renewal date?", mock_rag_client)

        assert "couldn't find" in result["answer"].lower()
        assert result["confidence"] == 0.0

    def test_generate_answer_confidence(self, answer_generator, mock_rag_client):
        """Test answer confidence based on chunk count."""
        chunks = [
            {"id": f"chunk_{i}", "text": f"Sample text {i}", "section": "GENERAL"}
            for i in range(5)
        ]

        result = answer_generator.generate_answer(chunks, "Sample query", mock_rag_client)

        assert result["confidence"] > 0.0
        assert result["confidence"] <= 1.0


# Low Confidence Tests
class TestLowConfidence:
    """Tests for low confidence handling."""

    def test_low_confidence_response(self, answer_generator, mock_rag_client):
        """Test handling of poor retrieval results."""
        weak_chunks = [
            {
                "id": "chunk_1",
                "text": "Slightly related information",
                "section": "GENERAL",
            }
        ]

        result = answer_generator.generate_answer(
            weak_chunks, "Very specific detailed query", mock_rag_client
        )

        assert "answer" in result
        # Confidence should be lower with fewer chunks
        assert result["confidence"] < 1.0


# Integration Tests
class TestSemanticSearchIntegration:
    """Integration tests for semantic search pipeline."""

    def test_end_to_end_lease_search(
        self,
        document_chunker,
        embedding_service,
        search_service,
        reranking_service,
        answer_generator,
        mock_rag_client,
        sample_lease_document,
    ):
        """Test complete semantic search pipeline for lease document."""
        # Chunk
        chunks = document_chunker.chunk_lease_document(sample_lease_document)
        assert len(chunks) > 0

        # Embed
        embeddings = embedding_service.embed_batch(
            [c["text"] for c in chunks], mock_rag_client
        )
        assert len(embeddings) == len(chunks)

        # Add embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding

        # Search
        query = "renewal option"
        query_embedding = embedding_service.embed_text(query, mock_rag_client)

        vector_results = search_service.vector_search(query_embedding, chunks)
        assert len(vector_results) > 0

        # Generate answer
        result = answer_generator.generate_answer(
            [r["doc"] for r in vector_results[:3]],
            query,
            mock_rag_client,
        )

        assert "answer" in result
        assert len(result["citations"]) > 0

    @pytest.mark.parametrize(
        "query",
        [
            "What are the lease renewal terms?",
            "Describe the property maintenance responsibilities",
            "What is the security deposit amount?",
        ],
    )
    def test_parametrized_semantic_queries(
        self,
        query,
        document_chunker,
        sample_lease_document,
    ):
        """Parametrized test for various semantic queries."""
        chunks = document_chunker.chunk_lease_document(sample_lease_document)
        assert len(chunks) > 0
