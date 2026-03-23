#!/usr/bin/env python3
"""
ActivityWatch MCP Server.

Exposes ActivityWatch time-tracking data as MCP tools for Claude Code.
Uses the AW query API for server-side aggregation (no raw event limits).
"""

import json
import logging
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen, Request
from urllib.error import URLError

from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

mcp = FastMCP("activitywatch")

AW_BASE = "http://localhost:5600/api/0"
TZ = timezone(timedelta(hours=-5))  # EST
HOSTNAME = "Sizhuangs-MacBook-Pro-4.local"

BUCKET_WINDOW = f"aw-watcher-window_{HOSTNAME}"
BUCKET_AFK = f"aw-watcher-afk_{HOSTNAME}"
BUCKET_WEB = f"aw-watcher-web-chrome_{HOSTNAME}"


def _aw_get(path: str) -> dict | list | None:
    """GET from ActivityWatch API. Returns None if AW is not running."""
    try:
        url = f"{AW_BASE}{path}"
        req = Request(url)
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except URLError:
        return None


def _aw_query(query: str, timeperiods: list[str]) -> list | None:
    """POST a query to the AW query2 endpoint for server-side aggregation."""
    try:
        url = f"{AW_BASE}/query/"
        payload = json.dumps({
            "query": query.split("\n"),
            "timeperiods": timeperiods,
        }).encode()
        req = Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except URLError:
        return None


def _day_period(date: str | None = None) -> str:
    """Return a timeperiod string for a given date."""
    if date:
        dt = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=TZ)
    else:
        dt = datetime.now(TZ)
    start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return f"{start.isoformat()}/{end.isoformat()}"


@mcp.tool()
def aw_status() -> str:
    """Check if ActivityWatch is running and list available buckets."""
    buckets = _aw_get("/buckets/")
    if buckets is None:
        return json.dumps({"running": False, "message": "ActivityWatch is not running. Start it with: open -a ActivityWatch"})
    return json.dumps({
        "running": True,
        "buckets": list(buckets.keys()),
    })


@mcp.tool()
def aw_app_usage(date: str | None = None) -> str:
    """Get app/window usage summary for a given date (server-side aggregated).

    Returns total time spent per app, sorted by duration.

    Args:
        date: Date in YYYY-MM-DD format (default: today)
    """
    period = _day_period(date)
    query = f"""
events = query_bucket("{BUCKET_WINDOW}");
events = merge_events_by_keys(events, ["app"]);
events = sort_by_duration(events);
RETURN = events;
"""
    result = _aw_query(query.strip(), [period])
    if result is None:
        return json.dumps({"error": "ActivityWatch not running"})

    events = result[0] if result else []
    summary = []
    total_secs = 0
    for e in events:
        app = e.get("data", {}).get("app", "unknown")
        dur = e.get("duration", 0)
        if dur > 0:
            summary.append({"app": app, "minutes": round(dur / 60, 1)})
            total_secs += dur

    return json.dumps({
        "date": date or datetime.now(TZ).strftime("%Y-%m-%d"),
        "total_tracked_minutes": round(total_secs / 60, 1),
        "by_app": summary,
    })


@mcp.tool()
def aw_web_usage(date: str | None = None) -> str:
    """Get browser tab usage summary for a given date (server-side aggregated).

    Returns time spent per domain and top pages visited.

    Args:
        date: Date in YYYY-MM-DD format (default: today)
    """
    period = _day_period(date)

    # Aggregate by URL (title + url)
    query = f"""
events = query_bucket("{BUCKET_WEB}");
events = merge_events_by_keys(events, ["url", "title"]);
events = sort_by_duration(events);
RETURN = events;
"""
    result = _aw_query(query.strip(), [period])
    if result is None:
        return json.dumps({"error": "ActivityWatch not running or no web watcher"})

    events = result[0] if result else []

    from urllib.parse import urlparse
    domain_time: dict[str, float] = {}
    top_pages = []
    for e in events:
        data = e.get("data", {})
        url = data.get("url", "")
        title = data.get("title", "")
        dur = e.get("duration", 0)
        try:
            domain = urlparse(url).netloc
        except Exception:
            domain = "unknown"
        domain_time[domain] = domain_time.get(domain, 0) + dur
        if dur > 0 and len(top_pages) < 20:
            top_pages.append({"page": f"{title[:80]} | {domain}", "minutes": round(dur / 60, 1)})

    sorted_domains = sorted(domain_time.items(), key=lambda x: -x[1])

    return json.dumps({
        "date": date or datetime.now(TZ).strftime("%Y-%m-%d"),
        "by_domain": [{"domain": d, "minutes": round(s / 60, 1)} for d, s in sorted_domains if s > 0][:30],
        "top_pages": top_pages,
    })


