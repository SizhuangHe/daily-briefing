"""
Gemini API service using the google-genai SDK.

Handles embedding, topic/region classification, and structured article analysis.
Summarization and clustering are handled by Claude (via MCP).
"""

import json
import logging

from google import genai

from app.config import settings

logger = logging.getLogger(__name__)

_client: genai.Client | None = None


def _get_client() -> genai.Client | None:
    """Lazy-initialize Gemini client."""
    global _client
    if _client is None and settings.gemini_api_key:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts using Gemini embedding model.

    Returns a list of embedding vectors (one per input text).
    Raises on failure (caller should handle).
    """
    client = _get_client()
    if not client:
        raise RuntimeError("Gemini client not available")

    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=texts,
    )
    return [emb.values for emb in result.embeddings]


VALID_TOPICS = [
    "ai", "tech", "finance", "science", "world", "health",
    "business", "energy", "sports", "entertainment",
    "disaster", "public_safety", "weather", "infrastructure",
    "war_conflict", "policy", "financial_shock", "market",
    "crime", "diplomacy", "education", "space", "automotive", "crypto",
    "environment",
]

VALID_REGIONS = [
    "us", "china", "europe", "middle_east", "japan", "korea",
    "south_asia", "southeast_asia", "russia", "africa",
    "latin_america", "canada", "australia", "uk", "global",
]


def classify_topics(articles: list[dict]) -> dict[int, list[str]]:
    """Classify articles into topics using Gemini.

    Used as fallback when keyword matching results in 'general'.

    Args:
        articles: List of dicts with keys: id, title, description

    Returns:
        Dict mapping article ID to list of topic strings.
    """
    client = _get_client()
    if not client or not articles:
        return {}

    article_texts = []
    for a in articles:
        article_texts.append(
            f"ID: {a['id']}\n"
            f"Title: {a['title']}\n"
            f"Description: {(a.get('description') or '')[:300]}"
        )

    topics_str = ", ".join(VALID_TOPICS)
    prompt = (
        "You are a news classifier. For each article below, assign 1-3 topic labels.\n\n"
        f"Valid topics: {topics_str}\n\n"
        "Rules:\n"
        "- Pick the most specific applicable topics\n"
        "- Use 1-3 topics per article\n"
        "- Only use topics from the valid list above\n"
        "- 'sports' is ONLY for articles primarily about athletic competitions, teams, players, or sporting events. "
        "Do NOT tag geopolitical, finance, or conflict articles as 'sports' even if they mention a sporting event in passing.\n"
        "- Be precise: an article about oil prices is 'finance'/'energy', not 'sports'\n\n"
        "Articles:\n"
        + "\n---\n".join(article_texts)
        + '\n\nReturn JSON: {"articles": {"<id>": ["topic1", "topic2"]}}'
    )

    try:
        response = client.models.generate_content(
            model=settings.gemini_fallback_model,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        result = json.loads(response.text)
        articles_data = result.get("articles", result)
        # Validate topics
        classified = {}
        for k, v in articles_data.items():
            valid = [t for t in v if t in VALID_TOPICS]
            if valid:
                classified[int(k)] = valid
        return classified
    except Exception as e:
        logger.error(f"Gemini topic classification failed: {e}")
        return {}


def classify_regions(articles: list[dict]) -> dict[int, list[str]]:
    """Classify articles by geographic region using Gemini.

    Args:
        articles: List of dicts with keys: id, title, description

    Returns:
        Dict mapping article ID to list of region strings.
    """
    client = _get_client()
    if not client or not articles:
        return {}

    article_texts = []
    for a in articles:
        article_texts.append(
            f"ID: {a['id']}\n"
            f"Title: {a['title']}\n"
            f"Description: {(a.get('description') or '')[:300]}"
        )

    regions_str = ", ".join(VALID_REGIONS)
    prompt = (
        "You are a news geo-tagger. For each article below, assign 1-3 geographic region labels.\n\n"
        f"Valid regions: {regions_str}\n\n"
        "Rules:\n"
        "- Pick the most relevant regions where the event takes place or has impact\n"
        "- Use 'global' only for truly worldwide events (e.g. climate change, global recession)\n"
        "- Use 1-3 regions per article\n"
        "- Only use regions from the valid list above\n\n"
        "Articles:\n"
        + "\n---\n".join(article_texts)
        + '\n\nReturn JSON: {"articles": {"<id>": ["region1", "region2"]}}'
    )

    try:
        response = client.models.generate_content(
            model=settings.gemini_fallback_model,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        result = json.loads(response.text)
        articles_data = result.get("articles", result)
        classified = {}
        for k, v in articles_data.items():
            valid = [r for r in v if r in VALID_REGIONS]
            if valid:
                classified[int(k)] = valid
        return classified
    except Exception as e:
        logger.error(f"Gemini region classification failed: {e}")
        return {}


def analyze_articles(articles: list[dict]) -> dict[int, dict]:
    """Extract structured fields from articles using Gemini.

    For each article, extracts: event_type, geo_scope, time_sensitivity,
    severity, personal_impact_flags, one_line_summary, why_it_matters.

    Args:
        articles: List of dicts with keys: id, title, description, source_name

    Returns:
        Dict mapping article ID to structured analysis dict.
    """
    client = _get_client()
    if not client or not articles:
        return {}

    article_texts = []
    for a in articles:
        article_texts.append(
            f"ID: {a['id']}\n"
            f"Source: {a.get('source_name', 'Unknown')}\n"
            f"Title: {a['title']}\n"
            f"Description: {a.get('description', 'N/A')[:500]}\n"
        )

    prompt = (
        "You are a news analyst. For each article below, extract structured metadata.\n\n"
        "For each article, provide:\n"
        "- event_type: one of [disaster, public_safety, health, weather, policy, war_conflict, "
        "financial_shock, market, tech, science, crime, infrastructure, diplomacy, sports, entertainment]\n"
        "- geo_scope: one of [global, us, regional, local]\n"
        "- time_sensitivity: one of [immediate, today, this_week, none]\n"
        "- severity: one of [critical, high, medium, low]\n"
        "- personal_impact_flags: array from [travel, health, safety, finance, utilities, "
        "policy_deadline, work, education] (empty array if none)\n"
        "- one_line_summary: 1 sentence summary (max 30 words)\n"
        "- why_it_matters: 1 sentence on why a reader should care (max 25 words)\n\n"
        "Articles:\n"
        + "\n---\n".join(article_texts)
        + "\n\nReturn JSON: {\"articles\": {\"<id>\": {fields...}}}"
    )

    try:
        response = client.models.generate_content(
            model=settings.gemini_primary_model,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        result = json.loads(response.text)
        articles_data = result.get("articles", result)
        return {int(k): v for k, v in articles_data.items()}
    except Exception as e:
        logger.error(f"Gemini article analysis failed with primary: {e}")
        try:
            response = client.models.generate_content(
                model=settings.gemini_fallback_model,
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            result = json.loads(response.text)
            articles_data = result.get("articles", result)
            return {int(k): v for k, v in articles_data.items()}
        except Exception as e2:
            logger.error(f"Gemini article analysis failed with fallback: {e2}")
            return {}
