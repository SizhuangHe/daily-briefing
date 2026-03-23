#!/usr/bin/env python3
"""
Cron data collection script.

Fetches RSS feeds, classifies topics/regions via Gemini,
runs importance analysis, generates embeddings,
and recalculates recommendation scores.

Usage:
    conda run -n daily-briefing python collect.py

Intended to run every 30 minutes via cron or launchd.
"""

import logging
import sys
from pathlib import Path

# Ensure app modules are importable
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal, init_db
from app.services import news_service, recommendation
from app.services.importance import analyze_and_score_articles

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def collect():
    """Run the full data collection pipeline."""
    init_db()
    db = SessionLocal()

    try:
        # 1. Fetch RSS + dedup + keyword topic extraction
        #    (also runs Gemini classify for untagged articles and region tagging)
        logger.info("Fetching news from all RSS sources...")
        new_count = news_service.fetch_all_sources(db)
        logger.info(f"Fetched {new_count} new articles")

        if new_count == 0:
            logger.info("No new articles, skipping analysis")
            return

        # 2. Importance analysis (Gemini structured extraction + scoring)
        logger.info("Running importance analysis...")
        scored = analyze_and_score_articles(db, limit=50)
        logger.info(f"Analyzed {scored} articles for importance")

        # 3. Recalculate recommendation scores (embedding + topic + source + recency)
        #    This also generates embeddings for articles missing them.
        logger.info("Recalculating recommendation scores...")
        updated = recommendation.recalculate_scores(db)
        logger.info(f"Updated scores for {updated} articles")

        logger.info(
            f"Done: {new_count} new articles, "
            f"{scored} importance-scored, "
            f"{updated} recommendation-scored"
        )

    finally:
        db.close()


if __name__ == "__main__":
    collect()
