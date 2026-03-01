"""
Recommendation engine.

Hybrid scoring: TF-IDF content similarity + topic weights +
source preference + recency.

Includes diversity constraints and epsilon-greedy exploration.

Score formula:
  score = 0.30 * topic + 0.35 * tfidf + 0.15 * source + 0.20 * recency
"""

import json
import logging
import random
from collections import Counter
from datetime import datetime, timedelta
from math import log

from sqlalchemy.orm import Session

from app.models.article import Article, ArticleRating
from app.models.preference import TopicWeight

logger = logging.getLogger(__name__)

# Weights for score components
W_TOPIC = 0.30
W_TFIDF = 0.35
W_SOURCE = 0.15
W_RECENCY = 0.20

# Diversity constraints
MAX_SOURCE_RATIO = 0.30   # No single source > 30% of top results
MAX_TOPIC_RATIO = 0.40    # No single topic > 40% of top results

# Exploration
EXPLORATION_EPSILON = 0.10  # 10% chance of inserting exploration articles


def recalculate_scores(db: Session) -> int:
    """Recalculate recommendation scores for all articles.

    Returns the number of articles updated.
    """
    articles = db.query(Article).all()
    if not articles:
        return 0

    # Load ratings to build user profile
    ratings = db.query(ArticleRating).all()
    rating_map = {r.article_id: r.score for r in ratings}

    # Build user topic preferences from ratings
    topic_prefs = _build_topic_preferences(db, articles, rating_map)

    # Build source preferences from ratings
    source_prefs = _build_source_preferences(articles, rating_map)

    # Build TF-IDF similarity scores
    tfidf_scores = _compute_tfidf_scores(articles, rating_map)

    # Calculate composite scores
    now = datetime.utcnow()
    updated = 0
    for article in articles:
        topic_score = _topic_score(article, topic_prefs)
        tfidf_score = tfidf_scores.get(article.id, 0.0)
        source_score = source_prefs.get(article.source_name, 0.5)
        recency_score = _recency_score(article, now)

        score = (
            W_TOPIC * topic_score
            + W_TFIDF * tfidf_score
            + W_SOURCE * source_score
            + W_RECENCY * recency_score
        )

        article.recommendation_score = round(score, 4)
        updated += 1

    db.commit()
    logger.info(f"Updated recommendation scores for {updated} articles")
    return updated


