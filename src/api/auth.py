"""
Authentication Module - Clerk JWT Verification

Handles:
- JWT token verification against Clerk public keys
- User context extraction from JWT claims
- Role-based access control
- FastAPI dependency injection for auth
"""

import logging
from typing import Optional
from dataclasses import dataclass
from functools import lru_cache
import base64

import httpx
import jwt
from jwt import PyJWTError
from fastapi import Request, HTTPException, status, Depends
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

from src.core.config import Settings
from src.core.exceptions import AuthenticationError

logger = logging.getLogger(__name__)
settings = Settings()


# ============================================================================
# Models
# ============================================================================

@dataclass
class UserContext:
    """
    User context extracted from JWT token.
    
    Attributes:
        user_id: Unique user identifier (Clerk user ID)
        tenant_id: Organization/tenant identifier
        role: User role (admin, analyst, viewer)
        assigned_properties: List of property IDs user has access to
        email: User email address
        full_name: User full name
    """
    user_id: str
    tenant_id: str
    role: str
    assigned_properties: list[str]
    email: str
    full_name: str
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == "admin"
    
    @property
    def is_analyst(self) -> bool:
        """Check if user has analyst role."""
        return self.role == "analyst"
    
    @property
    def is_viewer(self) -> bool:
        """Check if user has viewer role."""
        return self.role == "viewer"


# ============================================================================
# Clerk Public Key Management
# ============================================================================

def _jwk_to_pem(jwk: dict) -> str:
    """
    Convert a JWK (JSON Web Key) to PEM format.

    Args:
        jwk: JWK dictionary from Clerk JWKS endpoint

    Returns:
        Public key in PEM format

    Raises:
        ValueError: If JWK format is invalid
    """
    try:
        # Check if x5c (certificate chain) is available - this is simplest
        if "x5c" in jwk and jwk["x5c"]:
            cert_str = jwk["x5c"][0]
            # x5c is base64 encoded DER certificate
            cert_der = base64.b64decode(cert_str)
            # Load the certificate
            from cryptography.hazmat.primitives.serialization import load_der_x509_certificate
            cert = load_der_x509_certificate(cert_der, default_backend())
            # Extract public key and convert to PEM
            public_key = cert.public_key()
            pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            return pem.decode('utf-8')

        # Fallback: construct RSA key from n and e components (JWK RSA format)
        if jwk.get("kty") == "RSA" and "n" in jwk and "e" in jwk:
            from cryptography.hazmat.primitives.asymmetric import rsa
            from jwt.utils import base64url_decode
            import json

            # Decode base64url encoded components
            n = int.from_bytes(base64url_decode(jwk["n"] + "=="), byteorder='big')
            e = int.from_bytes(base64url_decode(jwk["e"] + "=="), byteorder='big')

            # Create RSA public key
            public_numbers = rsa.RSAPublicNumbers(e, n)
            public_key = public_numbers.public_key(default_backend())

            # Convert to PEM
            pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            return pem.decode('utf-8')

        raise ValueError(f"Unsupported JWK format or missing required fields: {jwk.keys()}")

    except Exception as e:
        logger.error(f"Failed to convert JWK to PEM: {e}")
        raise ValueError(f"Invalid JWK format: {str(e)}")


@lru_cache(maxsize=1)
def get_clerk_public_key() -> str:
    """
    Fetch and cache Clerk public key.

    Returns:
        Public key for JWT verification (in PEM format)

    Raises:
        AuthenticationError: If public key cannot be fetched
    """
    try:
        url = f"{settings.CLERK_API_URL}/jwks"
        response = httpx.get(
            url,
            headers={"Authorization": f"Bearer {settings.CLERK_API_KEY}"},
            timeout=10.0,
        )
        response.raise_for_status()

        jwks = response.json()

        # Get first key from JWKS (in production, implement proper key selection by kid)
        if jwks.get("keys"):
            key_data = jwks["keys"][0]
            # Convert JWK to PEM format for PyJWT
            pem_key = _jwk_to_pem(key_data)
            logger.info("Clerk public key cached and converted to PEM format")
            return pem_key

        raise AuthenticationError("No keys found in JWKS")

    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch Clerk public key: {str(e)}")
        raise AuthenticationError("Failed to fetch public key for token verification")


# ============================================================================
# Token Verification
# ============================================================================

