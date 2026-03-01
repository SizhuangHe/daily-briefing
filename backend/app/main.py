from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import SessionLocal, init_db
from app.routers import briefing, calendar, inspiration, news, preferences, stocks
from app.services.news_service import seed_default_sources


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database tables and seed data
    init_db()
    db = SessionLocal()
    try:
        seed_default_sources(db)
    finally:
        db.close()
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="Daily Briefing API",
    description="Personal daily briefing aggregator",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(briefing.router, prefix="/api/v1", tags=["briefing"])
app.include_router(news.router, prefix="/api/v1/news", tags=["news"])
app.include_router(stocks.router, prefix="/api/v1/stocks", tags=["stocks"])
app.include_router(calendar.router, prefix="/api/v1/calendar", tags=["calendar"])
app.include_router(
    inspiration.router, prefix="/api/v1/inspiration", tags=["inspiration"]
)
app.include_router(
    preferences.router, prefix="/api/v1/preferences", tags=["preferences"]
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
