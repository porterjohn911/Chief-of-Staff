from datetime import date as _date, timedelta

from ..storage import connect, now
from .registry import tool

KNOWN_METRICS = {
    "weight": "lbs",
    "sleep_hours": "hours",
    "workout": "minutes",
    "water": "oz",
    "steps": "count",
    "mood": "1-10",
    "energy": "1-10",
    "meds": "yes/no",
}


@tool(
    name="log_health",
    description=(
        "Log a health metric for a given day (default today). "
        f"Common metrics: {', '.join(KNOWN_METRICS)}. Use any metric name you like."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "metric": {"type": "string"},
            "value": {"type": "number"},
            "unit": {"type": "string"},
            "notes": {"type": "string"},
            "date": {"type": "string", "description": "YYYY-MM-DD, defaults to today"},
        },
        "required": ["metric", "value"],
    },
)
def log_health(metric: str, value: float, unit: str | None = None,
               notes: str = "", date: str | None = None):
    d = date or _date.today().isoformat()
    unit = unit or KNOWN_METRICS.get(metric, "")
    with connect() as c:
        c.execute(
            "INSERT INTO health_logs (date, metric, value, unit, notes, ts) VALUES (?,?,?,?,?,?)",
            (d, metric, value, unit, notes, now()),
        )
    return {"logged": True, "date": d, "metric": metric, "value": value, "unit": unit}


@tool(
    name="health_summary",
    description="Get a summary of recent health metrics over the last N days.",
    input_schema={
        "type": "object",
        "properties": {
            "days": {"type": "integer", "default": 7},
            "metric": {"type": "string", "description": "Optional filter to one metric"},
        },
    },
)
def health_summary(days: int = 7, metric: str | None = None):
    since = (_date.today() - timedelta(days=days)).isoformat()
    with connect() as c:
        if metric:
            rows = c.execute(
                "SELECT date, metric, value, unit, notes FROM health_logs "
                "WHERE date >= ? AND metric = ? ORDER BY date DESC",
                (since, metric),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT date, metric, value, unit, notes FROM health_logs "
                "WHERE date >= ? ORDER BY date DESC, metric",
                (since,),
            ).fetchall()
    entries = [dict(r) for r in rows]
    by_metric: dict[str, list] = {}
    for e in entries:
        by_metric.setdefault(e["metric"], []).append(e["value"])
    averages = {m: round(sum(vs) / len(vs), 2) for m, vs in by_metric.items() if vs}
    return {"days": days, "entries": entries, "averages": averages}
