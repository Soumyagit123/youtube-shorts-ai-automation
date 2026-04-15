"""
config.py — Centralised settings for SaaS Backend
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Try to import colorlog, but don't fail if it's missing (helps with disk space issues)
try:
    import colorlog
    HAS_COLORLOG = True
except ImportError:
    HAS_COLORLOG = False

load_dotenv()

# ── Directory Layout ───────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent
OUTPUT_DIR  = BASE_DIR / "output"
TEMP_DIR    = BASE_DIR / "temp"
STATIC_DIR  = BASE_DIR / "static"
# Link to parent for workflow_api.json
WORKFLOW_JSON = BASE_DIR.parent.parent / "workflow_api.json"

OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

# ── API Keys ───────────────────────────────────────────────────────────────────
GEMINI_API_KEY      = os.getenv("GEMINI_API_KEY", "")

# ── Video Settings ─────────────────────────────────────────────────────────────
VIDEO_WIDTH  = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS    = 30

# ── Gemini Model ───────────────────────────────────────────────────────────────
GEMINI_MODEL = "gemini-2.5-flash"

# ── Language Settings ──────────────────────────────────────────────────────────
VOICEOVER_LANG = os.getenv("VOICEOVER_LANG", "hindi")

# ── Default Topics ─────────────────────────────────────────────────────────────
DEFAULT_TOPICS = [
    "AI Robots That Can Feel Emotions",
    "OpenAI's Secret New Model That Changes Everything",
    "Google's AI Can Now Write Full Apps in Seconds",
]

# ── Logging ────────────────────────────────────────────────────────────────────
def get_logger(name: str) -> logging.Logger:
    """Return a logger for any module."""
    if HAS_COLORLOG:
        handler = colorlog.StreamHandler()
        handler.setFormatter(colorlog.ColoredFormatter(
            "%(log_color)s[%(asctime)s] %(levelname)-8s%(reset)s %(cyan)s%(name)s%(reset)s › %(message)s",
            datefmt="%H:%M:%S",
            log_colors={
                "DEBUG":    "white",
                "INFO":     "green",
                "WARNING":  "yellow",
                "ERROR":    "red",
                "CRITICAL": "bold_red",
            }
        ))
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "[%(asctime)s] %(levelname)-8s %(name)s › %(message)s",
            datefmt="%H:%M:%S"
        ))
    
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger
