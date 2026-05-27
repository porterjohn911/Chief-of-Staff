from __future__ import annotations

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from . import config

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
]


def _token_path(account: str) -> Path:
    return config.TOKEN_DIR / f"{account}_token.json"


def get_credentials(account: str = "user") -> Credentials:
    config.ensure_dirs()
    token_file = _token_path(account)
    creds: Credentials | None = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_file.write_text(creds.to_json())
        return creds
    if not config.GOOGLE_OAUTH_CLIENT_SECRETS.exists():
        raise RuntimeError(
            f"OAuth client secrets not found at {config.GOOGLE_OAUTH_CLIENT_SECRETS}. "
            "Create an OAuth client at https://console.cloud.google.com/apis/credentials "
            "(type: Desktop app) and download the JSON."
        )
    flow = InstalledAppFlow.from_client_secrets_file(
        str(config.GOOGLE_OAUTH_CLIENT_SECRETS), SCOPES
    )
    creds = flow.run_local_server(port=0)
    token_file.write_text(creds.to_json())
    return creds


def gmail_service(account: str = "user"):
    return build("gmail", "v1", credentials=get_credentials(account), cache_discovery=False)


def calendar_service(account: str = "user"):
    return build("calendar", "v3", credentials=get_credentials(account), cache_discovery=False)
