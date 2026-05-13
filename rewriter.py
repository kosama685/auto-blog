"""AI rewriting and SEO drafting with the OpenAI API."""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional

from openai import OpenAI

from config import Settings, get_settings
from models import Article
from seo_optimizer import make_meta_description, sanitize_html_fragment

INTRO_TEMPLATE = "\u0641\u064a \u0647\u0630\u0627 \u0627\u0644\u0645\u0642\u0627\u0644 \u0646\u0633\u062a\u0639\u0631\u0636"
DISCLAIMER = "\u0645\u0639\u0644\u0648\u0645\u0627\u062a \u0639\u0627\u0645\u0629 \u0648\u0644\u0627 \u062a\u063a\u0646\u064a \u0639\u0646 \u0627\u0633\u062a\u0634\u0627\u0631\u0629 \u0627\u0644\u0637\u0628\u064a\u0628."

SYSTEM_PROMPT = f"""
You are an expert Arabic health editor, SEO specialist, and compliance reviewer.
Create legally safe, original Arabic health-blog content from source summaries.
Rules:
- Write in Modern Standard Arabic, right-to-left friendly HTML.
- Start with the phrase: {INTRO_TEMPLATE}.
- Do not copy source wording. Rewrite completely and keep factual accuracy.
- Avoid diagnosis, cure guarantees, dosage instructions, or unsafe medical claims.
- Include a concise conclusion and this disclaimer: {DISCLAIMER}
- Use H2/H3 structure, short paragraphs, and natural Saudi-focused SEO phrasing.
- Include source attribution in a neutral way; never imply medical endorsement.
Return ONLY valid JSON with keys: seo_title, meta_description, html_body, labels, faq.
labels must be a JSON array of Arabic tags. faq must be an array of objects with question and answer.
""".strip()


def _extract_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return output_text
    chunks = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                chunks.append(text)
    return "\n".join(chunks)


def _parse_json(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.S)
        if not match:
            raise
        return json.loads(match.group(0))


def _fallback_result(article: Article, settings: Settings) -> Dict[str, Any]:
    keyword = settings.health_keywords[0]
    title = f"{keyword}: {article.title}"[:90]
    html_body = f"""
    <p>{INTRO_TEMPLATE} موضوع <strong>{article.title}</strong> اعتمادا على ملخص من مصدره الاصلي، مع تبسيط المعلومات للقارئ العربي.</p>
    <h2>نظرة عامة</h2>
    <p>{article.body}</p>
    <h2>ملاحظات مهمة</h2>
    <p>ينبغي التعامل مع المعلومات الصحية العامة بحذر، خصوصا عند وجود حمل، امراض مزمنة، او استخدام ادوية منتظمة.</p>
    <h2>الخلاصة</h2>
    <p>{DISCLAIMER}</p>
    """
    return {
        "seo_title": title,
        "meta_description": make_meta_description(f"{title}. {article.body}"),
        "html_body": sanitize_html_fragment(html_body),
        "labels": settings.labels,
        "faq": [],
    }


def rewrite_article(
    article: Article,
    settings: Optional[Settings] = None,
    logger: Optional[logging.Logger] = None,
) -> Dict[str, Any]:
    settings = settings or get_settings()
    if not settings.openai_api_key:
        if logger:
            logger.warning("OPENAI_API_KEY not set; using fallback rewrite")
        return _fallback_result(article, settings)

    client = OpenAI(api_key=settings.openai_api_key)
    user_prompt = {
        "source_title": article.title,
        "source_body": article.body,
        "source_url": article.source_url,
        "author": article.author,
        "published_at": article.published_iso,
        "target_keywords": settings.health_keywords,
        "target_country": settings.target_country,
        "requirements": [
            "Produce clean Blogger-ready HTML only inside html_body.",
            "Meta description must be 120-155 Arabic characters.",
            "Add 3 to 5 FAQ items only when safe and relevant.",
            "Mention the source URL only as attribution, not as copied content.",
        ],
    }

    try:
        response = client.responses.create(
            model=settings.openai_text_model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
            ],
            temperature=settings.openai_temperature,
        )
        parsed = _parse_json(_extract_text(response))
        parsed["html_body"] = sanitize_html_fragment(parsed.get("html_body", ""))
        parsed["meta_description"] = make_meta_description(parsed.get("meta_description") or parsed.get("html_body", ""))
        labels = parsed.get("labels") or settings.labels
        parsed["labels"] = list(dict.fromkeys([str(label).strip() for label in labels if str(label).strip()]))[:8]
        parsed["faq"] = parsed.get("faq") if isinstance(parsed.get("faq"), list) else []
        if not parsed.get("seo_title"):
            parsed["seo_title"] = article.title[:90]
        return parsed
    except Exception as exc:
        if logger:
            logger.exception("OpenAI rewrite failed; using fallback for %s", article.source_url)
        return _fallback_result(article, settings)
