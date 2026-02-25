"""fal.ai FLUX Schnell image generation for workout #4 (Synthetic Studio)."""
from __future__ import annotations

import logging
import os
import re

import fal_client

from mktbook.config import settings

log = logging.getLogger(__name__)


def extract_image_prompt(text: str) -> tuple[str, str | None]:
    """Extract [IMAGE: ...] tag from a bot's response.

    Returns (clean_text, image_prompt). The tag is stripped from the
    displayed content so the platform shows clean prose only.
    """
    match = re.search(r"\[(?:IMAGE|Creative Image Concept):\s*(.+?)\]", text, re.DOTALL | re.IGNORECASE)
    if match:
        clean = text[: match.start()].strip()
        prompt = match.group(1).strip()
        return clean, prompt
    return text, None


async def generate_image(prompt: str) -> str | None:
    """Call fal.ai FLUX Schnell with *prompt* and return the image URL.

    Returns None on any error — callers should treat images as optional.
    fal-client reads the FAL_KEY environment variable automatically;
    settings.fal_api_key is set into the env here as a convenience.
    """
    if not prompt:
        return None

    # Ensure FAL_KEY is available to the fal_client library.
    # fal-client reads FAL_KEY from the environment; settings.fal_api_key
    # comes from FAL_API_KEY in .env (pydantic naming convention).
    if not os.environ.get("FAL_KEY"):
        key = settings.fal_api_key or os.environ.get("FAL_API_KEY", "")
        if key:
            os.environ["FAL_KEY"] = key

    try:
        result = await fal_client.run_async(
            "fal-ai/flux/schnell",
            arguments={
                "prompt": prompt,
                "image_size": "landscape_4_3",
                "num_inference_steps": 4,
                "num_images": 1,
            },
        )
        images = result.get("images", [])
        if images:
            return images[0]["url"]
        log.warning("fal.ai returned no images for prompt: %.80s", prompt)
    except Exception:
        log.exception("fal.ai image generation failed for prompt: %.80s", prompt)
    return None
