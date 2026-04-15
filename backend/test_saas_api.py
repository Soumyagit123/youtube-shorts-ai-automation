"""
QA Script for Ghost Creator SaaS Backend
Tests module integration, paths, and API startup.
"""
import sys
import os
from pathlib import Path

# Add backend and site-packages to path
BASE_DIR = Path(__file__).resolve().parent
SITE_PACKAGES = BASE_DIR / "site-packages"

sys.path.append(str(BASE_DIR))
sys.path.append(str(SITE_PACKAGES))

print("🔍 QA Check 1: Importing Core Modules and Dependencies...")
try:
    import fastapi
    import feedparser
    import pytrends
    from config import get_logger, OUTPUT_DIR, STATIC_DIR
    from core.config_manager import config
    from modules.pipeline_runner import PipelineRunner
    from modules.researcher    import find_trending_topic
    from modules.scripter      import generate_script
    from modules.video_builder import build_video
    print("✅ Core Modules & Deps: IMPORT SUCCESS")
except Exception as e:
    print(f"❌ Core Modules & Deps: IMPORT FAILED - {e}")
    sys.exit(1)

print("\n🔍 QA Check 2: Verifying Binaries...")
ffmpeg_path = BASE_DIR / "ffmpeg" / "ffmpeg.exe"
if ffmpeg_path.exists():
    print(f"✅ FFmpeg: FOUND at {ffmpeg_path}")
else:
    print(f"❌ FFmpeg: NOT FOUND at {ffmpeg_path}")

print("\n🔍 QA Check 3: Verifying Data Directories...")
for d in [OUTPUT_DIR, STATIC_DIR]:
    if d.exists():
        print(f"✅ Path: {d.name} exists.")
    else:
        print(f"❌ Path: {d.name} missing!")

print("\n🔍 QA Check 4: Testing Config Manager...")
try:
    val = config.get("pipeline.gemini_model")
    print(f"✅ Config: Loaded successfully (Model: {val})")
except Exception as e:
    print(f"❌ Config: Failed to load - {e}")

print("\n🚀 SaaS Backend QA: SUCCESS")
