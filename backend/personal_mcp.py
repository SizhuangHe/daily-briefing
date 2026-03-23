#!/usr/bin/env python3
"""
Personal Tools MCP Server.

Exposes Things 3 as MCP tools for Claude Code.
Things reads use subprocess (things conda env), writes use URL Scheme.

Yale Google account (sizhuang.he@yale.edu) readonly access for Gmail and Calendar.
Personal Google account (sizhuangh@gmail.com) uses gws MCP server separately.
"""

import json
import logging
import os
import plistlib
import sqlite3
import subprocess
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

mcp = FastMCP("personal-tools")

# ── Config ─────────────────────────────────────────────────────────────

TZ = timezone(timedelta(hours=-5))  # America/New_York (EST)
THINGS_AUTH_TOKEN = os.environ.get("THINGS_AUTH_TOKEN", "")
THINGS_DB = Path.home() / (
    "Library/Group Containers/JLMPQHK86H.com.culturedcode.ThingsMac/"
    "ThingsData-4TTAX/Things Database.thingsdatabase/main.sqlite"
)

# Yale Google account (readonly)
DATA_DIR = Path(__file__).parent / "data"
YALE_CREDENTIALS_FILE = DATA_DIR / "google_credentials.json"
YALE_GMAIL_TOKEN_FILE = DATA_DIR / "google_token_gmail_2.json"
YALE_CALENDAR_TOKEN_FILE = DATA_DIR / "google_token_2.json"


def _get_yale_creds(token_file: Path, scopes: list[str]) -> Credentials:
    """Load and refresh Yale Google credentials."""
    creds = Credentials.from_authorized_user_file(str(token_file), scopes)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_file.write_text(creds.to_json())
    return creds


def _yale_gmail():
    """Get Yale Gmail service (readonly)."""
    creds = _get_yale_creds(YALE_GMAIL_TOKEN_FILE, ["https://www.googleapis.com/auth/gmail.readonly"])
    return build("gmail", "v1", credentials=creds)


def _yale_calendar():
    """Get Yale Calendar service (readonly)."""
    creds = _get_yale_creds(YALE_CALENDAR_TOKEN_FILE, ["https://www.googleapis.com/auth/calendar.readonly"])
    return build("calendar", "v3", credentials=creds)


# ── Helpers ────────────────────────────────────────────────────────────

