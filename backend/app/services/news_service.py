"""
News aggregation service.

Handles RSS fetching, article deduplication (triple strategy),
etag caching, topic extraction, and article storage.
"""

import hashlib
import json
import logging
import re
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

import feedparser
from sqlalchemy.orm import Session

from app.models.article import Article
from app.models.preference import NewsSource
from app.services import gemini_service
from app.utils.text_processing import clean_html
from app.utils.url_normalize import normalize_url

logger = logging.getLogger(__name__)

# Simple keyword-based topic taxonomy
TOPIC_KEYWORDS = {
    "ai": [
        "artificial intelligence", "machine learning", "deep learning", "llm",
        "gpt", "neural network", "ai model", "generative ai", "chatbot",
        "transformer", "diffusion", "openai", "anthropic", "gemini ai",
        "claude", "copilot", "midjourney", "stable diffusion", "ai safety",
        "large language model", "foundation model",
    ],
    "tech": [
        "software", "startup", "silicon valley", "programming", "developer",
        "cloud", "saas", "api", "open source", "github", "app",
        "apple", "google", "microsoft", "amazon", "meta", "nvidia",
        "semiconductor", "chip", "smartphone", "iphone", "android",
        "cybersecurity", "hack", "data breach", "privacy",
        "social media", "tiktok", "instagram", "twitter",
    ],
    "finance": [
        "stock", "market", "investment", "banking", "crypto", "bitcoin",
        "ethereum", "fed", "inflation", "earnings", "ipo", "trading",
        "wall street", "hedge fund", "venture capital", "interest rate",
        "recession", "gdp", "treasury", "bond", "dow", "nasdaq", "s&p",
        "dividend", "forex", "commodity",
    ],
    "science": [
        "research", "study", "discovery", "physics", "biology", "chemistry",
        "space", "nasa", "climate", "quantum", "genome", "vaccine",
        "astronomy", "mars", "satellite", "telescope", "evolution",
        "neuroscience", "particle", "laboratory", "experiment",
    ],
    "world": [
        "politics", "election", "government", "war", "diplomacy", "united nations",
        "policy", "regulation", "congress", "senate", "president",
        "geopolitics", "sanctions", "trade war", "nato", "eu ", "china",
        "russia", "ukraine", "middle east", "immigration", "refugee",
        "summit", "treaty", "alliance",
    ],
    "health": [
        "health", "medical", "hospital", "doctor", "patient", "disease",
        "drug", "pharmaceutical", "fda", "clinical trial", "surgery",
        "mental health", "cancer", "diabetes", "pandemic", "covid",
        "wellness", "nutrition", "fitness", "obesity",
    ],
    "business": [
        "ceo", "merger", "acquisition", "revenue", "profit", "corporate",
        "layoff", "hiring", "retail", "supply chain", "e-commerce",
        "franchise", "bankruptcy", "valuation", "quarterly",
    ],
    "energy": [
        "oil", "gas", "solar", "wind", "renewable", "energy",
        "nuclear", "battery", "ev ", "electric vehicle", "tesla",
        "opec", "pipeline", "grid", "power plant", "carbon",
    ],
    "sports": [
        "nba", "nfl", "mlb", "soccer", "football", "basketball",
        "tennis", "golf", "olympic", "championship", "playoff",
        "tournament", "athlete", "coach", "stadium", "league",
    ],
    "entertainment": [
        "movie", "film", "tv show", "netflix", "disney", "streaming",
        "album", "concert", "celebrity", "grammy", "oscar", "emmy",
        "box office", "hollywood", "music", "series", "game",
    ],
}

SEED_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "seed_data"

# Cross-source dedup: similarity threshold for titles
TITLE_SIMILARITY_THRESHOLD = 0.65


def _normalize_title(title: str) -> str:
    """Normalize a title for similarity comparison.

    Strips punctuation, extra spaces, lowercases, and removes common
    prefixes/suffixes that vary across sources.
    """
    t = title.lower().strip()
    # Remove common editorial prefixes
    t = re.sub(r"^(breaking|exclusive|update|opinion|analysis|watch|live):\s*", "", t)
    # Remove source attribution suffixes like "- CNN", "| Reuters"
    t = re.sub(r"\s*[-|]\s*\w+[\w\s]*$", "", t)
    # Strip punctuation and collapse whitespace
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _is_similar_title(title: str, existing_titles: list[str]) -> bool:
    """Check if a title is similar to any existing title."""
    norm = _normalize_title(title)
    if not norm:
        return False
    for existing in existing_titles:
        ratio = SequenceMatcher(None, norm, existing).ratio()
        if ratio >= TITLE_SIMILARITY_THRESHOLD:
            return True
    return False


