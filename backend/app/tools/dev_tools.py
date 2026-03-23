"""MCP tools for developer introspection and system stats."""

import json
import logging
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models.article import Article, ArticleRating
from app.services import evaluation, recommendation

logger = logging.getLogger(__name__)


def get_system_stats() -> dict:
    """Get system statistics: article counts, embeddings, ratings, recent rating history."""
    db = SessionLocal()
    try:
        total_articles = db.query(Article).count()
        articles_with_embeddings = (
            db.query(Article).filter(Article.embedding.isnot(None)).count()
        )
        total_ratings = db.query(ArticleRating).count()

        cutoff = datetime.utcnow() - timedelta(hours=72)
        candidate_window_size = (
            db.query(Article).filter(Article.published_at >= cutoff).count()
        )

        recent_ratings = (
            db.query(ArticleRating)
            .order_by(ArticleRating.rated_at.desc())
            .limit(20)
            .all()
        )

        article_ids = [r.article_id for r in recent_ratings]
        articles = (
            db.query(Article).filter(Article.id.in_(article_ids)).all()
            if article_ids else []
        )
        article_map = {a.id: a for a in articles}

        rating_history = []
        for r in recent_ratings:
            a = article_map.get(r.article_id)
            rating_history.append({
                "article_id": r.article_id,
                "article_title": a.title if a else "Unknown",
                "score": r.score,
                "rated_at": str(r.rated_at),
            })

        return {
            "total_articles": total_articles,
            "articles_with_embeddings": articles_with_embeddings,
            "total_ratings": total_ratings,
            "candidate_window_size": candidate_window_size,
            "candidate_window_hours": 72,
            "rating_history": rating_history,
        }
    finally:
        db.close()


def get_score_breakdown(limit: int = 20) -> dict:
    """Get per-article score breakdown showing raw channel scores.

    Args:
        limit: Number of articles to show (default 20, max 100)
    """
    limit = min(limit, 100)
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(hours=72)
        articles = (
            db.query(Article)
            .filter(
                (Article.published_at >= cutoff) | (Article.published_at.is_(None))
            )
            .order_by(Article.recommendation_score.desc())
            .limit(limit)
            .all()
        )

        ratings = db.query(ArticleRating).all()
        rating_map = {r.article_id: r.score for r in ratings}
        rating_dates = {r.article_id: r.rated_at for r in ratings}

        topic_prefs = recommendation._build_topic_preferences(db, articles, rating_map)
        source_prefs = recommendation._build_source_preferences(articles, rating_map)
        content_scores = recommendation._compute_content_scores(
            articles, rating_map, rating_dates
        )

        now = datetime.utcnow()
        results = []
        for a in articles:
            topics = []
            if a.topics:
                try:
                    topics = json.loads(a.topics)
                except (json.JSONDecodeError, TypeError):
                    pass

            results.append({
                "id": a.id,
                "title": a.title,
                "source_name": a.source_name,
                "topics": topics,
                "final_score": round(a.recommendation_score or 0.0, 4),
                "raw_scores": {
                    "topic": round(recommendation._topic_score(a, topic_prefs), 4),
                    "content": round(content_scores.get(a.id, 0.0), 4),
                    "source": round(source_prefs.get(a.source_name, 0.5), 4),
                    "recency": round(recommendation._recency_score(a, now), 4),
                },
                "importance_score": round(a.importance_score or 0.0, 4),
                "rating": rating_map.get(a.id),
                "published_at": str(a.published_at) if a.published_at else None,
            })

        return {"articles": results}
    finally:
        db.close()


def get_metrics(k: int = 20) -> dict:
    """Get offline evaluation metrics: NDCG@k, like-rate, coverage, novelty.

    Args:
        k: Number of top articles to evaluate (default 20)
    """
    k = min(k, 100)
    db = SessionLocal()
    try:
        return evaluation.compute_metrics(db, k=k)
    finally:
        db.close()
