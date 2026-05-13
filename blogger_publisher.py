"""Blogger API v3 publishing wrapper."""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import Settings, get_settings

SCOPES = ["https://www.googleapis.com/auth/blogger"]
TOKEN_URI = "https://oauth2.googleapis.com/token"


class BloggerConfigError(RuntimeError):
    pass


def _save_token(credentials: Credentials, token_file: Path) -> None:
    token_file.write_text(credentials.to_json(), encoding="utf-8")


def authenticate_blogger(settings: Optional[Settings] = None):
    settings = settings or get_settings()
    credentials: Optional[Credentials] = None

    if settings.google_token_file.exists():
        credentials = Credentials.from_authorized_user_file(str(settings.google_token_file), SCOPES)
    elif settings.blogger_refresh_token and settings.blogger_client_id and settings.blogger_client_secret:
        credentials = Credentials(
            token=None,
            refresh_token=settings.blogger_refresh_token,
            token_uri=TOKEN_URI,
            client_id=settings.blogger_client_id,
            client_secret=settings.blogger_client_secret,
            scopes=SCOPES,
        )
    elif settings.google_credentials_file.exists():
        flow = InstalledAppFlow.from_client_secrets_file(str(settings.google_credentials_file), SCOPES)
        credentials = flow.run_local_server(port=0)
        _save_token(credentials, settings.google_token_file)
    else:
        raise BloggerConfigError(
            "Set GOOGLE_CREDENTIALS_FILE for first OAuth login, or set BLOGGER_CLIENT_ID, "
            "BLOGGER_CLIENT_SECRET, and BLOGGER_REFRESH_TOKEN."
        )

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        _save_token(credentials, settings.google_token_file)

    if not credentials or not credentials.valid:
        raise BloggerConfigError("Blogger credentials are missing or invalid.")

    return build("blogger", "v3", credentials=credentials, cache_discovery=False)


def publish_to_blogger(
    title: str,
    content_html: str,
    labels: List[str],
    settings: Optional[Settings] = None,
    logger: Optional[logging.Logger] = None,
    as_draft: Optional[bool] = None,
) -> Dict:
    settings = settings or get_settings()
    if not settings.blogger_blog_id:
        raise BloggerConfigError("BLOGGER_BLOG_ID is required to publish posts.")

    service = authenticate_blogger(settings)
    is_draft = settings.blogger_publish_as_draft if as_draft is None else as_draft
    body = {
        "kind": "blogger#post",
        "title": title,
        "content": content_html,
        "labels": labels,
    }

    last_exc: Optional[Exception] = None
    for attempt in range(1, 4):
        try:
            request = service.posts().insert(
                blogId=settings.blogger_blog_id,
                body=body,
                isDraft=is_draft,
                fetchImages=True,
            )
            return request.execute()
        except HttpError as exc:
            last_exc = exc
            status = getattr(exc.resp, "status", None)
            retryable = status in {429, 500, 502, 503, 504}
            if logger:
                logger.warning("Blogger publish attempt %s failed status=%s", attempt, status)
            if not retryable or attempt == 3:
                raise
            time.sleep(2**attempt)
    raise RuntimeError(f"Blogger publishing failed: {last_exc}")
