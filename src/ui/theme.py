# src/ui/theme.py
"""
Theme helpers for Win Log Interpreter (Gemini-only)

Provides:
- a small set of named theme palettes (light, dark)
- functions to get/set the active theme
- apply_theme(root) to apply styles to a Tk / ttk root window

Notes:
- Tkinter/ttk has limited styling compared to modern web frameworks.
  This module applies a consistent palette and some ttk Style tweaks.
- Theme persistence uses config/app_settings.json via save_app_settings().
"""

from typing import Dict
import tkinter as tk
from tkinter import ttk

from src.main.config import load_config, save_app_settings
from src.main.constants import DEFAULT_THEME
from src.main.logger import logger

# -----------------------
# Theme palettes
# -----------------------
THEMES: Dict[str, Dict[str, str]] = {
    "light": {
        "bg": "#FFFFFF",
        "fg": "#111827",
        "panel_bg": "#F3F4F6",
        "muted": "#6B7280",
        "accent": "#2563EB",
        "button_bg": "#E5E7EB",
        "button_fg": "#111827",
    },
    "dark": {
        "bg": "#0B1220",
        "fg": "#E6EEF7",
        "panel_bg": "#0F1724",
        "muted": "#9CA3AF",
        "accent": "#60A5FA",
        "button_bg": "#0B1220",
        "button_fg": "#E6EEF7",
    },
}

DEFAULT = DEFAULT_THEME if DEFAULT_THEME in THEMES else "light"


def available_themes():
    """Return a list of available theme names."""
    return list(THEMES.keys())


def get_active_theme_name() -> str:
    """Return current theme name from app settings or default."""
    cfg = load_config()
    name = cfg.get("theme") or cfg.get("THEME") or DEFAULT
    if name not in THEMES:
        return DEFAULT
    return name


def set_active_theme_name(name: str) -> bool:
    """Set the theme name in app_settings.json (persist)."""
    if name not in THEMES:
        logger.warning("Attempted to set unknown theme: %s", name)
        return False
    # load existing settings and update
    cfg = load_config()
    cfg["theme"] = name
    success = save_app_settings(cfg)
    if success:
        logger.info("Saved active theme: %s", name)
    else:
        logger.error("Failed to save active theme: %s", name)
    return success


def _ttk_style_from_palette(pal: Dict[str, str]) -> None:
    """Apply ttk style tweaks based on palette."""
    style = ttk.Style()
    # Ensure using default theme that supports custom configuration
    try:
        style.theme_use("clam")
    except Exception:
        # If 'clam' unavailable, use current theme
        pass

    # General widget background / foreground
    style.configure(".", background=pal["bg"], foreground=pal["fg"])
    style.configure("TFrame", background=pal["panel_bg"])
    style.configure("TLabel", background=pal["panel_bg"], foreground=pal["fg"])
    style.configure("TButton", background=pal["button_bg"], foreground=pal["button_fg"])
    style.map(
        "TButton",
        foreground=[("active", pal["button_fg"])],
        background=[("active", pal["accent"])],
    )
    # Text widgets don't follow ttk, set their colors when created via config
    # but we set some standard options for ttk.Entry
    style.configure("TEntry", fieldbackground=pal["bg"], foreground=pal["fg"])


def apply_theme(root: tk.Tk) -> None:
    """
    Apply the active theme to a Tk root window and its common widgets.

    This function:
    - configures ttk styles
    - sets root background
    - attempts to update existing widgets (frames, labels, buttons, text)
    """
    name = get_active_theme_name()
    pal = THEMES.get(name, THEMES[DEFAULT])
    logger.debug("Applying theme '%s' with palette: %s", name, pal)

    # Root background
    try:
        root.configure(bg=pal["bg"])
    except Exception:
        logger.debug("Failed to configure root background")

    # Apply ttk style tweaks
    _ttk_style_from_palette(pal)

    # Walk widget tree and apply colors to non-ttk widgets (Text, ScrolledText)
    def _apply_recursive(widget):
        # For classic widgets:
        try:
            cls = widget.winfo_class().lower()
        except Exception:
            cls = ""
        # Text-like widgets
        if cls in ("text", "scrolledtext"):
            try:
                widget.configure(bg=pal["panel_bg"], fg=pal["fg"], insertbackground=pal["fg"])
            except Exception:
                pass
        # Frames and labels (non-ttk)
        if cls in ("frame", "labelframe"):
            try:
                widget.configure(bg=pal["panel_bg"])
            except Exception:
                pass
        if cls in ("label",):
            try:
                widget.configure(bg=pal["panel_bg"], fg=pal["fg"])
            except Exception:
                pass
        # Buttons (legacy)
        if cls in ("button",):
            try:
                widget.configure(bg=pal["button_bg"], fg=pal["button_fg"])
            except Exception:
                pass

        # Recurse
        for child in widget.winfo_children():
            _apply_recursive(child)

    try:
        _apply_recursive(root)
    except Exception:
        logger.debug("Failed to walk widget tree for theme application")

    logger.info("Theme '%s' applied", name)


# Small helper to toggle theme
def toggle_theme(root: tk.Tk = None) -> bool:
    """Toggle between light and dark themes. If root is provided, re-apply UI."""
    current = get_active_theme_name()
    names = list(THEMES.keys())
    try:
        next_idx = (names.index(current) + 1) % len(names)
    except ValueError:
        next_idx = 0
    new = names[next_idx]
    ok = set_active_theme_name(new)
    if ok and root:
        apply_theme(root)
    return ok


# If run directly, print available themes
if __name__ == "__main__":
    print("Available themes:", available_themes())
    print("Active theme:", get_active_theme_name())
