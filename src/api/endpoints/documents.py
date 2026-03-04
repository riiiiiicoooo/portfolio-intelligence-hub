"""
Document Endpoints - Upload, Search, and Management

Provides endpoints for:
- Document upload and async processing
- Semantic document search
- Document metadata retrieval
- Document filtering and listing
- Soft delete operations
"""

import logging
from typing import Optional
from datetime import datetime
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
    Query as FastAPIQuery,
)
from pydantic import BaseModel, Field

from src.api.auth import get_current_user, UserContext
from src.core.exceptions import DocumentProcessingError, ValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents")


# ============================================================================
# Request/Response Models
# ============================================================================

class DocumentUploadRequest(BaseModel):
    """Document upload request metadata."""
    property_id: str = Field(..., description="Property ID associated with document")
    doc_type: str = Field(
        ...,
        description="Document type: lease, listing, appraisal, inspection, tax_return, mortgage",
    )
    description: Optional[str] = Field(None, max_length=500)


class DocumentUploadResponse(BaseModel):
    """Response after uploading a document."""
    doc_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    property_id: str
    doc_type: str
    processing_status: str = Field(
        ...,
        description="Status: queued, processing, completed, failed",
    )
    created_at: datetime
    message: str


class SearchResult(BaseModel):
    """Single search result."""
    doc_id: str = Field(..., description="Document ID")
    filename: str = Field(..., description="Document filename")
    property_id: str = Field(..., description="Associated property ID")
    doc_type: str = Field(..., description="Document type")
    relevance_score: float = Field(..., ge=0, le=1, description="Relevance score")
    snippet: str = Field(..., description="Matching text snippet")
    snippet_position: int = Field(..., description="Character position in document")


class DocumentSearchResponse(BaseModel):
    """Semantic document search response."""
    query: str = Field(..., description="Search query")
    results: list[SearchResult] = Field(..., description="Search results")
    total_results: int = Field(..., description="Total matching documents")
    search_time_ms: int = Field(..., description="Search execution time")


class DocumentMetadata(BaseModel):
    """Document metadata."""
    doc_id: str
    filename: str
    property_id: str
    doc_type: str
    description: Optional[str]
    file_size_bytes: int
    pages: int
    processing_status: str
    created_at: datetime
    updated_at: datetime
    created_by: str
    is_deleted: bool


class DocumentListResponse(BaseModel):
    """Paginated document list response."""
    items: list[DocumentMetadata]
    total: int
    page: int
    page_size: int


class DocumentDeleteResponse(BaseModel):
    """Response after deleting a document."""
    doc_id: str
    message: str
    deleted_at: datetime


# ============================================================================
# Endpoints
# ============================================================================

@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload document",
    description=(
        "Upload a property document. Processing happens asynchronously. "
        "Triggers document embedding and indexing via Trigger.dev."
    ),
)
async def upload_document(
    file: UploadFile = File(..., description="Document file (PDF, DOCX, TXT)"),
    property_id: str = Form(..., description="Property ID"),
    doc_type: str = Form(
        ...,
        description="Document type",
    ),
    description: Optional[str] = Form(None, description="Optional description"),
    user: UserContext = Depends(get_current_user),
) -> DocumentUploadResponse:
    """
    Upload a document for processing.
    
    Accepts multiple file formats (PDF, DOCX, TXT) and queues async processing:
    1. File storage in S3/GCS
    2. Document chunking
    3. Embedding generation via OpenAI
    4. Index storage in Supabase pgvector
    5. Metadata storage
    
    Args:
        file: Document file to upload
        property_id: Associated property ID
        doc_type: Document type classification
        description: Optional document description
        user: Current authenticated user
        
    Returns:
        DocumentUploadResponse with doc_id and processing status
        
    Raises:
        HTTPException: 400 if validation fails
        HTTPException: 413 if file too large
        HTTPException: 415 if unsupported file type
    """
    doc_id = str(uuid4())
    
    try:
        # Validate file type
        allowed_types = {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
        }
        
        if file.content_type not in allowed_types:
            raise ValidationError(
                f"Unsupported file type: {file.content_type}. "
                f"Supported: PDF, DOCX, TXT"
            )
        
        # Validate file size (max 50MB)
        max_size = 50 * 1024 * 1024
        if file.size and file.size > max_size:
            raise ValidationError(f"File too large. Maximum size: 50MB")
        
        # Validate doc_type
        valid_types = {
            "lease",
            "listing",
            "appraisal",
            "inspection",
            "tax_return",
            "mortgage",
        }
        if doc_type not in valid_types:
            raise ValidationError(
                f"Invalid doc_type. Allowed: {', '.join(valid_types)}"
            )
        
        logger.info(
            f"[{doc_id}] Document upload started by user {user.user_id}: "
            f"filename={file.filename}, property_id={property_id}, doc_type={doc_type}"
        )
        
        # In production:
        # 1. Upload file to S3/GCS
        # 2. Store metadata in database
        # 3. Trigger Trigger.dev job for embedding
        # 4. Return immediately with processing_status=queued
        
        return DocumentUploadResponse(
            doc_id=doc_id,
            filename=file.filename or "document",
            property_id=property_id,
            doc_type=doc_type,
            processing_status="queued",
            created_at=datetime.utcnow(),
            message="Document queued for processing",
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message,
        )
    except Exception as e:
        logger.error(f"[{doc_id}] Document upload failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload document",
        )


