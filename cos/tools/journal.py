from __future__ import annotations

from datetime import date as _date, timedelta

from .. import config
from ..storage import connect, now
from .registry import tool

DEFAULT_PROMPTS = [
    "What's one thing you're proud of from today?",
    "What's draining you right now, and what's one step you could take to lower it?",
    "Who came to mind today that you should reach out to?",
    "What's the highest-leverage thing you could do tomorrow?",
    "What did you avoid today that you shouldn't have?",
    "What's working better than you expected?",
    "What's one belief you're holding that might be wrong?",
]


def _path_for(d: str):
    return config.JOURNAL_DIR / f"{d}.md"


@tool(
    name="save_journal_entry",
    description="Save a journal entry. One per day (upserts on date).",
    input_schema={
        "type": "object",
        "properties": {
            "content": {"type": "string"},
            "date": {"type": "string", "description": "YYYY-MM-DD, defaults to today"},
            "prompt": {"type": "string"},
            "mood": {"type": "integer", "description": "1-10"},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["content"],
    },
)
def save_journal_entry(content: str, date: str | None = None, prompt: str = "",
                       mood: int | None = None, tags: list[str] | None = None):
    config.ensure_dirs()
    d = date or _date.today().isoformat()
    tag_str = ",".join(tags or [])
    with connect() as c:
        c.execute(
            "INSERT INTO journal_entries (date, prompt, content, mood, tags, ts) "
            "VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(date) DO UPDATE SET prompt=excluded.prompt, content=excluded.content, "
            "mood=excluded.mood, tags=excluded.tags, ts=excluded.ts",
            (d, prompt, content, mood, tag_str, now()),
        )
    md = f"# {d}\n\n"
    if prompt:
        md += f"**Prompt:** {prompt}\n\n"
    if mood is not None:
        md += f"**Mood:** {mood}/10\n\n"
    if tags:
        md += f"**Tags:** {', '.join(tags)}\n\n"
    md += content + "\n"
    _path_for(d).write_text(md)
    return {"saved": True, "date": d, "path": str(_path_for(d))}


@tool(
    name="get_journal_entries",
    description="Get recent journal entries.",
    input_schema={
        "type": "object",
        "properties": {
            "days": {"type": "integer", "default": 14},
            "limit": {"type": "integer", "default": 14},
        },
    },
)
def get_journal_entries(days: int = 14, limit: int = 14):
    since = (_date.today() - timedelta(days=days)).isoformat()
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM journal_entries WHERE date >= ? ORDER BY date DESC LIMIT ?",
            (since, limit),
        ).fetchall()
    return {"entries": [dict(r) for r in rows]}


@tool(
    name="get_journal_prompt",
    description="Get a thoughtful journal prompt for today.",
    input_schema={"type": "object", "properties": {}},
)
def get_journal_prompt():
    import random
    return {"prompt": random.choice(DEFAULT_PROMPTS)}