def apply_diversity(
    articles: list[Article],
    limit: int = 20,
) -> list[Article]:
    """Apply diversity constraints and exploration to a ranked list."""
    if len(articles) <= limit:
        return articles

    selected: list[Article] = []
    source_counts: Counter[str] = Counter()
    topic_counts: Counter[str] = Counter()

    for article in articles:
        if len(selected) >= limit:
            break

        source = article.source_name or "unknown"
        topics = _get_topics(article)

        # Check source ratio
        if source_counts[source] / max(len(selected), 1) >= MAX_SOURCE_RATIO:
            continue

        # Check topic ratio (for primary topic)
        primary_topic = topics[0] if topics else "general"
        if topic_counts[primary_topic] / max(len(selected), 1) >= MAX_TOPIC_RATIO:
            continue

        selected.append(article)
        source_counts[source] += 1
        for t in topics:
            topic_counts[t] += 1

    # Epsilon-greedy exploration: insert 1-2 random articles from the tail
    if len(articles) > limit and random.random() < EXPLORATION_EPSILON:
        tail = articles[limit:]
        if tail:
            explorer = random.choice(tail)
            insert_pos = random.randint(len(selected) // 2, max(len(selected) - 1, 1))
            selected.insert(insert_pos, explorer)
            if len(selected) > limit:
                selected = selected[:limit]

    return selected


def update_topic_weights(db: Session) -> None:
    """Update topic weights based on article ratings."""
    ratings = db.query(ArticleRating).all()
    if not ratings:
        return

    articles = db.query(Article).all()
    article_map = {a.id: a for a in articles}

    topic_scores: dict[str, list[int]] = {}
    for r in ratings:
        article = article_map.get(r.article_id)
        if not article:
            continue
        for topic in _get_topics(article):
            if topic not in topic_scores:
                topic_scores[topic] = []
            topic_scores[topic].append(r.score)

    for topic, scores in topic_scores.items():
        avg = sum(scores) / len(scores)
        # Map from [-1, 1] to [0.2, 2.0]
        weight = 1.0 + avg * 0.8
        weight = max(0.2, min(2.0, weight))

        existing = db.query(TopicWeight).filter_by(topic=topic).first()
        if existing:
            existing.weight = weight
        else:
            db.add(TopicWeight(topic=topic, weight=weight))

    db.commit()


# --- Internal helpers ---

def _get_topics(article: Article) -> list[str]:
    """Parse JSON topics from article."""
    if not article.topics:
        return ["general"]
    try:
        topics = json.loads(article.topics)
        return topics if topics else ["general"]
    except (json.JSONDecodeError, TypeError):
        return ["general"]


def _build_topic_preferences(
    db: Session,
    articles: list[Article],
    rating_map: dict[int, int],
) -> dict[str, float]:
    """Build topic preference scores from ratings + stored weights."""
    # Start with stored weights
    prefs: dict[str, float] = {}
    for tw in db.query(TopicWeight).all():
        prefs[tw.topic] = tw.weight

    # Enhance with recent ratings
    if rating_map:
        topic_signals: dict[str, list[int]] = {}
        article_map = {a.id: a for a in articles}
        for aid, score in rating_map.items():
            article = article_map.get(aid)
            if not article:
                continue
            for t in _get_topics(article):
                if t not in topic_signals:
                    topic_signals[t] = []
                topic_signals[t].append(score)

        for topic, signals in topic_signals.items():
            avg_signal = sum(signals) / len(signals)
            # Blend stored weight with signal
            stored = prefs.get(topic, 1.0)
            prefs[topic] = stored * 0.6 + (1.0 + avg_signal * 0.8) * 0.4

    return prefs


def _build_source_preferences(
    articles: list[Article],
    rating_map: dict[int, int],
) -> dict[str, float]:
    """Build source preference from ratings."""
    if not rating_map:
        return {}

    source_scores: dict[str, list[int]] = {}
    article_map = {a.id: a for a in articles}
    for aid, score in rating_map.items():
        article = article_map.get(aid)
        if not article or not article.source_name:
            continue
        if article.source_name not in source_scores:
            source_scores[article.source_name] = []
        source_scores[article.source_name].append(score)

    prefs = {}
    for source, scores in source_scores.items():
        avg = sum(scores) / len(scores)
        # Map from [-1, 1] to [0.2, 1.0]
        prefs[source] = 0.6 + avg * 0.4
    return prefs


def _topic_score(article: Article, topic_prefs: dict[str, float]) -> float:
    """Score article based on topic match with user preferences."""
    topics = _get_topics(article)
    if not topic_prefs:
        return 0.5

    scores = [topic_prefs.get(t, 1.0) for t in topics]
    # Normalize to [0, 1] (weights are in [0.2, 2.0])
    avg = sum(scores) / len(scores)
    return min(1.0, avg / 2.0)


def _recency_score(article: Article, now: datetime) -> float:
    """Score article freshness. Recent articles score higher."""
    if not article.published_at:
        return 0.3

    age = now - article.published_at
    hours = age.total_seconds() / 3600

    if hours <= 1:
        return 1.0
    elif hours <= 6:
        return 0.9
    elif hours <= 12:
        return 0.8
    elif hours <= 24:
        return 0.6
    elif hours <= 48:
        return 0.4
    elif hours <= 72:
        return 0.2
    else:
        return 0.1


def _compute_tfidf_scores(
    articles: list[Article],
    rating_map: dict[int, int],
) -> dict[int, float]:
    """Compute TF-IDF similarity between each article and liked articles.

    Uses a simple bag-of-words approach on title + description.
    """
    if not rating_map:
        # No ratings yet - cold start, return neutral scores
        return {a.id: 0.5 for a in articles}

    liked_ids = [aid for aid, s in rating_map.items() if s > 0]
    if not liked_ids:
        return {a.id: 0.3 for a in articles}

    # Build vocabulary from all articles
    article_map = {a.id: a for a in articles}
    docs: dict[int, list[str]] = {}
    for a in articles:
        text = f"{a.title or ''} {a.description or ''}".lower()
        words = [w for w in text.split() if len(w) > 2]
        docs[a.id] = words

    # IDF: log(N / df)
    n = len(docs)
    df: Counter[str] = Counter()
    for words in docs.values():
        for w in set(words):
            df[w] += 1

    idf = {w: log(n / freq) for w, freq in df.items() if freq < n * 0.8}

    # Build liked profile (average TF-IDF vector of liked articles)
    profile: Counter[str] = Counter()
    for aid in liked_ids:
        if aid not in docs:
            continue
        words = docs[aid]
        tf = Counter(words)
        for w, count in tf.items():
            if w in idf:
                profile[w] += (count / len(words)) * idf[w]

    if not profile:
        return {a.id: 0.5 for a in articles}

    # Normalize profile
    prof_norm = sum(v ** 2 for v in profile.values()) ** 0.5
    if prof_norm == 0:
        return {a.id: 0.5 for a in articles}

    # Score each article by cosine similarity to profile
    scores: dict[int, float] = {}
    for aid, words in docs.items():
        if not words:
            scores[aid] = 0.0
            continue
        tf = Counter(words)
        dot = 0.0
        doc_norm_sq = 0.0
        for w, count in tf.items():
            if w in idf:
                tfidf_val = (count / len(words)) * idf[w]
                dot += tfidf_val * profile.get(w, 0.0)
                doc_norm_sq += tfidf_val ** 2

        doc_norm = doc_norm_sq ** 0.5
        if doc_norm > 0 and prof_norm > 0:
            similarity = dot / (doc_norm * prof_norm)
            scores[aid] = max(0.0, min(1.0, similarity))
        else:
            scores[aid] = 0.0

    return scores
