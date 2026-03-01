from datetime import date

from fastapi import APIRouter

from app.schemas.briefing import BriefingResponse

router = APIRouter()


@router.get("/briefing", response_model=BriefingResponse)
async def get_briefing():
    """Get the aggregated daily briefing."""
    # TODO: Aggregate data from all services
    return BriefingResponse(date=date.today())


@router.get("/briefing/history")
async def get_briefing_history():
    """Get historical briefing list."""
    # TODO: Query daily_briefings table
    return []
