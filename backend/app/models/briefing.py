from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Integer, Text

from app.database import Base


class DailyBriefing(Base):
    __tablename__ = "daily_briefings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, unique=True, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    sections_json = Column(Text, nullable=False)
    model_versions = Column(Text)
    article_ids = Column(Text)
    notes = Column(Text)


class GeminiCache(Base):
    __tablename__ = "gemini_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cache_key = Column(Text, unique=True, nullable=False)
    response = Column(Text, nullable=False)  # JSON
    model_version = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class SchedulerLock(Base):
    __tablename__ = "scheduler_locks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_key = Column(Text, unique=True, nullable=False)
    lock_date = Column(Date, nullable=False)
    completed_at = Column(DateTime)
