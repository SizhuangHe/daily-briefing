"""
Gemini API service using the new google-genai SDK.

Handles news summarization, recommendation reasoning,
and schedule summarization with model fallback and JSON mode.
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


def summarize_articles(articles: list[dict]) -> dict[int, str]:
    """Generate concise summaries for a batch of articles.

    Args:
        articles: List of dicts with keys: id, title, description

    Returns:
        Dict mapping article ID to summary string.
    """
    client = _get_client()
    if not client or not articles:
        return {}

    # Build prompt with all articles
    article_texts = []
    for i, a in enumerate(articles):
        article_texts.append(
            f"Article {i+1} (ID: {a['id']}):\n"
            f"Title: {a['title']}\n"
            f"Description: {a.get('description', 'N/A')}\n"
        )

    prompt = (
        "You are a news summarizer. For each article below, write a concise "
        "1-2 sentence summary that captures the key point.\n\n"
        "Return a JSON object where keys are article IDs (as strings) and "
        "values are summary strings.\n\n"
        + "\n".join(article_texts)
    )

    try:
        response = client.models.generate_content(
            model=settings.gemini_primary_model,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        result = json.loads(response.text)
        return {int(k): v for k, v in result.items()}
    except Exception as e:
        logger.error(f"Gemini summarization failed with primary model: {e}")
        try:
            response = client.models.generate_content(
                model=settings.gemini_fallback_model,
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            result = json.loads(response.text)
            return {int(k): v for k, v in result.items()}
        except Exception as e2:
            logger.error(f"Gemini summarization failed with fallback: {e2}")
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
        "financial_shock, market, tech, science, crime, infrastructure, diplomacy, sports, entertainment, general]\n"
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


def summarize_news_by_topic(articles: list[dict]) -> dict:
    """Generate a high-level news summary organized by topic.

    Args:
        articles: List of dicts with keys: title, description, source_name, topics

    Returns:
        Dict with 'sections' (list of {topic, summary, key_stories}) and 'overview'.
    """
    client = _get_client()
    if not client or not articles:
        return _fallback_news_summary(articles)

    # Group articles by topic for the prompt
    article_texts = []
    for i, a in enumerate(articles):
        topics = ", ".join(a.get("topics", [])) or "general"
        article_texts.append(
            f"{i+1}. [{topics}] {a['title']} ({a.get('source_name', 'Unknown')})\n"
            f"   {a.get('description', '')[:200]}"
        )

    prompt = (
        "You are a concise news analyst. Given today's top news articles below, "
        "create a brief summary organized by topic area.\n\n"
        "Requirements:\n"
        "- Write a 1-sentence overall overview\n"
        "- Group into 3-5 topic sections (e.g., Technology, Finance, World, Science)\n"
        "- Each section: 1-2 sentence summary of key developments\n"
        "- Be concise and insightful, focus on what matters most\n\n"
        "Articles:\n"
        + "\n".join(article_texts)
        + "\n\nReturn JSON with this schema:\n"
        '{"overview": "string", "sections": [{"topic": "string", "summary": "string"}]}'
    )

    try:
        response = client.models.generate_content(
            model=settings.gemini_primary_model,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"Gemini news summary failed with primary model: {e}")
        try:
            response = client.models.generate_content(
                model=settings.gemini_fallback_model,
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            return json.loads(response.text)
        except Exception as e2:
            logger.error(f"Gemini news summary failed with fallback: {e2}")
            return _fallback_news_summary(articles)


def _fallback_news_summary(articles: list[dict]) -> dict:
    """Simple fallback summary without Gemini."""
    topic_counts: dict[str, int] = {}
    for a in articles:
        for t in a.get("topics", ["general"]):
            topic_counts[t] = topic_counts.get(t, 0) + 1

    sections = []
    for topic, count in sorted(topic_counts.items(), key=lambda x: -x[1]):
        sections.append({
            "topic": topic.capitalize(),
            "summary": f"{count} article{'s' if count != 1 else ''} in this category.",
        })

    return {
        "overview": f"Today's briefing includes {len(articles)} articles across {len(topic_counts)} topics.",
        "sections": sections[:5],
    }


def summarize_schedule(events: list[dict], reminders: list[dict]) -> str:
    """Generate a natural language summary of today's schedule."""
    client = _get_client()
    if not client:
        return _fallback_schedule_summary(events, reminders)

    prompt = (
        "You are a helpful personal assistant. Summarize the user's schedule "
        "for today in 2-3 conversational sentences. Highlight the most important "
        "items and any time-sensitive tasks.\n\n"
        f"Calendar events:\n{json.dumps(events, indent=2, default=str)}\n\n"
        f"Pending reminders:\n{json.dumps(reminders, indent=2, default=str)}\n\n"
        "Return a JSON object with a single key 'summary' containing the string."
    )

    try:
        response = client.models.generate_content(
            model=settings.gemini_primary_model,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        result = json.loads(response.text)
        return result.get("summary", "")
    except Exception as e:
        logger.error(f"Gemini schedule summary failed: {e}")
        return _fallback_schedule_summary(events, reminders)


def _fallback_schedule_summary(events: list[dict], reminders: list[dict]) -> str:
    """Simple fallback summary without Gemini."""
    parts = []
    if events:
        parts.append(f"You have {len(events)} event{'s' if len(events) != 1 else ''} today.")
    else:
        parts.append("You have no calendar events today.")
    if reminders:
        parts.append(f"You have {len(reminders)} pending reminder{'s' if len(reminders) != 1 else ''}.")
    else:
        parts.append("No pending reminders.")
    return " ".join(parts)


def cluster_and_narrate(articles: list[dict]) -> list[dict]:
    """Cluster related articles into stories and generate narrative summaries.

    Args:
        articles: List of dicts with keys: id, title, description, source_name,
                  event_type, severity, importance_score, interest_score,
                  must_know_level, published_at

    Returns:
        List of story dicts, each with:
          headline, narrative, why_it_matters, event_type, severity, article_ids
    """
    client = _get_client()
    if not client or not articles:
        return _fallback_cluster(articles)

    article_texts = []
    for a in articles:
        article_texts.append(
            f"ID: {a['id']}\n"
            f"Title: {a['title']}\n"
            f"Source: {a.get('source_name', 'Unknown')}\n"
            f"Description: {(a.get('description') or '')[:300]}\n"
            f"Event type: {a.get('event_type', 'general')}\n"
            f"Severity: {a.get('severity', 'medium')}"
        )

    prompt = (
        "You are a news editor creating a morning briefing. Given the articles below, "
        "group related articles covering the same event or topic into stories. "
        "For each story, write a concise narrative summary.\n\n"
        "Rules:\n"
        "- Articles about the same event/topic from different sources = ONE story\n"
        "- Each article belongs to exactly one story\n"
        "- Write a short headline (max 10 words) for each story\n"
        "- Write a 2-3 sentence narrative that explains what happened (not just repeating headlines)\n"
        "- Write 1 sentence on why it matters to the reader\n"
        "- Use the most significant event_type and severity from the cluster\n"
        "- Sort stories by importance (most critical first)\n"
        "- Single-article topics are fine as their own story\n\n"
        "Articles:\n"
        + "\n---\n".join(article_texts)
        + '\n\nReturn JSON: {"stories": [{"headline": "...", "narrative": "...", '
        '"why_it_matters": "...", "event_type": "...", "severity": "...", '
        '"article_ids": [1, 2, ...]}]}'
    )

    try:
        response = client.models.generate_content(
            model=settings.gemini_primary_model,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        result = json.loads(response.text)
        return result.get("stories", [])
    except Exception as e:
        logger.error(f"Gemini cluster_and_narrate failed with primary: {e}")
        try:
            response = client.models.generate_content(
                model=settings.gemini_fallback_model,
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            result = json.loads(response.text)
            return result.get("stories", [])
        except Exception as e2:
            logger.error(f"Gemini cluster_and_narrate failed with fallback: {e2}")
            return _fallback_cluster(articles)


def _fallback_cluster(articles: list[dict]) -> list[dict]:
    """Simple fallback: each article becomes its own story."""
    stories = []
    for a in articles:
        stories.append({
            "headline": a.get("title", "Untitled"),
            "narrative": a.get("description") or a.get("title", ""),
            "why_it_matters": None,
            "event_type": a.get("event_type", "general"),
            "severity": a.get("severity", "medium"),
            "article_ids": [a["id"]],
        })
    return stories
