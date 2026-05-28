from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    TextBlock,
    create_sdk_mcp_server,
    query,
    tool as sdk_tool,
)
from zoneinfo import ZoneInfo

from . import config
from .memory import read_memory
from .tools import gmail, calendar, health, projects, journal, relationships, memory as memory_tools  # noqa: F401
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
    base = tmpl.format(user_name=config.USER_NAME, today=today, timezone=config.USER_TIMEZONE)
    mem = read_memory()
    if mem.strip():
        base += "\n\n---\n\n" + mem.strip() + "\n"
    return base


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
    """One-shot query. Each call is its own session. Use AgentSession for multi-turn."""
    text = asyncio.run(_run_async(user_input, on_tool))
    return text, history or []


class AgentSession:
    """Multi-turn chat session. The SDK client preserves conversation history
    across `send()` calls. Long-term memory.md is loaded into the system prompt
    once at session start.

    Usage:
        with AgentSession(on_tool=cb) as s:
            print(s.send("hello"))
            print(s.send("what did i just say?"))
    """

    def __init__(self, on_tool=None):
        self.on_tool = on_tool
        self._client: ClaudeSDKClient | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def __enter__(self) -> AgentSession:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._start())
        return self

    async def _start(self) -> None:
        self._client = ClaudeSDKClient(options=_options())
        await self._client.__aenter__()

    def send(self, user_input: str) -> str:
        assert self._loop is not None
        return self._loop.run_until_complete(self._send(user_input))

    async def _send(self, user_input: str) -> str:
        assert self._client is not None
        await self._client.query(user_input)
        final: list[str] = []
        async for msg in self._client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        final.append(block.text)
                    elif self.on_tool and hasattr(block, "name") and hasattr(block, "input"):
                        try:
                            self.on_tool(block.name, block.input)
                        except Exception:
                            pass
        return "".join(final).strip()

    def __exit__(self, exc_type, exc, tb):
        if self._client is not None and self._loop is not None:
            self._loop.run_until_complete(self._client.__aexit__(exc_type, exc, tb))
        if self._loop is not None:
            self._loop.close()