def seed_default_sources(db: Session) -> None:
    """Load default RSS sources if the table is empty."""
    count = db.query(NewsSource).count()
    if count > 0:
        return

    sources_file = SEED_DATA_PATH / "default_sources.json"
    if not sources_file.exists():
        logger.warning("Default sources file not found")
        return

    sources = json.loads(sources_file.read_text())
    for src in sources:
        db.add(NewsSource(
            name=src["name"],
            url=src["url"],
            source_type=src.get("source_type", "rss"),
        ))
    db.commit()
    logger.info(f"Seeded {len(sources)} default news sources")


def _generate_external_id(url: str, guid: str | None, title: str) -> str:
    """Generate a dedup key from canonical URL, guid, and title hash."""
    canonical = normalize_url(url)
    raw = f"{canonical}|{guid or ''}|{title.strip().lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _extract_topics(title: str, description: str) -> list[str]:
    """Extract topics from article text using keyword matching."""
    text = f"{title} {description}".lower()
    matched = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            matched.append(topic)
    return matched


def fetch_rss_feed(source: NewsSource) -> list[dict]:
    """Fetch and parse a single RSS feed, respecting etag/last_modified."""
    headers = {}
    if source.etag:
        headers["If-None-Match"] = source.etag
    if source.last_modified:
        headers["If-Modified-Since"] = source.last_modified

    try:
        feed = feedparser.parse(source.url, request_headers=headers)
    except Exception as e:
        logger.error(f"Failed to fetch {source.name}: {e}")
        return []

    # Check for 304 Not Modified
    if hasattr(feed, "status") and feed.status == 304:
        logger.debug(f"{source.name}: not modified (304)")
        return []

    articles = []
    for entry in feed.entries:
        title = entry.get("title", "").strip()
        if not title:
            continue

        link = entry.get("link", "")
        raw_desc = entry.get("summary", entry.get("description", ""))
        description = clean_html(raw_desc)
        guid = entry.get("id", entry.get("guid"))
        published = entry.get("published_parsed") or entry.get("updated_parsed")
        image = None

        # Try to get image from media content
        if hasattr(entry, "media_content") and entry.media_content:
            image = entry.media_content[0].get("url")
        elif hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
            image = entry.media_thumbnail[0].get("url")

        pub_dt = None
        if published:
            try:
                pub_dt = datetime(*published[:6])
            except (TypeError, ValueError):
                pass

        articles.append({
            "external_id": _generate_external_id(link, guid, title),
            "canonical_url": normalize_url(link) if link else None,
            "title": title,
            "description": description[:2000] if description else None,
            "url": link,
            "source_name": source.name,
            "source_url": source.url,
            "image_url": image,
            "topics": _extract_topics(title, description or ""),
            "published_at": pub_dt,
        })

    return articles


def fetch_all_sources(db: Session) -> int:
    """Fetch articles from all enabled sources and store them."""
    sources = db.query(NewsSource).filter_by(enabled=True).all()
    if not sources:
        seed_default_sources(db)
        sources = db.query(NewsSource).filter_by(enabled=True).all()

    # Track seen IDs across the entire batch to prevent in-batch duplicates
    seen_ids: set[str] = set()
    total_new = 0

    # Build a list of normalized titles from recent DB articles for cross-source dedup
    recent_articles = (
        db.query(Article.title)
        .order_by(Article.published_at.desc())
        .limit(500)
        .all()
    )
    seen_titles: list[str] = [_normalize_title(a.title) for a in recent_articles]

    for source in sources:
        articles = fetch_rss_feed(source)
        for article_data in articles:
            ext_id = article_data["external_id"]

            # Skip if already seen in this batch
            if ext_id in seen_ids:
                continue
            seen_ids.add(ext_id)

            # Skip if already in DB (exact match)
            existing = db.query(Article).filter_by(external_id=ext_id).first()
            if existing:
                continue

            # Skip if a similar title already exists (cross-source dedup)
            title = article_data["title"]
            if _is_similar_title(title, seen_titles):
                logger.debug(f"Skipping cross-source duplicate: {title}")
                continue

            # Track this title for subsequent articles
            seen_titles.append(_normalize_title(title))

            topics = article_data.pop("topics")
            db_article = Article(
                **article_data,
                topics=json.dumps(topics),
            )
            db.add(db_article)
            total_new += 1

        # Commit per source, with rollback on error
        try:
            db.commit()
        except Exception as e:
            logger.error(f"Failed to commit articles from {source.name}: {e}")
            db.rollback()

    logger.info(f"Fetched {total_new} new articles from {len(sources)} sources")

    # Gemini fallback: reclassify articles with no topics
    if total_new > 0:
        _reclassify_untagged_articles(db)
        _classify_untagged_regions(db)

    return total_new


