"""Image generation and optional upload for Blogger featured images."""
from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Optional

import requests
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

from config import Settings, get_settings


def _safe_filename(text: str, suffix: str = ".png") -> str:
    keep = []
    for ch in text.lower():
        if ch.isalnum():
            keep.append(ch)
        elif ch in {" ", "-", "_"}:
            keep.append("-")
    name = "".join(keep).strip("-")[:70] or "generated-image"
    return f"{name}{suffix}"


def _download_url(url: str, output_path: Path, timeout: int) -> Path:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    output_path.write_bytes(response.content)
    return output_path


def add_overlay(image_path: Path, text: str) -> Path:
    if not text:
        return image_path
    try:
        image = Image.open(image_path).convert("RGBA")
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        font_size = max(32, image.width // 20)
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()
        margin = image.width // 20
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = max(margin, (image.width - text_w) // 2)
        y = image.height - text_h - margin * 2
        box = (x - margin, y - margin // 2, x + text_w + margin, y + text_h + margin)
        draw.rounded_rectangle(box, radius=20, fill=(0, 0, 0, 130))
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
        Image.alpha_composite(image, overlay).convert("RGB").save(image_path)
    except Exception:
        return image_path
    return image_path


def generate_image(title: str, settings: Optional[Settings] = None, logger: Optional[logging.Logger] = None) -> Optional[Path]:
    settings = settings or get_settings()
    if not settings.enable_images:
        return None
    if not settings.openai_api_key:
        if logger:
            logger.warning("OPENAI_API_KEY not set; skipping image generation")
        return None

    client = OpenAI(api_key=settings.openai_api_key)
    output_path = settings.generated_dir / _safe_filename(title)
    prompt = f"{settings.image_prompt}. Article topic: {title}. Avoid text in the image except clean space for optional overlay."

    try:
        result = client.images.generate(
            model=settings.openai_image_model,
            prompt=prompt,
            size=settings.image_size,
            n=1,
        )
        image_data = result.data[0]
        b64_json = getattr(image_data, "b64_json", None)
        url = getattr(image_data, "url", None)
        if b64_json:
            output_path.write_bytes(base64.b64decode(b64_json))
        elif url:
            _download_url(url, output_path, settings.request_timeout_seconds)
        else:
            raise RuntimeError("Image API returned no b64_json or url")
        return add_overlay(output_path, settings.image_overlay_text)
    except Exception as exc:
        if logger:
            logger.exception("Image generation failed for %s", title)
        return None


def upload_to_cloudinary(image_path: Path, settings: Optional[Settings] = None, logger: Optional[logging.Logger] = None) -> Optional[str]:
    settings = settings or get_settings()
    if not image_path or not image_path.exists():
        return None
    if not (settings.cloudinary_cloud_name and settings.cloudinary_api_key and settings.cloudinary_api_secret):
        if logger:
            logger.info("Cloudinary credentials not set; keeping image local: %s", image_path)
        return None
    upload_url = f"https://api.cloudinary.com/v1_1/{settings.cloudinary_cloud_name}/image/upload"
    try:
        with image_path.open("rb") as fh:
            response = requests.post(
                upload_url,
                auth=(settings.cloudinary_api_key, settings.cloudinary_api_secret),
                data={"folder": settings.cloudinary_folder},
                files={"file": fh},
                timeout=settings.request_timeout_seconds,
            )
        response.raise_for_status()
        return response.json().get("secure_url")
    except Exception:
        if logger:
            logger.exception("Cloudinary upload failed for %s", image_path)
        return None


def generate_and_upload_image(title: str, settings: Optional[Settings] = None, logger: Optional[logging.Logger] = None) -> Optional[str]:
    settings = settings or get_settings()
    image_path = generate_image(title, settings, logger)
    if not image_path:
        return None
    return upload_to_cloudinary(image_path, settings, logger)
