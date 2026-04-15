"""
backends/image/pollinations.py — Pollinations.ai Image Backend
================================================================
Free image generation, no API key required.  Uses the Pollinations.ai
URL-based API with SDXL-class quality.
"""

import logging
import time
from urllib.parse import quote

import requests
import asyncio

from backends.base import ImageBackend
from core.config_manager import config

logger = logging.getLogger("ghost.image.pollinations")


class PollinationsBackend(ImageBackend):
    """Free cloud image generation via Pollinations.ai — no API key needed."""

    @property
    def name(self) -> str:
        return "Pollinations.ai"

    @property
    def requires_key(self) -> bool:
        return False

    @property
    def is_local(self) -> bool:
        return False

    async def generate(self, prompt: str, output_path: str, width: int, height: int) -> str:
        """
        Generate an image using Pollinations.ai URL-based API.

        Includes a 3s sleep after each call to respect rate limits.
        """
        model = config.get("image.pollinations_model", "dreamshaper")
        encoded_prompt = quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        params = {
            "width": width,
            "height": height,
            "model": model,
            "nologo": "true",
            "enhance": "true",
        }

        logger.info(f"Pollinations: generating {width}x{height}, model={model}")
        logger.debug(f"  Prompt: {prompt[:80]}…")

        try:
            # Use to_thread to prevent blocking the event loop during the network call
            def _fetch():
                resp = requests.get(url, params=params, timeout=120)
                resp.raise_for_status()
                return resp

            response = await asyncio.to_thread(_fetch)

            if len(response.content) < 1000:
                raise RuntimeError(f"Pollinations returned suspiciously small response ({len(response.content)} bytes)")

            with open(output_path, "wb") as f:
                f.write(response.content)

            logger.info(f"Pollinations: saved → {output_path} ({len(response.content) / 1024:.1f} KB)")

            # Rate limit: ~1 request per 3 seconds - USE ASYNC SLEEP!
            await asyncio.sleep(3)
            return output_path

        except requests.Timeout:
            raise RuntimeError("Pollinations.ai request timed out (120s)")
        except requests.ConnectionError:
            raise RuntimeError("Pollinations.ai is unreachable — check your internet connection")
        except Exception as exc:
            logger.error(f"Pollinations failed: {exc}")
            raise RuntimeError(f"Pollinations.ai failed: {exc}") from exc

    def validate_config(self, config_data: dict) -> tuple[bool, str]:
        """Check if Pollinations.ai is reachable."""
        try:
            resp = requests.head("https://image.pollinations.ai/", timeout=5)
            return (True, "")
        except Exception:
            return (False, "Pollinations.ai is unreachable. Check your internet connection.")
