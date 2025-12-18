# src/ui/components/explanation_panel.py
"""
Explanation Panel Component

A reusable Tkinter component that displays AI explanations in a scrollable text area
with utility actions: copy to clipboard, save to file, clear, and basic search.

Public methods:
- set_text(text: str)
- append_text(text: str)
- clear()
- get_text() -> str

Designed to be embedded in the main UI.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from typing import Optional

from src.main.logger import logger


class ExplanationPanel(ttk.Frame):
    def __init__(self, master=None, height: int = 20, **kwargs):
        super().__init__(master, padding=5, **kwargs)

        # Header
        header = ttk.Frame(self)
        header.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(header, text="AI Explanation", font=("Arial", 11, "bold")).pack(side=tk.LEFT)

        btns = ttk.Frame(header)
        btns.pack(side=tk.RIGHT)

        ttk.Button(btns, text="Copy", command=self.copy_to_clipboard).pack(side=tk.LEFT, padx=3)
        ttk.Button(btns, text="Save...", command=self.save_to_file).pack(side=tk.LEFT, padx=3)
        ttk.Button(btns, text="Clear", command=self.clear).pack(side=tk.LEFT, padx=3)

        # Search box
        search_frame = ttk.Frame(self)
        search_frame.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 6))
        self._search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self._search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(search_frame, text="Find", command=self.find_next).pack(side=tk.LEFT, padx=4)

        # Text area
        self.text = ScrolledText(self, wrap=tk.WORD, height=height)
        self.text.pack(fill=tk.BOTH, expand=True)
        # configure default tags
        self.text.tag_configure("highlight", background="#FFF59D")  # light yellow highlight

    # ----------------------
    # Public API
    # ----------------------
    def set_text(self, text: str):
        """Replace content with `text` and move view to top."""
        self.text.delete(1.0, tk.END)
        self.text.insert(tk.END, text or "")
        self.text.mark_set(tk.INSERT, "1.0")
        self.text.see("1.0")

    def append_text(self, text: str):
        """Append additional text."""
        self.text.insert(tk.END, text or "")

    def clear(self):
        """Clear the explanation area."""
        self.text.delete(1.0, tk.END)

    def get_text(self) -> str:
        """Return the current content as a string."""
        return self.text.get(1.0, tk.END).rstrip("\n")

    # ----------------------
    # Utilities
    # ----------------------
    def copy_to_clipboard(self):
        """Copy current text to the system clipboard."""
        content = self.get_text()
        if not content:
            messagebox.showinfo("Copy", "Nothing to copy.")
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(content)
            messagebox.showinfo("Copy", "Explanation copied to clipboard.")
        except Exception as exc:
            logger.exception("Failed to copy to clipboard: %s", exc)
            messagebox.showerror("Copy Error", f"Failed to copy: {exc}")

    def save_to_file(self):
        """Save the explanation to a user-selected file."""
        content = self.get_text()
        if not content:
            messagebox.showinfo("Save", "Nothing to save.")
            return

        path = filedialog.asksaveasfilename(
            title="Save Explanation",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("Save", f"Saved explanation to:\n{path}")
        except Exception as exc:
            logger.exception("Failed to save explanation: %s", exc)
            messagebox.showerror("Save Error", f"Failed to save file: {exc}")

    # ----------------------
    # Search / Highlight
    # ----------------------
    def find_next(self):
        """Find next occurrence of the search term and highlight it."""
        term = (self._search_var.get() or "").strip()
        if not term:
            messagebox.showinfo("Search", "Enter a search term.")
            return

        start_pos = self.text.index(tk.INSERT)
        # remove previous highlights
        self.text.tag_remove("highlight", "1.0", tk.END)

        idx = self.text.search(term, start_pos, nocase=True, stopindex=tk.END)
        if not idx:
            # try from top
            idx = self.text.search(term, "1.0", nocase=True, stopindex=start_pos)

        if not idx:
            messagebox.showinfo("Search", f"'{term}' not found.")
            return

        # determine end index
        end_idx = f"{idx}+{len(term)}c"
        # highlight
        self.text.tag_add("highlight", idx, end_idx)
        self.text.mark_set(tk.INSERT, end_idx)
        self.text.see(idx)

    # ----------------------
    # Helper to expose clipboard to parent (when embedding)
    # ----------------------
    def clipboard_clear(self):
        try:
            self.master.clipboard_clear()
        except Exception:
            # fallback to self
            pass

    def clipboard_append(self, text: str):
        try:
            self.master.clipboard_append(text)
        except Exception:
            # fallback to self
            pass


# Standalone test
if __name__ == "__main__":
    root = tk.Tk()
    root.title("ExplanationPanel Test")
    panel = ExplanationPanel(root)
    panel.pack(fill=tk.BOTH, expand=True)
    panel.set_text("This is a test explanation.\n\nSteps:\n1. Check logs\n2. Verify service\n\nEnd of explanation.")
    root.mainloop()