def _things_read(code: str) -> str:
    """Run Python code in the 'things' conda env and return stdout."""
    result = subprocess.run(
        ["conda", "run", "-n", "things", "python3", "-c", code],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(f"things.py error: {result.stderr.strip()}")
    return result.stdout.strip()


def _things_url(path: str, params: dict) -> None:
    """Open a Things URL Scheme command."""
    query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    url = f"things:///{path}?{query}"
    subprocess.run(["open", url], timeout=5)


# ── Things 3 Tools ────────────────────────────────────────────────────

@mcp.tool()
def things_today() -> str:
    """Get all tasks from Things 3 Today list."""
    raw = _things_read("import things, json; print(json.dumps(things.today()))")
    return raw


@mcp.tool()
def things_upcoming() -> str:
    """Get tasks from Things 3 Upcoming list."""
    raw = _things_read("import things, json; print(json.dumps(things.upcoming()))")
    return raw


@mcp.tool()
def things_anytime() -> str:
    """Get tasks from Things 3 Anytime list."""
    raw = _things_read("import things, json; print(json.dumps(things.anytime()))")
    return raw


@mcp.tool()
def things_inbox() -> str:
    """Get tasks from Things 3 Inbox."""
    raw = _things_read("import things, json; print(json.dumps(things.inbox()))")
    return raw


@mcp.tool()
def things_logbook(period: str = "today") -> str:
    """Get completed tasks from Things 3 Logbook.

    Args:
        period: "today", "week" (last 7 days), or "all"
    """
    if period == "today":
        today = datetime.now().strftime("%Y-%m-%d")
        code = (
            f"import things, json; "
            f"print(json.dumps([t for t in things.logbook() if t.get('stop_date','') >= '{today}']))"
        )
    elif period == "week":
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        code = (
            f"import things, json; "
            f"print(json.dumps([t for t in things.logbook() if t.get('stop_date','') >= '{week_ago}']))"
        )
    else:
        code = "import things, json; print(json.dumps(things.logbook()))"
    return _things_read(code)


@mcp.tool()
def things_projects() -> str:
    """List all Things 3 projects with their UUIDs and areas."""
    raw = _things_read("import things, json; print(json.dumps(things.projects()))")
    return raw


@mcp.tool()
def things_project_todos(project_name: str) -> str:
    """Get all tasks in a specific Things 3 project.

    Args:
        project_name: Project title (e.g. "HarmonyAgent", "Reasoning C2S")
    """
    code = (
        "import things, json\n"
        f"name = {json.dumps(project_name)}\n"
        "projects = things.projects()\n"
        "proj = next((p for p in projects if p['title'] == name), None)\n"
        "if proj:\n"
        "    tasks = things.todos(project=proj['uuid'])\n"
        "    print(json.dumps(tasks))\n"
        "else:\n"
        "    print(json.dumps({'error': f'Project not found: {name}'}))\n"
    )
    return _things_read(code)


@mcp.tool()
def things_add_todo(
    title: str,
    when: str | None = None,
    project: str | None = None,
    tags: str | None = None,
    deadline: str | None = None,
    notes: str | None = None,
) -> str:
    """Create a new task in Things 3.

    Args:
        title: Task title (e.g. "🧪 跑 baseline experiments")
        when: "today", "tomorrow", "evening", "anytime", "someday", or YYYY-MM-DD
        project: Project name to add to (e.g. "HarmonyAgent")
        tags: Comma-separated tags (e.g. "urgent,important")
        deadline: Deadline date YYYY-MM-DD
        notes: Task notes
    """
    params = {"title": title}
    if when:
        params["when"] = when
    if project:
        params["list"] = project
    if tags:
        params["tags"] = tags
    if deadline:
        params["deadline"] = deadline
    if notes:
        params["notes"] = notes

    _things_url("add", params)
    return json.dumps({"status": "created", "title": title})


@mcp.tool()
def things_add_todos(todos: str) -> str:
    """Batch create multiple tasks in Things 3.

    Args:
        todos: JSON array of task objects. Each object has:
            title (required), when, project (as "list"), tags (array), deadline, notes
            Example: [{"title": "Task 1", "when": "today", "list": "ProjectName"}]
    """
    items = json.loads(todos)
    things_items = []
    for t in items:
        attrs = {"title": t["title"]}
        for key in ["when", "list", "deadline", "notes"]:
            if key in t:
                attrs[key] = t[key]
        if "tags" in t:
            attrs["tags"] = t["tags"] if isinstance(t["tags"], list) else [t["tags"]]
        if "project" in t:
            attrs["list"] = t["project"]
        things_items.append({"type": "to-do", "attributes": attrs})

    data_str = json.dumps(things_items)
    encoded = urllib.parse.quote(data_str)
    subprocess.run(["open", f"things:///json?data={encoded}"], timeout=5)
    return json.dumps({"status": "created", "count": len(things_items)})


@mcp.tool()
def things_update_todo(
    uuid: str,
    when: str | None = None,
    deadline: str | None = None,
    completed: bool | None = None,
    canceled: bool | None = None,
    title: str | None = None,
    notes: str | None = None,
    append_notes: str | None = None,
    tags: str | None = None,
    add_tags: str | None = None,
) -> str:
    """Update an existing task in Things 3.

    Requires THINGS_AUTH_TOKEN environment variable.

    Args:
        uuid: Task UUID to update
        when: New date ("today", "tomorrow", YYYY-MM-DD, etc.)
        deadline: New deadline YYYY-MM-DD
        completed: Set to true to mark complete
        canceled: Set to true to cancel
        title: New title
        notes: Replace notes
        append_notes: Append to existing notes
        tags: Replace all tags (comma-separated)
        add_tags: Add tags (comma-separated)
    """
    if not THINGS_AUTH_TOKEN:
        return json.dumps({"error": "THINGS_AUTH_TOKEN not set"})

    params: dict = {"id": uuid, "auth-token": THINGS_AUTH_TOKEN}
    if when is not None:
        params["when"] = when
    if deadline is not None:
        params["deadline"] = deadline
    if completed is not None:
        params["completed"] = str(completed).lower()
    if canceled is not None:
        params["canceled"] = str(canceled).lower()
    if title is not None:
        params["title"] = title
    if notes is not None:
        params["notes"] = notes
    if append_notes is not None:
        params["append-notes"] = append_notes
    if tags is not None:
        params["tags"] = tags
    if add_tags is not None:
        params["add-tags"] = add_tags

    _things_url("update", params)
    return json.dumps({"status": "updated", "uuid": uuid})


@mcp.tool()
def things_set_repeat(
    uuid: str,
    frequency: str,
    interval: int = 1,
) -> str:
    """Set a repeating schedule on a Things 3 task via direct SQLite write.

    Args:
        uuid: Task UUID
        frequency: "daily", "weekly", "monthly", "yearly"
        interval: Repeat every N units (e.g. 2 = every 2 weeks). Default 1.
    """
    freq_map = {"daily": 64, "weekly": 256, "monthly": 1024, "yearly": 4096}
    if frequency not in freq_map:
        return json.dumps({"error": f"Invalid frequency: {frequency}. Use: {list(freq_map.keys())}"})

    if not THINGS_DB.exists():
        return json.dumps({"error": f"Things database not found: {THINGS_DB}"})

    conn = sqlite3.connect(str(THINGS_DB))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT uuid, title, startDate FROM TMTask WHERE uuid = ?", (uuid,)
    ).fetchone()
    if not row:
        conn.close()
        return json.dumps({"error": f"Task not found: {uuid}"})

    start_date = row["startDate"]
    if not start_date:
        conn.close()
        return json.dumps({"error": "Task has no start date (when). Set a date first."})

    # startDate in Things is days since 2001-01-01
    cocoa_epoch = datetime(2001, 1, 1, tzinfo=timezone.utc)
    task_dt = cocoa_epoch + timedelta(days=start_date)
    anchor_ts = int(task_dt.timestamp())
    weekday = task_dt.isoweekday()  # 1=Mon .. 7=Sun

    far_future = 64092211200  # ~4032, Cocoa timestamp for "no end date"

    plist = {
        "ed": float(far_future),
        "fa": interval,
        "fu": freq_map[frequency],
        "ia": float(anchor_ts),
        "of": [{"wd": weekday}] if frequency == "weekly" else [],
        "rc": 0,
        "rrv": 4,
        "sr": float(anchor_ts),
        "tp": 0,
        "ts": 0,
    }
    blob = plistlib.dumps(plist, fmt=plistlib.FMT_XML)

    conn.execute("UPDATE TMTask SET repeater = ? WHERE uuid = ?", (blob, uuid))
    conn.commit()
    conn.close()

    return json.dumps({
        "status": "repeat_set",
        "uuid": uuid,
        "title": row["title"],
        "frequency": frequency,
        "interval": interval,
    })


