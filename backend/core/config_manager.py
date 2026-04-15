"""
core/config_manager.py — JSON-based Configuration Manager (SaaS Sync)
====================================================================
Synchronized version that ensures web-app parity with desktop.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any
from supabase import create_client, Client


# ── Default configuration ───────────────────────────────────────────────────
DEFAULT_CONFIG: dict = {
    "api_keys": {
        "gemini": "",
        "elevenlabs": "",
        "google_tts": "",
        "fal_ai": "",
        "replicate": "",
        "stable_horde": "",
    },
    "tts": {
        "backend": "chatterbox",
        "chatterbox_url": "http://127.0.0.1:8004",
        "chatterbox_path": "",
        "chatterbox_reference_audio": "my_voice_reference.wav",
        "edge_tts_voice": "hi-IN-MadhurNeural",
        "elevenlabs_voice_id": "",
        "google_tts_language": "hi-IN",
        "kokoro_model_path": "",
    },
    "image": {
        "backend": "comfyui",
        "comfyui_url": "http://127.0.0.1:8188",
        "gemini_image_model": "nano_banana",
        "pollinations_model": "dreamshaper",
        "fal_model": "fal-ai/fast-sdxl",
        "replicate_model": "stability-ai/sdxl",
        "image_count": 6,
        "width": 1080,
        "height": 1920,
    },
    "pipeline": {
        "language": "hi",
        "upload_mode": "unlisted",
        "output_folder": "output",
        "gemini_model": "gemini-2.5-flash",
        "chrome_profiles": [],
        "active_profile_index": 0,
    },
}


class ConfigManager:
    _instance: "ConfigManager | None" = None
    _config_path: Path
    _data: dict
    _supabase: Client | None = None

    def __new__(cls, config_path: str | Path | None = None) -> "ConfigManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialised = False  # type: ignore[attr-defined]
        return cls._instance

    def __init__(self, config_path: str | Path | None = None) -> None:
        if self._initialised:  # type: ignore[attr-defined]
            return
        if config_path is None:
            self._config_path = Path(__file__).resolve().parent.parent / "config.json"
        else:
            self._config_path = Path(config_path)
            
        self._data = {}
        self._initialised = True  # type: ignore[attr-defined]
        self._init_supabase()
        self.load()

    def _init_supabase(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if url and key:
            try:
                self._supabase = create_client(url, key)
            except Exception:
                self._supabase = None

    def load(self) -> None:
        """Load local config as base."""
        if not self._config_path.exists():
            self._data = json.loads(json.dumps(DEFAULT_CONFIG))
            self.save()
            return
        with open(self._config_path, "r", encoding="utf-8") as f:
            try:
                self._data = json.load(f)
            except json.JSONDecodeError:
                self._data = json.loads(json.dumps(DEFAULT_CONFIG))
        self._merge_defaults(self._data, DEFAULT_CONFIG)

    def load_user_config(self, user_id: str) -> dict:
        """Fetch user-specific config from Supabase and merge with clean defaults."""
        # Start with a CLEAN base, not the global self._data which might have master keys
        merged = json.loads(json.dumps(DEFAULT_CONFIG))
        
        if not self._supabase:
            return merged
            
        try:
            response = self._supabase.table("user_settings").select("*").eq("user_id", user_id).single().execute()
            if response.data:
                user_data = {
                    "api_keys": response.data.get("api_keys", {}),
                    "tts": response.data.get("tts_settings", {}),
                    "image": response.data.get("image_settings", {}),
                    "pipeline": response.data.get("pipeline_settings", {}),
                }
                # Merge user overrides onto the clean defaults
                self.deep_update(merged, user_data)
                return merged
        except Exception as e:
            # If nothing found or error, return the clean DEFAULT_CONFIG
            pass
            
        return merged

    def save_user_config(self, user_id: str, updates: dict) -> bool:
        """Persist user overrides to Supabase."""
        if not self._supabase:
            return False
            
        db_data = {
            "user_id": user_id,
            "api_keys": updates.get("api_keys", {}),
            "tts_settings": updates.get("tts", {}),
            "image_settings": updates.get("image", {}),
            "pipeline_settings": updates.get("pipeline", {}),
            "updated_at": "now()"
        }
        try:
            self._supabase.table("user_settings").upsert(db_data).execute()
            return True
        except Exception as e:
            print(f"Error saving user config: {e}")
            return False

    def save(self) -> None:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, key_path: str, default: Any = None) -> Any:
        keys = key_path.split(".")
        node = self._data
        for key in keys:
            if isinstance(node, dict) and key in node:
                node = node[key]
            else:
                return default
        return node

    def set(self, key_path: str, value: Any) -> None:
        keys = key_path.split(".")
        node = self._data
        for key in keys[:-1]:
            if key not in node or not isinstance(node[key], dict):
                node[key] = {}
            node = node[key]
        node[keys[-1]] = value

    @property
    def data(self) -> dict: return self._data

    @property
    def supabase(self) -> Client | None: return self._supabase

    @staticmethod
    def deep_update(mapping: dict, *updating_mappings: dict) -> dict:
        for updating_mapping in updating_mappings:
            for k, v in updating_mapping.items():
                if k in mapping and isinstance(mapping[k], dict) and isinstance(v, dict):
                    ConfigManager.deep_update(mapping[k], v)
                else:
                    mapping[k] = v
        return mapping

    @staticmethod
    def _merge_defaults(target: dict, defaults: dict) -> None:
        for key, value in defaults.items():
            if key not in target:
                target[key] = json.loads(json.dumps(value))
            elif isinstance(value, dict) and isinstance(target.get(key), dict):
                ConfigManager._merge_defaults(target[key], value)

config = ConfigManager()
