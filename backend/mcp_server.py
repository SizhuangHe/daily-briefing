#!/usr/bin/env python3
"""
Daily Briefing MCP Server.

Exposes news, rating, source, stock, and dev tools to Claude Code.
Runs via stdio transport (spawned by Claude Code on demand).
"""

import json
import logging
import sys
from pathlib import Path

# Ensure app modules are importable
sys.path.insert(0, str(Path(__file__).parent))

from mcp.server.fastmcp import FastMCP

from app.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,  # MCP uses stdout for protocol, logs go to stderr
)
logger = logging.getLogger(__name__)

# Initialize database on startup
init_db()

mcp = FastMCP("daily-briefing")


# ── News Tools ──────────────────────────────────────────────────────────

@mcp.tool()
def get_news_articles(
    topic: str | None = None,
    source: str | None = None,
    region: str | None = None,
    sort: str = "score",
    limit: int = 30,
    min_importance: float | None = None,
) -> str:
    """Get news articles with optional filtering and sorting.

    Args:
        topic: Filter by topic (ai, tech, finance, science, world, health, business, energy, sports, entertainment)
        source: Filter by source name (e.g. "Reuters", "CNBC")
        region: Filter by region (us, china, europe, middle_east, japan, korea, etc.)
        sort: "score" (recommendation score, default) or "time" (newest first)
        limit: Max articles to return (default 30)
        min_importance: Minimum importance_score threshold (0.0-1.0)
    """
    from app.tools.news_tools import get_news_articles as _get
    result = _get(topic=topic, source=source, region=region,
                  sort=sort, limit=limit, min_importance=min_importance)
    return json.dumps(result, default=str)


@mcp.tool()
def refresh_news() -> str:
    """Trigger immediate RSS fetch + Gemini classification + importance scoring + recommendation recalc.

    Use this to pull the latest news before reading articles.
    """
    from app.tools.news_tools import refresh_news as _refresh
    return json.dumps(_refresh())


@mcp.tool()
def search_articles(query: str, limit: int = 10) -> str:
    """Search articles by title/description text match.

    Args:
        query: Search text to find in article titles and descriptions
        limit: Max results (default 10)
    """
    from app.tools.news_tools import search_articles as _search
    return json.dumps(_search(query=query, limit=limit), default=str)


# ── Rating Tools ────────────────────────────────────────────────────────

@mcp.tool()
def rate_article(article_id: int, score: int) -> str:
    """Rate an article: 1=thumbs up, -1=thumbs down, 0=remove rating.

    Triggers recommendation score recalculation after rating.

    Args:
        article_id: The article ID to rate
        score: Rating score (-1, 0, or 1)
    """
    from app.tools.rating_tools import rate_article as _rate
    return json.dumps(_rate(article_id=article_id, score=score))


@mcp.tool()
def get_ratings() -> str:
    """Get all article ratings as {article_id: score} mapping."""
    from app.tools.rating_tools import get_ratings as _get
    return json.dumps(_get())


@mcp.tool()
def get_user_profile() -> str:
    """Get user profile: topic weights, source preferences, region preferences, centroid count."""
    from app.tools.rating_tools import get_user_profile as _get
    return json.dumps(_get())


# ── Source Tools ────────────────────────────────────────────────────────

@mcp.tool()
def list_sources() -> str:
    """List all configured RSS news sources with their enabled/disabled status."""
    from app.tools.source_tools import list_sources as _list
    return json.dumps(_list())


@mcp.tool()
def add_source(name: str, url: str, source_type: str = "rss") -> str:
    """Add a new RSS news source.

    Args:
        name: Display name for the source (e.g. "TechCrunch")
        url: RSS feed URL
        source_type: Source type (default "rss")
    """
    from app.tools.source_tools import add_source as _add
    return json.dumps(_add(name=name, url=url, source_type=source_type))


@mcp.tool()
def toggle_source(source_id: int) -> str:
    """Toggle a news source enabled/disabled.

    Args:
        source_id: The source ID to toggle
    """
    from app.tools.source_tools import toggle_source as _toggle
    return json.dumps(_toggle(source_id=source_id))


@mcp.tool()
def remove_source(source_id: int) -> str:
    """Remove a news source permanently.

    Args:
        source_id: The source ID to remove
    """
    from app.tools.source_tools import remove_source as _remove
    return json.dumps(_remove(source_id=source_id))


# ── Stock Tools ─────────────────────────────────────────────────────────

@mcp.tool()
def get_stock_indices() -> str:
    """Get major stock indices: S&P 500, NASDAQ, SSE Composite, KOSPI."""
    from app.tools.stock_tools import get_stock_indices as _get
    return json.dumps(_get())


@mcp.tool()
def get_watchlist() -> str:
    """Get user's stock watchlist with current prices."""
    from app.tools.stock_tools import get_watchlist as _get
    return json.dumps(_get())


# ── Dev Tools ───────────────────────────────────────────────────────────

@mcp.tool()
def get_system_stats() -> str:
    """Get system statistics: article counts, embeddings, ratings, recent history."""
    from app.tools.dev_tools import get_system_stats as _get
    return json.dumps(_get(), default=str)


@mcp.tool()
def get_score_breakdown(limit: int = 20) -> str:
    """Get per-article score breakdown showing raw channel scores (topic, content, source, recency).

    Args:
        limit: Number of top articles to show (default 20, max 100)
    """
    from app.tools.dev_tools import get_score_breakdown as _get
    return json.dumps(_get(limit=limit), default=str)


@mcp.tool()
def get_metrics(k: int = 20) -> str:
    """Get offline evaluation metrics: NDCG@k, like-rate, coverage, novelty.

    Args:
        k: Number of top articles to evaluate (default 20)
    """
    from app.tools.dev_tools import get_metrics as _get
    return json.dumps(_get(k=k))


if __name__ == "__main__":
    mcp.run(transport="stdio")
