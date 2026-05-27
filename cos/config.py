from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def _expand(p: str) -> Path:
    return Path(os.path.expanduser(os.path.expandvars(p)))


ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-4-7")
CLAUDE_FAST_MODEL = os.getenv("CLAUDE_FAST_MODEL", "claude-haiku-4-5-20251001")

USER_NAME = os.getenv("USER_NAME", "friend")
USER_EMAIL = os.getenv("USER_EMAIL", "")
USER_TIMEZONE = os.getenv("USER_TIMEZONE", "America/Los_Angeles")
AGENT_EMAIL = os.getenv("AGENT_EMAIL", USER_EMAIL)

DATA_DIR = _expand(os.getenv("COS_DATA_DIR", "~/.local/share/cos"))
DB_PATH = DATA_DIR / "cos.db"
JOURNAL_DIR = DATA_DIR / "journal"
TOKEN_DIR = DATA_DIR / "tokens"
CONFIG_DIR = _expand("~/.config/cos")

GOOGLE_OAUTH_CLIENT_SECRETS = _expand(
    os.getenv("GOOGLE_OAUTH_CLIENT_SECRETS", str(CONFIG_DIR / "google_client_secrets.json"))
)

EMAIL_POLL_SECONDS = int(os.getenv("EMAIL_POLL_SECONDS", "120"))
BRIEFING_HOUR = int(os.getenv("BRIEFING_HOUR", "7"))
JOURNAL_REMINDER_HOUR = int(os.getenv("JOURNAL_REMINDER_HOUR", "21"))


def ensure_dirs() -> None:
    for d in (DATA_DIR, JOURNAL_DIR, TOKEN_DIR, CONFIG_DIR):
        d.mkdir(parents=True, exist_ok=True)
