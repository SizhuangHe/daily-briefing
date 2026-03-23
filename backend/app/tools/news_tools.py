"""MCP tools for news articles."""

import json
import logging

from app.database import SessionLocal
from app.models.article import Article
from app.services import news_service, recommendation
from app.services.importance import analyze_and_score_articles

logger = logging.getLogger(__name__)


def _article_to_dict(article: Article) -> dict:
    """Convert DB article to a plain dict for MCP response."""
    topics = []
    if article.topics:
        try:
            topics = json.loads(article.topics)
        except (json.JSONDecodeError, TypeError):
            pass

    regions = []
    if article.regions:
        try:
            regions = json.loads(article.regions)
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "id": article.id,
        "title": article.title,
        "description": article.description,
        "url": article.url,
        "source_name": article.source_name,
        "image_url": article.image_url,
        "topics": topics,
        "regions": regions,
        "gemini_summary": article.gemini_summary,
        "recommendation_score": article.recommendation_score or 0.0,
        "importance_score": article.importance_score or 0.0,
        "must_know_level": article.must_know_level or "normal",
        "interest_score": article.interest_score or 0.0,
        "event_type": article.event_type,
        "severity": article.severity,
        "published_at": str(article.published_at) if article.published_at else None,
    }


def get_news_articles(
    topic: str | None = None,
    source: str | None = None,
    region: str | None = None,
    sort: str = "score",
    limit: int = 30,
    min_importance: float | None = None,
) -> list[dict]:
    """Get news articles with optional filtering and sorting.

    Args:
        topic: Filter by topic (e.g. "ai", "tech", "finance")
        source: Filter by source name
        region: Filter by region (e.g. "us", "china")
        sort: "score" (recommendation) or "time" (newest first)
        limit: Max articles to return (default 30)
        min_importance: Minimum importance_score threshold
    """
    db = SessionLocal()
    try:
        articles = news_service.get_articles(
            db, topic=topic, source=source, region=region,
            sort=sort, limit=limit,
        )
        results = [_article_to_dict(a) for a in articles]
        if min_importance is not None:
            results = [r for r in results if r["importance_score"] >= min_importance]
        return results
    finally:
        db.close()


def refresh_news() -> dict:
    """Trigger immediate RSS fetch + classification + importance scoring + recommendation recalc."""
    db = SessionLocal()
    try:
        new_count = news_service.fetch_all_sources(db)
        scored = analyze_and_score_articles(db, limit=50)
        updated = recommendation.recalculate_scores(db)
        return {
            "new_articles": new_count,
            "importance_scored": scored,
            "recommendation_updated": updated,
        }
    finally:
        db.close()


def search_articles(query: str, limit: int = 10) -> list[dict]:
    """Search articles by title/description text match.

    Args:
        query: Search text
        limit: Max results (default 10)
    """
    db = SessionLocal()
    try:
        articles = (
            db.query(Article)
            .filter(
                Article.title.contains(query)
                | Article.description.contains(query)
            )
            .order_by(Article.published_at.desc())
            .limit(limit)
            .all()
        )
        return [_article_to_dict(a) for a in articles]
    finally:
        db.close()
