"""SEO and HTML helpers for Blogger posts."""
from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from bs4 import BeautifulSoup

DISCLAIMER = "\u0645\u0639\u0644\u0648\u0645\u0627\u062a \u0639\u0627\u0645\u0629 \u0648\u0644\u0627 \u062a\u063a\u0646\u064a \u0639\u0646 \u0627\u0633\u062a\u0634\u0627\u0631\u0629 \u0627\u0644\u0637\u0628\u064a\u0628."

ALLOWED_TAGS = {
    "p", "br", "strong", "em", "b", "i", "ul", "ol", "li", "h1", "h2", "h3",
    "blockquote", "a", "img", "figure", "figcaption", "div", "span", "script"
}
ALLOWED_ATTRS = {
    "a": {"href", "rel", "target", "title"},
    "img": {"src", "alt", "title", "width", "height", "loading"},
    "div": {"dir", "class"},
    "span": {"class"},
    "script": {"type"},
}


def strip_tags(text: str) -> str:
    soup = BeautifulSoup(text or "", "html.parser")
    return " ".join(soup.get_text(" ").split())


def make_meta_description(text: str, limit: int = 155) -> str:
    clean = strip_tags(text)
    clean = re.sub(r"\s+", " ", clean).strip()
    if len(clean) <= limit:
        return clean
    trimmed = clean[: limit - 1].rsplit(" ", 1)[0]
    return f"{trimmed}..."


def sanitize_html_fragment(fragment: str) -> str:
    """Remove dangerous tags/attrs while keeping simple Blogger-ready HTML."""
    soup = BeautifulSoup(fragment or "", "html.parser")
    for tag in list(soup.find_all(True)):
        if tag.name not in ALLOWED_TAGS:
            tag.unwrap()
            continue
        allowed = ALLOWED_ATTRS.get(tag.name, set())
        attrs = dict(tag.attrs)
        for attr in attrs:
            if attr not in allowed:
                del tag.attrs[attr]
        if tag.name == "a":
            href = tag.get("href", "")
            if href and not href.lower().startswith(("http://", "https://")):
                del tag.attrs["href"]
            tag["target"] = "_blank"
            tag["rel"] = "nofollow noopener noreferrer"
        if tag.name == "script" and tag.get("type") != "application/ld+json":
            tag.decompose()
    return str(soup)


def article_schema(
    title: str,
    description: str,
    source_url: str,
    author: str,
    published_iso: str,
    image_url: Optional[str] = None,
) -> Dict[str, Any]:
    schema: Dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "author": {"@type": "Person", "name": author or "Unknown"},
        "datePublished": published_iso,
        "dateModified": datetime.now(timezone.utc).isoformat(),
        "mainEntityOfPage": source_url,
        "inLanguage": "ar",
    }
    if image_url:
        schema["image"] = [image_url]
    return schema


def faq_schema(faq: Iterable[Dict[str, str]]) -> Optional[Dict[str, Any]]:
    entities: List[Dict[str, Any]] = []
    for item in faq or []:
        question = str(item.get("question", "")).strip()
        answer = str(item.get("answer", "")).strip()
        if not question or not answer:
            continue
        entities.append(
            {
                "@type": "Question",
                "name": question,
                "acceptedAnswer": {"@type": "Answer", "text": answer},
            }
        )
    if not entities:
        return None
    return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": entities}


def _json_ld(data: Dict[str, Any]) -> str:
    return f'<script type="application/ld+json">{json.dumps(data, ensure_ascii=False)}</script>'


def build_post_html(
    title: str,
    html_body: str,
    meta_description: str,
    source_url: str,
    author: str,
    published_iso: str,
    image_url: Optional[str] = None,
    faq: Optional[List[Dict[str, str]]] = None,
) -> str:
    body = sanitize_html_fragment(html_body)
    image_block = ""
    if image_url:
        image_block = (
            f'<figure><img src="{html.escape(image_url)}" alt="{html.escape(title)}" '
            f'loading="lazy"/><figcaption>{html.escape(title)}</figcaption></figure>'
        )
    source_block = (
        '<p><small>المصدر: '
        f'<a href="{html.escape(source_url)}" target="_blank" rel="nofollow noopener noreferrer">'
        f'{html.escape(source_url)}</a></small></p>'
    )
    disclaimer_block = f'<blockquote><strong>تنبيه:</strong> {DISCLAIMER}</blockquote>'
    schemas = [_json_ld(article_schema(title, meta_description, source_url, author, published_iso, image_url))]
    faq_data = faq_schema(faq or [])
    if faq_data:
        schemas.append(_json_ld(faq_data))
    html_doc = f"""
<div dir="rtl" class="auto-blog-post">
<meta name="description" content="{html.escape(meta_description)}" />
<h1>{html.escape(title)}</h1>
{image_block}
{body}
{source_block}
{disclaimer_block}
{''.join(schemas)}
</div>
""".strip()
    return sanitize_html_fragment(html_doc)
