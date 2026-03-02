"""
Recommendation engine.

Hybrid scoring: embedding similarity + topic weights +
source preference + recency.

All four channels are percentile-rank normalized before weighting
to ensure comparable distributions.

Includes diversity constraints and quality-constrained exploration.

Score formula (on percentile-ranked values):
  score = 0.30 * topic + 0.35 * content + 0.15 * source + 0.20 * recency
"""

import json
import logging
import random
from collections import Counter
from datetime import datetime, timedelta
from math import log

from sqlalchemy.orm import Session

from app.models.article import Article, ArticleRating
from app.models.preference import TopicWeight, UserPreference

logger = logging.getLogger(__name__)

# Weights for score components
W_TOPIC = 0.30
W_CONTENT = 0.35
W_SOURCE = 0.15
W_RECENCY = 0.20

# Source credibility prior
DEFAULT_SOURCE_PRIOR = 0.6  # Neutral prior for all sources
PRIOR_BLEND_WEIGHT = 0.3    # 30% prior, 70% observed

# Diversity constraints
MAX_SOURCE_RATIO = 0.30   # No single source > 30% of top results
MAX_TOPIC_RATIO = 0.40    # No single topic > 40% of top results

# Exploration
EXPLORATION_EPSILON = 0.10  # 10% chance of inserting exploration articles


def recalculate_scores(db: Session) -> int:
    """Recalculate recommendation scores for all articles.

    Computes raw scores per channel, normalizes via percentile rank,
    then applies weighted combination.

    Returns the number of articles updated.
    """
    # Fixed 72h candidate window for stable percentile ranks
    cutoff = datetime.utcnow() - timedelta(hours=72)
    articles = db.query(Article).filter(
        (Article.published_at >= cutoff) | (Article.published_at.is_(None))
    ).all()
    if not articles:
        return 0

    # Load ratings to build user profile
    ratings = db.query(ArticleRating).all()
    rating_map = {r.article_id: r.score for r in ratings}
    rating_dates = {r.article_id: r.rated_at for r in ratings}

    # Ensure embeddings exist (generate for articles missing them)
    _ensure_embeddings(db, articles)

    # Build user topic preferences from ratings
    topic_prefs = _build_topic_preferences(db, articles, rating_map)

    # Build source preferences from ratings
    source_prefs = _build_source_preferences(articles, rating_map)

    # Compute raw content similarity scores (embedding with TF-IDF fallback)
    content_scores = _compute_content_scores(articles, rating_map, rating_dates)

    # Collect raw scores per channel
    now = datetime.utcnow()
    raw_topic: dict[int, float] = {}
    raw_content: dict[int, float] = {}
    raw_source: dict[int, float] = {}
    raw_recency: dict[int, float] = {}

    for article in articles:
        raw_topic[article.id] = _topic_score(article, topic_prefs)
        raw_content[article.id] = content_scores.get(article.id, 0.0)
        raw_source[article.id] = source_prefs.get(article.source_name, 0.5)
        raw_recency[article.id] = _recency_score(article, now)

    # Percentile-rank normalize each channel
    pr_topic = _percentile_rank(raw_topic)
    pr_content = _percentile_rank(raw_content)
    pr_source = _percentile_rank(raw_source)
    pr_recency = _percentile_rank(raw_recency)

    # Weighted combination of percentile ranks
    updated = 0
    for article in articles:
        aid = article.id
        score = (
            W_TOPIC * pr_topic[aid]
            + W_CONTENT * pr_content[aid]
            + W_SOURCE * pr_source[aid]
            + W_RECENCY * pr_recency[aid]
        )

        article.interest_score = round(score, 4)
        article.recommendation_score = round(score, 4)
        updated += 1

    db.commit()
    logger.info(f"Updated recommendation scores for {updated} articles (percentile-ranked)")
    return updated


