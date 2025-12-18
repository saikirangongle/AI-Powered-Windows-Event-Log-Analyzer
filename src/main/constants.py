# src/main/constants.py
"""
Application-wide constants for Win Log Interpreter (Gemini-only).
Keep configuration keys, default values and commonly used literals here.
"""

from pathlib import Path

APP_NAME = "Win Log Interpreter"
APP_SLUG = "win-log-interpreter"
VERSION = "0.1.0"

# File system
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SRC_DIR = ROOT_DIR / "src"
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = SRC_DIR / "data"
ASSETS_DIR = ROOT_DIR / "assets"

# Environment variable names
ENV_GEMINI_API_KEY = "GEMINI_API_KEY"

# Default filenames
DEFAULT_SETTINGS_FILE = CONFIG_DIR / "default_settings.json"
APP_SETTINGS_FILE = CONFIG_DIR / "app_settings.json"

# Network / API defaults (replace base with real Gemini endpoint when known)
GEMINI_DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com"
GEMINI_API_VERSION = "v1beta"
GEMINI_DEFAULT_MODEL = "models/gemini-2.5-flash"

# Logging / runtime
LOGGER_NAME = "win-log-interpreter"

# UI hints
DEFAULT_THEME = "light"

# Misc
SUPPORTED_FILE_EXTENSIONS = [".evtx", ".log", ".txt", ".json"]