# ── Yale Gmail (readonly) ─────────────────────────────────────────────

@mcp.tool()
def yale_gmail_unread(max_results: int = 20) -> str:
    """Get unread emails from Yale Gmail (sizhuang.he@yale.edu). Readonly.

    Args:
        max_results: Max number of messages to return (default 20)
    """
    svc = _yale_gmail()
    results = svc.users().messages().list(
        userId="me", q="is:unread", maxResults=max_results
    ).execute()
    messages = results.get("messages", [])
    if not messages:
        return json.dumps({"count": 0, "messages": []})

    out = []
    for msg_meta in messages:
        msg = svc.users().messages().get(
            userId="me", id=msg_meta["id"], format="metadata",
            metadataHeaders=["From", "Subject", "Date"],
        ).execute()
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        out.append({
            "id": msg["id"],
            "from": headers.get("From", ""),
            "subject": headers.get("Subject", ""),
            "date": headers.get("Date", ""),
            "snippet": msg.get("snippet", ""),
        })
    return json.dumps({"count": len(out), "messages": out})


@mcp.tool()
def yale_gmail_read(message_id: str) -> str:
    """Read a specific Yale Gmail message by ID. Readonly.

    Args:
        message_id: Gmail message ID
    """
    svc = _yale_gmail()
    msg = svc.users().messages().get(userId="me", id=message_id, format="full").execute()
    headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}

    # Extract body
    payload = msg.get("payload", {})
    body = ""
    if payload.get("body", {}).get("data"):
        import base64
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    elif payload.get("parts"):
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                import base64
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                break

    return json.dumps({
        "id": msg["id"],
        "from": headers.get("From", ""),
        "to": headers.get("To", ""),
        "subject": headers.get("Subject", ""),
        "date": headers.get("Date", ""),
        "body": body if "arxiv.org" in headers.get("From", "").lower() else body[:5000],
    })


