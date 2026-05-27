from __future__ import annotations

import os
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


_TRAILING_JUNK = re.compile(r"\s*(?:[←#]|//).*$")


def _clean(v: str) -> str:
    if not v:
        return v
    return _TRAILING_JUNK.sub("", v).strip().strip('"').strip("'")


def _get(name: str, default: str = "") -> str:
    return _clean(os.getenv(name, default))


def _expand(p: str) -> Path:
    return Path(os.path.expanduser(os.path.expandvars(_clean(p))))


ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = _get("CLAUDE_MODEL", "claude-opus-4-7")
CLAUDE_FAST_MODEL = _get("CLAUDE_FAST_MODEL", "claude-haiku-4-5-20251001")

USER_NAME = _get("USER_NAME", "friend")
USER_EMAIL = _get("USER_EMAIL", "")
USER_TIMEZONE = _get("USER_TIMEZONE", "America/Los_Angeles")
AGENT_EMAIL = _get("AGENT_EMAIL", USER_EMAIL)

DATA_DIR = _expand(os.getenv("COS_DATA_DIR", "~/.local/share/cos"))
DB_PATH = DATA_DIR / "cos.db"
JOURNAL_DIR = DATA_DIR / "journal"
TOKEN_DIR = DATA_DIR / "tokens"
CONFIG_DIR = _expand("~/.config/cos")

GOOGLE_OAUTH_CLIENT_SECRETS = _expand(
    os.getenv("GOOGLE_OAUTH_CLIENT_SECRETS", str(CONFIG_DIR / "google_client_secrets.json"))
)

EMAIL_POLL_SECONDS = int(_get("EMAIL_POLL_SECONDS", "120"))
BRIEFING_HOUR = int(_get("BRIEFING_HOUR", "7"))
JOURNAL_REMINDER_HOUR = int(_get("JOURNAL_REMINDER_HOUR", "21"))


def ensure_dirs() -> None:
    for d in (DATA_DIR, JOURNAL_DIR, TOKEN_DIR, CONFIG_DIR):
        d.mkdir(parents=True, exist_ok=True)
