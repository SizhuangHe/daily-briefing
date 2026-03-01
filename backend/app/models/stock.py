from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, Text

from app.database import Base


class WatchlistItem(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(Text, unique=True, nullable=False)
    name = Column(Text)
    added_at = Column(DateTime, default=datetime.utcnow)


class StockSnapshot(Base):
    __tablename__ = "stock_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(Text, nullable=False)
    price = Column(Float, nullable=False)
    change = Column(Float)
    change_percent = Column(Float)
    volume = Column(Integer)
    fetched_at = Column(DateTime, default=datetime.utcnow)
