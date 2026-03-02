"""Developer dashboard API endpoints.

Provides introspection into the recommendation engine:
user profile, score breakdowns, evaluation metrics, system stats.
"""

import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.article import Article, ArticleRating
from app.models.preference import TopicWeight, UserPreference
from app.services import evaluation, news_service, recommendation

router = APIRouter()


@router.get("/dev/profile")
async def get_profile(db: Session = Depends(get_db)):
    """Get user profile data: topic weights, source preferences, centroid count."""
    topic_weights = db.query(TopicWeight).all()
    topics = {tw.topic: round(tw.weight, 3) for tw in topic_weights}

    articles = db.query(Article).all()
    ratings = db.query(ArticleRating).all()
    rating_map = {r.article_id: r.score for r in ratings}
    source_prefs = recommendation._build_source_preferences(articles, rating_map)
    source_prefs = {k: round(v, 3) for k, v in source_prefs.items()}

    # Centroid count (based on number of liked articles with embeddings)
    liked_ids = [aid for aid, s in rating_map.items() if s > 0]
    article_map = {a.id: a for a in articles}
    liked_with_emb = [
        aid
        for aid in liked_ids
        if article_map.get(aid) and article_map[aid].embedding
    ]
    centroid_count = min(len(liked_with_emb), 4)

    selected_pref = db.query(UserPreference).filter_by(key="topics").first()
    selected_topics = []
    if selected_pref:
        try:
            selected_topics = json.loads(selected_pref.value)
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "topic_weights": topics,
        "source_preferences": source_prefs,
        "centroid_count": centroid_count,
        "selected_topics": selected_topics,
        "total_liked": len(liked_ids),
        "total_disliked": sum(1 for s in rating_map.values() if s < 0),
    }


@router.get("/dev/scores")
async def get_scores(
    limit: int = Query(default=30, le=100),
    db: Session = Depends(get_db),
):
    """Get article score breakdowns: per-channel raw scores."""
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

        results.append(
            {
                "id": a.id,
                "title": a.title,
                "source_name": a.source_name,
                "topics": topics,
                "final_score": round(a.recommendation_score or 0.0, 4),
                "raw_scores": {
                    "topic": round(recommendation._topic_score(a, topic_prefs), 4),
                    "content": round(content_scores.get(a.id, 0.0), 4),
                    "source": round(
                        source_prefs.get(a.source_name, 0.5), 4
                    ),
                    "recency": round(
                        recommendation._recency_score(a, now), 4
                    ),
                },
                "rating": rating_map.get(a.id),
                "published_at": str(a.published_at) if a.published_at else None,
            }
        )

    return {"articles": results}


@router.get("/dev/metrics")
async def get_metrics(
    k: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
):
    """Get offline evaluation metrics."""
    return evaluation.compute_metrics(db, k=k)


@router.get("/dev/centroids")
async def get_centroids(db: Session = Depends(get_db)):
    """Get centroid details: topics, liked articles, and top matches per centroid."""
    return recommendation.get_centroid_details(db)


@router.get("/dev/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get system statistics."""
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
        if article_ids
        else []
    )
    article_map = {a.id: a for a in articles}

    rating_history = []
    for r in recent_ratings:
        a = article_map.get(r.article_id)
        rating_history.append(
            {
                "article_id": r.article_id,
                "article_title": a.title if a else "Unknown",
                "score": r.score,
                "rated_at": str(r.rated_at),
            }
        )

    return {
        "total_articles": total_articles,
        "articles_with_embeddings": articles_with_embeddings,
        "total_ratings": total_ratings,
        "candidate_window_size": candidate_window_size,
        "candidate_window_hours": 72,
        "rating_history": rating_history,
    }


@router.post("/dev/reclassify")
async def reclassify_topics(db: Session = Depends(get_db)):
    """Reclassify all articles using Gemini. Use sparingly."""
    updated = news_service.reclassify_all_articles(db)
    total = db.query(Article).count()
    return {"updated": updated, "total": total}


@router.post("/dev/classify-regions")
async def classify_regions(db: Session = Depends(get_db)):
    """Classify all articles by geographic region using Gemini."""
    updated = news_service.classify_all_regions(db)
    total = db.query(Article).count()
    return {"updated": updated, "total": total}
