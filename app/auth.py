from typing import Optional
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .settings import get_settings

security = HTTPBearer()

def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)) -> bool:
    """
    Verify API key from Authorization header.
    Expected format: Authorization: Bearer <api_key>
    """
    settings = get_settings()

    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing"
        )

    if credentials.credentials != settings.api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )

    return True

def get_current_user(auth: bool = Depends(verify_api_key)) -> dict:
    """
    Simple user context for authenticated requests.
    Since this is single-user, we just return a basic user object.
    """
    return {"user_id": "admin", "authenticated": True}