"""Configuration for the Arabic Herbal Health Blog System.

All secrets are read from environment variables or a local .env file.
Do not commit .env to source control.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _csv_env(name: str, default: List[str]) -> List[str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


DEFAULT_RSS_FEEDS = [
    "https://www.webteb.com/rss",
    "https://www.aljazeera.net/xml/rss/health.xml",
]

DEFAULT_HEALTH_KEYWORDS = [
    "\u0639\u0644\u0627\u062c \u0628\u0627\u0644\u0623\u0639\u0634\u0627\u0628",
    "\u0641\u0648\u0627\u0626\u062f \u0635\u062d\u064a\u0629",
    "\u0637\u0628 \u0628\u062f\u064a\u0644",
    "\u0627\u0644\u0635\u062d\u0629 \u0627\u0644\u0637\u0628\u064a\u0639\u064a\u0629",
]

DEFAULT_LABELS = [
    "\u0637\u0628 \u0628\u062f\u064a\u0644",
    "\u0639\u0644\u0627\u062c \u0628\u0627\u0644\u0623\u0639\u0634\u0627\u0628",
    "\u0635\u062d\u0629",
]


@dataclass(frozen=True)
class Settings:
    project_name: str = os.getenv("PROJECT_NAME", "Arabic Herbal Health Blog System")
    environment: str = os.getenv("APP_ENV", "local")

    # API keys
    newsapi_key: str = os.getenv("NEWSAPI_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

    # OpenAI settings
    openai_text_model: str = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o")
    openai_image_model: str = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
    openai_temperature: float = float(os.getenv("OPENAI_TEMPERATURE", "0.5"))

    # Blogger settings
    blogger_blog_id: str = os.getenv("BLOGGER_BLOG_ID", "")
    blogger_client_id: str = os.getenv("BLOGGER_CLIENT_ID", "")
    blogger_client_secret: str = os.getenv("BLOGGER_CLIENT_SECRET", "")
    blogger_refresh_token: str = os.getenv("BLOGGER_REFRESH_TOKEN", "")
    google_credentials_file: Path = BASE_DIR / os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    google_token_file: Path = BASE_DIR / os.getenv("GOOGLE_TOKEN_FILE", "token.json")
    blogger_publish_as_draft: bool = os.getenv("BLOGGER_PUBLISH_AS_DRAFT", "true").lower() in {"1", "true", "yes"}

    # Content sourcing and compliance
    rss_feeds: List[str] = field(default_factory=lambda: _csv_env("RSS_FEEDS", DEFAULT_RSS_FEEDS))
    health_keywords: List[str] = field(default_factory=lambda: _csv_env("HEALTH_KEYWORDS", DEFAULT_HEALTH_KEYWORDS))
    labels: List[str] = field(default_factory=lambda: _csv_env("BLOG_LABELS", DEFAULT_LABELS))
    request_timeout_seconds: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "20"))
    fetch_delay_seconds: float = float(os.getenv("FETCH_DELAY_SECONDS", "1.5"))
    user_agent: str = os.getenv(
        "USER_AGENT",
        "ArabicHerbalHealthBot/1.0 (+contact@example.com; compliant RSS/news fetcher)",
    )
    max_articles_per_run: int = int(os.getenv("MAX_ARTICLES_PER_RUN", "3"))
    similarity_note_threshold: int = int(os.getenv("SIMILARITY_NOTE_THRESHOLD", "30"))

    # SEO and image settings
    site_base_url: str = os.getenv("SITE_BASE_URL", "")
    target_country: str = os.getenv("TARGET_COUNTRY", "SA")
    image_prompt: str = os.getenv(
        "IMAGE_GEN_PROMPT",
        "Herbal medicine illustration, black seed, honey, natural background, professional Arabic health blog style, no medical claims, clean composition",
    )
    image_size: str = os.getenv("IMAGE_SIZE", "1024x1024")
    enable_images: bool = os.getenv("ENABLE_IMAGES", "true").lower() in {"1", "true", "yes"}
    image_overlay_text: str = os.getenv("IMAGE_OVERLAY_TEXT", "\u0639\u0644\u0627\u062c \u0628\u0627\u0644\u0623\u0639\u0634\u0627\u0628")

    # Optional Cloudinary upload for featured images
    cloudinary_cloud_name: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    cloudinary_api_key: str = os.getenv("CLOUDINARY_API_KEY", "")
    cloudinary_api_secret: str = os.getenv("CLOUDINARY_API_SECRET", "")
    cloudinary_folder: str = os.getenv("CLOUDINARY_FOLDER", "auto-blog")

    # Runtime files
    db_path: Path = BASE_DIR / os.getenv("DB_PATH", "auto_blog.sqlite3")
    log_dir: Path = BASE_DIR / os.getenv("LOG_DIR", "logs")
    generated_dir: Path = BASE_DIR / os.getenv("GENERATED_DIR", "generated")

    # Scheduler
    schedule_interval_hours: int = int(os.getenv("SCHEDULE_INTERVAL_HOURS", "4"))


def get_settings() -> Settings:
    settings = Settings()
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    settings.generated_dir.mkdir(parents=True, exist_ok=True)
    return settings
