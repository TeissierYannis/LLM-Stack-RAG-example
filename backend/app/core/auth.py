"""Authentication module: JWT tokens + API key support.

Provides:
- JWT token generation and validation (for frontend sessions)
- API key validation (for programmatic access)
- FastAPI dependency for protected routes
"""

import logging
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, APIKeyHeader

from app.core.config import settings

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

JWT_ALGORITHM = "HS256"


# ---------------------------------------------------------------------------
# JWT Token management
# ---------------------------------------------------------------------------

def create_access_token(
    subject: str,
    extra_claims: dict | None = None,
    expires_minutes: int | None = None,
) -> str:
    """Create a signed JWT access token."""
    exp = expires_minutes or settings.jwt_expiration_minutes
    payload = {
        "sub": subject,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=exp),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises on invalid/expired."""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


# ---------------------------------------------------------------------------
# API Key validation
# ---------------------------------------------------------------------------

def _validate_api_key(key: str) -> bool:
    """Validate an API key against configured keys."""
    if not settings.api_keys:
        return False
    valid_keys = [k.strip() for k in settings.api_keys.split(",") if k.strip()]
    return key in valid_keys


# ---------------------------------------------------------------------------
# FastAPI Dependencies
# ---------------------------------------------------------------------------

async def get_current_user(
    bearer: HTTPAuthorizationCredentials | None = Security(_bearer_scheme),
    api_key: str | None = Security(_api_key_header),
) -> dict:
    """Authenticate via JWT Bearer token or API key.

    Returns user info dict with at least {"sub": "..."}.
    """
    # If auth is disabled, allow all requests
    if not settings.auth_enabled:
        return {"sub": "anonymous", "auth": "disabled"}

    # Try API key first
    if api_key:
        if _validate_api_key(api_key):
            return {"sub": "api-client", "auth": "api_key"}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # Try JWT Bearer token
    if bearer:
        payload = decode_token(bearer.credentials)
        return {"sub": payload["sub"], "auth": "jwt", **payload}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required (Bearer token or X-API-Key header)",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def optional_auth(
    bearer: HTTPAuthorizationCredentials | None = Security(_bearer_scheme),
    api_key: str | None = Security(_api_key_header),
) -> dict | None:
    """Optional authentication — returns None if no credentials provided."""
    if not settings.auth_enabled:
        return {"sub": "anonymous", "auth": "disabled"}

    if not bearer and not api_key:
        return None

    return await get_current_user(bearer, api_key)