@mcp.tool()
def yale_gmail_search(query: str, max_results: int = 20) -> str:
    """Search Yale Gmail with a query. Readonly.

    Args:
        query: Gmail search query (e.g. "from:professor subject:deadline")
        max_results: Max number of messages to return (default 20)
    """
    svc = _yale_gmail()
    results = svc.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()
    messages = results.get("messages", [])
    if not messages:
        return json.dumps({"count": 0, "messages": []})

    out = []
    for msg_meta in messages:
        msg = svc.users().messages().get(
            userId="me", id=msg_meta["id"], format="metadata",
            metadataHeaders=["From", "Subject", "Date"],
        ).execute()
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        out.append({
            "id": msg["id"],
            "from": headers.get("From", ""),
            "subject": headers.get("Subject", ""),
            "date": headers.get("Date", ""),
            "snippet": msg.get("snippet", ""),
        })
    return json.dumps({"count": len(out), "messages": out})


# ── Yale Calendar (readonly) ─────────────────────────────────────────

@mcp.tool()
def yale_calendar_today() -> str:
    """Get today's events from Yale Calendar (sizhuang.he@yale.edu). Readonly."""
    svc = _yale_calendar()
    now = datetime.now(TZ)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    end = now.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()

    results = svc.events().list(
        calendarId="primary", timeMin=start, timeMax=end,
        singleEvents=True, orderBy="startTime",
    ).execute()

    events = []
    for e in results.get("items", []):
        events.append({
            "id": e["id"],
            "summary": e.get("summary", "(no title)"),
            "start": e.get("start", {}).get("dateTime", e.get("start", {}).get("date", "")),
            "end": e.get("end", {}).get("dateTime", e.get("end", {}).get("date", "")),
            "location": e.get("location", ""),
            "description": e.get("description", "")[:500],
        })
    return json.dumps({"date": now.strftime("%Y-%m-%d"), "count": len(events), "events": events})


@mcp.tool()
def yale_calendar_events(
    time_min: str | None = None,
    time_max: str | None = None,
    max_results: int = 30,
) -> str:
    """Get events from Yale Calendar in a date range. Readonly.

    Args:
        time_min: Start datetime ISO format (default: now)
        time_max: End datetime ISO format (default: 7 days from now)
        max_results: Max events to return (default 30)
    """
    svc = _yale_calendar()
    now = datetime.now(TZ)
    if not time_min:
        time_min = now.isoformat()
    if not time_max:
        time_max = (now + timedelta(days=7)).isoformat()

    results = svc.events().list(
        calendarId="primary", timeMin=time_min, timeMax=time_max,
        singleEvents=True, orderBy="startTime", maxResults=max_results,
    ).execute()

    events = []
    for e in results.get("items", []):
        events.append({
            "id": e["id"],
            "summary": e.get("summary", "(no title)"),
            "start": e.get("start", {}).get("dateTime", e.get("start", {}).get("date", "")),
            "end": e.get("end", {}).get("dateTime", e.get("end", {}).get("date", "")),
            "location": e.get("location", ""),
            "description": e.get("description", "")[:500],
        })
    return json.dumps({"count": len(events), "events": events})


if __name__ == "__main__":
    mcp.run(transport="stdio")
