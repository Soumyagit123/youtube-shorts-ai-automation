"""
modules/image_gen.py — Image Generation Dispatcher (Thin Wrapper)
==================================================================
Routes image generation to the configured backend.
All backend-specific logic lives in backends/image/*.py.

Usage:
    from modules.image_gen import run_image_generation, generate_images

    paths = run_image_generation(prompts, output_dir)
    # or legacy:
    paths = generate_images(prompts)
"""

import asyncio
from pathlib import Path

from config import get_logger
from core.config_manager import config
from core.utils import get_user_conf

log = get_logger("image_gen")

# ── Backend registry ──────────────────────────────────────────────────────────

BACKEND_MAP: dict[str, type] = {}


def _get_backend_map() -> dict[str, type]:
    """Lazy-load backend classes only when needed."""
    global BACKEND_MAP
    if BACKEND_MAP:
        return BACKEND_MAP

    from backends.image.comfyui import ComfyUIBackend
    from backends.image.pollinations import PollinationsBackend
    from backends.image.gemini_imagen import GeminiImagenBackend
    from backends.image.fal_ai import FalAIBackend
    from backends.image.stable_horde import StableHordeBackend
    from backends.image.replicate import ReplicateBackend

    BACKEND_MAP = {
        "comfyui": ComfyUIBackend,
        "pollinations": PollinationsBackend,
        "gemini_imagen": GeminiImagenBackend,
        "fal_ai": FalAIBackend,
        "stable_horde": StableHordeBackend,
        "replicate": ReplicateBackend,
    }
    return BACKEND_MAP


def _get_backend(user_config: dict | None = None):
    """Instantiate the configured image backend."""
    backend_name = get_user_conf("image.backend", user_config, "pollinations")
    backend_map = _get_backend_map()

    if backend_name not in backend_map:
        raise ValueError(
            f"Unknown image backend: {backend_name!r}. "
            f"Available: {list(backend_map.keys())}"
        )

    backend = backend_map[backend_name]()
    log.info(f"Image backend: {backend.name} (local={backend.is_local}, key={backend.requires_key})")
    return backend


# ── Public API ────────────────────────────────────────────────────────────────

async def run_image_generation(
    prompts: list[str],
    output_dir: str | Path | None = None,
    user_config: dict | None = None
) -> list[str]:
    """
    Generate images for a list of prompts using the configured backend.

    Parameters
    ----------
    prompts : list[str]
        List of image generation prompts.
    output_dir : str or Path, optional
        Directory to save images. Defaults to the current working directory.
    user_config : dict, optional
        User settings.

    Returns
    -------
    list[str]
        Ordered list of output image paths.
    """
    if output_dir is None:
        output_dir = Path.cwd()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    backend = _get_backend(user_config)
    width = get_user_conf("image.width", user_config, 1080)
    height = get_user_conf("image.height", user_config, 1920)

    # Validate backend config
    cfg_data = user_config if user_config else config.data
    valid, error = backend.validate_config(cfg_data)
    if not valid:
        raise ValueError(f"Image backend {backend.name} config error: {error}")

    log.info(f"Generating {len(prompts)} images with {backend.name} ({width}x{height})")

    # Free models if ComfyUI (before starting fresh)
    if hasattr(backend, '_free_models'):
        backend._free_models()

    saved_paths: list[str] = []

    for idx, prompt in enumerate(prompts, start=1):
        out_path = str(output_dir / f"scene_{idx:02d}.png")
        log.info(f"Generating image {idx}/{len(prompts)} …")
        await backend.generate(prompt, out_path, width, height)
        saved_paths.append(out_path)

    log.info(f"All {len(saved_paths)} image(s) saved to {output_dir}")
    return saved_paths


# ── Legacy compatibility ──────────────────────────────────────────────────────

async def generate_images(image_prompts: list[str], workspace_dir: Path, user_config: dict | None = None) -> list[Path]:
    """Async wrapper — returns list of Path objects."""
    paths = await run_image_generation(image_prompts, output_dir=workspace_dir, user_config=user_config)
    return [Path(p) for p in paths]


if __name__ == "__main__":
    test_prompts = [
        "A futuristic AI robot brain with glowing neural pathways, ultra-realistic, 8K, cinematic lighting",
    ]
    import asyncio
    paths = asyncio.run(generate_images(test_prompts, Path.cwd()))
    for p in paths:
        print(f"  {p}")
