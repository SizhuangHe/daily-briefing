from fastapi import APIRouter

from app.schemas.inspiration import InspirationResponse
from app.services import inspiration_service

router = APIRouter()


@router.get("/today", response_model=InspirationResponse)
async def get_today_inspiration():
    """Get today's inspiration bundle (quote + fact + activity)."""
    return inspiration_service.get_today_inspiration()


@router.post("/refresh", response_model=InspirationResponse)
async def refresh_inspiration():
    """Get a new set of inspiration content."""
    return inspiration_service.get_refreshed_inspiration()
