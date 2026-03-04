"""Document ingestion and semantic chunking pipeline.

This module handles:
1. Extracting text from PDFs (leases, inspection reports, work orders)
2. OCR fallback for scanned documents
3. Semantic chunking (splitting documents intelligently by clauses/sections)
4. Storing chunks in Supabase with metadata

PM Context: Real estate documents like leases and inspection reports contain
critical information (tenant obligations, maintenance issues, renewal terms)
that must be searchable. This module converts unstructured PDFs into chunks
that can be embedded and searched.

Reference Implementation: Uses Docling for PDF extraction (simple and robust).
Production would handle:
- Layout preservation for tabular data
- Form extraction for standard lease clauses
- Document classification (lease vs report vs work order)
- Multi-language support
"""

import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class PageContent:
    """Content extracted from a single page.
    
    Attributes:
        page_number: 1-indexed page number
        text: Extracted text content
        has_images: Whether page contains images
        has_tables: Whether page contains tables
        confidence: OCR confidence if extracted via OCR (0.0-1.0)
    """
    page_number: int
    text: str
    has_images: bool = False
    has_tables: bool = False
    confidence: float = 1.0


@dataclass
class DocumentChunk:
    """Semantic chunk of a document suitable for embedding and retrieval.
    
    Attributes:
        chunk_id: Unique identifier for this chunk
        doc_id: Parent document identifier
        chunk_text: The actual text content to embed
        chunk_index: 0-based position in document
        page_number: Page where chunk starts
        section: Document section (for leases: 'tenant_obligations', 'payment_terms', etc.)
        confidence: Confidence in extraction/chunking (0.0-1.0)
        metadata: Additional metadata (tenant_name, lease_number, etc.)
    
    Example:
        >>> chunk = DocumentChunk(
        ...     chunk_id="LEASE_001_CHUNK_003",
        ...     doc_id="LEASE_001",
        ...     chunk_text="Tenant shall pay rent by the first of each month...",
        ...     chunk_index=2,
        ...     page_number=1,
        ...     section="payment_terms",
        ...     confidence=0.95,
        ...     metadata={'lease_number': 'L-2024-001'}
        ... )
    """
    chunk_id: str
    doc_id: str
    chunk_text: str
    chunk_index: int
    page_number: int
    section: str = "general"
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessedDocument:
    """Result of processing a document through the full pipeline.
    
    Attributes:
        doc_id: Unique document identifier
        property_id: Property this document relates to
        doc_type: Type of document (lease, inspection_report, work_order, etc.)
        chunks: List of DocumentChunk objects
        total_pages: Number of pages in original document
        extraction_method: How text was extracted (docling_pdf, ocr, etc.)
        processed_at: Timestamp of processing
        status: Processing status (success, partial, failed)
    """
    doc_id: str
    property_id: str
    doc_type: str
    chunks: List[DocumentChunk]
    total_pages: int
    extraction_method: str = "docling_pdf"
    processed_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "success"


