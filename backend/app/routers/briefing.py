from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.briefing import BriefingResponse
from app.services import briefing_service
from app.services import gemini_service, news_service

router = APIRouter()


@router.get("/briefing", response_model=BriefingResponse)
async def get_briefing(db: Session = Depends(get_db)):
    """Get the aggregated daily briefing with Must-Know + Interest channels."""
    sections = briefing_service.build_briefing(db)

    # Generate AI overview from urgent + affects_you articles
    overview_articles = []
    for section in [sections["urgent"], sections["affects_you"]]:
        for a in section.articles:
            overview_articles.append({
                "title": a.title,
                "description": a.gemini_summary or a.description or "",
                "source_name": a.source_name or "",
                "topics": a.topics,
            })

    overview = ""
    if overview_articles:
        summary_data = gemini_service.summarize_news_by_topic(overview_articles)
        overview = summary_data.get("overview", "")

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
