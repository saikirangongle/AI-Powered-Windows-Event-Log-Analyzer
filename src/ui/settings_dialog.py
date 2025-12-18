# src/ui/settings_dialog.py
"""
Settings dialog (Gemini-only) — updated to support callback on save.

Features:
- Load & display current Gemini API key
- Edit and save Gemini API key
- Mask key when showing it
- Save to config/app_settings.json using save_app_settings()
- Accepts optional on_save_callback(new_key) which is called after successful save
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional

from src.main.config import load_config, save_app_settings
from src.main.logger import logger
from src.utils.validators import is_valid_api_key


class SettingsDialog(tk.Toplevel):
    def __init__(self, master=None, on_save_callback: Optional[Callable[[str], None]] = None):
        super().__init__(master)
        self.on_save_callback = on_save_callback

        self.title("Settings — Gemini API")
        self.geometry("480x260")
        self.resizable(False, False)

        self.config_data = load_config()
        # Read either uppercase or lowercase keys if present for compatibility
        self.current_key = self.config_data.get("GEMINI_API_KEY", "") or self.config_data.get("gemini_api_key", "")

        padding = {"padx": 12, "pady": 8}
        ttk.Label(self, text="Gemini API Key", font=("Arial", 12, "bold")).pack(**padding)

        # Entry field (plain text not shown as stars so user can verify; also provide mask preview)
        self.key_var = tk.StringVar(value=self.current_key)
        self.key_entry = ttk.Entry(self, textvariable=self.key_var, width=56)
        self.key_entry.pack(**padding)
        self.key_entry.focus_set()

        # Masked preview + info
        self.preview_label = ttk.Label(self, text=self._mask_key(self.current_key))
        self.preview_label.pack(pady=(0, 8))

        info = (
            "Paste your Gemini API key above and click Save. "
            "This will persist the key to config/app_settings.json.\n"
            "After saving, analysis and explanation features will be enabled."
        )
        ttk.Label(self, text=info, wraplength=440).pack(padx=12, pady=(0, 8))

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=(6, 10))
        save_btn = ttk.Button(btn_frame, text="Save", command=self.save_key)
        save_btn.grid(row=0, column=0, padx=6)
        clear_btn = ttk.Button(btn_frame, text="Clear Key", command=self.clear_key)
        clear_btn.grid(row=0, column=1, padx=6)
        close_btn = ttk.Button(btn_frame, text="Close", command=self.destroy)
        close_btn.grid(row=0, column=2, padx=6)

    def _mask_key(self, key: str) -> str:
        if not key:
            return "No key set"
        if len(key) <= 8:
            return "****"
        return f"{key[:4]}{'*'*(len(key)-8)}{key[-4:]}"

    def save_key(self):
        new_key = self.key_var.get().strip()
        if not new_key:
            messagebox.showerror("Error", "API key cannot be empty.")
            return
        if not is_valid_api_key(new_key):
            messagebox.showerror("Error", "API key seems invalid (too short).")
            return

        # Save into app_settings.json (write both uppercase and lowercase keys for compatibility)
        try:
            # Preserve any existing settings, update the key under both expected names
            cfg = load_config()
            cfg["GEMINI_API_KEY"] = new_key
            cfg["gemini_api_key"] = new_key  # normalized key name for other modules
            ok = save_app_settings(cfg)
            if not ok:
                raise RuntimeError("Failed to write config file")
            self.preview_label.config(text=self._mask_key(new_key))
            messagebox.showinfo("Saved", "Gemini API key saved successfully.")
            logger.info("Gemini API key saved via Settings dialog.")

            # Invoke callback so UI can dynamically initialize Gemini client
            if callable(self.on_save_callback):
                try:
                    self.on_save_callback(new_key)
                except Exception:
                    logger.exception("on_save_callback raised an exception after saving API key.")
        except Exception as exc:
            logger.exception("Failed to save Gemini API key: %s", exc)
            messagebox.showerror("Error", f"Failed to save settings: {exc}")

    def clear_key(self):
        # Clear key from settings file (remove both key variants)
        try:
            cfg = load_config()
            cfg.pop("GEMINI_API_KEY", None)
            cfg.pop("gemini_api_key", None)
            ok = save_app_settings(cfg)
            if not ok:
                raise RuntimeError("Failed to clear key in config file")
            self.key_var.set("")
            self.preview_label.config(text="No key set")
            messagebox.showinfo("Cleared", "Gemini API key removed from settings.")
            if callable(self.on_save_callback):
                # Inform caller that key was cleared (pass empty string)
                try:
                    self.on_save_callback("")
                except Exception:
                    logger.exception("on_save_callback raised an exception after clearing API key.")
        except Exception as exc:
            logger.exception("Failed to clear Gemini API key: %s", exc)
            messagebox.showerror("Error", f"Failed to clear settings: {exc}")
