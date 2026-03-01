from datetime import date

from pydantic import BaseModel

from app.schemas.article import ArticleResponse
from app.schemas.calendar import CalendarSummaryResponse
from app.schemas.inspiration import InspirationResponse
from app.schemas.stock import IndexResponse, WatchlistItemResponse


class StocksSection(BaseModel):
    indices: list[IndexResponse] = []
    watchlist: list[WatchlistItemResponse] = []


class BriefingResponse(BaseModel):
    date: date
    news: list[ArticleResponse] = []
    stocks: StocksSection = StocksSection()
    calendar: CalendarSummaryResponse = CalendarSummaryResponse()
    inspiration: InspirationResponse = InspirationResponse()
