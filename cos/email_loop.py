import time
from typing import Any

from . import config
from .agent import run_turn
from .google_auth import gmail_service
from .tools.gmail import read_email, send_email


SYSTEM_NOTE = (
    "The following is an email from {user_name} sent to your agent inbox. "
    "Treat it as a chat message. Take any actions they ask. Then craft a reply email — "
    "but DO NOT call send_email yourself; just write the reply as your final text. "
    "The framework will send it.\n\n"
    "From: {frm}\nSubject: {subj}\n\n{body}"
)


def _list_unread(svc) -> list[dict[str, Any]]:
    res = svc.users().messages().list(
        userId="me",
        q=f"is:unread to:{config.AGENT_EMAIL} OR is:unread -from:me",
        maxResults=10,
    ).execute()
    return res.get("messages", [])


def _process_one(msg_id: str) -> None:
    email = read_email(msg_id, account="agent")
    frm = email.get("from", "")
    # Only respond to the configured user, ignore spam/randoms
    if config.USER_EMAIL and config.USER_EMAIL.lower() not in frm.lower():
        _mark_read(msg_id)
        return
    prompt = SYSTEM_NOTE.format(
        user_name=config.USER_NAME,
        frm=frm,
        subj=email.get("subject", ""),
        body=email.get("body", "")[:8000],
    )
    reply_text, _ = run_turn(prompt)
    if reply_text.strip():
        subj = email.get("subject", "")
        if not subj.lower().startswith("re:"):
            subj = "Re: " + subj
        send_email(
            to=config.USER_EMAIL,
            subject=subj,
            body=reply_text,
            in_reply_to_thread_id=email.get("thread_id"),
            account="agent",
        )
    _mark_read(msg_id)


def _mark_read(msg_id: str) -> None:
    svc = gmail_service("agent")
    svc.users().messages().modify(
        userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
    ).execute()


def run_loop(once: bool = False) -> None:
    print(f"[email-loop] polling {config.AGENT_EMAIL} every {config.EMAIL_POLL_SECONDS}s")
    while True:
        try:
            svc = gmail_service("agent")
            for m in _list_unread(svc):
                print(f"[email-loop] processing {m['id']}")
                try:
                    _process_one(m["id"])
                except Exception as e:
                    print(f"[email-loop] error on {m['id']}: {e}")
        except Exception as e:
            print(f"[email-loop] poll error: {e}")
        if once:
            return
        time.sleep(config.EMAIL_POLL_SECONDS)
