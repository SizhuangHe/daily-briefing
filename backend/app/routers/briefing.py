from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.briefing import BriefingResponse
from app.services import briefing_service

router = APIRouter()


@router.get("/briefing", response_model=BriefingResponse)
async def get_briefing(db: Session = Depends(get_db)):
    """Get the aggregated daily briefing with story clusters."""
    sections = briefing_service.build_briefing(db)

    # Build overview from story headlines in urgent + affects_you
    overview_parts = []
    for section in [sections["urgent"], sections["affects_you"]]:
        for story in section.stories:
            overview_parts.append(story.headline)

    overview = ""
    if overview_parts:
        overview = "Today's key stories: " + "; ".join(overview_parts) + "."

    return BriefingResponse(
        date=date.today(),
        urgent=sections["urgent"],
        affects_you=sections["affects_you"],
        interests=sections["interests"],
        overview=overview,
    )


@router.get("/briefing/history")
async def get_briefing_history():
    """Get historical briefing list."""
    # TODO: Query daily_briefings table
    return []
