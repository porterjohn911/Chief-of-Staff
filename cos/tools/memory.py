from __future__ import annotations

from ..memory import append_memory, read_memory, replace_memory
from .registry import tool


@tool(
    name="remember",
    description=(
        "Save a fact about the user to long-term memory. Use this whenever the "
        "user mentions something worth recalling in future sessions: preferences, "
        "important people, ongoing projects, values, recurring frustrations, "
        "goals, health context, anything that helps you be a better Chief of Staff "
        "over time. Each call appends one fact — keep them short and durable."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "fact": {
                "type": "string",
                "description": "A single concise fact, written as a complete sentence.",
            },
        },
        "required": ["fact"],
    },
)
def remember(fact: str):
    line = append_memory(fact)
    return {"saved": True, "line": line.strip()}


@tool(
    name="recall_memory",
    description=(
        "Read back everything currently stored in long-term memory. Use this if "
        "the user asks what you remember, or if you want to refresh your context."
    ),
    input_schema={"type": "object", "properties": {}},
)
def recall_memory():
    content = read_memory()
    return {"memory": content or "(empty)"}


@tool(
    name="rewrite_memory",
    description=(
        "Replace the entire long-term memory file with new content. Use this to "
        "consolidate, condense, or correct memory. Pass the full new markdown "
        "content — do NOT use this for small additions (use `remember` instead)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "content": {"type": "string"},
        },
        "required": ["content"],
    },
)
def rewrite_memory(content: str):
    replace_memory(content)
    return {"rewritten": True, "chars": len(content)}
