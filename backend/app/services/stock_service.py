"""
Stock market data service.

Fetches US major indices and watchlist stock prices via yfinance.
"""

import logging
from datetime import datetime, timezone
from dataclasses import dataclass

import yfinance as yf

logger = logging.getLogger(__name__)

INDICES = [
    {"symbol": "^GSPC", "name": "S&P 500"},
    {"symbol": "^IXIC", "name": "NASDAQ"},
    {"symbol": "000001.SS", "name": "SSE Composite"},
    {"symbol": "^KS11", "name": "KOSPI"},
]


@dataclass
class IndexData:
    name: str
    symbol: str
    price: float = 0.0
    change: float = 0.0
    change_percent: float = 0.0


@dataclass
class WatchlistData:
    symbol: str
    name: str | None = None
    price: float = 0.0
    change: float = 0.0
    change_percent: float = 0.0


def get_indices() -> list[IndexData]:
    """Fetch current data for major stock indices."""
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
                IndexData(
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


def get_watchlist_prices(symbols: list[str]) -> list[WatchlistData]:
    """Fetch current prices for a list of stock symbols."""
    if not symbols:
        return []

    results = []
    try:
        tickers = yf.Tickers(" ".join(symbols))
        for symbol in symbols:
            ticker = tickers.tickers.get(symbol)
            if ticker is None:
                results.append(WatchlistData(symbol=symbol))
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
                WatchlistData(
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
    if now.weekday() >= 5:
        return False
    hour_utc = now.hour
    return 13 <= hour_utc <= 21
