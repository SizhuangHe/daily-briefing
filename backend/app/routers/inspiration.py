from fastapi import APIRouter

from app.schemas.inspiration import InspirationResponse

router = APIRouter()


@router.get("/today", response_model=InspirationResponse)
async def get_today_inspiration():
    """Get today's inspiration bundle (quote + fact + activity)."""
    # TODO: Call inspiration_service
    return InspirationResponse()


@router.post("/refresh", response_model=InspirationResponse)
async def refresh_inspiration():
    """Get a new set of inspiration content."""
    # TODO: Call inspiration_service.refresh()
    return InspirationResponse()
