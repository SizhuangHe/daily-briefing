from datetime import date, datetime

from pydantic import BaseModel


class BriefArticle(BaseModel):
    """Article in a briefing section with importance context."""
    id: int
    title: str
    description: str | None = None
    url: str
    source_name: str | None = None
    image_url: str | None = None
    topics: list[str] = []
    gemini_summary: str | None = None
    event_type: str | None = None
    severity: str | None = None
    time_sensitivity: str | None = None
    geo_scope: str | None = None
    personal_impact_flags: list[str] = []
    why_it_matters: str | None = None
    must_know_level: str = "normal"
    importance_score: float = 0.0
    interest_score: float = 0.0
    confirmed_sources: int = 1
    published_at: datetime | None = None

    model_config = {"from_attributes": True}


class StorySource(BaseModel):
    """A source article within a story cluster."""
    id: int
    title: str
    url: str
    source_name: str | None = None
    published_at: datetime | None = None


class BriefingStory(BaseModel):
    """A story/topic cluster in the briefing."""
    headline: str
    narrative: str
    why_it_matters: str | None = None
    event_type: str | None = None
    severity: str | None = None
    must_know_level: str = "normal"
    importance_score: float = 0.0
    interest_score: float = 0.0
    sources: list[StorySource] = []
    section_type: str = "for_you"  # "for_you" or "explore"


class BriefingSection(BaseModel):
    """A section in the daily briefing."""
    title: str
    description: str = ""
    stories: list[BriefingStory] = []


class OverviewDomain(BaseModel):
    """A single domain/theme in the at-a-glance overview."""
    domain: str       # e.g. "International", "Economy", "Technology"
    summary: str      # 1-2 sentence summary


class BriefingResponse(BaseModel):
    date: date
    urgent: BriefingSection = BriefingSection(
        title="Urgent",
        description="Critical events you need to know about right now",
    )
    affects_you: BriefingSection = BriefingSection(
        title="Affects You",
        description="News that may impact your daily life",
    )
    interests: BriefingSection = BriefingSection(
        title="Your Interests",
        description="Personalized picks based on your preferences",
    )
    overview: str = ""
    overview_domains: list[OverviewDomain] = []
