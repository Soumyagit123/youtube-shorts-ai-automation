"""
backend/main.py — Ghost Creator SaaS API v2.5
"""
import asyncio
import os
import sys
import uuid
from pathlib import Path
from typing import List, Optional

# Path Setup
BASE_DIR = Path(__file__).resolve().parent
SITE_PACKAGES = BASE_DIR / "site-packages"
sys.path.append(str(BASE_DIR))
sys.path.append(str(SITE_PACKAGES))

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException, Depends, Security, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from supabase import create_client, Client

from config import get_logger, OUTPUT_DIR
from core.config_manager import config
from modules.pipeline_runner import PipelineRunner

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    asyncio.create_task(manager.broadcast_logs())
    yield
    # Shutdown logic

app = FastAPI(title="Ghost Creator AI SaaS API", lifespan=lifespan)
log = get_logger("api")

# Supabase Auth Setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="outputs")

# --- Auth Dependency ---
async def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    token = authorization.split(" ")[1]
    if not supabase:
        # Fallback for local dev if Supabase is not configured
        return {"id": "local-dev-user", "email": "local@example.com"}

    try:
        user_resp = supabase.auth.get_user(token)
        if not user_resp or not user_resp.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_resp.user
    except Exception as e:
        log.error(f"Auth error: {e}")
        # Allow local dev even if key is provided but invalid (only if SUPABASE_URL is missing)
        if not SUPABASE_URL:
            return {"id": "local-dev-user", "email": "local@example.com"}
        raise HTTPException(status_code=401, detail="Authentication failed")

# --- WebSocket Manager (Per-User isolation needed) ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, List[WebSocket]] = {} # user_id -> list of websockets

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        log.info(f"WebSocket connected for user: {user_id}")

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                self.active_connections.pop(user_id, None)
        log.info(f"WebSocket disconnected for user: {user_id}")

    async def broadcast_logs(self):
        """Continuously poll all user runners and push logs to their WebSockets."""
        log.info("Log Broadcaster started.")
        while True:
            try:
                # Iterate over a copy of user_runners to avoid concurrency issues
                for user_id, runner in list(user_runners.items()):
                    if not runner.queue:
                        continue
                    
                    # Pull all available logs from this user's queue
                    while not runner.queue.empty():
                        msg = await runner.queue.get()
                        
                        # Send to all active connections for this user
                        if user_id in self.active_connections:
                            dead_links = []
                            for ws in self.active_connections[user_id]:
                                try:
                                    await ws.send_text(msg)
                                except Exception:
                                    dead_links.append(ws)
                            
                            # Clean up broken connections
                            for ws in dead_links:
                                self.disconnect(ws, user_id)
                
                await asyncio.sleep(0.1)  # High frequency polling
            except Exception as e:
                log.error(f"Error in broadcast_logs: {e}")
                await asyncio.sleep(1)

manager = ConnectionManager()

# --- State (Per-User isolation needed) ---
# For a production SaaS, this state should be in Redis or Postgres
user_runners: dict[str, PipelineRunner] = {}
user_states: dict[str, dict] = {}

def get_user_state(user_id: str):
    if user_id not in user_states:
        user_states[user_id] = {
            "running": False,
            "progress": 0,
            "logs": [],
            "current_video_url": None,
            "abort": False
        }
    return user_states[user_id]

def get_user_runner(user_id: str):
    if user_id not in user_runners:
        log_queue = asyncio.Queue()
        user_runners[user_id] = PipelineRunner(get_user_state(user_id), log_queue)
    return user_runners[user_id]

# --- Models ---
class RunRequest(BaseModel):
    topic: Optional[str] = None
    language: str = "hi"
    mode: str = "full"

# --- Endpoints ---

@app.get("/api/health")
async def health():
    return {"status": "online", "mode": "saas-multi-tenant"}

@app.get("/api/settings")
async def get_settings(user: dict = Depends(get_current_user)):
    user_id = user["id"] if isinstance(user, dict) else user.id
    user_config = config.load_user_config(user_id)
    return user_config