def extract_text_pdf(file_path: str) -> List[PageContent]:
    """Extract text from PDF using Docling (simple, robust extraction).
    
    Args:
        file_path: Path to PDF file
    
    Returns:
        List of PageContent, one per page
    
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is not a valid PDF
    
    Note:
        This is a reference implementation using Docling.
        Docling is simpler than pdfplumber and handles both standard and scanned PDFs.
        
        In production, would also extract:
        - Table structure
        - Form fields
        - Handwritten annotations
    
    Example:
        >>> pages = extract_text_pdf("/documents/lease_001.pdf")
        >>> for page in pages:
        ...     print(f"Page {page.page_number}: {len(page.text)} chars")
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    
    try:
        # In production: from docling.document_converter import DocumentConverter
        # This is a reference implementation
        logger.info(f"Extracting text from PDF: {file_path}")
        
        pages = []
        # Simulated extraction - production would use Docling
        pages.append(PageContent(
            page_number=1,
            text="Sample lease document text extracted from PDF...",
            has_images=False,
            has_tables=False,
            confidence=1.0
        ))
        
        logger.info(f"Extracted {len(pages)} pages from PDF")
        return pages
    
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        raise ValueError(f"Failed to extract PDF: {e}")


def extract_text_ocr(file_path: str) -> List[PageContent]:
    """Extract text from scanned PDF using Azure Document Intelligence.
    
    Args:
        file_path: Path to PDF file
    
    Returns:
        List of PageContent with OCR confidence scores
    
    Raises:
        Exception: If Azure service fails
    
    Note:
        Fallback when Docling cannot extract text (scanned documents).
        
        Requires environment variables:
        - AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT
        - AZURE_DOCUMENT_INTELLIGENCE_KEY
    """
    try:
        # In production: from azure.ai.documentintelligence import DocumentIntelligenceClient
        logger.info(f"Running OCR on scanned PDF: {file_path}")
        
        # Simulated OCR - production would call Azure
        pages = []
        pages.append(PageContent(
            page_number=1,
            text="Extracted via OCR from scanned lease...",
            has_images=True,
            confidence=0.87
        ))
        
        logger.info(f"OCR extracted {len(pages)} pages with avg confidence 0.87")
        return pages
    
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        raise


def chunk_document(pages: List[PageContent], doc_type: str) -> List[DocumentChunk]:
    """Split document into semantic chunks using intelligent boundaries.
    
    Args:
        pages: List of PageContent from extract_text_pdf() or extract_text_ocr()
        doc_type: Document type ('lease', 'inspection_report', 'work_order', etc.)
    
    Returns:
        List of DocumentChunk objects
    
    Strategy:
        - For leases: Split by clause (payment_terms, tenant_obligations, etc.)
        - For reports: Split by section (summary, property_condition, etc.)
        - Default: Split by paragraph (500-token chunks)
    
    Example:
        >>> pages = extract_text_pdf("lease.pdf")
        >>> chunks = chunk_document(pages, "lease")
        >>> print(f"Created {len(chunks)} chunks from {len(pages)} pages")
    """
    if doc_type.lower() == "lease":
        return chunk_lease(pages)
    elif doc_type.lower() in ["inspection_report", "report"]:
        return chunk_report(pages)
    else:
        return chunk_generic(pages)


def chunk_lease(pages: List[PageContent]) -> List[DocumentChunk]:
    """Split lease document by clause boundaries.
    
    Standard lease sections:
    - Parties
    - Premises description
    - Term
    - Rent and payment
    - Security deposit
    - Tenant obligations
    - Landlord obligations
    - Maintenance and repairs
    - Insurance
    - Renewal/Extension
    - Termination
    - Default and remedies
    
    Args:
        pages: List of PageContent
    
    Returns:
        List of DocumentChunk with section-level boundaries
    """
    chunks = []
    chunk_index = 0
    
    # Combine all pages into single text
    full_text = "\n".join([p.text for p in pages])
    
    # Lease section keywords
    sections = {
        "parties": r"(?i)section 1|parties to lease|landlord.*tenant",
        "premises": r"(?i)section 2|premises|described as|located at",
        "term": r"(?i)section 3|term of lease|commencement",
        "rent": r"(?i)section 4|rent|payment|monthly",
        "security_deposit": r"(?i)section 5|security deposit|damage",
        "tenant_obligations": r"(?i)section 6|tenant.*obligation|shall|must",
        "landlord_obligations": r"(?i)section 7|landlord.*obligation|maintain",
        "maintenance": r"(?i)section 8|maintenance|repair",
        "insurance": r"(?i)section 9|insurance|liability",
        "renewal": r"(?i)section 10|renewal|extension|option",
        "termination": r"(?i)section 11|termination|end of term",
        "default": r"(?i)section 12|default|breach",
    }
    
    # Split by paragraphs and assign to sections
    paragraphs = full_text.split('\n\n')
    current_section = "general"
    
    for page_idx, page in enumerate(pages, 1):
        for para_idx, para in enumerate(page.text.split('\n\n')):
            if not para.strip():
                continue
            
            # Check if paragraph starts a new section
            for section_name, pattern in sections.items():
                if re.match(pattern, para[:100]):
                    current_section = section_name
                    break
            
            chunk = DocumentChunk(
                chunk_id=f"CHUNK_{chunk_index:04d}",
                doc_id="",  # Set by caller
                chunk_text=para.strip(),
                chunk_index=chunk_index,
                page_number=page_idx,
                section=current_section,
                confidence=page.confidence,
                metadata={'section': current_section}
            )
            chunks.append(chunk)
            chunk_index += 1
    
    logger.info(f"Chunked lease into {len(chunks)} chunks across {len(set(c.section for c in chunks))} sections")
    return chunks


def chunk_report(pages: List[PageContent]) -> List[DocumentChunk]:
    """Split inspection/assessment report by section boundaries.
    
    Common report sections:
    - Executive Summary
    - Property Overview
    - Building Systems (HVAC, Plumbing, Electrical)
    - Structural Condition
    - Unit Condition
    - Safety Issues
    - Maintenance Recommendations
    - Cost Estimates
    
    Args:
        pages: List of PageContent
    
    Returns:
        List of DocumentChunk with section-level boundaries
    """
    chunks = []
    chunk_index = 0
    
    for page_idx, page in enumerate(pages, 1):
        # Split by common report section markers
        sections = re.split(r'\n(?=\d+\.|##|[A-Z][A-Z\s]+\n)', page.text)
        
        current_section = "general"
        for section_text in sections:
            if not section_text.strip():
                continue
            
            # Try to identify section name from first line
            first_line = section_text.split('\n')[0]
            if any(x in first_line.lower() for x in ['summary', 'overview', 'condition', 'system', 'issue', 'recommendation']):
                current_section = first_line[:50].lower()
            
            chunk = DocumentChunk(
                chunk_id=f"CHUNK_{chunk_index:04d}",
                doc_id="",  # Set by caller
                chunk_text=section_text.strip(),
                chunk_index=chunk_index,
                page_number=page_idx,
                section=current_section,
                confidence=page.confidence,
                metadata={'page': page_idx}
            )
            chunks.append(chunk)
            chunk_index += 1
    
    logger.info(f"Chunked report into {len(chunks)} chunks")
    return chunks


def chunk_generic(pages: List[PageContent]) -> List[DocumentChunk]:
    """Default chunking strategy: split by paragraphs (500-token targets).
    
    Args:
        pages: List of PageContent
    
    Returns:
        List of DocumentChunk
    """
    chunks = []
    chunk_index = 0
    
    for page_idx, page in enumerate(pages, 1):
        # Split by paragraphs and group into 500-token chunks
        paragraphs = page.text.split('\n\n')
        current_chunk = ""
        
        for para in paragraphs:
            if not para.strip():
                continue
            
            # Rough token count (1 token ~= 4 chars)
            if len((current_chunk + para).replace(' ', '')) > 500 * 4:
                if current_chunk:
                    chunk = DocumentChunk(
                        chunk_id=f"CHUNK_{chunk_index:04d}",
                        doc_id="",  # Set by caller
                        chunk_text=current_chunk.strip(),
                        chunk_index=chunk_index,
                        page_number=page_idx,
                        section="general",
                        confidence=page.confidence
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                current_chunk = para
            else:
                current_chunk += "\n\n" + para
        
        if current_chunk.strip():
            chunk = DocumentChunk(
                chunk_id=f"CHUNK_{chunk_index:04d}",
                doc_id="",  # Set by caller
                chunk_text=current_chunk.strip(),
                chunk_index=chunk_index,
                page_number=page_idx,
                section="general",
                confidence=page.confidence
            )
            chunks.append(chunk)
            chunk_index += 1
    
    logger.info(f"Chunked document into {len(chunks)} generic chunks")
    return chunks


def process_document(file_path: str, property_id: str, doc_type: str) -> ProcessedDocument:
    """End-to-end document processing: extract -> chunk -> store.
    
    Args:
        file_path: Path to document file
        property_id: Property this document relates to
        doc_type: Document type (lease, inspection_report, work_order, etc.)
    
    Returns:
        ProcessedDocument with extracted and chunked content
    
    Process:
        1. Extract text via Docling or OCR
        2. Semantic chunking based on document type
        3. Store in Supabase
        4. Return ProcessedDocument
    
    Example:
        >>> result = process_document("/docs/lease.pdf", "PROP_001", "lease")
        >>> print(f"Processed {result.total_pages} pages into {len(result.chunks)} chunks")
    """
    doc_id = hashlib.md5(file_path.encode()).hexdigest()[:12]
    
    try:
        # Step 1: Extract text
        try:
            pages = extract_text_pdf(file_path)
            extraction_method = "docling_pdf"
        except Exception as e:
            logger.warning(f"Docling extraction failed, attempting OCR: {e}")
            pages = extract_text_ocr(file_path)
            extraction_method = "azure_ocr"
        
        # Step 2: Chunk document
        chunks = chunk_document(pages, doc_type)
        
        # Update chunk IDs and doc references
        for chunk in chunks:
            chunk.doc_id = doc_id
            chunk.chunk_id = f"{doc_id}_{chunk.chunk_index:04d}"
            chunk.metadata['property_id'] = property_id
            chunk.metadata['doc_type'] = doc_type
        
        # Step 3: Store chunks (in production: to Supabase)
        store_chunks(chunks, doc_id)
        
        result = ProcessedDocument(
            doc_id=doc_id,
            property_id=property_id,
            doc_type=doc_type,
            chunks=chunks,
            total_pages=len(pages),
            extraction_method=extraction_method,
            status="success"
        )
        
        logger.info(f"Processed document {doc_id}: {len(chunks)} chunks from {len(pages)} pages")
        return result
    
    except Exception as e:
        logger.error(f"Document processing failed for {file_path}: {e}")
        return ProcessedDocument(
            doc_id=doc_id,
            property_id=property_id,
            doc_type=doc_type,
            chunks=[],
            total_pages=0,
            status="failed"
        )


def store_chunks(chunks: List[DocumentChunk], doc_id: str) -> None:
    """Store document chunks in Supabase for later retrieval.
    
    Args:
        chunks: List of DocumentChunk to store
        doc_id: Document ID (for grouping)
    
    Note:
        In reference implementation, this is a no-op.
        Production would INSERT INTO supabase table with chunks.
        
        Table schema:
            CREATE TABLE document_chunks (
                chunk_id VARCHAR PRIMARY KEY,
                doc_id VARCHAR,
                chunk_text TEXT,
                page_number INT,
                section VARCHAR,
                metadata JSONB,
                embedding VECTOR(1536),
                created_at TIMESTAMP
            )
    """
    logger.debug(f"Storing {len(chunks)} chunks for doc {doc_id} (reference implementation)")
    # In production: INSERT chunks into Supabase
    pass


import re
