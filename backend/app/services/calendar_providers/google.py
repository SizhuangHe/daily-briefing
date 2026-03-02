"""Google Calendar API provider using OAuth2 (multi-account)."""

import logging
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.schemas.calendar import CalendarEvent, Reminder
from app.services.calendar_providers.base import CalendarProvider

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
]

# Token and credentials paths (relative to backend/)
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
CREDENTIALS_PATH = DATA_DIR / "google_credentials.json"


def _get_all_token_paths() -> list[Path]:
    """Find all google_token*.json files in the data directory."""
    if not DATA_DIR.exists():
        return []
    return sorted(DATA_DIR.glob("google_token*.json"))


def _load_credentials(token_path: Path) -> Credentials | None:
    """Load or refresh credentials from a specific token file."""
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            token_path.write_text(creds.to_json())
            return creds
        except Exception as e:
            logger.error(f"Failed to refresh token {token_path.name}: {e}")
            token_path.unlink(missing_ok=True)

    return None


def _get_all_credentials() -> list[Credentials]:
    """Load credentials from all token files."""
    all_creds = []
    for token_path in _get_all_token_paths():
        creds = _load_credentials(token_path)
        if creds:
            all_creds.append(creds)
    return all_creds


def add_account() -> bool:
    """Run OAuth flow to add a new Google account. Returns True on success."""
    if not CREDENTIALS_PATH.exists():
        logger.error(
            f"Google credentials not found at {CREDENTIALS_PATH}. "
            "Download OAuth client credentials from Google Cloud Console "
            "and save as backend/data/google_credentials.json"
        )
        return False

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_PATH), SCOPES
        )
        creds = flow.run_local_server(port=0)
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Determine next token filename
        existing = _get_all_token_paths()
        if not existing:
            token_path = DATA_DIR / "google_token.json"
        else:
            token_path = DATA_DIR / f"google_token_{len(existing) + 1}.json"

        token_path.write_text(creds.to_json())
        logger.info(f"Saved new account token to {token_path.name}")
        return True
    except Exception as e:
        logger.error(f"Google OAuth flow failed: {e}")
        return False


class GoogleCalendarProvider(CalendarProvider):
    """Calendar provider using Google Calendar API (multi-account)."""

    async def get_events(self, target_date: date) -> list[CalendarEvent]:
        """Get calendar events for the given date from all accounts."""
        all_creds = _get_all_credentials()
        if not all_creds:
            # No tokens yet — try to add first account
            if add_account():
                all_creds = _get_all_credentials()
            if not all_creds:
                return []

        all_events: list[CalendarEvent] = []
        for creds in all_creds:
            events = self._fetch_events_for_account(creds, target_date)
            all_events.extend(events)

        return all_events

    def _fetch_events_for_account(
        self, creds: Credentials, target_date: date
    ) -> list[CalendarEvent]:
        """Fetch events from a single Google account."""
        try:
            service = build("calendar", "v3", credentials=creds)

            # Use the user's primary calendar timezone
            cal_settings = service.settings().get(setting="timezone").execute()
            tz = ZoneInfo(cal_settings["value"])

            start_of_day = datetime(
                target_date.year, target_date.month, target_date.day,
                tzinfo=tz,
            )
            end_of_day = datetime(
                target_date.year, target_date.month, target_date.day,
                23, 59, 59, tzinfo=tz,
            )

            calendar_list = service.calendarList().list().execute()
            events: list[CalendarEvent] = []

            for cal in calendar_list.get("items", []):
                cal_id = cal["id"]
                cal_name = cal.get("summary", cal_id)

                try:
                    events_result = (
                        service.events()
                        .list(
                            calendarId=cal_id,
                            timeMin=start_of_day.isoformat(),
                            timeMax=end_of_day.isoformat(),
                            singleEvents=True,
                            orderBy="startTime",
                        )
                        .execute()
                    )
                except Exception as e:
                    logger.debug(f"Skipping calendar {cal_name}: {e}")
                    continue

                for event in events_result.get("items", []):
                    title = event.get("summary", "(No title)")
                    location = event.get("location")

                    start = event.get("start", {})
                    end = event.get("end", {})
                    start_time = self._parse_gcal_time(
                        start.get("dateTime") or start.get("date")
                    )
                    end_time = self._parse_gcal_time(
                        end.get("dateTime") or end.get("date")
                    )

                    events.append(CalendarEvent(
                        title=title,
                        start_time=start_time,
                        end_time=end_time,
                        location=location,
                        calendar=cal_name,
                    ))

            return events

        except Exception as e:
            logger.error(f"Google Calendar API error: {e}")
            return []

    async def get_reminders(self) -> list[Reminder]:
        """Reminders come from Apple Reminders, not Google Tasks."""
        return []

    @staticmethod
    def _parse_gcal_time(s: str | None) -> datetime | None:
        """Parse Google Calendar datetime string."""
        if not s:
            return None
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            return None
