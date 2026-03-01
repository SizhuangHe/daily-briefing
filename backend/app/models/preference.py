from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, Text

from app.database import Base


class UserPreference(Base):
    __tablename__ = "user_preferences"

    key = Column(Text, primary_key=True)
    value = Column(Text, nullable=False)  # JSON-encoded
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NewsSource(Base):
    __tablename__ = "news_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    url = Column(Text, unique=True, nullable=False)
    source_type = Column(Text, default="rss")  # rss, api, website
    enabled = Column(Boolean, default=True)
    etag = Column(Text)
    last_modified = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class TopicWeight(Base):
    __tablename__ = "topic_weights"

    topic = Column(Text, primary_key=True)
    weight = Column(Float, default=1.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
