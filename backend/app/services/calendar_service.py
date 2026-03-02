"""
Calendar service with provider abstraction.

Uses CalendarProvider interface to support multiple backends
(Google Calendar API or AppleScript for macOS).
"""

import logging
from datetime import date

from app.config import settings
from app.schemas.calendar import CalendarEvent, Reminder
from app.services.calendar_providers.base import CalendarProvider
from app.services import gemini_service

logger = logging.getLogger(__name__)


def _create_provider() -> CalendarProvider:
    """Create calendar provider based on config."""
    if settings.calendar_provider == "google":
        from app.services.calendar_providers.google import GoogleCalendarProvider
        return GoogleCalendarProvider()
    else:
        from app.services.calendar_providers.applescript import AppleScriptProvider
        return AppleScriptProvider()


_provider: CalendarProvider = _create_provider()


def get_provider() -> CalendarProvider:
    """Get the active calendar provider."""
    return _provider


async def get_events(target_date: date | None = None) -> list[CalendarEvent]:
    """Get calendar events for the given date (defaults to today)."""
    if target_date is None:
        target_date = date.today()
    return await _provider.get_events(target_date)


async def get_reminders() -> list[Reminder]:
    """Get pending reminders (always from Apple Reminders)."""
    from app.services.calendar_providers.applescript import AppleScriptProvider
    apple = AppleScriptProvider()
    return await apple.get_reminders()


async def get_summary() -> str:
    """Get a Gemini-powered natural language schedule summary."""
    today = date.today()

    try:
        events = await get_events(today)
    except PermissionError:
        return (
            "Calendar access is not authorized. Please go to "
            "System Settings > Privacy & Security > Automation "
            "and enable access for Terminal."
        )

    try:
        reminders = await get_reminders()
    except PermissionError:
        reminders = []

    event_dicts = [
        {
            "title": e.title,
            "start_time": e.start_time.isoformat() if e.start_time else None,
            "end_time": e.end_time.isoformat() if e.end_time else None,
            "location": e.location,
            "calendar": e.calendar,
        }
        for e in events
    ]

    reminder_dicts = [
        {
            "title": r.title,
            "due_date": r.due_date.isoformat() if r.due_date else None,
            "notes": r.notes,
            "priority": r.priority,
            "list_name": r.list_name,
        }
        for r in reminders
    ]

    return gemini_service.summarize_schedule(event_dicts, reminder_dicts)
