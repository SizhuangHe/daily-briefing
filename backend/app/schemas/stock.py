from pydantic import BaseModel


class IndexResponse(BaseModel):
    name: str
    symbol: str
    price: float
    change: float
    change_percent: float


class WatchlistItemResponse(BaseModel):
    symbol: str
    name: str | None = None
    price: float | None = None
    change: float | None = None
    change_percent: float | None = None

    model_config = {"from_attributes": True}


class WatchlistAddRequest(BaseModel):
    symbol: str