@router.get(
    "/search",
    response_model=DocumentSearchResponse,
    summary="Semantic document search",
    description=(
        "Search documents using semantic similarity. "
        "Query is embedded and compared against stored document embeddings."
    ),
)
async def search_documents(
    q: str = FastAPIQuery(..., min_length=1, max_length=500, description="Search query"),
    property_id: Optional[str] = FastAPIQuery(None, description="Filter by property"),
    doc_type: Optional[str] = FastAPIQuery(None, description="Filter by document type"),
    top_k: int = FastAPIQuery(10, ge=1, le=100, description="Number of results"),
    user: UserContext = Depends(get_current_user),
) -> DocumentSearchResponse:
    """
    Semantic search over documents.
    
    Args:
        q: Search query text
        property_id: Optional property filter
        doc_type: Optional document type filter
        top_k: Number of top results to return
        user: Current authenticated user
        
    Returns:
        DocumentSearchResponse with ranked search results
        
    Raises:
        HTTPException: 400 if validation fails
    """
    try:
        logger.info(
            f"Semantic search by user {user.user_id}: "
            f"query='{q[:50]}...', property_id={property_id}, top_k={top_k}"
        )
        
        # In production:
        # 1. Embed query using OpenAI
        # 2. Query Supabase pgvector for similar embeddings
        # 3. Filter by property_id and doc_type if provided
        # 4. Verify user has access to results (tenant_id, property access)
        # 5. Extract snippets around matches
        # 6. Return with relevance scores
        
        return DocumentSearchResponse(
            query=q,
            results=[],
            total_results=0,
            search_time_ms=0,
        )
        
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed",
        )


@router.get(
    "/{doc_id}",
    response_model=DocumentMetadata,
    summary="Get document metadata",
    description="Retrieve metadata for a specific document.",
)
async def get_document(
    doc_id: str,
    user: UserContext = Depends(get_current_user),
) -> DocumentMetadata:
    """
    Get document metadata.
    
    Args:
        doc_id: Document ID
        user: Current authenticated user
        
    Returns:
        DocumentMetadata
        
    Raises:
        HTTPException: 404 if document not found
        HTTPException: 403 if no access
    """
    try:
        logger.info(f"Fetching document {doc_id} for user {user.user_id}")
        
        # In production:
        # 1. Fetch from database
        # 2. Check tenant_id matches
        # 3. Check property access if restricted
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching document {doc_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch document",
        )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List documents",
    description="List documents with optional filtering by property, type, and status.",
)
async def list_documents(
    page: int = FastAPIQuery(1, ge=1),
    page_size: int = FastAPIQuery(20, ge=1, le=100),
    property_id: Optional[str] = FastAPIQuery(None),
    doc_type: Optional[str] = FastAPIQuery(None),
    status_filter: Optional[str] = FastAPIQuery(None),
    user: UserContext = Depends(get_current_user),
) -> DocumentListResponse:
    """
    List documents with filtering.
    
    Args:
        page: Page number (1-indexed)
        page_size: Results per page
        property_id: Filter by property
        doc_type: Filter by document type
        status_filter: Filter by processing status
        user: Current authenticated user
        
    Returns:
        Paginated document list
    """
    try:
        logger.info(
            f"Listing documents for user {user.user_id} "
            f"(property={property_id}, type={doc_type})"
        )
        
        # In production:
        # 1. Query database with filters
        # 2. Apply tenant isolation
        # 3. Paginate results
        # 4. Exclude deleted documents
        
        return DocumentListResponse(
            items=[],
            total=0,
            page=page,
            page_size=page_size,
        )
        
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list documents",
        )


@router.delete(
    "/{doc_id}",
    response_model=DocumentDeleteResponse,
    summary="Delete document",
    description="Soft delete a document. Metadata is preserved for audit purposes.",
)
async def delete_document(
    doc_id: str,
    user: UserContext = Depends(get_current_user),
) -> DocumentDeleteResponse:
    """
    Soft delete a document.
    
    Args:
        doc_id: Document ID to delete
        user: Current authenticated user
        
    Returns:
        DocumentDeleteResponse
        
    Raises:
        HTTPException: 404 if document not found
        HTTPException: 403 if no access
    """
    try:
        logger.info(f"Deleting document {doc_id} for user {user.user_id}")
        
        # In production:
        # 1. Fetch document
        # 2. Check access
        # 3. Set is_deleted = True
        # 4. Keep metadata for audit
        
        return DocumentDeleteResponse(
            doc_id=doc_id,
            message="Document deleted",
            deleted_at=datetime.utcnow(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {doc_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document",
        )
