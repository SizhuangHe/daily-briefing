"""
Inspiration content service.

Provides daily quotes, fun facts, and activity suggestions.
Uses local seed data with date-based selection to avoid repeats.
"""

import json
import logging
from datetime import date
from pathlib import Path

from app.schemas.inspiration import InspirationResponse, Quote

logger = logging.getLogger(__name__)

SEED_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "seed_data"

_quotes: list[dict] = []
_facts: list[str] = []

ACTIVITIES = [
    "Take a 10-minute walk outside and notice three things you haven't seen before.",
    "Write down three things you're grateful for today.",
    "Try a 5-minute breathing exercise: breathe in for 4 counts, hold for 4, out for 4.",
    "Send a message to someone you haven't talked to in a while.",
    "Learn one new keyboard shortcut for a tool you use daily.",
    "Organize your desk or workspace for 5 minutes.",
    "Read one article outside your usual interests.",
    "Stretch for 5 minutes—focus on your neck, shoulders, and back.",
    "Cook something new for lunch or dinner today.",
    "Spend 10 minutes learning a word or phrase in a new language.",
    "Take a photo of something beautiful you see today.",
    "Write a quick journal entry about how you're feeling right now.",
    "Try the Pomodoro technique: 25 minutes focused work, then a 5-minute break.",
    "Listen to a podcast episode on a topic you know nothing about.",
    "Do a random act of kindness for someone today.",
]


def _load_seed_data() -> None:
    """Load quotes and fun facts from seed data files."""
    global _quotes, _facts

    if not _quotes:
        quotes_file = SEED_DATA_PATH / "quotes.json"
        if quotes_file.exists():
            _quotes = json.loads(quotes_file.read_text())
            logger.info(f"Loaded {len(_quotes)} quotes")

    if not _facts:
        facts_file = SEED_DATA_PATH / "fun_facts.json"
        if facts_file.exists():
            _facts = json.loads(facts_file.read_text())
            logger.info(f"Loaded {len(_facts)} fun facts")


def _day_index() -> int:
    """Get a deterministic index based on today's date."""
    today = date.today()
    return today.toordinal()


def get_today_inspiration() -> InspirationResponse:
    """Get today's inspiration bundle. Uses date-based indexing to avoid repeats."""
    _load_seed_data()
    idx = _day_index()

    quote = None
    if _quotes:
        q = _quotes[idx % len(_quotes)]
        quote = Quote(text=q["text"], author=q.get("author"))

    fact = None
    if _facts:
        # Offset from quotes to get different content
        fact = _facts[(idx + 7) % len(_facts)]

    activity = ACTIVITIES[(idx + 13) % len(ACTIVITIES)]

    return InspirationResponse(
        quote=quote,
        fun_fact=fact,
        activity=activity,
    )


def get_refreshed_inspiration() -> InspirationResponse:
    """Get a different set of inspiration (offset from today's default)."""
    _load_seed_data()
    idx = _day_index()

    # Use different offsets to get different content
    quote = None
    if _quotes:
        q = _quotes[(idx + 3) % len(_quotes)]
        quote = Quote(text=q["text"], author=q.get("author"))

    fact = None
    if _facts:
        fact = _facts[(idx + 11) % len(_facts)]

    activity = ACTIVITIES[(idx + 5) % len(ACTIVITIES)]

    return InspirationResponse(
        quote=quote,
        fun_fact=fact,
        activity=activity,
    )
