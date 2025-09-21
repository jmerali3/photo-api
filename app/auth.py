from typing import Optional, Dict, Any
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .settings import get_settings, Settings

security: HTTPBearer = HTTPBearer()

def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)) -> bool:
    """
    Verify API key from Authorization header.
    Expected format: Authorization: Bearer <api_key>
    """
    settings: Settings = get_settings()

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

def get_current_user(auth: bool = Depends(verify_api_key)) -> Dict[str, Any]:
    """
    Simple user context for authenticated requests.
    Since this is single-user, we just return a basic user object.
    """
    return {"user_id": "admin", "authenticated": True}