"""
Generate the daily briefing: fetch news, summarize, cluster into stories,
save snapshot to DB, and export a standalone HTML file.

Usage:
    conda run -n daily-briefing python generate_briefing.py
    # or: make generate
"""

import json
import logging
import sys
from datetime import date, datetime
from pathlib import Path

# Ensure app modules are importable
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.database import SessionLocal, init_db
from app.models.article import Article
from app.models.briefing import DailyBriefing
from app.services import briefing_service, gemini_service, news_service, recommendation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent.parent / "output"


def fetch_and_summarize(db) -> dict:
    """Fetch news, generate Gemini summaries for new articles."""
    logger.info("Fetching news from all RSS sources...")
    new_count = news_service.fetch_all_sources(db)
    logger.info(f"Fetched {new_count} new articles")

    # Summarize unsummarized articles
    unsummarized = (
        db.query(Article)
        .filter(Article.gemini_summary.is_(None))
        .order_by(Article.published_at.desc())
        .limit(20)
        .all()
    )

    summaries_count = 0
    if unsummarized:
        logger.info(f"Summarizing {len(unsummarized)} articles via Gemini...")
        article_dicts = [
            {"id": a.id, "title": a.title, "description": a.description}
            for a in unsummarized
        ]
        summaries = gemini_service.summarize_articles(article_dicts)
        for article in unsummarized:
            if article.id in summaries:
                article.gemini_summary = summaries[article.id]
        db.commit()
        summaries_count = len(summaries)
        logger.info(f"Generated {summaries_count} summaries")

    recommendation.recalculate_scores(db)

    return {"new_articles": new_count, "summaries": summaries_count}


def save_snapshot(db, sections: dict):
    """Save briefing snapshot to daily_briefings table."""
    today = date.today()

    sections_data = {}
    for key, section in sections.items():
        sections_data[key] = section.model_dump(mode="json")

    existing = db.query(DailyBriefing).filter_by(date=today).first()
    if existing:
        existing.sections_json = json.dumps(sections_data)
        existing.generated_at = datetime.utcnow()
        existing.model_versions = settings.gemini_primary_model
    else:
        db.add(DailyBriefing(
            date=today,
            sections_json=json.dumps(sections_data),
            model_versions=settings.gemini_primary_model,
        ))
    db.commit()
    logger.info("Saved briefing snapshot to database")


