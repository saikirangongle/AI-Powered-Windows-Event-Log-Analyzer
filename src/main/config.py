# src/main/config.py
"""
Configuration loader for Win Log Interpreter (Gemini-only).

Responsibilities:
- Load environment variables.
- Apply defaults from config/default_settings.json.
- Provide a unified config dictionary to the app.

Environment:
    GEMINI_API_KEY     -> Required for API client

Files:
    config/default_settings.json
    config/app_settings.json      (user-modifiable)
"""

import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"

DEFAULT_SETTINGS_FILE = CONFIG_DIR / "default_settings.json"
APP_SETTINGS_FILE = CONFIG_DIR / "app_settings.json"


def _load_json_file(path, fallback=None):
    """Safely load JSON file."""
    if not path.exists():
        return fallback or {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return fallback or {}


def load_config():
    """
    Load settings from:
    1. Default settings JSON
    2. App settings JSON
    3. Environment variables

    Environment values override JSON values.
    """
    config = {}

    # --- Layer 1: Load defaults ---
    defaults = _load_json_file(DEFAULT_SETTINGS_FILE, {})
    config.update(defaults)

    # --- Layer 2: Load user app settings ---
    app_settings = _load_json_file(APP_SETTINGS_FILE, {})
    config.update(app_settings)

    # --- Layer 3: Load environment variables ---
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        config["GEMINI_API_KEY"] = gemini_key

    return config


def save_app_settings(settings: dict):
    """Save settings to app_settings.json."""
    try:
        with open(APP_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
        return True
    except Exception:
        return False


if __name__ == "__main__":
    # Debug print
    print(json.dumps(load_config(), indent=4))