def apply_diversity(
    articles: list[Article],
    limit: int = 20,
) -> list[Article]:
    """Apply diversity constraints and quality-constrained exploration."""
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
        primary_topic = topics[0] if topics else None
        if topic_counts[primary_topic] / max(len(selected), 1) >= MAX_TOPIC_RATIO:
            continue

        selected.append(article)
        source_counts[source] += 1
        for t in topics:
            topic_counts[t] += 1

    # Quality-constrained exploration: pick high-importance articles
    # from outside the selection that cover missing topics
    if len(articles) > limit and random.random() < EXPLORATION_EPSILON:
        selected_ids = {a.id for a in selected}
        covered_topics = set(topic_counts.keys())

        # Candidates: not selected, decent importance
        candidates = [
            a for a in articles
            if a.id not in selected_ids
            and (a.importance_score or 0.0) >= 0.3
        ]

        if candidates:
            # Prefer articles covering topics not yet in the selection
            gap_candidates = [
                a for a in candidates
                if not set(_get_topics(a)) & covered_topics
            ]
            pool = gap_candidates if gap_candidates else candidates
            # Pick highest importance from the pool
            explorer = max(pool, key=lambda a: a.importance_score or 0.0)
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
        return []
    try:
        topics = json.loads(article.topics)
        return [t for t in topics if t != "general"] if topics else []
    except (json.JSONDecodeError, TypeError):
        return []


def _build_topic_preferences(
    db: Session,
    articles: list[Article],
    rating_map: dict[int, int],
) -> dict[str, float]:
    """Build topic preference scores from ratings + stored weights + explicit selection."""
    # Start with stored weights
    prefs: dict[str, float] = {}
    for tw in db.query(TopicWeight).all():
        prefs[tw.topic] = tw.weight

    # Boost explicitly selected topics
    selected_pref = db.query(UserPreference).filter_by(key="topics").first()
    if selected_pref:
        try:
            selected_topics = json.loads(selected_pref.value)
            if isinstance(selected_topics, list):
                for topic in selected_topics:
                    current = prefs.get(topic, 1.0)
                    prefs[topic] = min(2.0, current + 0.5)
        except (json.JSONDecodeError, TypeError):
            pass

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
    """Build source preference from ratings blended with credibility prior.

    Final source score = (1 - PRIOR_BLEND_WEIGHT) * observed + PRIOR_BLEND_WEIGHT * prior.
    Sources without ratings get the prior value.
    """
    # Collect all known sources
    all_sources = set()
    for a in articles:
        if a.source_name:
            all_sources.add(a.source_name)

    # Compute observed source scores from ratings
    observed: dict[str, float] = {}
    if rating_map:
        source_scores: dict[str, list[float]] = {}
        article_map = {a.id: a for a in articles}
        for aid, score in rating_map.items():
            article = article_map.get(aid)
            if not article or not article.source_name:
                continue
            if article.source_name not in source_scores:
                source_scores[article.source_name] = []
            source_scores[article.source_name].append(float(score))

        for source, scores in source_scores.items():
            avg = sum(scores) / len(scores)
            # Map from [-1, 1] to [0.2, 1.0]
            observed[source] = 0.6 + max(-1.0, min(1.0, avg)) * 0.4

    # Blend observed with prior for all sources
    prefs = {}
    for source in all_sources:
        prior = DEFAULT_SOURCE_PRIOR
        if source in observed:
            prefs[source] = (1 - PRIOR_BLEND_WEIGHT) * observed[source] + PRIOR_BLEND_WEIGHT * prior
        else:
            prefs[source] = prior

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


