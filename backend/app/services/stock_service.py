"""
Stock market data service.

Fetches US major indices and watchlist stock prices via yfinance.
"""

import logging
from datetime import datetime, timezone

import yfinance as yf

from app.schemas.stock import IndexResponse, WatchlistItemResponse

logger = logging.getLogger(__name__)

INDICES = [
    {"symbol": "^GSPC", "name": "S&P 500"},
    {"symbol": "^IXIC", "name": "NASDAQ"},
    {"symbol": "000001.SS", "name": "SSE Composite"},
    {"symbol": "^KS11", "name": "KOSPI"},
]


def get_indices() -> list[IndexResponse]:
    """Fetch current data for major US stock indices."""
    results = []
    symbols = [idx["symbol"] for idx in INDICES]
    name_map = {idx["symbol"]: idx["name"] for idx in INDICES}

    try:
        tickers = yf.Tickers(" ".join(symbols))
        for symbol in symbols:
            ticker = tickers.tickers.get(symbol)
            if ticker is None:
                continue
            info = ticker.fast_info
            price = info.get("lastPrice", 0.0)
            prev_close = info.get("previousClose", 0.0)
            change = price - prev_close if prev_close else 0.0
            change_pct = (change / prev_close * 100) if prev_close else 0.0

            results.append(
                IndexResponse(
                    name=name_map[symbol],
                    symbol=symbol,
                    price=round(price, 2),
                    change=round(change, 2),
                    change_percent=round(change_pct, 2),
                )
            )
    except Exception as e:
        logger.error(f"Failed to fetch indices: {e}")

    return results


def get_watchlist_prices(symbols: list[str]) -> list[WatchlistItemResponse]:
    """Fetch current prices for a list of stock symbols."""
    if not symbols:
        return []

    results = []
    try:
        tickers = yf.Tickers(" ".join(symbols))
        for symbol in symbols:
            ticker = tickers.tickers.get(symbol)
            if ticker is None:
                results.append(WatchlistItemResponse(symbol=symbol))
                continue

            info = ticker.fast_info
            price = info.get("lastPrice", 0.0)
            prev_close = info.get("previousClose", 0.0)
            change = price - prev_close if prev_close else 0.0
            change_pct = (change / prev_close * 100) if prev_close else 0.0

            # Try to get the company name
            name = None
            try:
                name = ticker.info.get("shortName")
            except Exception:
                pass

            results.append(
                WatchlistItemResponse(
                    symbol=symbol,
                    name=name,
                    price=round(price, 2),
                    change=round(change, 2),
                    change_percent=round(change_pct, 2),
                )
            )
    except Exception as e:
        logger.error(f"Failed to fetch watchlist prices: {e}")

    return results


def is_market_hours() -> bool:
    """Check if US stock market is currently open (rough check)."""
    now = datetime.now(timezone.utc)
    # NYSE: Mon-Fri, 9:30 AM - 4:00 PM ET (UTC-5 or UTC-4 DST)
    # Rough check: weekday and between 13:30-21:00 UTC
    if now.weekday() >= 5:  # Saturday or Sunday
        return False
    hour_utc = now.hour
    return 13 <= hour_utc <= 21
