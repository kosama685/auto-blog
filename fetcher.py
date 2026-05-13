"""Fetch Arabic health/herbal content from RSS and NewsAPI.

The fetcher prefers RSS summaries and NewsAPI descriptions instead of scraping full pages.
It respects robots.txt before optional page reads and adds delays between sources.
"""
from __future__ import annotations

import html
import logging
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable, List, Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import feedparser
import requests
from bs4 import BeautifulSoup

from config import Settings, get_settings
from models import Article


class FetchError(RuntimeError):
    pass


def _parse_datetime(value: object) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return parsedate_to_datetime(value)
        except Exception:
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except Exception:
                return None
    return None


def _clean_html_to_text(raw: str) -> str:
    if not raw:
        return ""
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return html.unescape(" ".join(soup.get_text(" ").split()))


def _source_name(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "") or "Unknown"
    except Exception:
        return "Unknown"


def can_fetch(url: str, user_agent: str, logger: Optional[logging.Logger] = None) -> bool:
    """Best-effort robots.txt check. If robots cannot be read, fail open for RSS/news metadata."""
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.read()
        return parser.can_fetch(user_agent, url)
    except Exception as exc:
        if logger:
            logger.warning("robots_txt_check_failed url=%s error=%s", url, exc)
        return True


def fetch_from_rss(settings: Optional[Settings] = None, logger: Optional[logging.Logger] = None) -> List[Article]:
    settings = settings or get_settings()
    articles: List[Article] = []
    headers = {"User-Agent": settings.user_agent}

    for feed_url in settings.rss_feeds:
        if not can_fetch(feed_url, settings.user_agent, logger):
            if logger:
                logger.warning("Skipping RSS blocked by robots.txt: %s", feed_url)
            continue
        try:
            response = requests.get(feed_url, headers=headers, timeout=settings.request_timeout_seconds)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
        except Exception as exc:
            if logger:
                logger.exception("RSS fetch failed for %s", feed_url)
            continue

        for entry in feed.entries:
            title = _clean_html_to_text(getattr(entry, "title", "")).strip()
            summary = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
            body = _clean_html_to_text(summary)
            link = getattr(entry, "link", "")
            author = getattr(entry, "author", "Unknown") or "Unknown"
            published = _parse_datetime(getattr(entry, "published", None) or getattr(entry, "updated", None))
            if title and body and link:
                articles.append(
                    Article(
                        title=title,
                        body=body,
                        publish_date=published,
                        source_url=link,
                        author=author,
                        source_name=_source_name(link),
                    )
                )
        time.sleep(settings.fetch_delay_seconds)
    return articles


def fetch_from_newsapi(settings: Optional[Settings] = None, logger: Optional[logging.Logger] = None) -> List[Article]:
    settings = settings or get_settings()
    if not settings.newsapi_key:
        if logger:
            logger.info("NEWSAPI_KEY not set; skipping NewsAPI source")
        return []

    query = " OR ".join(settings.health_keywords)
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "language": "ar",
        "sortBy": "publishedAt",
        "pageSize": 50,
        "apiKey": settings.newsapi_key,
    }
    headers = {"User-Agent": settings.user_agent}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=settings.request_timeout_seconds)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        raise FetchError(f"NewsAPI fetch failed: {exc}") from exc

    if payload.get("status") != "ok":
        raise FetchError(f"NewsAPI returned non-ok status: {payload}")

    results: List[Article] = []
    for item in payload.get("articles", []):
        title = _clean_html_to_text(item.get("title") or "")
        body = _clean_html_to_text(item.get("description") or item.get("content") or "")
        source_url = item.get("url") or ""
        if not title or not body or not source_url:
            continue
        results.append(
            Article(
                title=title,
                body=body,
                publish_date=_parse_datetime(item.get("publishedAt")) or datetime.now(timezone.utc),
                source_url=source_url,
                author=item.get("author") or "Unknown",
                source_name=(item.get("source") or {}).get("name") or _source_name(source_url),
            )
        )
    return results


def dedupe_articles(articles: Iterable[Article]) -> List[Article]:
    seen = set()
    unique: List[Article] = []
    for article in articles:
        if article.uid in seen:
            continue
        seen.add(article.uid)
        unique.append(article)
    unique.sort(key=lambda a: a.publish_date or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return unique


def fetch_content(settings: Optional[Settings] = None, logger: Optional[logging.Logger] = None) -> List[Article]:
    settings = settings or get_settings()
    all_articles: List[Article] = []
    try:
        all_articles.extend(fetch_from_newsapi(settings, logger))
    except Exception as exc:
        if logger:
            logger.exception("NewsAPI source failed: %s", exc)
    all_articles.extend(fetch_from_rss(settings, logger))
    return dedupe_articles(all_articles)