@app.post("/api/settings")
async def update_settings(data: dict, user: dict = Depends(get_current_user)):
    user_id = user["id"] if isinstance(user, dict) else user.id
    success = config.save_user_config(user_id, data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save settings")
    return {"status": "saved"}

class SetupProfileRequest(BaseModel):
    name: str

@app.post("/api/settings/setup_profile")
async def setup_profile(req: SetupProfileRequest, user: dict = Depends(get_current_user)):
    user_id = user["id"] if isinstance(user, dict) else user.id
    
    # We run the setup script as a detached process because it opens a GUI window
    # on the user's desktop (since we are on Windows/Local).
    import subprocess
    try:
        root_dir = BASE_DIR.parent.parent
        script_path = str(root_dir / "setup_chrome_profile.py")
        
        # Priority: Root VENV (has all deps) -> Current VENV
        root_python = root_dir / "venv" / "Scripts" / "python.exe"
        python_exe = str(root_python) if root_python.exists() else sys.executable
        
        log.info(f"Launching setup script: {python_exe} {script_path} --name {req.name} --user-id {user_id} (CWD: {root_dir})")
        
        subprocess.Popen([python_exe, script_path, "--name", req.name, "--user-id", user_id], 
                        cwd=str(root_dir),
                        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
        return {"status": "setup_triggered", "msg": "A new window has opened on the server to guide you through login."}
    except Exception as e:
        log.error(f"Failed to launch setup script: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/settings/profile/{index}")
async def remove_profile(index: int, user: dict = Depends(get_current_user)):
    user_id = user["id"] if isinstance(user, dict) else user.id
    user_config = config.load_user_config(user_id)
    
    profiles = user_config.get("pipeline", {}).get("chrome_profiles", [])
    if 0 <= index < len(profiles):
        profiles.pop(index)
        user_config["pipeline"]["chrome_profiles"] = profiles
        # Reset active index if needed
        if user_config["pipeline"]["active_profile_index"] >= len(profiles):
            user_config["pipeline"]["active_profile_index"] = max(0, len(profiles) - 1)
        
        config.save_user_config(user_id, user_config)
        return {"status": "removed"}
    
    raise HTTPException(status_code=404, detail="Profile not found")

@app.get("/api/settings/profiles/scan")
async def scan_profiles(user: dict = Depends(get_current_user)):
    r"""Scan D:\ChromeProfiles for existing GhostCreator profiles."""
    profiles_dir = Path(r"D:\ChromeProfiles")
    found = []
    if profiles_dir.exists():
        for item in profiles_dir.iterdir():
            if item.is_dir() and item.name.startswith("GhostCreator_"):
                display_name = item.name.replace("GhostCreator_", "").replace("_", " ")
                found.append({
                    "name": display_name,
                    "path": str(item).replace("\\", "/"),
                    "profile_name": "Default"
                })
    return found

@app.post("/api/pipeline/run")
async def run_pipeline(req: RunRequest, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    user_id = user["id"] if isinstance(user, dict) else user.id
    state = get_user_state(user_id)
    runner = get_user_runner(user_id)

    if state["running"]:
        raise HTTPException(status_code=400, detail="Neural Processor Busy — wait for current run to finish.")

    job_id = str(uuid.uuid4())
    state["running"] = True
    state["progress"] = 0
    state["logs"] = []
    state["current_video_url"] = None
    state["abort"] = False
    state["job_id"] = job_id

    # Load user-specific settings for the run
    user_config = config.load_user_config(user_id)

    background_tasks.add_task(runner.run, user_id=user_id, topic=req.topic, lang=req.language, mode=req.mode, user_config=user_config)
    return {"status": "started", "job_id": job_id}

@app.post("/api/pipeline/reset")
async def reset_pipeline(user: dict = Depends(get_current_user)):
    """Force-reset the pipeline state (use if a run got stuck)."""
    user_id = user["id"] if isinstance(user, dict) else user.id
    state = get_user_state(user_id)
    state["running"] = False
    state["progress"] = 0
    state["logs"] = ["[INFO] Pipeline state reset manually."]
    state["abort"] = False
    return {"status": "reset"}

@app.post("/api/pipeline/abort")
async def abort_pipeline(user: dict = Depends(get_current_user)):
    """Signal the background runner to abort gracefully."""
    user_id = user["id"] if isinstance(user, dict) else user.id
    state = get_user_state(user_id)
    if state["running"]:
        state["abort"] = True
        state["logs"].append("[INFO] Abort signal sent. Pipeline will halt safely...")
    return {"status": "aborting"}

@app.get("/api/pipeline/status")
async def get_status(user: dict = Depends(get_current_user)):
    user_id = user["id"] if isinstance(user, dict) else user.id
    state = get_user_state(user_id)
    return {
        "running": state["running"],
        "progress": state["progress"],
        "logs": state["logs"][-25:],
        "video_url": state["current_video_url"]
    }

@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket, token: str = Header(...)):
    # Simple token check for WS (in prod, use a proper auth flow)
    if not supabase:
        user_id = "local-dev-user"
    else:
        try:
            user_resp = supabase.auth.get_user(token)
            user_id = user_resp.user.id
        except:
            await websocket.close(code=1008)
            return

    await manager.connect(websocket, user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

if __name__ == "__main__":
    import uvicorn
    # access_log=False prevents the terminal from being flooded with status pooling requests from the UI
    uvicorn.run(app, host="127.0.0.1", port=8000, access_log=False)
