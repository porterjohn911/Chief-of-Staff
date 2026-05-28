from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    TextBlock,
    create_sdk_mcp_server,
    query,
    tool as sdk_tool,
)
from zoneinfo import ZoneInfo

from . import config
from .tools import gmail, calendar, health, projects, journal, relationships  # noqa: F401  (imports register tools)
from .tools.registry import _SCHEMAS, _TOOLS

_SYSTEM_PATH = Path(__file__).parent / "prompts" / "system.md"

_JSON_TO_PY = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def _system_prompt() -> str:
    tmpl = _SYSTEM_PATH.read_text()
    today = datetime.now(ZoneInfo(config.USER_TIMEZONE)).strftime("%A, %B %d, %Y")
    return tmpl.format(user_name=config.USER_NAME, today=today, timezone=config.USER_TIMEZONE)


def _make_tool(name: str, desc: str, fn, props: dict):
    py_schema = {k: _JSON_TO_PY.get(v.get("type", "string"), str) for k, v in props.items()}

    @sdk_tool(name, desc, py_schema)
    async def _wrapper(args: dict[str, Any]) -> dict[str, Any]:
        try:
            result = fn(**args)
        except Exception as e:
            result = {"error": f"{type(e).__name__}: {e}"}
        return {"content": [{"type": "text", "text": json.dumps(result, default=str)[:30000]}]}

    return _wrapper


def _build_server():
    tools = []
    for schema in _SCHEMAS:
        name = schema["name"]
        desc = schema["description"]
        props = schema["input_schema"].get("properties", {})
        fn = _TOOLS[name]
        tools.append(_make_tool(name, desc, fn, props))
    return create_sdk_mcp_server(name="cos", version="0.1.0", tools=tools)


def _options() -> ClaudeAgentOptions:
    server = _build_server()
    allowed = [f"mcp__cos__{s['name']}" for s in _SCHEMAS]
    return ClaudeAgentOptions(
        system_prompt=_system_prompt(),
        mcp_servers={"cos": server},
        allowed_tools=allowed,
        permission_mode="acceptEdits",
    )


async def _run_async(prompt: str, on_tool=None) -> str:
    final: list[str] = []
    options = _options()
    async for msg in query(prompt=prompt, options=options):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    final.append(block.text)
                elif on_tool and hasattr(block, "name") and hasattr(block, "input"):
                    try:
                        on_tool(block.name, block.input)
                    except Exception:
                        pass
    return "".join(final).strip()


def run_turn(user_input: str, history=None, on_tool=None, max_iters: int = 12):
    """Sync wrapper around the SDK's async query.

    History is currently not threaded across turns — each call is its own
    session. Conversational continuity within `cos chat` is limited; persistent
    state (tasks, journal, contacts, health logs) lives in SQLite so it carries
    across turns through tool calls.
    """
    text = asyncio.run(_run_async(user_input, on_tool))
    return text, history or []
