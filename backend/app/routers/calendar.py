from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.schemas.calendar import CalendarEvent, CalendarSummaryResponse, Reminder
from app.services import calendar_service

router = APIRouter()


@router.get("/events", response_model=list[CalendarEvent])
async def get_events(
    target_date: date | None = Query(default=None, description="Date in YYYY-MM-DD format, defaults to today"),
):
    """Get calendar events for a given date."""
    try:
        return await calendar_service.get_events(target_date)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/reminders", response_model=list[Reminder])
async def get_reminders():
    """Get pending reminders/tasks."""
    try:
        return await calendar_service.get_reminders()
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/summary", response_model=CalendarSummaryResponse)
async def get_calendar_summary():
    """Get today's events, reminders, and a Gemini-powered summary."""
    try:
        events = await calendar_service.get_events()
    except PermissionError as e:
        return CalendarSummaryResponse(summary=str(e))

    try:
        reminders = await calendar_service.get_reminders()
    except PermissionError:
        reminders = []

    summary = await calendar_service.get_summary()

    return CalendarSummaryResponse(
        events=events,
        reminders=reminders,
        summary=summary,
    )
