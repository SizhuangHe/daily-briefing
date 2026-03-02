from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
)

from app.database import Base


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(Text, unique=True, nullable=False)
    canonical_url = Column(Text)
    title = Column(Text, nullable=False)
    description = Column(Text)
    content = Column(Text)
    url = Column(Text, nullable=False)
    source_name = Column(Text)
    source_url = Column(Text)
    image_url = Column(Text)
    topics = Column(Text)  # JSON array: ["ai", "tech"]
    regions = Column(Text)  # JSON array: ["us", "china", "europe"]
    gemini_summary = Column(Text)

    # Interest channel (Phase 5 TF-IDF)
    interest_score = Column(Float, default=0.0)
    # Legacy alias kept for backward compat during transition
    recommendation_score = Column(Float, default=0.0)

    # Must-Know channel (importance scoring)
    importance_score = Column(Float, default=0.0)
    must_know_level = Column(Text, default="normal")  # urgent | affects_you | normal

    # Structured extraction fields (Gemini-filled)
    event_type = Column(Text)      # disaster, policy, war, market, tech, health, crime, etc.
    geo_scope = Column(Text)       # global, us, regional, local
    time_sensitivity = Column(Text) # immediate, today, this_week, none
    severity = Column(Text)        # critical, high, medium, low
    personal_impact_flags = Column(Text)  # JSON: ["travel","health","safety","finance"]
    confirmed_sources = Column(Integer, default=1)

    # Cached embedding from Gemini text-embedding-004
    embedding = Column(Text)  # JSON-encoded list[float]

    published_at = Column(DateTime)
    fetched_at = Column(DateTime, default=datetime.utcnow)


class ArticleRating(Base):
    __tablename__ = "article_ratings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(
        Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    score = Column(Integer, nullable=False)  # -1 = thumbs down, 1 = thumbs up
    rating_source = Column(Text, default="article")  # "article" or "story"
    rated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("article_id", name="uq_article_rating"),)
