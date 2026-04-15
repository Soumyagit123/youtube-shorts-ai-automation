"""
Integration Test for Frontend-Backend link.
Checks if WebSocket receives logs when a run is triggered.
"""
import sys
import asyncio
import requests
import websockets
import threading
import time
from pathlib import Path

# Add backend and site-packages to path
BASE_DIR = Path(__file__).resolve().parent
SITE_PACKAGES = BASE_DIR / "site-packages"
sys.path.append(str(BASE_DIR))
sys.path.append(str(SITE_PACKAGES))

async def test_integration():
    print("🚀 INTEGRATION TEST: Verifying WebSocket -> Pipeline Link")
    
    # 1. Trigger the run via HTTP POST
    try:
        res = requests.post("http://localhost:8000/api/pipeline/run", 
                           json={"topic": "Integration Test Topic", "language": "hi"})
        if res.status_code == 200:
            print("✅ API: Pipeline Run Triggered Successfully")
        else:
            print(f"❌ API: Failed to trigger run ({res.status_code})")
            return
    except Exception as e:
        print(f"❌ API: Connection Failed - {e}")
        return

    # 2. Connect to WebSocket and listen for logs
    uri = "ws://localhost:8000/ws/logs"
    print(f"📡 WEBSOCKET: Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WEBSOCKET: Connected!")
            # We wait for at least 3 logs to prove it's working
            logs_received = 0
            while logs_received < 3:
                message = await asyncio.wait_for(websocket.recv(), timeout=10)
                print(f"📥 RECEIVED LOG: {message}")
                logs_received += 1
            print("✅ INTEGRATION: REAL-TIME LOGS VERIFIED")
    except Exception as e:
        print(f"❌ WEBSOCKET: Test Failed - {e}")

if __name__ == "__main__":
    # This test assumes the FastAPI server is ALREADY running
    asyncio.run(test_integration())
