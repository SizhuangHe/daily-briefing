from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.article import (
    ArticleRatingRequest,
    ArticleRatingResponse,
    ArticleResponse,
)

router = APIRouter()


@router.get("", response_model=list[ArticleResponse])
async def get_news(
    topic: str | None = None,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """Get news articles sorted by recommendation score."""
    # TODO: Query articles with recommendation sorting
    return []


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(article_id: int, db: Session = Depends(get_db)):
    """Get a single article by ID."""
    # TODO: Query single article
    return {"id": article_id, "title": "placeholder", "url": ""}


@router.post("/{article_id}/rate", response_model=ArticleRatingResponse)
async def rate_article(
    article_id: int,
    rating: ArticleRatingRequest,
    db: Session = Depends(get_db),
):
    """Rate an article (thumbs up/down)."""
    # TODO: Store rating and trigger recommendation update
    from datetime import datetime

    return ArticleRatingResponse(
        article_id=article_id, score=rating.score, rated_at=datetime.utcnow()
    )


@router.post("/refresh")
async def refresh_news(db: Session = Depends(get_db)):
    """Manually trigger news fetch from all sources."""
    # TODO: Call news_service.fetch_all_sources()
    return {"status": "refresh triggered"}
