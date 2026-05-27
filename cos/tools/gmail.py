import base64
from email.message import EmailMessage
from typing import Any

from .. import config
from ..google_auth import gmail_service
from .registry import tool


def _decode(data: str) -> str:
    return base64.urlsafe_b64decode(data.encode()).decode(errors="replace")


def _extract_body(payload: dict[str, Any]) -> str:
    if payload.get("body", {}).get("data"):
        return _decode(payload["body"]["data"])
    for part in payload.get("parts", []) or []:
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return _decode(part["body"]["data"])
    for part in payload.get("parts", []) or []:
        body = _extract_body(part)
        if body:
            return body
    return ""


@tool(
    name="list_emails",
    description=(
        "List recent emails from a Gmail inbox. Returns sender, subject, snippet, "
        "and Gmail message id. Use account='user' for the user's inbox or "
        "account='agent' for the agent's own inbox."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Gmail search query, e.g. 'is:unread newer_than:1d -from:me'",
            },
            "max_results": {"type": "integer", "default": 10},
            "account": {"type": "string", "enum": ["user", "agent"], "default": "user"},
        },
    },
)
def list_emails(query: str = "is:unread newer_than:1d", max_results: int = 10, account: str = "user"):
    svc = gmail_service(account)
    res = svc.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    msgs = res.get("messages", [])
    out = []
    for m in msgs:
        full = svc.users().messages().get(userId="me", id=m["id"], format="metadata",
                                          metadataHeaders=["From", "Subject", "Date"]).execute()
        headers = {h["name"]: h["value"] for h in full["payload"].get("headers", [])}
        out.append({
            "id": full["id"],
            "thread_id": full["threadId"],
            "from": headers.get("From", ""),
            "subject": headers.get("Subject", "(no subject)"),
            "date": headers.get("Date", ""),
            "snippet": full.get("snippet", ""),
            "unread": "UNREAD" in full.get("labelIds", []),
        })
    return {"emails": out, "count": len(out)}


@tool(
    name="read_email",
    description="Read the full body of a Gmail message by id.",
    input_schema={
        "type": "object",
        "properties": {
            "message_id": {"type": "string"},
            "account": {"type": "string", "enum": ["user", "agent"], "default": "user"},
        },
        "required": ["message_id"],
    },
)
def read_email(message_id: str, account: str = "user"):
    svc = gmail_service(account)
    full = svc.users().messages().get(userId="me", id=message_id, format="full").execute()
    headers = {h["name"]: h["value"] for h in full["payload"].get("headers", [])}
    return {
        "id": full["id"],
        "thread_id": full["threadId"],
        "from": headers.get("From", ""),
        "to": headers.get("To", ""),
        "subject": headers.get("Subject", ""),
        "date": headers.get("Date", ""),
        "body": _extract_body(full["payload"])[:20000],
    }


@tool(
    name="send_email",
    description=(
        "Send an email. By default sends from the agent's email account. "
        "Use account='user' to send from the user's own account."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Recipient email, comma-separated for multiple"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
            "cc": {"type": "string"},
            "in_reply_to_thread_id": {
                "type": "string",
                "description": "Gmail thread id to reply within (keeps the thread).",
            },
            "account": {"type": "string", "enum": ["user", "agent"], "default": "agent"},
        },
        "required": ["to", "subject", "body"],
    },
)
def send_email(to: str, subject: str, body: str, cc: str | None = None,
               in_reply_to_thread_id: str | None = None, account: str = "agent"):
    svc = gmail_service(account)
    msg = EmailMessage()
    msg["To"] = to
    if cc:
        msg["Cc"] = cc
    msg["Subject"] = subject
    msg["From"] = config.AGENT_EMAIL if account == "agent" else config.USER_EMAIL
    msg.set_content(body)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    payload: dict[str, Any] = {"raw": raw}
    if in_reply_to_thread_id:
        payload["threadId"] = in_reply_to_thread_id
    result = svc.users().messages().send(userId="me", body=payload).execute()
    return {"sent": True, "id": result.get("id"), "thread_id": result.get("threadId")}


@tool(
    name="mark_email_read",
    description="Mark an email as read.",
    input_schema={
        "type": "object",
        "properties": {
            "message_id": {"type": "string"},
            "account": {"type": "string", "enum": ["user", "agent"], "default": "user"},
        },
        "required": ["message_id"],
    },
)
def mark_email_read(message_id: str, account: str = "user"):
    svc = gmail_service(account)
    svc.users().messages().modify(
        userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
    ).execute()
    return {"ok": True}
