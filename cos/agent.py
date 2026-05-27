from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from anthropic import Anthropic
from zoneinfo import ZoneInfo

from . import config
from .tools import TOOL_SCHEMAS, dispatch

_SYSTEM_PATH = Path(__file__).parent / "prompts" / "system.md"


def _system_prompt() -> str:
    tmpl = _SYSTEM_PATH.read_text()
    today = datetime.now(ZoneInfo(config.USER_TIMEZONE)).strftime("%A, %B %d, %Y")
    return tmpl.format(user_name=config.USER_NAME, today=today, timezone=config.USER_TIMEZONE)


_client: Anthropic | None = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        if not config.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to .env.")
        _client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def _content_to_dict(content_blocks) -> list[dict[str, Any]]:
    out = []
    for b in content_blocks:
        if b.type == "text":
            out.append({"type": "text", "text": b.text})
        elif b.type == "tool_use":
            out.append({"type": "tool_use", "id": b.id, "name": b.name, "input": b.input})
    return out


def run_turn(user_input: str, history: list[dict[str, Any]] | None = None,
             on_tool: callable | None = None, max_iters: int = 12) -> tuple[str, list[dict]]:
    """Run one user turn through Claude with tool use until the model stops."""
    history = list(history or [])
    history.append({"role": "user", "content": user_input})
    client = _get_client()
    tools = list(TOOL_SCHEMAS)
    system = [{
        "type": "text",
        "text": _system_prompt(),
        "cache_control": {"type": "ephemeral"},
    }]

    for _ in range(max_iters):
        resp = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=4096,
            system=system,
            tools=tools,
            messages=history,
        )
        history.append({"role": "assistant", "content": _content_to_dict(resp.content)})

        if resp.stop_reason != "tool_use":
            text = "".join(b.text for b in resp.content if b.type == "text")
            return text.strip(), history

        tool_results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            if on_tool:
                on_tool(block.name, block.input)
            result = dispatch(block.name, dict(block.input))
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": _stringify(result),
            })
        history.append({"role": "user", "content": tool_results})

    return "(stopped: tool iteration limit reached)", history


def _stringify(result: Any) -> str:
    import json
    try:
        return json.dumps(result, default=str)[:30000]
    except Exception:
        return str(result)[:30000]
