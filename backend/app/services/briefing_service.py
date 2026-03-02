"""
Briefing assembly service.

Clusters articles into stories via Gemini, then splits stories into
Urgent / Affects You / Your Interests tiers.
"""

import logging
import random
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.article import Article
from app.schemas.briefing import BriefingSection, BriefingStory, StorySource
from app.services import gemini_service
from app.services import importance as importance_service
from app.services import recommendation

logger = logging.getLogger(__name__)

# Max stories per section
MAX_URGENT = 3
MAX_AFFECTS_YOU = 5
MAX_INTERESTS = 10

# Importance thresholds (same as importance.py)
URGENT_THRESHOLD = 0.75
AFFECTS_YOU_THRESHOLD = 0.45


def build_briefing(db: Session) -> dict:
    """Build the structured daily briefing with story clusters.

    Returns dict with urgent, affects_you, interests sections.
    """
    # 1. Run importance analysis + interest scoring
    importance_service.analyze_and_score_articles(db, limit=50)
    recommendation.recalculate_scores(db)

    # 2. Fetch articles from the last 24 hours
    cutoff = datetime.utcnow() - timedelta(hours=24)
    all_articles = (
        db.query(Article)
        .filter(Article.event_type.isnot(None))
        .filter(Article.published_at >= cutoff)
        .order_by(Article.importance_score.desc())
        .limit(200)
        .all()
    )

    if not all_articles:
        empty_section = lambda title, desc: BriefingSection(title=title, description=desc)
        return {
            "urgent": empty_section("Urgent", "Critical events you need to know about right now"),
            "affects_you": empty_section("Affects You", "News that may impact your daily life"),
            "interests": empty_section("Your Interests", "Personalized picks based on your preferences"),
        }

    # 3. Build article lookup and Gemini input
    article_map: dict[int, Article] = {a.id: a for a in all_articles}

    article_dicts = [
        {
            "id": a.id,
            "title": a.title,
            "description": a.description or "",
            "source_name": a.source_name or "",
            "event_type": a.event_type or "",
            "severity": a.severity or "medium",
            "importance_score": a.importance_score or 0.0,
            "interest_score": a.interest_score or 0.0,
            "must_know_level": a.must_know_level or "normal",
            "published_at": str(a.published_at) if a.published_at else None,
        }
        for a in all_articles
    ]

    # 4. Cluster articles into stories via Gemini
    stories_raw = gemini_service.cluster_and_narrate(article_dicts)

    # 5. Enrich stories with scores from their articles
    enriched_stories: list[BriefingStory] = []
    for story_data in stories_raw:
        article_ids = story_data.get("article_ids", [])
        cluster_articles = [article_map[aid] for aid in article_ids if aid in article_map]

        if not cluster_articles:
            continue

        # Derive scores from the cluster
        max_importance = max((a.importance_score or 0.0) for a in cluster_articles)
        avg_interest = sum((a.interest_score or 0.0) for a in cluster_articles) / len(cluster_articles)

        # Must-know level from the highest-importance article
        best_article = max(cluster_articles, key=lambda a: a.importance_score or 0.0)
        must_know_level = best_article.must_know_level or "normal"

        # Build source references
        sources = [
            StorySource(
                id=a.id,
                title=a.title,
                url=a.url,
                source_name=a.source_name,
                published_at=a.published_at,
            )
            for a in cluster_articles
        ]

        enriched_stories.append(BriefingStory(
            headline=story_data.get("headline", "Untitled"),
            narrative=story_data.get("narrative", ""),
            why_it_matters=story_data.get("why_it_matters"),
            event_type=story_data.get("event_type"),
            severity=story_data.get("severity"),
            must_know_level=must_know_level,
            importance_score=max_importance,
            interest_score=avg_interest,
            sources=sources,
        ))

    # 6. Split stories into 3 tiers
    used_story_indices: set[int] = set()

    urgent_stories = []
    for i, s in enumerate(enriched_stories):
        if s.must_know_level == "urgent" and len(urgent_stories) < MAX_URGENT:
            urgent_stories.append(s)
            used_story_indices.add(i)

    affects_stories = []
    for i, s in enumerate(enriched_stories):
        if i not in used_story_indices and s.must_know_level == "affects_you" and len(affects_stories) < MAX_AFFECTS_YOU:
            affects_stories.append(s)
            used_story_indices.add(i)

    # 6c. Split remaining into "for_you" (top 70%) + "explore" (bottom 30%)
    # Explore stories prefer topics not already covered by for_you (coverage gap)
    remaining = [
        (i, s) for i, s in enumerate(enriched_stories)
        if i not in used_story_indices
    ]
    remaining.sort(key=lambda x: x[1].interest_score, reverse=True)
    capped = remaining[:MAX_INTERESTS]

    for_you_count = max(1, int(len(capped) * 0.7))

    # Tag for_you stories and collect their event types
    for_you_stories: list[BriefingStory] = []
    for_you_types: set[str] = set()
    for idx, (i, s) in enumerate(capped[:for_you_count]):
        s.section_type = "for_you"
        for_you_stories.append(s)
        if s.event_type:
            for_you_types.add(s.event_type)

    # For explore: prefer stories whose event_type is NOT in for_you (coverage gap)
    explore_candidates = [(i, s) for i, s in capped[for_you_count:]]
    gap_stories = [(i, s) for i, s in explore_candidates if s.event_type not in for_you_types]
    other_stories = [(i, s) for i, s in explore_candidates if s.event_type in for_you_types]
    # Coverage-gap stories first, then the rest
    ordered_explore = gap_stories + other_stories
    explore_stories: list[BriefingStory] = []
    for i, s in ordered_explore:
        s.section_type = "explore"
        explore_stories.append(s)

    random.shuffle(explore_stories)
    interest_stories = for_you_stories + explore_stories

    return {
        "urgent": BriefingSection(
            title="Urgent",
            description="Critical events you need to know about right now",
            stories=urgent_stories,
        ),
        "affects_you": BriefingSection(
            title="Affects You",
            description="News that may impact your daily life",
            stories=affects_stories,
        ),
        "interests": BriefingSection(
            title="Your Interests",
            description="Personalized picks based on your preferences",
            stories=interest_stories,
        ),
    }
