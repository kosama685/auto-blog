"""CLI entrypoint for the Arabic Herbal Health Blog System."""
from __future__ import annotations

import argparse
import sys

from config import get_settings
from logger import configure_logging
from scheduler import process_once, start_scheduler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Automated Arabic herbal health Blogger pipeline")
    parser.add_argument("--once", action="store_true", help="Run one fetch/rewrite/publish cycle and exit")
    parser.add_argument("--schedule", action="store_true", help="Run continuously with APScheduler")
    parser.add_argument("--dry-run", action="store_true", help="Write HTML previews without publishing")
    parser.add_argument("--max-posts", type=int, default=None, help="Maximum posts to process this run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = get_settings()
    logger = configure_logging(settings.log_dir)

    if args.schedule:
        start_scheduler(settings=settings, dry_run=args.dry_run)
        return 0

    # Default to one cycle so first-time users can test quickly.
    process_once(settings=settings, logger=logger, dry_run=args.dry_run, max_posts=args.max_posts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
