from typing import Dict, Any
from fastapi import APIRouter

router: APIRouter = APIRouter()

@router.get("/healthz")
async def health() -> Dict[str, bool]:
    """Health check endpoint - no authentication required."""
    return {"ok": True}