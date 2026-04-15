"""
core/utils.py — Shared utilities for Hunter Ghost Creator
"""
from core.config_manager import config

def get_user_conf(path: str, user_config: dict | None, default: any = None) -> any:
    """
    Retrieves a configuration value from user_config (per-user Supabase settings)
    with a fallback to the global config (local config.json).
    """
    if user_config:
        parts = path.split('.')
        val = user_config
        found = True
        for p in parts:
            if isinstance(val, dict) and p in val:
                val = val[p]
            else:
                found = False
                break
        if found:
            return val
            
    # Fallback to singleton config manager
    return config.get(path, default)
