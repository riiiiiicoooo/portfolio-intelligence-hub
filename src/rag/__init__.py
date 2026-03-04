"""RAG (Retrieval-Augmented Generation) pipeline for document-based Q&A.

Provides end-to-end functionality for:
1. Ingesting unstructured documents (leases, inspection reports, work orders)
2. Chunking semantically and embedding with dense vectors
3. Hybrid search combining BM25 full-text and vector similarity
4. Reranking and answer synthesis with source citations

PM Context: Real estate leases, inspection reports, and maintenance records contain
critical information about tenant obligations, property condition, and work needed.
This module makes that unstructured knowledge searchable and synthesizable alongside
structured metrics.
"""

from .document_processor import DocumentChunk, ProcessedDocument, process_document, extract_text_pdf, chunk_document
from .embedder import EmbeddingResult, embed_text, embed_batch, refresh_embeddings
from .retriever import SearchResult, search_documents, bm25_search, vector_search, rerank_results, merge_results
from .llm_augmentation import AugmentedAnswer, generate_answer, format_context_window, extract_citations, suggest_follow_ups

__all__ = [
    'DocumentChunk',
    'ProcessedDocument',
    'process_document',
    'extract_text_pdf',
    'chunk_document',
    'EmbeddingResult',
    'embed_text',
    'embed_batch',
    'refresh_embeddings',
    'SearchResult',
    'search_documents',
    'bm25_search',
    'vector_search',
    'rerank_results',
    'merge_results',
    'AugmentedAnswer',
    'generate_answer',
    'format_context_window',
    'extract_citations',
    'suggest_follow_ups',
]
