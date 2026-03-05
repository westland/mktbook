"""fal.ai FLUX Schnell image generation for workout #4 (Synthetic Studio)."""
from __future__ import annotations

import logging
import math
import os
import random
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


def _poisson_sample(lam: float) -> int:
    """Draw a non-negative integer from Poisson(lam) using Knuth's algorithm."""
    L = math.exp(-lam)
    k, p = 0, 1.0
    while p > L:
        k += 1
        p *= random.random()
    return k - 1


class W4ImageGate:
    """Poisson-gated trigger for Workout #4 fal.ai image generation.

    The gap between picture-producing conversations follows Poisson(MEAN_GAP).
    With MEAN_GAP=6 the average cycle (gap + 1) equals 7 conversations,
    giving one image per ~7 conversations on average.
    """

    MEAN_GAP = 6

    def __init__(self) -> None:
        self._remaining: int = _poisson_sample(self.MEAN_GAP)

    def should_trigger(self) -> bool:
        """Call once per conversation.  Returns True ~1 in 7 times."""
        if self._remaining <= 0:
            self._remaining = _poisson_sample(self.MEAN_GAP)
            return True
        self._remaining -= 1
        return False


# Singleton — shared across all W4 bot-bot and bot-human conversations.
w4_image_gate = W4ImageGate()
