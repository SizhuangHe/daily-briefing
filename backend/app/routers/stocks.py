from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.stock import WatchlistItem
from app.schemas.stock import IndexResponse, WatchlistAddRequest, WatchlistItemResponse
from app.services import stock_service

router = APIRouter()


@router.get("/indices", response_model=list[IndexResponse])
async def get_indices():
    """Get major US stock indices (S&P 500, NASDAQ, Dow Jones)."""
    return stock_service.get_indices()


@router.get("/watchlist", response_model=list[WatchlistItemResponse])
async def get_watchlist(db: Session = Depends(get_db)):
    """Get watchlist with current prices."""
    items = db.query(WatchlistItem).all()
    if not items:
        return []
    symbols = [item.symbol for item in items]
    return stock_service.get_watchlist_prices(symbols)


@router.post("/watchlist", response_model=WatchlistItemResponse)
async def add_to_watchlist(
    item: WatchlistAddRequest, db: Session = Depends(get_db)
):
    """Add a stock to the watchlist."""
    symbol = item.symbol.upper().strip()
    existing = db.query(WatchlistItem).filter_by(symbol=symbol).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"{symbol} already in watchlist")

    db_item = WatchlistItem(symbol=symbol)
    db.add(db_item)
    db.commit()

    # Fetch current price for the response
    prices = stock_service.get_watchlist_prices([symbol])
    if prices:
        return prices[0]
    return WatchlistItemResponse(symbol=symbol)


@router.delete("/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str, db: Session = Depends(get_db)):
    """Remove a stock from the watchlist."""
    symbol = symbol.upper().strip()
    item = db.query(WatchlistItem).filter_by(symbol=symbol).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"{symbol} not in watchlist")
    db.delete(item)
    db.commit()
    return {"status": "removed", "symbol": symbol}
