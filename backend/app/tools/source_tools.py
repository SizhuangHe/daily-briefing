"""MCP tools for managing news sources."""

from app.database import SessionLocal
from app.models.preference import NewsSource


def list_sources() -> list[dict]:
    """List all configured news sources."""
    db = SessionLocal()
    try:
        sources = db.query(NewsSource).order_by(NewsSource.name).all()
        return [
            {
                "id": s.id,
                "name": s.name,
                "url": s.url,
                "source_type": s.source_type,
                "enabled": s.enabled,
            }
            for s in sources
        ]
    finally:
        db.close()


def add_source(name: str, url: str, source_type: str = "rss") -> dict:
    """Add a new RSS news source.

    Args:
        name: Display name for the source
        url: RSS feed URL
        source_type: Source type (default "rss")
    """
    db = SessionLocal()
    try:
        existing = db.query(NewsSource).filter_by(url=url).first()
        if existing:
            return {"error": f"Source URL already exists (id={existing.id})"}

        source = NewsSource(name=name, url=url, source_type=source_type)
        db.add(source)
        db.commit()
        db.refresh(source)
        return {
            "id": source.id,
            "name": source.name,
            "url": source.url,
            "source_type": source.source_type,
            "enabled": source.enabled,
            "status": "created",
        }
    finally:
        db.close()


def toggle_source(source_id: int) -> dict:
    """Toggle a news source enabled/disabled.

    Args:
        source_id: The source ID to toggle
    """
    db = SessionLocal()
    try:
        source = db.query(NewsSource).filter_by(id=source_id).first()
        if not source:
            return {"error": f"Source {source_id} not found"}
        source.enabled = not source.enabled
        db.commit()
        return {"id": source.id, "name": source.name, "enabled": source.enabled}
    finally:
        db.close()


def remove_source(source_id: int) -> dict:
    """Remove a news source.

    Args:
        source_id: The source ID to remove
    """
    db = SessionLocal()
    try:
        source = db.query(NewsSource).filter_by(id=source_id).first()
        if not source:
            return {"error": f"Source {source_id} not found"}
        name = source.name
        db.delete(source)
        db.commit()
        return {"status": "removed", "id": source_id, "name": name}
    finally:
        db.close()
