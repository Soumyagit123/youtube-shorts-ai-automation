"""
modules/voicer.py — TTS Dispatcher (Thin Wrapper)
===================================================
Routes voiceover synthesis to the configured TTS backend.
All backend-specific logic lives in backends/tts/*.py.

Usage:
    from modules.voicer import run_voiceover, ensure_tts_ready

    ensure_tts_ready()              # Validates config + starts server if needed
    path = run_voiceover(text, language, output_path)
"""

import asyncio
from pathlib import Path

from config import get_logger
from core.config_manager import config
from core.utils import get_user_conf

log = get_logger("voicer")

# ── Backend registry ──────────────────────────────────────────────────────────
# Lazy imports to avoid loading unused heavy SDKs

BACKEND_MAP: dict[str, type] = {}


def _get_backend_map() -> dict[str, type]:
    """Lazy-load backend classes only when needed."""
    global BACKEND_MAP
    if BACKEND_MAP:
        return BACKEND_MAP

    from backends.tts.chatterbox import ChatterboxTTS
    from backends.tts.edge_tts import EdgeTTS
    from backends.tts.elevenlabs import ElevenLabsTTS
    from backends.tts.google_tts import GoogleTTS
    from backends.tts.kokoro_tts import KokoroTTS

    BACKEND_MAP = {
        "chatterbox": ChatterboxTTS,
        "edge_tts": EdgeTTS,
        "elevenlabs": ElevenLabsTTS,
        "google_tts": GoogleTTS,
        "kokoro": KokoroTTS,
    }
    return BACKEND_MAP


def _get_backend(user_config: dict | None = None):
    """Instantiate the configured TTS backend."""
    backend_name = get_user_conf("tts.backend", user_config, "chatterbox")
    backend_map = _get_backend_map()

    if backend_name not in backend_map:
        raise ValueError(
            f"Unknown TTS backend: {backend_name!r}. "
            f"Available: {list(backend_map.keys())}"
        )

    backend = backend_map[backend_name]()
    log.info(f"TTS backend: {backend.name} (local={backend.is_local}, key={backend.requires_key})")
    return backend


# ── Public API ────────────────────────────────────────────────────────────────

async def ensure_tts_ready(user_config: dict | None = None) -> bool:
    """
    Validate the configured TTS backend is ready.
    For Chatterbox: starts the server if needed.
    Returns True if ready.
    """
    backend = _get_backend(user_config)

    # Chatterbox has special startup logic
    if hasattr(backend, "ensure_running"):
        language = get_user_conf("pipeline.language", user_config, "hi")
        return await backend.ensure_running(language)

    # For other backends, validate config
    cfg_data = user_config if user_config else config.data
    valid, error = backend.validate_config(cfg_data)
    if not valid:
        log.error(f"TTS backend {backend.name} config invalid: {error}")
        return False
    return True


async def run_voiceover(
    text: str,
    language: str | None = None,
    output_path: str | Path | None = None,
    user_config: dict | None = None
) -> Path:
    """
    Synthesize voiceover text using the configured TTS backend.
    """
    if language is None:
        language = get_user_conf("pipeline.language", user_config, "hi")
    if not output_path:
        output_path = Path.cwd() / "voiceover.mp3"

    output_path = Path(output_path)
    backend = _get_backend(user_config)

    log.info(f"Generating voiceover with {backend.name} ({len(text)} chars, lang={language})")

    # Await the async synthesize method
    result = await backend.synthesize(text, language, str(output_path))

    log.info(f"Voiceover saved → {result}")
    return Path(result)


async def generate_voiceover(text: str, workspace_dir: Path, output_filename: str = "voiceover.mp3", user_config: dict | None = None) -> Path:
    """Async wrapper — calls run_voiceover."""
    output_path = workspace_dir / output_filename
    return await run_voiceover(text, output_path=output_path, user_config=user_config)


async def ensure_chatterbox_running(user_config: dict | None = None) -> bool:
    """Legacy wrapper — calls ensure_tts_ready."""
    return await ensure_tts_ready(user_config)


if __name__ == "__main__":
    sample = (
        "What if AI could replace every developer on the planet within three years? "
        "Here's what's actually happening inside the world's most secretive AI labs."
    )
    path = run_voiceover(sample, language="en")
    print(f"Output: {path}")
