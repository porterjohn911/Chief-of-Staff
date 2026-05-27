from __future__ import annotations

from typing import Any, Callable

_TOOLS: dict[str, Callable[..., Any]] = {}
_SCHEMAS: list[dict[str, Any]] = []


def tool(name: str, description: str, input_schema: dict[str, Any]):
    """Register a function as a Claude-callable tool."""
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        _TOOLS[name] = fn
        _SCHEMAS.append({
            "name": name,
            "description": description,
            "input_schema": input_schema,
        })
        return fn
    return decorator


def dispatch(name: str, inputs: dict[str, Any]) -> Any:
    if name not in _TOOLS:
        return {"error": f"Unknown tool: {name}"}
    try:
        return _TOOLS[name](**inputs)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


# Lazy property so tools register on import before this is read
class _Schemas(list):
    def __iter__(self):
        return iter(_SCHEMAS)

    def __len__(self):
        return len(_SCHEMAS)

    def __getitem__(self, i):
        return _SCHEMAS[i]


TOOL_SCHEMAS = _Schemas()
