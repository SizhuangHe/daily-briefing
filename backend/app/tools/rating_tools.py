"""MCP tools for article ratings and user profile."""

import json
import logging
from datetime import datetime

from app.database import SessionLocal
from app.models.article import Article, ArticleRating
from app.models.preference import TopicWeight, UserPreference
from app.services import recommendation

logger = logging.getLogger(__name__)


def rate_article(article_id: int, score: int) -> dict:
    """Rate an article: 1=thumbs up, -1=thumbs down, 0=remove rating.

    Triggers recommendation score recalculation after rating.

    Args:
        article_id: The article ID to rate
        score: Rating score (-1, 0, or 1)
    """
    if score not in (-1, 0, 1):
        return {"error": "Score must be -1, 0, or 1"}

    db = SessionLocal()
    try:
        article = db.query(Article).filter_by(id=article_id).first()
        if not article:
            return {"error": f"Article {article_id} not found"}

        existing = db.query(ArticleRating).filter_by(article_id=article_id).first()

        if score == 0:
            if existing:
                db.delete(existing)
            db.commit()
        elif existing:
            existing.score = score
            existing.rating_source = "mcp"
            existing.rated_at = datetime.utcnow()
            db.commit()
        else:
            db.add(ArticleRating(
                article_id=article_id,
                score=score,
                rating_source="mcp",
            ))
            db.commit()

        # Recalculate after rating
        recommendation.update_topic_weights(db)
        recommendation.recalculate_scores(db)

        return {
            "article_id": article_id,
            "score": score,
            "status": "ok",
        }
    finally:
        db.close()


def get_ratings() -> dict[int, int]:
    """Get all article ratings as {article_id: score}."""
    db = SessionLocal()
    try:
        ratings = db.query(ArticleRating).all()
        return {r.article_id: r.score for r in ratings}
    finally:
        db.close()


def get_user_profile() -> dict:
    """Get user profile: topic weights, source preferences, region preferences, centroid count."""
    db = SessionLocal()
    try:
        # Topic weights
        topic_weights = db.query(TopicWeight).all()
        topics = {tw.topic: round(tw.weight, 3) for tw in topic_weights}

        # Source preferences
        articles = db.query(Article).all()
        ratings = db.query(ArticleRating).all()
        rating_map = {r.article_id: r.score for r in ratings}
        source_prefs = recommendation._build_source_preferences(articles, rating_map)
        source_prefs = {k: round(v, 3) for k, v in source_prefs.items()}

        # Centroid count
        liked_ids = [aid for aid, s in rating_map.items() if s > 0]
        article_map = {a.id: a for a in articles}
        liked_with_emb = [
            aid for aid in liked_ids
            if article_map.get(aid) and article_map[aid].embedding
        ]
        centroid_count = min(len(liked_with_emb), 4)

        # Selected topics
        selected_pref = db.query(UserPreference).filter_by(key="topics").first()
        selected_topics = []
        if selected_pref:
            try:
                selected_topics = json.loads(selected_pref.value)
            except (json.JSONDecodeError, TypeError):
                pass

        # Region preferences
        region_counts: dict[str, dict[str, int]] = {}
        for a in articles:
            r = rating_map.get(a.id)
            if r is None or not a.regions:
                continue
            try:
                regions = json.loads(a.regions) if isinstance(a.regions, str) else a.regions
            except (json.JSONDecodeError, TypeError):
                continue
            for region in regions:
                if region not in region_counts:
                    region_counts[region] = {"likes": 0, "dislikes": 0, "total": 0}
                region_counts[region]["total"] += 1
                if r > 0:
                    region_counts[region]["likes"] += 1
                elif r < 0:
                    region_counts[region]["dislikes"] += 1

        region_prefs = {}
        for region, counts in region_counts.items():
            total = counts["total"]
            if total > 0:
                region_prefs[region] = round((counts["likes"] - counts["dislikes"]) / total, 3)

        return {
            "topic_weights": topics,
            "source_preferences": source_prefs,
            "region_preferences": region_prefs,
            "centroid_count": centroid_count,
            "selected_topics": selected_topics,
            "total_liked": len(liked_ids),
            "total_disliked": sum(1 for s in rating_map.values() if s < 0),
        }
    finally:
        db.close()
