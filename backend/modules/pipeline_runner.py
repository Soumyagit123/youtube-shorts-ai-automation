"""
modules/pipeline_runner.py — Ghost Creator SaaS Orchestrator v2.5
"""
import asyncio
import uuid
import shutil
from pathlib import Path
from config import get_logger

# Original modules
from modules.researcher    import find_trending_topic
from modules.scripter      import generate_script
from modules.voicer        import generate_voiceover, ensure_chatterbox_running
from modules.image_gen     import generate_images
from modules.video_builder import build_video
from modules.uploader      import upload_to_youtube
import logging
from core.utils            import get_user_conf
from core.config_manager   import config

class StateLogHandler(logging.Handler):
    def __init__(self, state_logs_list, loop=None, queue=None):
        super().__init__()
        self.state_logs_list = state_logs_list
        self.loop = loop
        self.queue = queue

    def emit(self, record):
        try:
            msg = self.format(record)
            # Remove any existing [INFO] prefix to avoid double tags
            clean_msg = msg.replace("[INFO] ", "")
            full_msg = f"[INFO] {clean_msg}"
            
            # Update state list
            self.state_logs_list.append(full_msg)
            
            # Push to WebSocket queue if present
            if self.loop and self.queue:
                try:
                    self.loop.call_soon_threadsafe(self.queue.put_nowait, full_msg)
                except Exception:
                    pass
        except Exception:
            self.handleError(record)

log = get_logger("runner")

