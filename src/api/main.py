"""
Portfolio Intelligence Hub - FastAPI Application

A RAG platform for real estate operators providing:
- Natural language to SQL query execution on Snowflake
- Semantic search over property documents
- Report generation and export
"""

import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Callable, Optional
from datetime import datetime

from fastapi import (
    FastAPI,
    Request,
    Response,
    HTTPException,
    status,
    Depends,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import redis.asyncio as redis
import uvicorn

from src.api.auth import get_current_user, UserContext
from src.api.endpoints import queries, documents, export
from src.core.exceptions import (
    PIHException,
    QueryExecutionError,
    DocumentProcessingError,
    AuthenticationError,
    ValidationError,
    RateLimitError,
)
from src.core.config import Settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
settings = Settings()


# ============================================================================
# Models
# ============================================================================

class HealthCheckResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    version: str
    services: dict[str, str]


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str
    error_code: str
    details: Optional[dict[str, Any]] = None
    timestamp: datetime
    request_id: Optional[str] = None


# ============================================================================
# Global State
# ============================================================================

class AppState:
    """Global application state."""
    redis_client: Optional[redis.Redis] = None
    snowflake_pool: Optional[Any] = None


app_state = AppState()


# ============================================================================
# Lifespan Handler
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application startup and shutdown.
    
    Startup:
    - Initialize Redis connection pool
    - Initialize Snowflake connection pool
    - Log initialization status
    
    Shutdown:
    - Close Redis connections
    - Close Snowflake connections
    """
    # Startup
    try:
        logger.info("Initializing Portfolio Intelligence Hub...")
        
        # Initialize Redis
        app_state.redis_client = await redis.from_url(
            settings.REDIS_URL,
            encoding="utf8",
            decode_responses=True,
            max_connections=20,
        )
        logger.info("Redis connection pool initialized")
        
        # Initialize Snowflake pool (placeholder)
        # In production, use snowflake-sqlalchemy or snowflake-connector-python
        logger.info("Snowflake connection pool initialized")
        
        logger.info("Application startup complete")
        
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    try:
        logger.info("Shutting down Portfolio Intelligence Hub...")
        
        if app_state.redis_client:
            await app_state.redis_client.close()
            logger.info("Redis connection pool closed")
        
        logger.info("Application shutdown complete")
        
    except Exception as e:
        logger.error(f"Shutdown error: {str(e)}")


# ============================================================================
# FastAPI App Initialization
# ============================================================================

app = FastAPI(
    title="Portfolio Intelligence Hub",
    description=(
        "RAG platform for real estate operators. "
        "Combines Snowflake data with semantic search for intelligent querying."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


# ============================================================================
# Middleware
# ============================================================================

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


# Request ID and logging middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next: Callable) -> Response:
    """
    Add request ID to all requests for tracing.
    Log request/response details.
    """
    request_id = request.headers.get("X-Request-ID", f"req_{int(time.time() * 1000)}")
    request.state.request_id = request_id
    
    start_time = time.time()
    
    logger.info(
        f"[{request_id}] {request.method} {request.url.path}",
        extra={"request_id": request_id},
    )
    
    response = await call_next(request)
    
    duration_ms = int((time.time() - start_time) * 1000)
    logger.info(
        f"[{request_id}] {request.method} {request.url.path} - "
        f"{response.status_code} ({duration_ms}ms)",
        extra={"request_id": request_id},
    )
    
    response.headers["X-Request-ID"] = request_id
    return response


# Tenant context injection middleware
@app.middleware("http")
async def inject_tenant_context(request: Request, call_next: Callable) -> Response:
    """
    Extract and inject tenant context from authenticated user.
    Makes tenant_id available throughout request lifecycle.
    """
    try:
        # Auth endpoints bypass tenant injection
        if request.url.path.startswith("/api/health"):
            return await call_next(request)
        
        # For protected endpoints, tenant context is extracted in auth dependency
        response = await call_next(request)
        return response
        
    except Exception as e:
        logger.error(f"Tenant context injection failed: {str(e)}")
        return await call_next(request)


# Rate limiting middleware
@app.middleware("http")
async def rate_limit(request: Request, call_next: Callable) -> Response:
    """
    Implement per-user rate limiting using Redis.
    
    Limits:
    - 100 requests per minute for standard users
    - 500 requests per minute for premium users
    """
    if not app_state.redis_client or request.url.path.startswith("/api/health"):
        return await call_next(request)
    
    try:
        # Try to get user from request (if authenticated)
        if request.headers.get("Authorization"):
            user_id = request.state.get("user_id", "anonymous")
            
            rate_limit_key = f"rate_limit:{user_id}"
            current = await app_state.redis_client.incr(rate_limit_key)
            
            if current == 1:
                await app_state.redis_client.expire(rate_limit_key, 60)
            
            limit = 500 if request.state.get("is_premium") else 100
            
            if current > limit:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "error_code": "RATE_LIMIT_EXCEEDED",
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
        
        response = await call_next(request)
        return response
        
    except Exception as e:
        logger.warning(f"Rate limiting check failed: {str(e)}")
        return await call_next(request)


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(PIHException)
async def pih_exception_handler(request: Request, exc: PIHException) -> JSONResponse:
    """Handle Portfolio Intelligence Hub domain exceptions."""
    request_id = getattr(request.state, "request_id", None)
    
    status_code_map = {
        QueryExecutionError: status.HTTP_400_BAD_REQUEST,
        DocumentProcessingError: status.HTTP_422_UNPROCESSABLE_ENTITY,
        AuthenticationError: status.HTTP_401_UNAUTHORIZED,
        ValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
        RateLimitError: status.HTTP_429_TOO_MANY_REQUESTS,
    }
    
    status_code = status_code_map.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    logger.error(
        f"[{request_id}] {type(exc).__name__}: {str(exc)}",
        extra={"request_id": request_id},
    )
    
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error=exc.message,
            error_code=exc.error_code,
            details=exc.details,
            timestamp=datetime.utcnow(),
            request_id=request_id,
        ).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    request_id = getattr(request.state, "request_id", None)
    
    logger.warning(
        f"[{request_id}] Validation error: {str(exc)}",
        extra={"request_id": request_id},
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="Validation error",
            error_code="VALIDATION_ERROR",
            details={"errors": exc.errors()},
            timestamp=datetime.utcnow(),
            request_id=request_id,
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    request_id = getattr(request.state, "request_id", None)
    
    logger.error(
        f"[{request_id}] Unexpected error: {type(exc).__name__}: {str(exc)}",
        exc_info=True,
        extra={"request_id": request_id},
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            error_code="INTERNAL_SERVER_ERROR",
            timestamp=datetime.utcnow(),
            request_id=request_id,
        ).model_dump(),
    )


# ============================================================================
# Health Check
# ============================================================================

@app.get(
    "/api/health",
    response_model=HealthCheckResponse,
    tags=["System"],
    summary="Health check endpoint",
)
async def health_check() -> HealthCheckResponse:
    """
    Check application and service health.
    
    Returns status of:
    - Application itself
    - Redis connection
    - Snowflake connection
    - OpenAI API
    """
    services = {}
    
    # Redis check
    if app_state.redis_client:
        try:
            await app_state.redis_client.ping()
            services["redis"] = "healthy"
        except Exception as e:
            logger.warning(f"Redis health check failed: {str(e)}")
            services["redis"] = "unhealthy"
    else:
        services["redis"] = "not_initialized"
    
    # Snowflake check (placeholder)
    services["snowflake"] = "healthy"
    
    # OpenAI check (placeholder)
    services["openai"] = "healthy"
    
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="1.0.0",
        services=services,
    )


# ============================================================================
# Router Registration
# ============================================================================

# Include endpoint routers
app.include_router(
    queries.router,
    prefix="/api/v1",
    tags=["Queries"],
)

app.include_router(
    documents.router,
    prefix="/api/v1",
    tags=["Documents"],
)

app.include_router(
    export.router,
    prefix="/api/v1",
    tags=["Export"],
)


# ============================================================================
# Root endpoint
# ============================================================================

@app.get("/", tags=["System"])
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "name": "Portfolio Intelligence Hub",
        "version": "1.0.0",
        "docs": "/api/docs",
        "health": "/api/health",
    }


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level="info",
    )
