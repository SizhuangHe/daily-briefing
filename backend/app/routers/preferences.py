import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.article import Article
from app.models.preference import NewsSource, TopicWeight, UserPreference
from app.schemas.preference import (
    NewsSourceAddRequest,
    NewsSourceResponse,
    PreferencesResponse,
    PreferencesUpdateRequest,
)

router = APIRouter()


def _get_pref(db: Session, key: str, default=None):
    """Get a user preference value."""
    pref = db.query(UserPreference).filter_by(key=key).first()
    if not pref:
        return default
    try:
        return json.loads(pref.value)
    except (json.JSONDecodeError, TypeError):
        return pref.value


def _set_pref(db: Session, key: str, value) -> None:
    """Set a user preference value."""
    existing = db.query(UserPreference).filter_by(key=key).first()
    encoded = json.dumps(value)
    if existing:
        existing.value = encoded
    else:
        db.add(UserPreference(key=key, value=encoded))


@router.get("", response_model=PreferencesResponse)
async def get_preferences(db: Session = Depends(get_db)):
    """Get all user preferences."""
    topics = _get_pref(db, "topics", [])
    rating_mode = _get_pref(db, "rating_mode", "thumbs")

    # Also get topic weights
    weights = db.query(TopicWeight).all()
    topic_weights = {tw.topic: tw.weight for tw in weights}

    return PreferencesResponse(
        topics=topics,
        rating_mode=rating_mode,
        topic_weights=topic_weights,
    )


@router.put("", response_model=PreferencesResponse)
async def update_preferences(
    prefs: PreferencesUpdateRequest, db: Session = Depends(get_db)
):
    """Update user preferences."""
    if prefs.topics is not None:
        _set_pref(db, "topics", prefs.topics)
    if prefs.rating_mode is not None:
        _set_pref(db, "rating_mode", prefs.rating_mode)

    db.commit()

    return PreferencesResponse(
        topics=_get_pref(db, "topics", []),
        rating_mode=_get_pref(db, "rating_mode", "thumbs"),
    )


@router.get("/topics")
async def get_available_topics(db: Session = Depends(get_db)):
    """Get all unique topics found across articles and event types."""
    articles = db.query(Article.topics).filter(Article.topics.isnot(None)).all()
    all_topics: set[str] = set()
    for (raw_topics,) in articles:
        try:
            parsed = json.loads(raw_topics)
            if isinstance(parsed, list):
                all_topics.update(parsed)
        except (json.JSONDecodeError, TypeError):
            pass

    event_types = (
        db.query(Article.event_type)
        .filter(Article.event_type.isnot(None))
        .distinct()
        .all()
    )
    for (et,) in event_types:
        all_topics.add(et)

    return sorted(all_topics - {"general"})


# --- News Sources CRUD ---

@router.get("/sources", response_model=list[NewsSourceResponse])
async def get_sources(db: Session = Depends(get_db)):
    """List configured news sources."""
    sources = db.query(NewsSource).order_by(NewsSource.name).all()
    return sources


@router.post("/sources", response_model=NewsSourceResponse)
async def add_source(
    source: NewsSourceAddRequest, db: Session = Depends(get_db)
):
    """Add a new news source."""
    existing = db.query(NewsSource).filter_by(url=source.url).first()
    if existing:
        raise HTTPException(status_code=409, detail="Source URL already exists")

    db_source = NewsSource(
        name=source.name,
        url=source.url,
        source_type=source.source_type,
    )
    db.add(db_source)
    db.commit()
    db.refresh(db_source)
    return db_source


@router.put("/sources/{source_id}")
async def toggle_source(source_id: int, db: Session = Depends(get_db)):
    """Toggle a news source enabled/disabled."""
    source = db.query(NewsSource).filter_by(id=source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    source.enabled = not source.enabled
    db.commit()
    return {"id": source.id, "enabled": source.enabled}


@router.delete("/sources/{source_id}")
async def delete_source(source_id: int, db: Session = Depends(get_db)):
    """Remove a news source."""
    source = db.query(NewsSource).filter_by(id=source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    db.delete(source)
    db.commit()
    return {"status": "removed", "id": source_id}
