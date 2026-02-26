"""Authentication API: login, token generation, user info."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import create_access_token, get_current_user
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserInfoResponse(BaseModel):
    sub: str
    auth: str


@router.post("/token", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Get a JWT access token.

    In production, integrate with your enterprise IdP (Azure AD, Okta, Cognito).
    This endpoint provides a simple username/password check for development.
    """
    if not settings.auth_enabled:
        # Auth disabled — issue token for any request
        token = create_access_token(subject=request.username)
        return TokenResponse(
            access_token=token,
            expires_in=settings.jwt_expiration_minutes * 60,
        )

    # Simple dev auth: check against configured credentials
    # In production, replace this with LDAP/OAuth2/SAML validation
    if request.username == "admin" and request.password == settings.secret_key:
        token = create_access_token(
            subject=request.username,
            extra_claims={"role": "admin"},
        )
        return TokenResponse(
            access_token=token,
            expires_in=settings.jwt_expiration_minutes * 60,
        )

    raise HTTPException(status_code=401, detail="Invalid credentials")


@router.get("/me", response_model=UserInfoResponse)
async def get_me(user: dict = Depends(get_current_user)):
    """Get current authenticated user info."""
    return UserInfoResponse(sub=user["sub"], auth=user.get("auth", "unknown"))


@router.get("/status")
async def auth_status():
    """Check if authentication is enabled."""
    return {"auth_enabled": settings.auth_enabled}