class PipelineRunner:
    def __init__(self, state: dict, log_queue=None):
        self.state = state
        self.log_queue = log_queue
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

    def _log(self, msg: str, progress: int | None = None):
        full_msg = f"[INFO] {msg}"
        log.info(full_msg)
        self.state["logs"].append(full_msg)
        if progress is not None:
            self.state["progress"] = progress
        if self.log_queue and self.loop:
            try:
                self.loop.call_soon_threadsafe(self.log_queue.put_nowait, full_msg)
            except Exception:
                pass

    def _check_abort(self):
        if self.state.get("abort"):
            self._log("Pipeline aborted by user. Halting execution.", 0)
            raise Exception("PipelineAborted")

    async def run(self, user_id: str, topic: str | None = None, lang: str = "hi", mode: str = "full", user_config: dict | None = None):
        job_id = str(uuid.uuid4())
        
        # Dynamic workspace isolation
        workspace_dir = Path("workspaces") / f"{user_id}_{job_id}"
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # ── Log Interception Setup ─────────────────────────────────────
            # Capture logs from our specific modules and redirect to the UI state
            handler = StateLogHandler(self.state["logs"], self.loop, self.log_queue)
            handler.setFormatter(logging.Formatter("%(message)s"))
            
            # Attach to key modules
            target_loggers = ["runner", "scripter", "voicer", "image_gen", "video_builder", "uploader"]
            for name in target_loggers:
                logging.getLogger(name).addHandler(handler)

            self._log(f"Initializing Neural Pipeline [Mode: {mode.upper()}] [Job: {job_id}]", 5)

            # DB Record
            if config.supabase:
                try:
                    config.supabase.table("video_jobs").insert({
                        "id": job_id, 
                        "user_id": user_id, 
                        "status": "running",
                        "topic": topic or "Brainstorming..."
                    }).execute()
                except Exception as e:
                    log.warning(f"Failed to insert job record: {e}")

            if mode == "full":
                if not topic:
                    self._log("Brainstorming trending topic...", 10)
                    topic = await find_trending_topic(user_config=user_config)
                    self._log(f"Selected Topic: {topic}", 20)
                else:
                    self._log(f"Using manual topic: {topic}", 20)

                self._check_abort()
                self._log("Generating script via Gemini...", 30)
                script = await generate_script(topic, lang=lang, user_config=user_config)

                # Only check Chatterbox if chatterbox is the selected TTS backend
                tts_backend = get_user_conf("tts.backend", user_config, "edge_tts")
                if tts_backend == "chatterbox":
                    if not (await ensure_chatterbox_running(user_config=user_config)):
                        self._log("ERROR: Chatterbox not responding. Check settings or switch TTS backend.", 0)
                        return

                self._check_abort()
                # --- 3. Voicer ---
                self._log("Synthesizing voiceover...", 40)
                try:
                    audio_path = await generate_voiceover(script["voiceover_text"], workspace_dir=workspace_dir, user_config=user_config)
                except Exception as e:
                    self._log(f"Voiceover Synthesis Failed: {e}", 0)
                    raise e

                self._check_abort()
                self._log(f"Generating {len(script['image_prompts'])} images...", 70)
                image_paths = await generate_images(script["image_prompts"], workspace_dir=workspace_dir, user_config=user_config)

                self._check_abort()
                self._log("Building video...", 90)
                video_path = await build_video(
                    image_paths=image_paths,
                    audio_path=audio_path,
                    voiceover_text=script["voiceover_text"],
                    title=script["metadata"]["title"],
                    workspace_dir=workspace_dir
                )

                self._check_abort()
                self._log("Uploading to Storage...", 95)
                
                # Handle Supabase storage upload
                if config.supabase:
                    try:
                        storage_path = f"{user_id}/{job_id}/final_short.mp4"
                        with open(video_path, "rb") as f:
                            # Use application/mp4 to ensure it streams correctly in browsers
                            config.supabase.storage.from_("youtube-automation").upload(storage_path, f, file_options={"content-type": "video/mp4"})
                        
                        public_url = config.supabase.storage.from_("youtube-automation").get_public_url(storage_path)
                        self.state["current_video_url"] = public_url
                        
                        # Sync to DB
                        config.supabase.table("video_jobs").update({"status": "completed", "video_url": public_url}).eq("id", job_id).execute()
                        
                        # --- 10b. YouTube Auto-Upload ---
                        self._log("Initiating YouTube Auto-Upload...", 98)
                        try:
                            # Pass the user_config so uploader knows which Chrome Profile to use
                            await upload_to_youtube(video_path, script["metadata"], user_config=user_config)
                            self._log("YouTube upload successful!", 100)
                        except Exception as ye:
                            self._log(f"YouTube Upload Failed: {ye}", 100)
                            log.error(f"YouTube upload error: {ye}")

                    except Exception as e:
                        log.error(f"Storage upload failed: {e}")
                        self.state["current_video_url"] = None
                else:
                    self._log("Supabase not configured, skipping cloud upload.", 100)
                    self.state["current_video_url"] = None

                self._log("Process complete! Video is ready.", 100)

                # --- 11. Cleanup (Optional: only if you want to save space immediately) ---
                # The user requested to keep images/videos until uploaded.
                # Since we are here, everything is uploaded.
                # We'll do the actual rmtree in the finally block but with checks.

            else:
                self._log(f"ERROR: Legacy mode '{mode}' is not supported in the SaaS environment.", 0)
                return

        except Exception as e:
            if config.supabase:
                try:
                    config.supabase.table("video_jobs").update({"status": "failed"}).eq("id", job_id).execute()
                except Exception:
                    pass
            if str(e) == "PipelineAborted":
                self.state["progress"] = 0
                return
            self._log(f"CRITICAL ERROR: {str(e)}")
            log.error(f"Pipeline failed: {e}", exc_info=True)
        finally:
            # Clean up logging handler
            try:
                for name in ["runner", "scripter", "voicer", "image_gen", "video_builder", "uploader"]:
                    logging.getLogger(name).removeHandler(handler)
            except Exception:
                pass

            self.state["running"] = False
            self.state["abort"] = False
            # Clean up isolated workspace securely AFTER upload (as requested)
            if workspace_dir.exists():
                try:
                    # We only clear if the job finished or failed (finally covers both)
                    # But we ensure it's logged clearly.
                    shutil.rmtree(workspace_dir)
                    log.info(f"Cleaned up workspace {workspace_dir}")
                except Exception as e:
                    log.error(f"Failed to cleanup workspace {workspace_dir}: {e}")
