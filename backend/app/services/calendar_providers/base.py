"""Base calendar provider interface."""

from abc import ABC, abstractmethod
from datetime import date

from app.schemas.calendar import CalendarEvent, Reminder


class CalendarProvider(ABC):
    """Abstract base class for calendar data providers."""

    @abstractmethod
    async def get_events(self, target_date: date) -> list[CalendarEvent]:
        """Get calendar events for the given date."""
        ...

    @abstractmethod
    async def get_reminders(self) -> list[Reminder]:
        """Get pending (uncompleted) reminders."""
        ...
