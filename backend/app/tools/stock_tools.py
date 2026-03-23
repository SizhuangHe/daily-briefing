"""MCP tools for stock market data."""

import dataclasses

from app.database import SessionLocal
from app.models.stock import WatchlistItem
from app.services import stock_service


def get_stock_indices() -> list[dict]:
    """Get major stock indices: S&P 500, NASDAQ, SSE Composite, KOSPI."""
    results = stock_service.get_indices()
    return [dataclasses.asdict(r) for r in results]


def get_watchlist() -> list[dict]:
    """Get user's stock watchlist with current prices."""
    db = SessionLocal()
    try:
        items = db.query(WatchlistItem).all()
        if not items:
            return []
        symbols = [item.symbol for item in items]
        results = stock_service.get_watchlist_prices(symbols)
        return [dataclasses.asdict(r) for r in results]
    finally:
        db.close()