def _percentile_rank(scores: dict[int, float]) -> dict[int, float]:
    """Convert raw scores to percentile ranks in [0, 1].

    Ties receive averaged rank. Ensures all channels have comparable
    distributions before weighted combination.
    """
    if not scores:
        return {}
    n = len(scores)
    if n == 1:
        return {k: 0.5 for k in scores}

    # Sort by value
    sorted_items = sorted(scores.items(), key=lambda x: x[1])

    # Assign ranks with tie-averaging
    ranks: dict[int, float] = {}
    i = 0
    while i < n:
        j = i
        while j < n and sorted_items[j][1] == sorted_items[i][1]:
            j += 1
        avg_rank = (i + j - 1) / 2.0
        for k in range(i, j):
            ranks[sorted_items[k][0]] = avg_rank
        i = j

    # Normalize to [0, 1]
    return {k: v / (n - 1) if n > 1 else 0.5 for k, v in ranks.items()}


def _ensure_embeddings(db: Session, articles: list[Article]) -> None:
    """Generate embeddings for articles that don't have them yet."""
    from app.services import gemini_service

    missing = [a for a in articles if not a.embedding]
    if not missing:
        return

    # Batch embed (limit to 100 at a time to avoid API limits)
    batch_size = 100
    total_embedded = 0
    for start in range(0, len(missing), batch_size):
        batch = missing[start : start + batch_size]
        texts = [f"{a.title or ''} {a.description or ''}" for a in batch]
        try:
            embeddings = gemini_service.embed_texts(texts)
            for article, emb in zip(batch, embeddings):
                article.embedding = json.dumps(emb)
                total_embedded += 1
        except Exception:
            logger.warning("Failed to generate embeddings, will use TF-IDF fallback", exc_info=True)
            break

    if total_embedded > 0:
        db.commit()
        logger.info(f"Generated embeddings for {total_embedded} articles")


def _compute_content_scores(
    articles: list[Article],
    rating_map: dict[int, int],
    rating_dates: dict[int, datetime | None] | None = None,
) -> dict[int, float]:
    """Compute content similarity scores using embeddings (with TF-IDF fallback).

    User profile = time-decayed weighted mean of liked article embeddings.
    Time decay: weight = 0.5 ^ (age_days / 7) — 7-day half-life.
    """
    if not rating_map:
        return {a.id: 0.5 for a in articles}

    liked_ids = [aid for aid, s in rating_map.items() if s > 0]
    if not liked_ids:
        return {a.id: 0.3 for a in articles}

    # Try embedding-based scoring first
    article_map = {a.id: a for a in articles}
    embeddings: dict[int, list[float]] = {}
    for a in articles:
        if a.embedding:
            try:
                emb = json.loads(a.embedding)
                if isinstance(emb, list) and len(emb) > 0:
                    embeddings[a.id] = emb
            except (json.JSONDecodeError, TypeError):
                pass

    # Need embeddings for at least some liked articles
    liked_with_emb = [aid for aid in liked_ids if aid in embeddings]
    if liked_with_emb and len(embeddings) > len(articles) * 0.3:
        return _embedding_similarity(embeddings, liked_with_emb, articles, rating_dates)

    # Fallback to TF-IDF
    logger.debug("Using TF-IDF fallback (insufficient embeddings)")
    return _compute_tfidf_scores(articles, rating_map)


