"""
Briefing assembly service.

Merges Must-Know channel (importance) and Interest channel (TF-IDF)
into a structured 5-section daily briefing.
"""

import json
import logging
from datetime import date

from sqlalchemy.orm import Session

from app.models.article import Article
from app.schemas.briefing import BriefArticle, BriefingSection
from app.services import importance as importance_service
from app.services import recommendation

logger = logging.getLogger(__name__)

# Limits per section
MAX_URGENT = 3
MAX_AFFECTS_YOU = 5
MAX_INTERESTS = 12


def _article_to_brief(article: Article) -> BriefArticle:
    """Convert DB article to BriefArticle."""
    topics = []
    if article.topics:
        try:
            topics = json.loads(article.topics)
        except (json.JSONDecodeError, TypeError):
            pass

    impact_flags = []
    if article.personal_impact_flags:
        try:
            impact_flags = json.loads(article.personal_impact_flags)
        except (json.JSONDecodeError, TypeError):
            pass

    # Extract "why it matters" from gemini_summary if it contains " — "
    summary = article.gemini_summary or ""
    why_it_matters = None
    if " — " in summary:
        parts = summary.split(" — ", 1)
        summary = parts[0]
        why_it_matters = parts[1]

    return BriefArticle(
        id=article.id,
        title=article.title,
        description=article.description,
        url=article.url,
        source_name=article.source_name,
        image_url=article.image_url,
        topics=topics,
        gemini_summary=summary,
        event_type=article.event_type,
        severity=article.severity,
        time_sensitivity=article.time_sensitivity,
        geo_scope=article.geo_scope,
        personal_impact_flags=impact_flags,
        why_it_matters=why_it_matters,
        must_know_level=article.must_know_level or "normal",
        importance_score=article.importance_score or 0.0,
        interest_score=article.interest_score or 0.0,
        confirmed_sources=article.confirmed_sources or 1,
        published_at=article.published_at,
    )


def build_briefing(db: Session) -> dict:
    """Build the structured daily briefing.

    Returns dict with urgent, affects_you, interests sections.
    """
    # Ensure articles have been analyzed
    importance_service.analyze_and_score_articles(db, limit=50)

    # Ensure interest scores are up to date
    recommendation.recalculate_scores(db)

    # Fetch all recent articles sorted by importance
    all_articles = (
        db.query(Article)
        .filter(Article.event_type.isnot(None))
        .order_by(Article.importance_score.desc())
        .limit(200)
        .all()
    )

    used_ids: set[int] = set()

    # Section 1: Urgent (must-know, importance >= urgent threshold)
    urgent_articles = [
        a for a in all_articles
        if a.must_know_level == "urgent"
    ][:MAX_URGENT]

    for a in urgent_articles:
        used_ids.add(a.id)

    # Section 2: Affects You (importance >= affects_you threshold, not already in urgent)
    affects_articles = [
        a for a in all_articles
        if a.must_know_level == "affects_you" and a.id not in used_ids
    ][:MAX_AFFECTS_YOU]

    for a in affects_articles:
        used_ids.add(a.id)

    # Section 3: Your Interests (by interest_score, not already used)
    interest_candidates = [
        a for a in all_articles
        if a.id not in used_ids
    ]
    interest_candidates.sort(key=lambda a: a.interest_score or 0.0, reverse=True)

    # Apply diversity constraint
    interest_articles = recommendation.apply_diversity(
        interest_candidates, limit=MAX_INTERESTS
    )

    return {
        "urgent": BriefingSection(
            title="Urgent",
            description="Critical events you need to know about right now",
            articles=[_article_to_brief(a) for a in urgent_articles],
        ),
        "affects_you": BriefingSection(
            title="Affects You",
            description="News that may impact your daily life",
            articles=[_article_to_brief(a) for a in affects_articles],
        ),
        "interests": BriefingSection(
            title="Your Interests",
            description="Personalized picks based on your preferences",
            articles=[_article_to_brief(a) for a in interest_articles],
        ),
    }
