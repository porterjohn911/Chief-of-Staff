from __future__ import annotations

from datetime import datetime

from . import config

MEMORY_HEADER = "# Things to remember about the user\n\n"


def memory_path():
    return config.DATA_DIR / "memory.md"


def read_memory() -> str:
    config.ensure_dirs()
    p = memory_path()
    if not p.exists():
        return ""
    return p.read_text()


def append_memory(fact: str) -> str:
    config.ensure_dirs()
    p = memory_path()
    existing = p.read_text() if p.exists() else ""
    if not existing:
        existing = MEMORY_HEADER
    stamp = datetime.now().strftime("%Y-%m-%d")
    line = f"- [{stamp}] {fact.strip()}\n"
    p.write_text(existing + line)
    return line


def replace_memory(content: str) -> None:
    config.ensure_dirs()
    if not content.startswith("#"):
        content = MEMORY_HEADER + content
    memory_path().write_text(content)


def clear_memory() -> None:
    p = memory_path()
    if p.exists():
        p.unlink()
