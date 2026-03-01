from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.preference import (
    NewsSourceAddRequest,
    NewsSourceResponse,
    PreferencesResponse,
    PreferencesUpdateRequest,
)

router = APIRouter()


@router.get("", response_model=PreferencesResponse)
async def get_preferences(db: Session = Depends(get_db)):
    """Get all user preferences."""
    # TODO: Query user_preferences table
    return PreferencesResponse()


@router.put("", response_model=PreferencesResponse)
async def update_preferences(
    prefs: PreferencesUpdateRequest, db: Session = Depends(get_db)
):
    """Update user preferences."""
    # TODO: Update user_preferences table
    return PreferencesResponse(
        topics=prefs.topics or [],
        rating_mode=prefs.rating_mode or "thumbs",
    )


@router.get("/sources", response_model=list[NewsSourceResponse])
async def get_sources(db: Session = Depends(get_db)):
    """List configured news sources."""
    # TODO: Query news_sources table
    return []


@router.post("/sources", response_model=NewsSourceResponse)
async def add_source(
    source: NewsSourceAddRequest, db: Session = Depends(get_db)
):
    """Add a new news source."""
    # TODO: Insert into news_sources table
    return NewsSourceResponse(
        id=0, name=source.name, url=source.url, source_type=source.source_type
    )


@router.delete("/sources/{source_id}")
async def delete_source(source_id: int, db: Session = Depends(get_db)):
    """Remove a news source."""
    # TODO: Delete from news_sources table
    return {"status": "removed", "id": source_id}
