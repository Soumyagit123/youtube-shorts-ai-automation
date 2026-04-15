"""
backends/image/replicate.py — Replicate Image Backend
======================================================
Paid cloud image generation via the Replicate API.
Uses the official replicate SDK.  ~$0.004/image.
"""

import logging
import os

import requests
import asyncio

from backends.base import ImageBackend
from core.config_manager import config

logger = logging.getLogger("ghost.image.replicate")


class ReplicateBackend(ImageBackend):
    """Replicate — paid cloud image generation via official SDK."""

    @property
    def name(self) -> str:
        return "Replicate"

    @property
    def requires_key(self) -> bool:
        return True

    @property
    def is_local(self) -> bool:
        return False

    async def generate(self, prompt: str, output_path: str, width: int, height: int) -> str:
        """
        Generate an image using the Replicate API.
        """
        import replicate as replicate_sdk

        api_key = config.get("api_keys.replicate", "")
        if not api_key:
            raise RuntimeError("Replicate API key not configured")

        # Set API token in environment (required by replicate SDK)
        os.environ["REPLICATE_API_TOKEN"] = api_key

        model = config.get("image.replicate_model", "stability-ai/sdxl")

        logger.info(f"Replicate: model={model}, size={width}x{height}")
        logger.debug(f"  Prompt: {prompt[:80]}…")

        try:
            def _generate():
                return replicate_sdk.run(
                    model,
                    input={
                        "prompt": prompt,
                        "width": width,
                        "height": height,
                    },
                )

            output = await asyncio.to_thread(_generate)

            # Output is typically a list of URLs
            if isinstance(output, list):
                image_url = str(output[0])
            else:
                image_url = str(output)

            # Download the image
            def _download():
                resp = requests.get(image_url, timeout=30)
                resp.raise_for_status()
                return resp
                
            response = await asyncio.to_thread(_download)

            with open(output_path, "wb") as f:
                f.write(response.content)

            logger.info(f"Replicate: saved → {output_path} ({len(response.content) / 1024:.1f} KB)")
            return output_path

        except Exception as exc:
            logger.error(f"Replicate failed: {exc}")
            raise RuntimeError(f"Replicate failed: {exc}") from exc

    def validate_config(self, config_data: dict) -> tuple[bool, str]:
        """Check that Replicate API key is configured."""
        api_key = config.get("api_keys.replicate", "")
        if not api_key:
            return (False, "Replicate API key required. Get one at replicate.com")
        return (True, "")
