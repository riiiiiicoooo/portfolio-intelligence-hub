"""Custom domain exceptions for Portfolio Intelligence Hub."""

from typing import Optional, Any


class PIHException(Exception):
    """Base exception for Portfolio Intelligence Hub."""

    def __init__(
        self,
        message: str,
        error_code: str,
        details: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize exception.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Optional additional error details
        """
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


class AuthenticationError(PIHException):
    """Authentication/authorization error."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, "AUTH_ERROR", details)


class ValidationError(PIHException):
    """Input validation error."""

    def __init__(
        self,
        message: str = "Validation failed",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, "VALIDATION_ERROR", details)


class QueryExecutionError(PIHException):
    """Query execution error."""

    def __init__(
        self,
        message: str = "Query execution failed",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, "QUERY_EXECUTION_ERROR", details)


class DocumentProcessingError(PIHException):
    """Document processing error."""

    def __init__(
        self,
        message: str = "Document processing failed",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, "DOCUMENT_PROCESSING_ERROR", details)


class RateLimitError(PIHException):
    """Rate limit exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, "RATE_LIMIT_EXCEEDED", details)


class NotFoundError(PIHException):
    """Resource not found."""

    def __init__(
        self,
        resource: str = "Resource",
        details: Optional[dict[str, Any]] = None,
    ):
        message = f"{resource} not found"
        super().__init__(message, "NOT_FOUND", details)


class PermissionError(PIHException):
    """Permission denied."""

    def __init__(
        self,
        message: str = "Permission denied",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, "PERMISSION_DENIED", details)
