import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.article import Article, ArticleRating
from app.schemas.article import (
    ArticleRatingRequest,
    ArticleRatingResponse,
    ArticleResponse,
)
from app.services import gemini_service, news_service, recommendation

router = APIRouter()


def _article_to_response(article: Article) -> ArticleResponse:
    """Convert DB article to response, parsing JSON topics."""
    topics = []
    if article.topics:
        try:
            topics = json.loads(article.topics)
        except (json.JSONDecodeError, TypeError):
            pass

    return ArticleResponse(
        id=article.id,
        title=article.title,
        description=article.description,
        url=article.url,
        source_name=article.source_name,
        image_url=article.image_url,
        topics=topics,
        gemini_summary=article.gemini_summary,
        recommendation_score=article.recommendation_score or 0.0,
        published_at=article.published_at,
    )


@router.get("", response_model=list[ArticleResponse])
async def get_news(
    topic: str | None = None,
    source: str | None = None,
    sort: str = Query(default="score", pattern="^(score|time)$"),
    limit: int = Query(default=20, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """Get news articles with optional filtering and sorting."""
    articles = news_service.get_articles(
        db, topic=topic, source=source, sort=sort, limit=limit, offset=offset
    )
    return [_article_to_response(a) for a in articles]


@router.get("/sources")
async def get_sources(db: Session = Depends(get_db)):
    """Get all distinct news source names."""
    return news_service.get_sources(db)


@router.get("/summary")
async def get_news_summary(db: Session = Depends(get_db)):
    """Get an AI-generated summary of today's news organized by topic."""
    articles = news_service.get_articles(db, limit=30)
    if not articles:
        return {"overview": "No articles available. Click Refresh to fetch news.", "sections": []}

    article_dicts = []
    for a in articles:
        topics = []
        if a.topics:
            try:
                topics = json.loads(a.topics)
            except (json.JSONDecodeError, TypeError):
                pass
        article_dicts.append({
            "title": a.title,
            "description": a.description or "",
            "source_name": a.source_name or "",
            "topics": topics,
        })

    result = gemini_service.summarize_news_by_topic(article_dicts)
    return result


@router.get("/ratings")
async def get_ratings(db: Session = Depends(get_db)):
    """Get all article ratings as a map of article_id -> score."""
    ratings = db.query(ArticleRating).all()
    return {r.article_id: r.score for r in ratings}


@router.get("/liked", response_model=list[ArticleResponse])
async def get_liked_articles(db: Session = Depends(get_db)):
    """Get all articles the user has liked (score=1), newest first."""
    liked = (
        db.query(Article)
        .join(ArticleRating, ArticleRating.article_id == Article.id)
        .filter(ArticleRating.score == 1)
        .order_by(ArticleRating.rated_at.desc())
        .all()
    )
    return [_article_to_response(a) for a in liked]


@router.get("/disliked", response_model=list[ArticleResponse])
async def get_disliked_articles(db: Session = Depends(get_db)):
    """Get all articles the user has disliked (score=-1), newest first."""
    disliked = (
        db.query(Article)
        .join(ArticleRating, ArticleRating.article_id == Article.id)
        .filter(ArticleRating.score == -1)
        .order_by(ArticleRating.rated_at.desc())
        .all()
    )
    return [_article_to_response(a) for a in disliked]



@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(article_id: int, db: Session = Depends(get_db)):
    """Get a single article by ID."""
    article = db.query(Article).filter_by(id=article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return _article_to_response(article)


@router.post("/{article_id}/rate", response_model=ArticleRatingResponse)
async def rate_article(
    article_id: int,
    rating: ArticleRatingRequest,
    db: Session = Depends(get_db),
):
    """Rate an article (1=up, -1=down, 0=remove)."""
    article = db.query(Article).filter_by(id=article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if rating.score not in (-1, 0, 1):
        raise HTTPException(status_code=400, detail="Score must be -1, 0, or 1")

    existing = db.query(ArticleRating).filter_by(article_id=article_id).first()
    if rating.score == 0:
        if existing:
            db.delete(existing)
        db.commit()
        recommendation.update_topic_weights(db)
        recommendation.recalculate_scores(db)
        return ArticleRatingResponse(
            article_id=article_id,
            score=0,
            rated_at=datetime.utcnow(),
        )

    if existing:
        existing.score = rating.score
        existing.rating_source = "article"
        existing.rated_at = datetime.utcnow()
    else:
        db.add(ArticleRating(
            article_id=article_id,
            score=rating.score,
            rating_source="article",
        ))
    db.commit()

    # Recalculate recommendation scores after rating
    recommendation.update_topic_weights(db)
    recommendation.recalculate_scores(db)

    return ArticleRatingResponse(
        article_id=article_id,
        score=rating.score,
        rated_at=datetime.utcnow(),
    )


@router.post("/refresh")
async def refresh_news(db: Session = Depends(get_db)):
    """Manually trigger news fetch from all sources + Gemini summaries."""
    new_count = news_service.fetch_all_sources(db)

    # Generate Gemini summaries for articles that don't have one
    unsummarized = (
        db.query(Article)
        .filter(Article.gemini_summary.is_(None))
        .order_by(Article.published_at.desc())
        .limit(20)
        .all()
    )

    summaries_count = 0
    if unsummarized:
        article_dicts = [
            {"id": a.id, "title": a.title, "description": a.description}
            for a in unsummarized
        ]
        summaries = gemini_service.summarize_articles(article_dicts)
        for article in unsummarized:
            if article.id in summaries:
                article.gemini_summary = summaries[article.id]
        db.commit()
        summaries_count = len(summaries)

    # Recalculate recommendation scores for all articles
    recommendation.recalculate_scores(db)

    return {
        "status": "ok",
        "new_articles": new_count,
        "summaries_generated": summaries_count,
    }
