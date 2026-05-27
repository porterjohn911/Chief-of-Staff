from datetime import date as _date, timedelta

from ..storage import connect, now
from .registry import tool


@tool(
    name="add_contact",
    description=(
        "Add or update a contact in the relationship tracker. "
        "cadence_days is how often you want to be reminded to reach out (e.g. 30 for monthly)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "email": {"type": "string"},
            "phone": {"type": "string"},
            "relationship": {"type": "string", "description": "e.g. friend, family, mentor, colleague"},
            "notes": {"type": "string"},
            "cadence_days": {"type": "integer"},
        },
        "required": ["name"],
    },
)
def add_contact(name: str, email: str = "", phone: str = "", relationship: str = "",
                notes: str = "", cadence_days: int | None = None):
    with connect() as c:
        c.execute(
            "INSERT INTO contacts (name, email, phone, relationship, notes, cadence_days, created_at) "
            "VALUES (?,?,?,?,?,?,?) "
            "ON CONFLICT(name) DO UPDATE SET email=excluded.email, phone=excluded.phone, "
            "relationship=excluded.relationship, notes=excluded.notes, cadence_days=excluded.cadence_days",
            (name, email, phone, relationship, notes, cadence_days, now()),
        )
    return {"saved": True, "name": name}


@tool(
    name="log_contact",
    description="Record that you connected with someone today (or on a given date).",
    input_schema={
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "date": {"type": "string", "description": "YYYY-MM-DD"},
            "notes": {"type": "string"},
        },
        "required": ["name"],
    },
)
def log_contact(name: str, date: str | None = None, notes: str = ""):
    d = date or _date.today().isoformat()
    with connect() as c:
        row = c.execute("SELECT id, notes FROM contacts WHERE name = ?", (name,)).fetchone()
        if not row:
            c.execute(
                "INSERT INTO contacts (name, last_contact, notes, created_at) VALUES (?,?,?,?)",
                (name, d, notes, now()),
            )
        else:
            combined = (row["notes"] or "")
            if notes:
                combined = (combined + f"\n[{d}] {notes}").strip()
            c.execute(
                "UPDATE contacts SET last_contact = ?, notes = ? WHERE id = ?",
                (d, combined, row["id"]),
            )
    return {"logged": True, "name": name, "date": d}


@tool(
    name="list_contacts",
    description="List all tracked contacts.",
    input_schema={"type": "object", "properties": {}},
)
def list_contacts():
    with connect() as c:
        rows = c.execute("SELECT * FROM contacts ORDER BY name").fetchall()
    return {"contacts": [dict(r) for r in rows]}


@tool(
    name="who_to_reach_out_to",
    description=(
        "Surface contacts who are overdue for outreach based on their cadence_days. "
        "Returns each with how many days overdue."
    ),
    input_schema={"type": "object", "properties": {}},
)
def who_to_reach_out_to():
    today = _date.today()
    overdue = []
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM contacts WHERE cadence_days IS NOT NULL"
        ).fetchall()
    for r in rows:
        last = r["last_contact"]
        cad = r["cadence_days"]
        if not last:
            overdue.append({**dict(r), "days_overdue": None, "reason": "never contacted"})
            continue
        try:
            last_d = _date.fromisoformat(last)
        except Exception:
            continue
        gap = (today - last_d).days
        if gap >= cad:
            overdue.append({**dict(r), "days_overdue": gap - cad})
    overdue.sort(key=lambda x: (x["days_overdue"] is None, -(x["days_overdue"] or 0)), reverse=False)
    return {"overdue": overdue, "count": len(overdue)}
