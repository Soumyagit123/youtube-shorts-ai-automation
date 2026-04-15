"""
Full Pipeline Test for Ghost Creator SaaS
Runs all steps from research to video assembly.
"""
import sys
import os
import asyncio
from pathlib import Path

# Add backend and site-packages to path
BASE_DIR = Path(__file__).resolve().parent
SITE_PACKAGES = BASE_DIR / "site-packages"
sys.path.append(str(BASE_DIR))
sys.path.append(str(SITE_PACKAGES))

from modules.pipeline_runner import PipelineRunner
from core.config_manager import config

class MockState:
    running = False
    progress = 0
    logs = []
    current_video_url = None

async def main():
    state = MockState()
    runner = PipelineRunner(state)
    
    print("🚀 STARTING FULL PIPELINE TEST (TOPIC: 'Ghost AI Test')")
    print("Note: Step 6 (Upload) will be logic-checked but not fully executed to prevent browser hangs.")
    
    # Run the runner (it's synchronous in its current implementation, calling from thread)
    # We will run it directly here for testing
    runner.run(topic="Ghost AI Test video", lang="hi")
    
    print("\n--- TEST LOGS ---")
    for log in state.logs:
        print(log)
    
    print("\n--- FINAL STATUS ---")
    print(f"Progress: {state.progress}%")
    print(f"Video URL: {state.current_video_url}")
    
    if state.progress == 100:
        print("\n✅ FULL PIPELINE FLOW: SUCCESS")
    else:
        print("\n❌ FULL PIPELINE FLOW: FAILED / INCOMPLETED")

if __name__ == "__main__":
    asyncio.run(main())
