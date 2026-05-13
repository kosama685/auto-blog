# Arabic Herbal Health Blog System

A production-ready Python pipeline that fetches Arabic health/herbal article summaries, rewrites them into original Arabic HTML with safety disclaimers, optionally generates featured images, and publishes Blogger drafts/posts.

## What is included

```text
auto-blog/
├── config.py
├── fetcher.py
├── rewriter.py
├── image_gen.py
├── blogger_publisher.py
├── seo_optimizer.py
├── scheduler.py
├── logger.py
├── storage.py
├── models.py
├── main.py
├── requirements.txt
├── .env.example
└── README.md
```

## Compliance design

- Fetches from RSS and NewsAPI metadata/summaries by default.
- Performs a best-effort robots.txt check before RSS reads.
- Deduplicates by source URL/hash in SQLite.
- Requires source attribution in the final Blogger HTML.
- Adds a medical disclaimer to every post.
- Prompts the AI model to avoid diagnosis, dosage instructions, cure guarantees, and unsafe claims.
- Defaults to Blogger drafts with `BLOGGER_PUBLISH_AS_DRAFT=true`.

## Setup

1. Create and activate a virtual environment.

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Configure environment variables.

```bash
cp .env.example .env
```

Edit `.env` and add your keys.

## OpenAI configuration

Set:

```text
OPENAI_API_KEY=sk-your-key
OPENAI_TEXT_MODEL=gpt-4o
OPENAI_IMAGE_MODEL=gpt-image-1
```

If you do not want images, set:

```text
ENABLE_IMAGES=false
```

The code uses the OpenAI Python SDK and the Responses API for rewriting, plus the Images API for featured images.

## Blogger OAuth setup

1. In Google Cloud Console, create an OAuth client for a desktop app.
2. Download the client JSON file.
3. Rename it to `credentials.json` and place it in the project folder, or set `GOOGLE_CREDENTIALS_FILE` in `.env`.
4. Set `BLOGGER_BLOG_ID` in `.env`.
5. Run a dry run or first publishing run. The app opens a browser for OAuth and saves `token.json`.

Alternative: provide `BLOGGER_CLIENT_ID`, `BLOGGER_CLIENT_SECRET`, and `BLOGGER_REFRESH_TOKEN` directly.

## Optional public image hosting

Blogger needs a public image URL to embed a generated featured image. The project includes optional Cloudinary upload support.

Set these in `.env`:

```text
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
```

Without Cloudinary credentials, generated images remain in the local `generated/` folder and the post is published without a public featured image URL.

## Run once

Dry run, no publishing:

```bash
python main.py --once --dry-run --max-posts 1
```

This writes HTML previews into `generated/`.

Publish to Blogger according to `BLOGGER_PUBLISH_AS_DRAFT`:

```bash
python main.py --once --max-posts 1
```

## Run on a schedule

```bash
python main.py --schedule
```

The default interval is every 4 hours and timezone is Asia/Riyadh. Change it with:

```text
SCHEDULE_INTERVAL_HOURS=6
```

## Deployment notes

### PythonAnywhere

- Upload the project folder.
- Create a virtual environment and install requirements.
- Add `.env` and credentials.
- Use a scheduled task:

```bash
cd /home/youruser/auto-blog && /home/youruser/auto-blog/.venv/bin/python main.py --once
```

### Render / Railway

- Add environment variables in the dashboard.
- Use a worker command:

```bash
python main.py --schedule
```

### VPS / Raspberry Pi

Use cron for a simple scheduled run:

```cron
0 */4 * * * cd /opt/auto-blog && /opt/auto-blog/.venv/bin/python main.py --once >> cron.log 2>&1
```

## Important files generated at runtime

- `auto_blog.sqlite3`: duplicate and publish status database.
- `logs/auto_blog.log`: rotating JSON-style event logs.
- `generated/`: image files and dry-run HTML previews.
- `token.json`: Google OAuth token; keep it private.

## Safety reminder

This project is for general educational health content. It should not publish definitive medical advice, dosage instructions, or claims that herbs cure diseases. Review drafts before publishing live.
