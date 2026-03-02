import json
import logging
import time
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.article import Article
from app.schemas.briefing import BriefingResponse, OverviewDomain
from app.services import briefing_service

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Server-side briefing cache
# ---------------------------------------------------------------------------
_cache: dict = {
    "response": None,
    "built_at": 0.0,
    "article_ids": set(),
}
_CACHE_MIN_AGE = 10 * 60       # 10 min – never regenerate sooner
_CACHE_MAX_AGE = 2 * 60 * 60   # 2 h – force regenerate
_NEW_ARTICLE_THRESHOLD = 5      # need ≥5 new articles to trigger early regen


def _should_regenerate(db: Session) -> bool:
    """Return True if the briefing should be rebuilt."""
    if _cache["response"] is None:
        return True
    age = time.time() - _cache["built_at"]
    if age < _CACHE_MIN_AGE:
        return False
    if age > _CACHE_MAX_AGE:
        return True
    # Check for new articles not in the cached briefing
    cutoff = datetime.utcnow() - timedelta(hours=24)
    current_ids = {
        r[0]
        for r in db.query(Article.id)
        .filter(Article.event_type.isnot(None))
        .filter(Article.published_at >= cutoff)
        .all()
    }
    new_count = len(current_ids - _cache["article_ids"])
    if new_count >= _NEW_ARTICLE_THRESHOLD:
        logger.info("Briefing cache stale: %d new articles detected", new_count)
        return True
    return False


def _generate_overview(sections: dict) -> list[dict]:
    """Generate a domain-based 'at a glance' overview using Gemini.

    Returns a list of {"domain": str, "summary": str} dicts.
    """
    stories = []
    for section in [sections["urgent"], sections["affects_you"], sections["interests"]]:
        for story in section.stories:
            stories.append({
                "headline": story.headline,
                "narrative": story.narrative,
                "why_it_matters": story.why_it_matters,
                "event_type": story.event_type,
                "section": section.title,
            })

    if not stories:
        return []

    story_texts = []
    for s in stories[:15]:
        story_texts.append(
            f"[{s['section']}] [{s.get('event_type', 'general')}] "
            f"{s['headline']}: {s['narrative']}"
            + (f" Why it matters: {s['why_it_matters']}" if s.get("why_it_matters") else "")
        )

    prompt = (
        "You are writing a 'Today at a Glance' overview for a personalized daily news briefing.\n\n"
        "Given the stories below, identify 3-5 key domains/themes that matter today "
        "(e.g. International, Economy, Technology, Security, Health, Politics, Markets, Energy, etc.). "
        "The domains should be chosen dynamically based on the actual stories — do NOT use a fixed list.\n\n"
        "For each domain, write 1-2 concise sentences summarizing the overall landscape/trend, "
        "NOT individual story details. Think big-picture: what's the state of the world in this area today?\n\n"
        "Rules:\n"
        "- 3-5 domains, ordered by importance/urgency\n"
        "- Each summary should be 1-2 sentences, plain language\n"
        "- Synthesize across multiple stories — don't just describe one headline\n"
        "- Focus on trends, shifts, and why the reader should pay attention\n"
        "- Domain names should be short (1-2 words)\n"
        "- Return JSON: {\"domains\": [{\"domain\": \"...\", \"summary\": \"...\"}]}\n\n"
        "Stories:\n" + "\n---\n".join(story_texts)
    )

    try:
        from app.config import settings
        from google import genai
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model=settings.gemini_fallback_model,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        result = json.loads(response.text)
        return result.get("domains", [])
    except Exception as e:
        logger.error(f"Overview generation failed: {e}")
        return []


@router.get("/briefing", response_model=BriefingResponse)
def get_briefing(
    db: Session = Depends(get_db),
    force: bool = Query(False, description="Force regenerate the briefing"),
):
    """Get the aggregated daily briefing with story clusters."""
    if not force and not _should_regenerate(db):
        logger.info("Returning cached briefing (age %.0fs)", time.time() - _cache["built_at"])
        return _cache["response"]

    logger.info("Generating fresh briefing (force=%s)", force)
    sections = briefing_service.build_briefing(db)
    domains = _generate_overview(sections)

    response = BriefingResponse(
        date=date.today(),
        urgent=sections["urgent"],
        affects_you=sections["affects_you"],
        interests=sections["interests"],
        overview_domains=[
            OverviewDomain(domain=d["domain"], summary=d["summary"])
            for d in domains
            if d.get("domain") and d.get("summary")
        ],
    )

    # Collect article IDs used in this briefing
    used_ids: set[int] = set()
    for section in [sections["urgent"], sections["affects_you"], sections["interests"]]:
        for story in section.stories:
            for src in story.sources:
                used_ids.add(src.id)

    _cache["response"] = response
    _cache["built_at"] = time.time()
    _cache["article_ids"] = used_ids

    return response


@router.get("/briefing/history")
async def get_briefing_history():
    """Get historical briefing list."""
    # TODO: Query daily_briefings table
    return []
