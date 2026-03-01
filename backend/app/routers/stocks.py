from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.stock import IndexResponse, WatchlistAddRequest, WatchlistItemResponse

router = APIRouter()


@router.get("/indices", response_model=list[IndexResponse])
async def get_indices():
    """Get major US stock indices (S&P 500, NASDAQ, Dow Jones)."""
    # TODO: Call stock_service.get_indices()
    return []


@router.get("/watchlist", response_model=list[WatchlistItemResponse])
async def get_watchlist(db: Session = Depends(get_db)):
    """Get watchlist with current prices."""
    # TODO: Call stock_service.get_watchlist_prices()
    return []


@router.post("/watchlist", response_model=WatchlistItemResponse)
async def add_to_watchlist(
    item: WatchlistAddRequest, db: Session = Depends(get_db)
):
    """Add a stock to the watchlist."""
    # TODO: Add to watchlist table
    return WatchlistItemResponse(symbol=item.symbol)


@router.delete("/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str, db: Session = Depends(get_db)):
    """Remove a stock from the watchlist."""
    # TODO: Delete from watchlist table
    return {"status": "removed", "symbol": symbol}
