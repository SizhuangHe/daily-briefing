from pydantic import BaseModel


class Quote(BaseModel):
    text: str
    author: str | None = None


class InspirationResponse(BaseModel):
    quote: Quote | None = None
    fun_fact: str | None = None
    activity: str | None = None
