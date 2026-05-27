from __future__ import annotations

from datetime import datetime, timedelta, timezone as _tz
from zoneinfo import ZoneInfo

from dateutil import parser as dtparser

from .. import config
from ..google_auth import calendar_service
from .registry import tool


def _tz_now() -> datetime:
    return datetime.now(ZoneInfo(config.USER_TIMEZONE))


@tool(
    name="list_calendar_events",
    description="List upcoming calendar events from the user's primary calendar.",
    input_schema={
        "type": "object",
        "properties": {
            "days_ahead": {"type": "integer", "default": 7},
            "max_results": {"type": "integer", "default": 20},
        },
    },
)
def list_calendar_events(days_ahead: int = 7, max_results: int = 20):
    svc = calendar_service("user")
    now = _tz_now()
    end = now + timedelta(days=days_ahead)
    events = svc.events().list(
        calendarId="primary",
        timeMin=now.astimezone(_tz.utc).isoformat(),
        timeMax=end.astimezone(_tz.utc).isoformat(),
        singleEvents=True,
        orderBy="startTime",
        maxResults=max_results,
    ).execute()
    out = []
    for e in events.get("items", []):
        start = e["start"].get("dateTime") or e["start"].get("date")
        end_ = e["end"].get("dateTime") or e["end"].get("date")
        out.append({
            "id": e["id"],
            "summary": e.get("summary", "(untitled)"),
            "start": start,
            "end": end_,
            "location": e.get("location"),
            "attendees": [a.get("email") for a in e.get("attendees", [])],
            "description": (e.get("description") or "")[:500],
        })
    return {"events": out, "count": len(out)}


@tool(
    name="create_calendar_event",
    description=(
        "Create a new calendar event on the user's primary calendar. "
        "Times should be ISO 8601 in the user's timezone (e.g. 2026-05-28T15:00)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "start": {"type": "string", "description": "ISO datetime or YYYY-MM-DD for all-day"},
            "end": {"type": "string", "description": "ISO datetime or YYYY-MM-DD"},
            "description": {"type": "string"},
            "location": {"type": "string"},
            "attendees": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Email addresses to invite",
            },
        },
        "required": ["summary", "start", "end"],
    },
)
def create_calendar_event(summary: str, start: str, end: str,
                          description: str = "", location: str = "",
                          attendees: list[str] | None = None):
    svc = calendar_service("user")
    tz = config.USER_TIMEZONE

    def _slot(s: str) -> dict:
        if "T" in s:
            dt = dtparser.parse(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo(tz))
            return {"dateTime": dt.isoformat(), "timeZone": tz}
        return {"date": s}

    body = {
        "summary": summary,
        "description": description,
        "location": location,
        "start": _slot(start),
        "end": _slot(end),
    }
    if attendees:
        body["attendees"] = [{"email": e} for e in attendees]
    created = svc.events().insert(calendarId="primary", body=body,
                                  sendUpdates="all" if attendees else "none").execute()
    return {
        "created": True,
        "id": created["id"],
        "link": created.get("htmlLink"),
        "summary": created.get("summary"),
        "start": created["start"],
    }


@tool(
    name="delete_calendar_event",
    description="Delete a calendar event by id.",
    input_schema={
        "type": "object",
        "properties": {"event_id": {"type": "string"}},
        "required": ["event_id"],
    },
)
def delete_calendar_event(event_id: str):
    svc = calendar_service("user")
    svc.events().delete(calendarId="primary", eventId=event_id).execute()
    return {"deleted": True}