def verify_clerk_token(token: str) -> UserContext:
    """
    Verify Clerk JWT token and extract user context.
    
    Args:
        token: JWT token from Authorization header
        
    Returns:
        UserContext with user information and permissions
        
    Raises:
        AuthenticationError: If token is invalid, expired, or verification fails
    """
    if not token:
        raise AuthenticationError("No token provided")
    
    # Remove "Bearer " prefix if present
    if token.startswith("Bearer "):
        token = token[7:]
    
    try:
        # Fetch Clerk public key and verify token signature
        public_key = get_clerk_public_key()
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=settings.CLERK_API_ID,
        )
        
        # Extract user information from JWT claims
        user_id: str = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Token missing 'sub' claim (user ID)")
        
        # Extract tenant from organization metadata or custom claims
        tenant_id: str = payload.get("org_id") or payload.get("tenant_id")
        if not tenant_id:
            raise AuthenticationError("Token missing tenant information")
        
        # Extract user metadata
        email: str = payload.get("email", "")
        full_name: str = payload.get("name", "")
        
        # Extract role from metadata
        metadata = payload.get("metadata", {})
        role: str = metadata.get("role", "viewer").lower()
        
        # Validate role
        valid_roles = {"admin", "analyst", "viewer"}
        if role not in valid_roles:
            logger.warning(f"Invalid role in token: {role}. Defaulting to 'viewer'")
            role = "viewer"
        
        # Extract assigned properties
        assigned_properties: list[str] = metadata.get("assigned_properties", [])
        
        logger.info(
            f"Token verified for user {user_id} (tenant: {tenant_id}, role: {role})"
        )
        
        return UserContext(
            user_id=user_id,
            tenant_id=tenant_id,
            role=role,
            assigned_properties=assigned_properties,
            email=email,
            full_name=full_name,
        )
        
    except PyJWTError as e:
        logger.warning(f"Token verification failed: {str(e)}")
        raise AuthenticationError("Invalid or expired token")
    except KeyError as e:
        logger.warning(f"Missing required claim in token: {str(e)}")
        raise AuthenticationError(f"Invalid token: missing {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {str(e)}")
        raise AuthenticationError("Failed to verify token")


# ============================================================================
# FastAPI Dependencies
# ============================================================================

async def get_current_user(request: Request) -> UserContext:
    """
    FastAPI dependency to extract and verify current user.
    
    Extracts JWT token from Authorization header and verifies it.
    
    Args:
        request: FastAPI request object
        
    Returns:
        UserContext with verified user information
        
    Raises:
        HTTPException: 401 if token is invalid or missing
        
    Usage:
        @app.get("/protected")
        async def protected_endpoint(user: UserContext = Depends(get_current_user)):
            return {"user_id": user.user_id}
    """
    auth_header = request.headers.get("Authorization")
    
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user_context = verify_clerk_token(auth_header)
        # Store in request state for downstream access
        request.state.user = user_context
        request.state.user_id = user_context.user_id
        request.state.tenant_id = user_context.tenant_id
        return user_context
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_role(allowed_roles: list[str]):
    """
    Factory for creating role-based access control dependencies.
    
    Args:
        allowed_roles: List of roles that are allowed access (e.g., ["admin", "analyst"])
        
    Returns:
        FastAPI dependency function
        
    Usage:
        @app.delete("/admin/users/{user_id}")
        async def delete_user(
            user: UserContext = Depends(get_current_user),
            _: None = Depends(require_role(["admin"])),
        ):
            # Only accessible to admin users
            pass
    """
    async def role_checker(user: UserContext = Depends(get_current_user)) -> UserContext:
        """Check if user has required role."""
        if user.role not in allowed_roles:
            logger.warning(
                f"Access denied for user {user.user_id}: "
                f"role '{user.role}' not in {allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(allowed_roles)}",
            )
        return user
    
    return role_checker


def require_property_access(property_id: str):
    """
    Factory for creating property-level access control dependencies.
    
    Args:
        property_id: Property ID to check access for
        
    Returns:
        FastAPI dependency function
        
    Raises:
        HTTPException: 403 if user doesn't have access to property
        
    Usage:
        @app.get("/properties/{property_id}/documents")
        async def get_property_documents(
            property_id: str,
            user: UserContext = Depends(get_current_user),
            _: None = Depends(require_property_access(property_id)),
        ):
            # Only accessible if user has access to this property
            pass
    """
    async def property_checker(
        user: UserContext = Depends(get_current_user),
    ) -> UserContext:
        """Check if user has access to property."""
        # Admins have access to all properties
        if user.is_admin:
            return user
        
        # Check if property is in user's assigned properties
        if property_id not in user.assigned_properties:
            logger.warning(
                f"Access denied for user {user.user_id}: "
                f"no access to property {property_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to property {property_id}",
            )
        
        return user
    
    return property_checker


# ============================================================================
# Optional Authentication (for endpoints that work with or without auth)
# ============================================================================

async def get_optional_user(request: Request) -> Optional[UserContext]:
    """
    Optional FastAPI dependency for endpoints that work with or without auth.
    
    Returns None if no valid token is provided.
    
    Usage:
        @app.get("/public-data")
        async def get_public_data(user: Optional[UserContext] = Depends(get_optional_user)):
            if user:
                # User-specific data
                pass
            else:
                # Public data
                pass
    """
    auth_header = request.headers.get("Authorization")
    
    if not auth_header:
        return None
    
    try:
        return verify_clerk_token(auth_header)
    except AuthenticationError:
        return None
