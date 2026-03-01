from fastapi import APIRouter

from app.schemas.calendar import CalendarEvent, CalendarSummaryResponse, Reminder

router = APIRouter()


@router.get("/events", response_model=list[CalendarEvent])
async def get_events():
    """Get today's calendar events."""
    # TODO: Call calendar_service.get_events()
    return []


@router.get("/reminders", response_model=list[Reminder])
async def get_reminders():
    """Get pending reminders/tasks."""
    # TODO: Call calendar_service.get_reminders()
    return []


@router.get("/summary", response_model=CalendarSummaryResponse)
async def get_calendar_summary():
    """Get Gemini-powered schedule summary."""
    # TODO: Call calendar_service + gemini_service for summary
    return CalendarSummaryResponse(summary="No calendar data available yet.")