def _reclassify_untagged_articles(db: Session) -> int:
    """Use Gemini to classify articles that have no topics or only 'general'."""
    untagged = (
        db.query(Article)
        .filter(
            (Article.topics.is_(None))
            | (Article.topics == "[]")
            | (Article.topics == '["general"]')
        )
        .limit(50)
        .all()
    )
    if not untagged:
        return 0

    return _gemini_classify_batch(db, untagged)


def reclassify_all_articles(db: Session) -> int:
    """Use Gemini to reclassify ALL articles. Processes in batches of 30."""
    articles = db.query(Article).order_by(Article.published_at.desc()).all()
    if not articles:
        return 0

    total_updated = 0
    for i in range(0, len(articles), 30):
        batch = articles[i : i + 30]
        total_updated += _gemini_classify_batch(db, batch)

    logger.info(f"Reclassified {total_updated}/{len(articles)} articles via Gemini")
    return total_updated


def _gemini_classify_batch(db: Session, articles: list[Article]) -> int:
    """Classify a batch of articles using Gemini and update DB."""
    batch = [
        {"id": a.id, "title": a.title, "description": a.description}
        for a in articles
    ]

    try:
        classified = gemini_service.classify_topics(batch)
    except Exception as e:
        logger.error(f"Gemini topic classification failed: {e}")
        return 0

    updated = 0
    for a in articles:
        if a.id in classified:
            a.topics = json.dumps(classified[a.id])
            updated += 1

    if updated:
        db.commit()

    return updated


def _classify_untagged_regions(db: Session) -> int:
    """Use Gemini to classify regions for articles without region tags."""
    untagged = (
        db.query(Article)
        .filter(Article.regions.is_(None))
        .order_by(Article.published_at.desc())
        .limit(50)
        .all()
    )
    if not untagged:
        return 0
    return _gemini_regions_batch(db, untagged)


def classify_all_regions(db: Session) -> int:
    """Use Gemini to classify regions for ALL articles. Batches of 30."""
    articles = db.query(Article).order_by(Article.published_at.desc()).all()
    if not articles:
        return 0

    total_updated = 0
    for i in range(0, len(articles), 30):
        batch = articles[i : i + 30]
        total_updated += _gemini_regions_batch(db, batch)

    logger.info(f"Region-tagged {total_updated}/{len(articles)} articles via Gemini")
    return total_updated


def _gemini_regions_batch(db: Session, articles: list[Article]) -> int:
    """Classify a batch of articles by region using Gemini and update DB."""
    batch = [
        {"id": a.id, "title": a.title, "description": a.description}
        for a in articles
    ]

    try:
        classified = gemini_service.classify_regions(batch)
    except Exception as e:
        logger.error(f"Gemini region classification failed: {e}")
        return 0

    updated = 0
    for a in articles:
        if a.id in classified:
            a.regions = json.dumps(classified[a.id])
            updated += 1

    if updated:
        db.commit()

    return updated


def get_articles(
    db: Session,
    topic: str | None = None,
    source: str | None = None,
    region: str | None = None,
    sort: str = "score",
    limit: int = 20,
    offset: int = 0,
) -> list[Article]:
    """Get articles with optional filtering and sorting.

    sort: "score" (recommendation_score desc) or "time" (published_at desc).
    """
    query = db.query(Article)

    if sort == "time":
        query = query.order_by(Article.published_at.desc())
    else:
        query = query.order_by(
            Article.recommendation_score.desc(),
            Article.published_at.desc(),
        )

    if topic:
        query = query.filter(Article.topics.contains(f'"{topic}"'))

    if region:
        query = query.filter(Article.regions.contains(f'"{region}"'))

    if source:
        query = query.filter(Article.source_name == source)

    return query.offset(offset).limit(limit).all()


def get_sources(db: Session) -> list[str]:
    """Get all distinct source names."""
    rows = db.query(Article.source_name).distinct().all()
    return sorted([r[0] for r in rows if r[0]])