def _cosine_similarity(a: list[float], b: list[float], dim: int) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(a[i] * b[i] for i in range(dim))
    norm_a = sum(v ** 2 for v in a) ** 0.5
    norm_b = sum(v ** 2 for v in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _weighted_kmeans(
    points: list[tuple[list[float], float]],
    k: int,
    dim: int,
    max_iter: int = 20,
) -> list[list[float]]:
    """Simple weighted k-means clustering with k-means++ init.

    Args:
        points: List of (embedding, weight) tuples.
        k: Number of clusters.
        dim: Embedding dimensionality.
        max_iter: Maximum iterations.

    Returns:
        List of K centroid vectors.
    """
    if not points or k <= 0:
        return []

    indices = list(range(len(points)))
    chosen = [random.choice(indices)]

    for _ in range(k - 1):
        dists = []
        for i in indices:
            if i in chosen:
                dists.append(0.0)
                continue
            min_d = min(
                1.0 - _cosine_similarity(points[i][0], points[c][0], dim)
                for c in chosen
            )
            dists.append(max(0.0, min_d) * points[i][1])

        total = sum(dists)
        if total == 0:
            break
        r = random.random() * total
        cumulative = 0.0
        for i, d in enumerate(dists):
            cumulative += d
            if cumulative >= r and i not in chosen:
                chosen.append(i)
                break

    centroids = [list(points[i][0]) for i in chosen]

    for _ in range(max_iter):
        clusters: list[list[int]] = [[] for _ in range(len(centroids))]
        for i, (emb, w) in enumerate(points):
            best = 0
            best_sim = -1.0
            for c_idx, cent in enumerate(centroids):
                sim = _cosine_similarity(emb, cent, dim)
                if sim > best_sim:
                    best_sim = sim
                    best = c_idx
            clusters[best].append(i)

        new_centroids = []
        for c_idx, members in enumerate(clusters):
            if not members:
                new_centroids.append(centroids[c_idx])
                continue
            new_cent = [0.0] * dim
            total_w = 0.0
            for m in members:
                emb, w = points[m]
                for d in range(dim):
                    new_cent[d] += emb[d] * w
                total_w += w
            if total_w > 0:
                for d in range(dim):
                    new_cent[d] /= total_w
            new_centroids.append(new_cent)

        if centroids == new_centroids:
            break
        centroids = new_centroids

    return centroids


def _embedding_similarity(
    embeddings: dict[int, list[float]],
    liked_ids: list[int],
    articles: list[Article],
    rating_dates: dict[int, datetime | None] | None = None,
) -> dict[int, float]:
    """Score articles by max cosine similarity across K user profile centroids.

    Uses weighted k-means to cluster liked article embeddings into K centroids
    (K = min(num_liked_with_embeddings, 4)), with time-decay weights (7-day half-life).
    Article score = max cosine similarity to any centroid.
    """
    now = datetime.utcnow()
    dim = len(next(iter(embeddings.values())))

    # Collect weighted liked embeddings
    weighted_liked: list[tuple[list[float], float]] = []
    for aid in liked_ids:
        if aid not in embeddings:
            continue
        weight = 1.0
        if rating_dates and rating_dates.get(aid):
            age_days = (now - rating_dates[aid]).total_seconds() / 86400
            weight = 0.5 ** (age_days / 7.0)
        weighted_liked.append((embeddings[aid], weight))

    if not weighted_liked:
        return {a.id: 0.5 for a in articles}

    # Determine K and build centroids
    K = min(len(weighted_liked), 4)
    centroids = _weighted_kmeans(weighted_liked, K, dim)

    if not centroids:
        return {a.id: 0.5 for a in articles}

    # Score each article: max cosine similarity across centroids
    scores: dict[int, float] = {}
    for a in articles:
        if a.id not in embeddings:
            scores[a.id] = 0.0
            continue
        emb = embeddings[a.id]
        max_sim = max(_cosine_similarity(emb, c, dim) for c in centroids)
        scores[a.id] = max(0.0, min(1.0, max_sim))

    return scores


def get_centroid_details(
    db: Session,
) -> list[dict]:
    """Compute centroids and return details about each one.

    For each centroid, finds the closest liked articles and top-matching
    candidate articles, and summarizes the dominant topics.

    Returns list of dicts: {topics, liked_articles, top_articles}.
    """
    ratings = db.query(ArticleRating).all()
    rating_map = {r.article_id: r.score for r in ratings}
    rating_dates = {r.article_id: r.rated_at for r in ratings}

    liked_ids = [aid for aid, s in rating_map.items() if s > 0]
    if not liked_ids:
        return []

    # Load all articles with embeddings
    articles = db.query(Article).all()
    embeddings: dict[int, list[float]] = {}
    for a in articles:
        if a.embedding:
            try:
                emb = json.loads(a.embedding)
                if isinstance(emb, list) and len(emb) > 0:
                    embeddings[a.id] = emb
            except (json.JSONDecodeError, TypeError):
                pass

    liked_with_emb = [aid for aid in liked_ids if aid in embeddings]
    if not liked_with_emb:
        return []

    now = datetime.utcnow()
    dim = len(next(iter(embeddings.values())))

    # Build weighted liked embeddings and run k-means
    liked_data: list[tuple[int, list[float], float]] = []  # (id, emb, weight)
    weighted_liked: list[tuple[list[float], float]] = []
    for aid in liked_with_emb:
        weight = 1.0
        if rating_dates.get(aid):
            age_days = (now - rating_dates[aid]).total_seconds() / 86400
            weight = 0.5 ** (age_days / 7.0)
        liked_data.append((aid, embeddings[aid], weight))
        weighted_liked.append((embeddings[aid], weight))

    K = min(len(weighted_liked), 4)
    centroids = _weighted_kmeans(weighted_liked, K, dim)
    if not centroids:
        return []

    article_map = {a.id: a for a in articles}

    # Assign each liked article to its nearest centroid
    centroid_liked: list[list[int]] = [[] for _ in range(len(centroids))]
    for aid, emb, _ in liked_data:
        best = 0
        best_sim = -1.0
        for c_idx, cent in enumerate(centroids):
            sim = _cosine_similarity(emb, cent, dim)
            if sim > best_sim:
                best_sim = sim
                best = c_idx
        centroid_liked[best].append(aid)

    # For each centroid, find top 5 closest articles from all articles
    results = []
    for c_idx, cent in enumerate(centroids):
        # Score all articles against this centroid
        scored = []
        for a in articles:
            if a.id not in embeddings:
                continue
            sim = _cosine_similarity(embeddings[a.id], cent, dim)
            scored.append((a.id, sim))
        scored.sort(key=lambda x: -x[1])
        top_articles = scored[:5]

        # Collect topics from liked articles in this centroid
        topic_counts: dict[str, int] = {}
        for aid in centroid_liked[c_idx]:
            a = article_map.get(aid)
            if a:
                for t in _get_topics(a):
                    topic_counts[t] = topic_counts.get(t, 0) + 1
        top_topics = sorted(topic_counts.items(), key=lambda x: -x[1])

        results.append({
            "id": c_idx,
            "topics": [t for t, _ in top_topics[:5]],
            "liked_articles": [
                {"id": aid, "title": article_map[aid].title}
                for aid in centroid_liked[c_idx]
                if aid in article_map
            ],
            "top_matches": [
                {
                    "id": aid,
                    "title": article_map[aid].title,
                    "similarity": round(sim, 3),
                }
                for aid, sim in top_articles
                if aid in article_map
            ],
        })

    return results


def _compute_tfidf_scores(
    articles: list[Article],
    rating_map: dict[int, int],
) -> dict[int, float]:
    """Compute TF-IDF similarity between each article and liked articles.

    Used as fallback when embeddings are not available.
    """
    if not rating_map:
        return {a.id: 0.5 for a in articles}

    liked_ids = [aid for aid, s in rating_map.items() if s > 0]
    if not liked_ids:
        return {a.id: 0.3 for a in articles}

    docs: dict[int, list[str]] = {}
    for a in articles:
        text = f"{a.title or ''} {a.description or ''}".lower()
        words = [w for w in text.split() if len(w) > 2]
        docs[a.id] = words

    n = len(docs)
    df: Counter[str] = Counter()
    for words in docs.values():
        for w in set(words):
            df[w] += 1

    idf = {w: log(n / freq) for w, freq in df.items() if freq < n * 0.8}

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

    prof_norm = sum(v ** 2 for v in profile.values()) ** 0.5
    if prof_norm == 0:
        return {a.id: 0.5 for a in articles}

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
