from typing import Dict
from fastapi import APIRouter, status
router: APIRouter = APIRouter()

@router.get("/healthz", status_code=status.HTTP_200_OK)
async def health() -> Dict[str, bool]:
    """Health check endpoint - no authentication required."""
    return {"ok": True}
