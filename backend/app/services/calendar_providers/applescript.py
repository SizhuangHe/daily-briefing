"""macOS Calendar/Reminders provider using AppleScript."""

import logging
import re
from datetime import date, datetime

from app.schemas.calendar import CalendarEvent, Reminder
from app.services.calendar_providers.base import CalendarProvider
from app.utils.applescript import run_applescript

logger = logging.getLogger(__name__)

# Delimiter for parsing multi-field AppleScript output
DELIM = "|||"


class AppleScriptProvider(CalendarProvider):
    """Calendar/Reminders provider using macOS AppleScript."""

    async def get_events(self, target_date: date) -> list[CalendarEvent]:
        """Get calendar events for the given date via AppleScript."""
        # Use current date manipulation instead of locale-dependent date strings
        today = date.today()
        day_offset = (target_date - today).days

        if day_offset == 0:
            date_expr = "set targetDate to current date"
        else:
            date_expr = f"set targetDate to (current date) + ({day_offset} * days)"

        script = f'''
tell application "Calendar"
    {date_expr}
    set hours of targetDate to 0
    set minutes of targetDate to 0
    set seconds of targetDate to 0
    set startOfDay to targetDate
    set endOfDay to targetDate + (1 * days)
    set output to ""
    repeat with cal in calendars
        set calName to name of cal
        try
            set dayEvents to (every event of cal whose start date >= startOfDay and start date < endOfDay)
            repeat with evt in dayEvents
                set evtTitle to summary of evt
                set evtStart to start date of evt
                set evtEnd to end date of evt
                set evtLoc to ""
                try
                    set evtLoc to location of evt
                end try
                if evtLoc is missing value then set evtLoc to ""
                set output to output & evtTitle & "{DELIM}" & (evtStart as string) & "{DELIM}" & (evtEnd as string) & "{DELIM}" & evtLoc & "{DELIM}" & calName & linefeed
            end repeat
        end try
    end repeat
    return output
end tell
'''
        try:
            raw = run_applescript(script)
        except PermissionError:
            logger.warning("Calendar access denied by macOS")
            raise
        except Exception as e:
            logger.error(f"Failed to get calendar events: {e}")
            return []

        return self._parse_events(raw)

    async def get_reminders(self) -> list[Reminder]:
        """Get pending (uncompleted) reminders via AppleScript."""
        script = f'''
tell application "Reminders"
    set output to ""
    repeat with reminderList in lists
        set listName to name of reminderList
        set pendingReminders to (every reminder of reminderList whose completed is false)
        repeat with rem in pendingReminders
            set remTitle to name of rem
            set remDue to ""
            try
                set remDue to (due date of rem) as string
            end try
            if remDue is missing value then set remDue to ""
            set remNotes to ""
            try
                set remNotes to body of rem
            end try
            if remNotes is missing value then set remNotes to ""
            set remPriority to 0
            try
                set remPriority to priority of rem
            end try
            set output to output & remTitle & "{DELIM}" & remDue & "{DELIM}" & remNotes & "{DELIM}" & remPriority & "{DELIM}" & listName & linefeed
        end repeat
    end repeat
    return output
end tell
'''
        try:
            raw = run_applescript(script)
        except PermissionError:
            logger.warning("Reminders access denied by macOS")
            raise
        except Exception as e:
            logger.error(f"Failed to get reminders: {e}")
            return []

        return self._parse_reminders(raw)

    def _parse_events(self, raw: str) -> list[CalendarEvent]:
        """Parse AppleScript output into CalendarEvent objects."""
        events = []
        for line in raw.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split(DELIM)
            if len(parts) < 5:
                continue

            title, start_str, end_str, location, calendar = (
                parts[0].strip(),
                parts[1].strip(),
                parts[2].strip(),
                parts[3].strip(),
                parts[4].strip(),
            )

            events.append(CalendarEvent(
                title=title,
                start_time=self._parse_datetime(start_str),
                end_time=self._parse_datetime(end_str),
                location=location or None,
                calendar=calendar or None,
            ))
        return events

    def _parse_reminders(self, raw: str) -> list[Reminder]:
        """Parse AppleScript output into Reminder objects."""
        reminders = []
        for line in raw.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split(DELIM)
            if len(parts) < 5:
                continue

            title, due_str, notes, priority_str, list_name = (
                parts[0].strip(),
                parts[1].strip(),
                parts[2].strip(),
                parts[3].strip(),
                parts[4].strip(),
            )

            priority = 0
            try:
                priority = int(priority_str)
            except ValueError:
                pass

            reminders.append(Reminder(
                title=title,
                due_date=self._parse_datetime(due_str),
                notes=notes or None,
                priority=priority,
                list_name=list_name or None,
            ))
        return reminders

    @staticmethod
    def _parse_datetime(s: str) -> datetime | None:
        """Try multiple macOS date formats including Chinese locale."""
        if not s:
            return None

        # Chinese locale: "2026年3月1日 星期日 14:00:00"
        zh_match = re.match(
            r"(\d{4})年(\d{1,2})月(\d{1,2})日\s+\S+\s+(\d{1,2}):(\d{2}):(\d{2})",
            s,
        )
        if zh_match:
            y, mo, d, h, mi, sec = (int(x) for x in zh_match.groups())
            return datetime(y, mo, d, h, mi, sec)

        # English locale formats
        formats = [
            "%A, %B %d, %Y at %I:%M:%S %p",   # "Saturday, March 1, 2026 at 2:00:00 PM"
            "%B %d, %Y at %I:%M:%S %p",         # "March 1, 2026 at 2:00:00 PM"
            "%Y-%m-%d %H:%M:%S",                 # "2026-03-01 14:00:00"
            "%m/%d/%Y %I:%M:%S %p",              # "03/01/2026 2:00:00 PM"
            "%m/%d/%Y, %I:%M %p",                # "03/01/2026, 2:00 PM"
        ]
        for fmt in formats:
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue

        logger.debug(f"Could not parse datetime: {s}")
        return None
