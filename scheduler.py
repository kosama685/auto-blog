"""Orchestrates fetching, rewriting, image generation, SEO wrapping, and publishing."""
from __future__ import annotations

import logging
from typing import Optional

from apscheduler.schedulers.blocking import BlockingScheduler

from blogger_publisher import BloggerConfigError, publish_to_blogger
from config import Settings, get_settings
from fetcher import fetch_content
from image_gen import generate_and_upload_image
from logger import configure_logging, log_event
from rewriter import rewrite_article
from seo_optimizer import build_post_html
from storage import ArticleStore


def process_once(
    settings: Optional[Settings] = None,
    logger: Optional[logging.Logger] = None,
    dry_run: bool = False,
    max_posts: Optional[int] = None,
) -> int:
    settings = settings or get_settings()
    logger = logger or configure_logging(settings.log_dir)
    store = ArticleStore(settings.db_path)

    log_event(logger, "run_started", dry_run=dry_run)
    articles = fetch_content(settings, logger)
    log_event(logger, "articles_fetched", count=len(articles))

    published_count = 0
    limit = max_posts if max_posts is not None else settings.max_articles_per_run

    for article in articles:
        if published_count >= limit:
            break
        if store.has_seen(article):
            log_event(logger, "article_skipped_duplicate", title=article.title, source_url=article.source_url)
            continue

        store.mark(article, "processing")
        log_event(logger, "article_processing", title=article.title, source_url=article.source_url)

        rewritten = rewrite_article(article, settings, logger)
        image_url = generate_and_upload_image(rewritten["seo_title"], settings, logger)
        post_html = build_post_html(
            title=rewritten["seo_title"],
            html_body=rewritten["html_body"],
            meta_description=rewritten["meta_description"],
            source_url=article.source_url,
            author=article.author,
            published_iso=article.published_iso,
            image_url=image_url,
            faq=rewritten.get("faq", []),
        )

        if dry_run:
            preview_path = settings.generated_dir / f"preview-{article.uid[:12]}.html"
            preview_path.write_text(post_html, encoding="utf-8")
            store.mark(article, "dry_run")
            log_event(logger, "dry_run_preview_written", path=str(preview_path))
            published_count += 1
            continue

        try:
            result = publish_to_blogger(
                rewritten["seo_title"],
                post_html,
                rewritten.get("labels") or settings.labels,
                settings,
                logger,
            )
            blogger_id = result.get("id") if isinstance(result, dict) else None
            store.mark(article, "published", blogger_id)
            log_event(logger, "article_published", title=rewritten["seo_title"], blogger_post_id=blogger_id)
            published_count += 1
        except BloggerConfigError:
            store.mark(article, "publish_config_error")
            raise
        except Exception:
            store.mark(article, "publish_failed")
            logger.exception("Failed to publish article: %s", article.title)

    log_event(logger, "run_finished", processed=published_count)
    return published_count


def start_scheduler(settings: Optional[Settings] = None, dry_run: bool = False) -> None:
    settings = settings or get_settings()
    logger = configure_logging(settings.log_dir)
    scheduler = BlockingScheduler(timezone="Asia/Riyadh")
    scheduler.add_job(
        lambda: process_once(settings=settings, logger=logger, dry_run=dry_run),
        "interval",
        hours=settings.schedule_interval_hours,
        id="auto_blog_pipeline",
        max_instances=1,
        coalesce=True,
    )
    log_event(logger, "scheduler_started", interval_hours=settings.schedule_interval_hours, dry_run=dry_run)
    scheduler.start()