def export_html(sections: dict, overview: str):
    """Export briefing as a standalone HTML file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today()
    filepath = OUTPUT_DIR / f"briefing-{today.isoformat()}.html"

    html = render_briefing_html(sections, overview, today)
    filepath.write_text(html, encoding="utf-8")
    logger.info(f"Exported HTML to {filepath}")
    return filepath


def render_briefing_html(sections: dict, overview: str, today: date) -> str:
    """Render the briefing as a self-contained HTML page."""
    section_html_parts = []

    for key in ["urgent", "affects_you", "interests"]:
        section = sections[key]
        if not section.stories:
            continue

        config = {
            "urgent": {"title": "Urgent", "icon": "&#9679;", "color": "#475569"},
            "affects_you": {"title": "Affects You", "icon": "&#128214;", "color": "#64748b"},
            "interests": {"title": "Your Interests", "icon": "&#10024;", "color": "#3b82f6"},
        }[key]

        stories_html = ""
        for story in section.stories:
            # Event type badge
            badge = ""
            if story.event_type:
                badge_colors = {
                    "disaster": "#e2e8f0; color: #334155",
                    "public_safety": "#e2e8f0; color: #334155",
                    "health": "#fff1f2; color: #e11d48",
                    "weather": "#f0f9ff; color: #0284c7",
                    "infrastructure": "#fffbeb; color: #d97706",
                    "war_conflict": "#e2e8f0; color: #334155",
                    "policy": "#f5f3ff; color: #7c3aed",
                    "financial_shock": "#ecfdf5; color: #059669",
                    "market": "#f0fdf4; color: #16a34a",
                    "tech": "#eff6ff; color: #2563eb",
                    "science": "#f0fdfa; color: #0d9488",
                    "crime": "#e2e8f0; color: #334155",
                }
                bg = badge_colors.get(story.event_type, "#f1f5f9; color: #475569")
                label = story.event_type.replace("_", " ").title()
                badge = f'<span class="badge" style="background: {bg}">{label}</span>'

            # Source links
            sources_html = ""
            if story.sources:
                links = []
                for src in story.sources:
                    name = src.source_name or "Link"
                    links.append(f'<a href="{src.url}" target="_blank">{name}</a>')
                sources_html = f'<div class="sources">Sources: {" &middot; ".join(links)}</div>'

            # Why it matters
            why_html = ""
            if story.why_it_matters and key in ("urgent", "affects_you"):
                why_html = f'<p class="why">{story.why_it_matters}</p>'

            # Severity border
            severity_colors = {
                "critical": "#64748b",
                "high": "#94a3b8",
                "medium": "#cbd5e1",
                "low": "#e2e8f0",
            }
            border_color = severity_colors.get(story.severity or "medium", "#cbd5e1")

            stories_html += f"""
            <div class="story" style="border-left-color: {border_color}">
                <div class="story-header">
                    <h4>{story.headline}</h4>
                    {badge}
                </div>
                <p class="narrative">{story.narrative}</p>
                {why_html}
                {sources_html}
            </div>"""

        section_html_parts.append(f"""
        <div class="section">
            <div class="section-header">
                <span style="color: {config['color']}">{config['icon']}</span>
                <h3>{config['title']}</h3>
                <span class="count">({len(section.stories)})</span>
            </div>
            <p class="section-desc">{section.description}</p>
            {stories_html}
        </div>""")

    overview_html = ""
    if overview:
        overview_html = f"""
        <div class="overview">
            <p>{overview}</p>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Daily Briefing - {today.strftime('%B %d, %Y')}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #f8fafc;
    color: #1e293b;
    line-height: 1.6;
    padding: 2rem 1rem;
}}
.container {{ max-width: 720px; margin: 0 auto; }}
h1 {{ font-size: 1.5rem; font-weight: 700; color: #0f172a; }}
.date {{ font-size: 0.875rem; color: #64748b; margin-bottom: 1.5rem; }}
.overview {{
    background: #fff; border: 1px solid #e2e8f0; border-radius: 0.5rem;
    padding: 1.25rem; margin-bottom: 1rem; box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}}
.overview p {{ font-size: 0.875rem; color: #334155; }}
.section {{
    background: #fff; border: 1px solid #e2e8f0; border-radius: 0.5rem;
    padding: 1.25rem; margin-bottom: 1rem; box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}}
.section-header {{ display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem; }}
.section-header h3 {{ font-size: 0.875rem; font-weight: 600; color: #0f172a; }}
.count {{ font-size: 0.75rem; color: #94a3b8; }}
.section-desc {{ font-size: 0.75rem; color: #64748b; margin-bottom: 0.75rem; }}
.story {{
    border: 1px solid #f1f5f9; border-left: 3px solid #cbd5e1;
    border-radius: 0.375rem; padding: 0.75rem 1rem; margin-bottom: 0.5rem;
    background: #fff;
}}
.story-header {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 0.75rem; }}
.story-header h4 {{ font-size: 0.875rem; font-weight: 600; color: #1e293b; }}
.badge {{
    flex-shrink: 0; font-size: 0.7rem; font-weight: 500;
    padding: 0.125rem 0.5rem; border-radius: 0.25rem; white-space: nowrap;
}}
.narrative {{ font-size: 0.875rem; color: #475569; margin-top: 0.5rem; }}
.why {{ font-size: 0.75rem; color: #94a3b8; font-style: italic; margin-top: 0.375rem; }}
.sources {{
    font-size: 0.75rem; color: #94a3b8; margin-top: 0.5rem;
    display: flex; flex-wrap: wrap; gap: 0.25rem; align-items: center;
}}
.sources a {{ color: #64748b; text-decoration: none; }}
.sources a:hover {{ color: #2563eb; text-decoration: underline; }}
.footer {{ text-align: center; font-size: 0.75rem; color: #94a3b8; margin-top: 2rem; }}
</style>
</head>
<body>
<div class="container">
    <h1>Daily Briefing</h1>
    <p class="date">{today.strftime('%A, %B %d, %Y')}</p>
    {overview_html}
    {''.join(section_html_parts)}
    <p class="footer">Generated at {datetime.now().strftime('%H:%M')}</p>
</div>
</body>
</html>"""


def main():
    logger.info("=== Daily Briefing Generator ===")

    # Initialize database
    init_db()
    db = SessionLocal()

    try:
        # Step 1: Fetch and summarize news
        stats = fetch_and_summarize(db)

        # Step 2: Build briefing (importance + story clustering)
        logger.info("Building briefing (analyzing + clustering)...")
        sections = briefing_service.build_briefing(db)

        # Step 3: Generate overview
        overview_parts = []
        for key in ["urgent", "affects_you"]:
            for story in sections[key].stories:
                overview_parts.append(story.headline)
        overview = ""
        if overview_parts:
            overview = "Today's key stories: " + "; ".join(overview_parts) + "."

        # Step 4: Save snapshot
        save_snapshot(db, sections)

        # Step 5: Export HTML
        filepath = export_html(sections, overview)

        # Summary
        total_stories = sum(len(sections[k].stories) for k in ["urgent", "affects_you", "interests"])
        logger.info(
            f"Done! {stats['new_articles']} new articles, "
            f"{stats['summaries']} summaries, "
            f"{total_stories} stories in briefing"
        )
        logger.info(f"Open: file://{filepath.resolve()}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
