from pydantic import BaseModel


class PreferencesResponse(BaseModel):
    topics: list[str] = []
    rating_mode: str = "thumbs"
    topic_weights: dict[str, float] = {}


class PreferencesUpdateRequest(BaseModel):
    topics: list[str] | None = None
    rating_mode: str | None = None


class NewsSourceResponse(BaseModel):
    id: int
    name: str
    url: str
    source_type: str = "rss"
    enabled: bool = True

    model_config = {"from_attributes": True}


class NewsSourceAddRequest(BaseModel):
    name: str
    url: str
    source_type: str = "rss"
