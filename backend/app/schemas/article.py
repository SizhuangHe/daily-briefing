from datetime import datetime

from pydantic import BaseModel


class ArticleResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    url: str
    source_name: str | None = None
    image_url: str | None = None
    topics: list[str] = []
    gemini_summary: str | None = None
    recommendation_score: float = 0.0
    published_at: datetime | None = None

    model_config = {"from_attributes": True}


class ArticleRatingRequest(BaseModel):
    score: int  # -1 or 1



class ArticleRatingResponse(BaseModel):
    article_id: int
    score: int
    rated_at: datetime

    model_config = {"from_attributes": True}
