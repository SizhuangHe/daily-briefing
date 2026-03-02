"""
Offline evaluation metrics for the recommendation engine.

Computes NDCG@k, Like-rate@k, Coverage, and Novelty
on historical data to assess recommendation quality.
"""

import json
import logging
from collections import Counter
from math import log2

from sqlalchemy.orm import Session

from app.models.article import Article, ArticleRating

logger = logging.getLogger(__name__)


def compute_metrics(db: Session, k: int = 20) -> dict:
    """Compute all evaluation metrics."""
    articles = (
        db.query(Article)
        .order_by(Article.recommendation_score.desc())
        .limit(k * 5)
        .all()
    )

    ratings = db.query(ArticleRating).all()
    rating_map = {r.article_id: r.score for r in ratings}

    if not articles:
        return _empty_metrics()

    top_k = articles[:k]
    top_k_ids = [a.id for a in top_k]

    ndcg = _ndcg_at_k(top_k, rating_map, k)
    like_rate = _like_rate_at_k(top_k_ids, rating_map, k)
    coverage = _coverage(top_k, k)
    novelty = _novelty(top_k, db, k)

    return {
        "k": k,
        "ndcg_at_k": round(ndcg, 4),
        "like_rate_at_k": round(like_rate, 4),
        "coverage": coverage,
        "novelty": round(novelty, 4),
        "total_rated": len(rating_map),
        "total_liked": sum(1 for s in rating_map.values() if s > 0),
        "total_disliked": sum(1 for s in rating_map.values() if s < 0),
    }


def _empty_metrics() -> dict:
    return {
        "k": 0,
        "ndcg_at_k": 0.0,
        "like_rate_at_k": 0.0,
        "coverage": {
            "topic_entropy": 0.0,
            "source_entropy": 0.0,
            "unique_topics": 0,
            "unique_sources": 0,
        },
        "novelty": 0.0,
        "total_rated": 0,
        "total_liked": 0,
        "total_disliked": 0,
    }


def _ndcg_at_k(top_k: list[Article], rating_map: dict[int, int], k: int) -> float:
    """Normalized Discounted Cumulative Gain at k.

    Relevance: liked=1, else 0.
    """
    dcg = 0.0
    for i, article in enumerate(top_k[:k]):
        rel = max(0, rating_map.get(article.id, 0))
        dcg += rel / log2(i + 2)

    all_rels = sorted(
        [max(0, rating_map.get(a.id, 0)) for a in top_k], reverse=True
    )
    idcg = sum(rel / log2(i + 2) for i, rel in enumerate(all_rels[:k]))

    return dcg / idcg if idcg > 0 else 0.0


def _like_rate_at_k(
    top_k_ids: list[int], rating_map: dict[int, int], k: int
) -> float:
    """Fraction of top-k articles that were liked."""
    if not top_k_ids:
        return 0.0
    liked_count = sum(1 for aid in top_k_ids[:k] if rating_map.get(aid, 0) > 0)
    return liked_count / min(k, len(top_k_ids))


def _coverage(top_k: list[Article], k: int) -> dict:
    """Topic entropy and source entropy in top-k."""
    topic_counter: Counter[str] = Counter()
    source_counter: Counter[str] = Counter()

    for a in top_k[:k]:
        topics = ["general"]
        if a.topics:
            try:
                topics = json.loads(a.topics) or ["general"]
            except (json.JSONDecodeError, TypeError):
                pass
        for t in topics:
            topic_counter[t] += 1
        source_counter[a.source_name or "unknown"] += 1

    return {
        "topic_entropy": round(_entropy(topic_counter), 4),
        "source_entropy": round(_entropy(source_counter), 4),
        "unique_topics": len(topic_counter),
        "unique_sources": len(source_counter),
    }


def _entropy(counter: Counter) -> float:
    """Shannon entropy of a distribution."""
    total = sum(counter.values())
    if total == 0:
        return 0.0
    ent = 0.0
    for count in counter.values():
        p = count / total
        if p > 0:
            ent -= p * log2(p)
    return ent


def _novelty(top_k: list[Article], db: Session, k: int) -> float:
    """Fraction of topics in top-k that are 'new' for the user.

    A topic is 'new' if it does not appear in any liked article.
    """
    liked_ratings = db.query(ArticleRating).filter(ArticleRating.score > 0).all()
    liked_ids = {r.article_id for r in liked_ratings}

    liked_topics: set[str] = set()
    if liked_ids:
        liked_articles = db.query(Article).filter(Article.id.in_(liked_ids)).all()
        for a in liked_articles:
            if a.topics:
                try:
                    topics = json.loads(a.topics) or []
                    liked_topics.update(topics)
                except (json.JSONDecodeError, TypeError):
                    pass

    if not liked_topics:
        return 1.0

    top_k_topics: set[str] = set()
    for a in top_k[:k]:
        if a.topics:
            try:
                topics = json.loads(a.topics) or []
                top_k_topics.update(topics)
            except (json.JSONDecodeError, TypeError):
                pass

    if not top_k_topics:
        return 0.0

    new_topics = top_k_topics - liked_topics
    return len(new_topics) / len(top_k_topics)
