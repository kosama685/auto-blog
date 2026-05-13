"""SQLite duplicate tracking for fetched and published articles."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from models import Article


SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    uid TEXT PRIMARY KEY,
    source_url TEXT,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    blogger_post_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_articles_source_url ON articles(source_url);
"""


class ArticleStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def has_seen(self, article: Article) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM articles WHERE uid = ? OR source_url = ? LIMIT 1",
                (article.uid, article.source_url),
            ).fetchone()
        return row is not None

    def mark(self, article: Article, status: str, blogger_post_id: Optional[str] = None) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO articles(uid, source_url, title, status, blogger_post_id)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(uid) DO UPDATE SET
                    status=excluded.status,
                    blogger_post_id=excluded.blogger_post_id,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (article.uid, article.source_url, article.title, status, blogger_post_id),
            )