@mcp.tool()
def aw_afk_summary(date: str | None = None) -> str:
    """Get active vs AFK (away from keyboard) time for a given date (server-side aggregated).

    Args:
        date: Date in YYYY-MM-DD format (default: today)
    """
    period = _day_period(date)
    query = f"""
events = query_bucket("{BUCKET_AFK}");
events = merge_events_by_keys(events, ["status"]);
RETURN = events;
"""
    result = _aw_query(query.strip(), [period])
    if result is None:
        return json.dumps({"error": "ActivityWatch not running"})

    events = result[0] if result else []
    active_secs = 0
    afk_secs = 0
    for e in events:
        status = e.get("data", {}).get("status", "")
        dur = e.get("duration", 0)
        if status == "not-afk":
            active_secs += dur
        else:
            afk_secs += dur

    return json.dumps({
        "date": date or datetime.now(TZ).strftime("%Y-%m-%d"),
        "active_minutes": round(active_secs / 60, 1),
        "afk_minutes": round(afk_secs / 60, 1),
        "total_tracked_minutes": round((active_secs + afk_secs) / 60, 1),
    })


@mcp.tool()
def aw_timeline(date: str | None = None, min_duration_secs: int = 60) -> str:
    """Get a chronological timeline of app usage for a given date.

    Useful for reconstructing what the user did throughout the day.
    Uses raw events (sorted by time) since timeline needs temporal ordering.

    Args:
        date: Date in YYYY-MM-DD format (default: today)
        min_duration_secs: Minimum event duration to include (default 60s)
    """
    if date:
        dt = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=TZ)
        start = dt.replace(hour=0, minute=0, second=0).isoformat()
        end = dt.replace(hour=23, minute=59, second=59).isoformat()
    else:
        now = datetime.now(TZ)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        end = now.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()

    events = _aw_get(f"/buckets/{BUCKET_WINDOW}/events?start={start}&end={end}&limit=10000")
    if events is None:
        return json.dumps({"error": "ActivityWatch not running"})

    # Filter and format
    timeline = []
    for e in events:
        dur = e.get("duration", 0)
        if dur < min_duration_secs:
            continue
        ts = e.get("timestamp", "")
        data = e.get("data", {})
        try:
            t = datetime.fromisoformat(ts).astimezone(TZ).strftime("%H:%M")
        except Exception:
            t = ts[:16]
        timeline.append({
            "time": t,
            "app": data.get("app", ""),
            "title": data.get("title", "")[:100],
            "minutes": round(dur / 60, 1),
        })

    # Events come newest-first, reverse for chronological
    timeline.reverse()

    return json.dumps({
        "date": date or datetime.now(TZ).strftime("%Y-%m-%d"),
        "events": timeline,
    })


@mcp.tool()
def aw_ensure_running() -> str:
    """Check if ActivityWatch is running, and start it if not."""
    buckets = _aw_get("/buckets/")
    if buckets is not None:
        return json.dumps({"status": "already_running", "buckets": len(buckets)})

    # Try to start it
    subprocess.Popen(["open", "-a", "ActivityWatch"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return json.dumps({"status": "starting", "message": "ActivityWatch is being launched. It may take a few seconds to initialize."})


if __name__ == "__main__":
    mcp.run(transport="stdio")
