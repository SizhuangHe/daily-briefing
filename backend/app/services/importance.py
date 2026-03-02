"""
Importance scoring engine (Must-Know channel).

Two-stage scoring:
1. Rule-based baseline (fast, deterministic) from article metadata
2. Gemini-extracted structured fields boost/override

Tier 0 (Urgent): public safety, severe weather, health emergencies, infrastructure
Tier 1 (Affects You): policy changes, financial shocks, local governance
Tier 2 (Contextual): research/tech shocks with concrete downstream impact
"""

import json
import logging

from sqlalchemy.orm import Session

from app.models.article import Article
from app.services import gemini_service

logger = logging.getLogger(__name__)

# Thresholds for must-know classification
URGENT_THRESHOLD = 0.75
AFFECTS_YOU_THRESHOLD = 0.45

# Event type -> base importance weight
EVENT_TYPE_WEIGHTS = {
    # Tier 0: always high priority
    "disaster": 0.90,
    "public_safety": 0.90,
    "health": 0.80,
    "weather": 0.80,
    "infrastructure": 0.75,
    # Tier 1: important when severe
    "war_conflict": 0.70,
    "policy": 0.60,
    "financial_shock": 0.65,
    "crime": 0.55,
    "diplomacy": 0.50,
    # Tier 2: contextual
    "market": 0.40,
    "tech": 0.35,
    "science": 0.30,
    # Low importance
    "sports": 0.15,
    "entertainment": 0.15,
}

SEVERITY_MULTIPLIER = {
    "critical": 1.3,
    "high": 1.1,
    "medium": 0.9,
    "low": 0.7,
}

TIME_SENSITIVITY_BOOST = {
    "immediate": 0.20,
    "today": 0.10,
    "this_week": 0.0,
    "none": -0.05,
}

GEO_SCOPE_BOOST = {
    "local": 0.15,
    "regional": 0.10,  # US-level
    "us": 0.10,
    "global": 0.0,
}

# Personal impact flags that boost importance
IMPACT_FLAG_BOOST = 0.05  # per flag


def analyze_and_score_articles(db: Session, limit: int = 50) -> int:
    """Run Gemini structured extraction + importance scoring on recent articles.

    Returns number of articles scored.
    """
    # Get articles that haven't been analyzed yet (no event_type)
    articles = (
        db.query(Article)
        .filter(Article.event_type.is_(None))
        .order_by(Article.published_at.desc())
        .limit(limit)
        .all()
    )

    if not articles:
        return 0

    # Batch analyze with Gemini
    article_dicts = [
        {
            "id": a.id,
            "title": a.title,
            "description": a.description or "",
            "source_name": a.source_name or "",
        }
        for a in articles
    ]

    analysis = gemini_service.analyze_articles(article_dicts)

    scored = 0
    for article in articles:
        data = analysis.get(article.id, {})

        # Store structured fields
        article.event_type = data.get("event_type")
        article.geo_scope = data.get("geo_scope", "global")
        article.time_sensitivity = data.get("time_sensitivity", "none")
        article.severity = data.get("severity", "medium")

        impact_flags = data.get("personal_impact_flags", [])
        if isinstance(impact_flags, list):
            article.personal_impact_flags = json.dumps(impact_flags)
        else:
            article.personal_impact_flags = "[]"

        # Store one-line summary and why-it-matters in gemini_summary if not already set
        one_line = data.get("one_line_summary", "")
        why = data.get("why_it_matters", "")
        if not article.gemini_summary and one_line:
            article.gemini_summary = one_line
            if why:
                article.gemini_summary += f" — {why}"

        # Calculate importance score
        article.importance_score = _calculate_importance(article)

        # Classify must-know level
        if article.importance_score >= URGENT_THRESHOLD:
            article.must_know_level = "urgent"
        elif article.importance_score >= AFFECTS_YOU_THRESHOLD:
            article.must_know_level = "affects_you"
        else:
            article.must_know_level = "normal"

        scored += 1

    db.commit()
    logger.info(f"Analyzed and scored {scored} articles for importance")
    return scored


def score_all_articles(db: Session) -> int:
    """Recalculate importance scores for all articles that have been analyzed."""
    articles = db.query(Article).filter(Article.event_type.isnot(None)).all()

    for article in articles:
        article.importance_score = _calculate_importance(article)
        if article.importance_score >= URGENT_THRESHOLD:
            article.must_know_level = "urgent"
        elif article.importance_score >= AFFECTS_YOU_THRESHOLD:
            article.must_know_level = "affects_you"
        else:
            article.must_know_level = "normal"

    db.commit()
    return len(articles)


def _calculate_importance(article: Article) -> float:
    """Calculate importance score from structured fields."""
    # Base score from event type
    base = EVENT_TYPE_WEIGHTS.get(article.event_type or "", 0.25)

    # Severity multiplier
    multiplier = SEVERITY_MULTIPLIER.get(article.severity or "medium", 0.9)
    score = base * multiplier

    # Time sensitivity boost
    score += TIME_SENSITIVITY_BOOST.get(article.time_sensitivity or "none", 0.0)

    # Geo scope boost
    score += GEO_SCOPE_BOOST.get(article.geo_scope or "global", 0.0)

    # Personal impact flags boost
    try:
        flags = json.loads(article.personal_impact_flags or "[]")
        score += len(flags) * IMPACT_FLAG_BOOST
    except (json.JSONDecodeError, TypeError):
        pass

    # Multi-source confirmation boost
    if (article.confirmed_sources or 1) >= 2:
        score += 0.05

    return round(min(1.0, max(0.0, score)), 4)
