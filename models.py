"""Shared data models."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Optional


@dataclass(frozen=True)
class Article:
    title: str
    body: str
    publish_date: Optional[datetime]
    source_url: str
    author: str = "Unknown"
    source_name: str = "Unknown"

    @property
    def uid(self) -> str:
        key = self.source_url or f"{self.source_name}:{self.title}:{self.body[:200]}"
        return sha256(key.encode("utf-8", errors="ignore")).hexdigest()

    @property
    def published_iso(self) -> str:
        if not self.publish_date:
            return datetime.now(timezone.utc).isoformat()
        if self.publish_date.tzinfo is None:
            return self.publish_date.replace(tzinfo=timezone.utc).isoformat()
        return self.publish_date.isoformat()
