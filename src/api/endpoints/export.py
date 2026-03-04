"""
Export Endpoints - Report Generation and Download

Provides endpoints for:
- Generating reports from query results
- Checking export status
- Managing report templates
- File download
"""

import logging
from typing import Optional
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Query as FastAPIQuery
from pydantic import BaseModel, Field

from src.api.auth import get_current_user, UserContext
from src.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export")


# ============================================================================
# Request/Response Models
# ============================================================================

class ExportRequest(BaseModel):
    """Request to generate an export/report."""
    query_id: str = Field(..., description="Query ID to export results from")
    format: str = Field(
        ...,
        description="Export format: excel, pdf, csv",
        pattern="^(excel|pdf|csv)$",
    )
    include_metadata: bool = Field(
        True,
        description="Include query metadata in export",
    )
    template: Optional[str] = Field(
        None,
        description="Optional report template ID",
    )


class ExportResponse(BaseModel):
    """Response after initiating export."""
    export_id: str = Field(..., description="Unique export identifier")
    query_id: str
    format: str
    status: str = Field(
        ...,
        description="Status: queued, processing, completed, failed",
    )
    created_at: datetime
    message: str


class ExportStatusResponse(BaseModel):
    """Export status and download information."""
    export_id: str
    query_id: str
    format: str
    status: str
    progress_percent: int = Field(ge=0, le=100, description="Progress percentage")
    created_at: datetime
    completed_at: Optional[datetime] = None
    file_size_bytes: Optional[int] = None
    download_url: Optional[str] = Field(
        None,
        description="Download URL (valid for 24 hours)",
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="Download URL expiration time",
    )
    error: Optional[str] = None


class ReportTemplate(BaseModel):
    """Report template definition."""
    id: str = Field(..., description="Template ID")
    name: str = Field(..., description="User-friendly name")
    description: str
    format: str = Field(..., description="Supported format: excel, pdf, csv")
    sections: list[str] = Field(
        ...,
        description="Report sections: summary, details, charts, tables",
    )
    is_default: bool


class ReportTemplateListResponse(BaseModel):
    """List of available report templates."""
    templates: list[ReportTemplate]


# ============================================================================
# Endpoints
# ============================================================================

@router.post(
    "/report",
    response_model=ExportResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate report from query results",
    description=(
        "Generate a formatted report from query results. "
        "Processing happens asynchronously via Trigger.dev."
    ),
)
async def generate_report(
    request: ExportRequest,
    user: UserContext = Depends(get_current_user),
) -> ExportResponse:
    """
    Generate a report from query results.
    
    Supports multiple formats:
    - Excel: Multi-sheet workbook with formatting
    - PDF: Professional report with charts and branding
    - CSV: Flat data export
    
    Processing:
    1. Fetch query results
    2. Apply template formatting
    3. Generate report file
    4. Store on S3/GCS
    5. Create download link
    
    Args:
        request: Export request with query_id, format, and optional template
        user: Current authenticated user
        
    Returns:
        ExportResponse with export_id and processing status
        
    Raises:
        HTTPException: 400 if validation fails
        HTTPException: 404 if query not found
    """
    export_id = str(uuid4())
    
    try:
        # Validate format
        if request.format not in {"excel", "pdf", "csv"}:
            raise ValidationError(
                f"Invalid format: {request.format}. "
                f"Supported: excel, pdf, csv"
            )
        
        logger.info(
            f"[{export_id}] Report generation initiated by user {user.user_id}: "
            f"query_id={request.query_id}, format={request.format}, "
            f"template={request.template}"
        )
        
        # In production:
        # 1. Verify query_id exists and belongs to user's tenant
        # 2. Create export record in database
        # 3. Trigger Trigger.dev job for report generation
        # 4. Return with status=queued
        
        return ExportResponse(
            export_id=export_id,
            query_id=request.query_id,
            format=request.format,
            status="queued",
            created_at=datetime.utcnow(),
            message="Report generation queued",
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message,
        )
    except Exception as e:
        logger.error(f"[{export_id}] Report generation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report",
        )


@router.get(
    "/{export_id}",
    response_model=ExportStatusResponse,
    summary="Get export status and download link",
    description=(
        "Check the status of an export job and retrieve download URL if ready. "
        "Download URLs expire after 24 hours."
    ),
)
async def get_export_status(
    export_id: str,
    user: UserContext = Depends(get_current_user),
) -> ExportStatusResponse:
    """
    Get export status and download information.
    
    Args:
        export_id: Export ID
        user: Current authenticated user
        
    Returns:
        ExportStatusResponse with status, progress, and download URL if ready
        
    Raises:
        HTTPException: 404 if export not found
        HTTPException: 403 if user doesn't have access
    """
    try:
        logger.info(
            f"Checking export status {export_id} for user {user.user_id}"
        )
        
        # In production:
        # 1. Fetch export record
        # 2. Verify user has access (tenant_id)
        # 3. Check status from database
        # 4. If completed, generate signed S3/GCS URL
        # 5. Set expiration to 24 hours from now
        
        # Placeholder: return 404
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Export {export_id} not found",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching export status {export_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check export status",
        )


@router.get(
    "/templates",
    response_model=ReportTemplateListResponse,
    summary="List available report templates",
    description="Retrieve all available report templates for formatting exports.",
)
async def get_report_templates(
    format_filter: Optional[str] = FastAPIQuery(
        None,
        description="Filter templates by format (excel, pdf, csv)",
    ),
    user: UserContext = Depends(get_current_user),
) -> ReportTemplateListResponse:
    """
    Get available report templates.
    
    Args:
        format_filter: Optional format filter
        user: Current authenticated user
        
    Returns:
        ReportTemplateListResponse with available templates
    """
    try:
        logger.info(f"Fetching report templates for user {user.user_id}")
        
        # In production:
        # 1. Query database for templates
        # 2. Filter by format if provided
        # 3. Return templates available to user's organization
        
        # Return default templates
        templates = [
            ReportTemplate(
                id="default_excel",
                name="Standard Excel Report",
                description="Multi-sheet Excel workbook with summary and details",
                format="excel",
                sections=["summary", "details", "tables"],
                is_default=True,
            ),
            ReportTemplate(
                id="default_pdf",
                name="Professional PDF Report",
                description="Branded PDF with charts and executive summary",
                format="pdf",
                sections=["summary", "charts", "details"],
                is_default=True,
            ),
            ReportTemplate(
                id="default_csv",
                name="CSV Data Export",
                description="Flat CSV format for data analysis",
                format="csv",
                sections=["details"],
                is_default=True,
            ),
        ]
        
        # Apply format filter if provided
        if format_filter:
            templates = [t for t in templates if t.format == format_filter]
        
        return ReportTemplateListResponse(templates=templates)
        
    except Exception as e:
        logger.error(f"Error fetching report templates: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch templates",
        )
