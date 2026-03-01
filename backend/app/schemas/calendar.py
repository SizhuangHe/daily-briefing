from datetime import datetime

from pydantic import BaseModel


class CalendarEvent(BaseModel):
    title: str
    start_time: datetime | None = None
    end_time: datetime | None = None
    location: str | None = None
    calendar: str | None = None


class Reminder(BaseModel):
    title: str
    due_date: datetime | None = None
    notes: str | None = None
    priority: int = 0
    list_name: str | None = None


class CalendarSummaryResponse(BaseModel):
    events: list[CalendarEvent] = []
    reminders: list[Reminder] = []
    summary: str = ""
