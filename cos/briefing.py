from datetime import datetime
from zoneinfo import ZoneInfo

from . import config
from .agent import run_turn
from .tools.gmail import send_email

BRIEFING_PROMPT = """\
Generate {user}'s morning briefing for {date}. Use your tools to pull live data — don't make anything up.

Structure the briefing as concise sections:

1. **Today's calendar** — list events with times. Flag back-to-back meetings.
2. **Inbox** — list_emails on the user's account for unread newer_than:1d. Summarize what's important and what can be ignored.
3. **Tasks** — list_tasks status=open due_before=<today+2 days>. Highlight what's due today.
4. **Health check-in** — health_summary days=7. Note any concerning trends or wins.
5. **People to reach out to** — who_to_reach_out_to. Name them, suggest a simple opener for one.
6. **One thing** — your pick of the single most important thing for the user today.

Keep it tight. {user} should read this in under 60 seconds.
After you've gathered the data, do NOT call any more tools — just write the briefing as your final message.
"""


def generate_briefing() -> str:
    today = datetime.now(ZoneInfo(config.USER_TIMEZONE)).strftime("%A, %B %d, %Y")
    text, _ = run_turn(BRIEFING_PROMPT.format(user=config.USER_NAME, date=today))
    return text


def send_briefing() -> dict:
    body = generate_briefing()
    today = datetime.now(ZoneInfo(config.USER_TIMEZONE)).strftime("%a %b %d")
    if not config.USER_EMAIL:
        return {"sent": False, "body": body, "reason": "USER_EMAIL not set"}
    return send_email(
        to=config.USER_EMAIL,
        subject=f"Your morning briefing — {today}",
        body=body,
        account="agent" if config.AGENT_EMAIL != config.USER_EMAIL else "user",
    )
