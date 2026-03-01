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
    gemini_summary = Column(Text)
    recommendation_score = Column(Float, default=0.0)
    published_at = Column(DateTime)
    fetched_at = Column(DateTime, default=datetime.utcnow)


class ArticleRating(Base):
    __tablename__ = "article_ratings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(
        Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    score = Column(Integer, nullable=False)  # -1 = thumbs down, 1 = thumbs up
    rated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("article_id", name="uq_article_rating"),)
