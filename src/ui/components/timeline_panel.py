# src/ui/components/timeline_panel.py
"""
Timeline Panel Component
------------------------

A vertical timeline view for Windows events.

Features:
- Displays events in chronological order
- Attempts to extract timestamps automatically
- Click on an event to view full details (callback)
- Scrollable canvas-based timeline layout

Public API:
- load_events(events: list[str])
- clear()
- set_on_select(callback: function(event_text: str))
"""

import tkinter as tk
from tkinter import ttk
import re

from src.main.logger import logger


class TimelinePanel(ttk.Frame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, padding=5, **kwargs)

        ttk.Label(self, text="Event Timeline", font=("Arial", 11, "bold")).pack(anchor="w")

        # Scrollable Canvas
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        self.canvas = tk.Canvas(container, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas.configure(yscrollcommand=scrollbar.set)

        # Frame inside canvas
        self.inner_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

        self.inner_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Selection callback
        self._on_select_callback = None

        # Internal event cache
        self.events = []

    # -------------------------------------------------------------
    # Layout auto adjustment
    # -------------------------------------------------------------
    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    # -------------------------------------------------------------
    # Timestamp extraction (simple heuristic)
    # -------------------------------------------------------------
    def _extract_timestamp(self, text: str) -> str:
        """
        Try to detect timestamps such as:
        2024-01-25 10:33:22
        01/25/2024 10:33 AM
        25-01-2024 12:00:10
        """
        patterns = [
            r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}",
            r"\d{2}/\d{2}/\d{4} \d{1,2}:\d{2}(?: AM| PM)?",
            r"\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2}",
        ]

        for p in patterns:
            m = re.search(p, text)
            if m:
                return m.group(0)

        return "(No timestamp)"

    # -------------------------------------------------------------
    # Load events into timeline
    # -------------------------------------------------------------
    def load_events(self, events):
        self.clear()
        self.events = events

        for idx, ev in enumerate(events, start=1):
            timestamp = self._extract_timestamp(ev)
            self._add_timeline_entry(idx, timestamp, ev)

        logger.info("Timeline loaded with %d events", len(events))

    # -------------------------------------------------------------
    # Add timeline entry widget
    # -------------------------------------------------------------
    def _add_timeline_entry(self, index: int, timestamp: str, text: str):
        frame = ttk.Frame(self.inner_frame, padding=5)
        frame.pack(fill=tk.X, anchor="w", pady=2)

        # Dot + connecting line style timeline marker
        marker_canvas = tk.Canvas(frame, width=20, height=20, highlightthickness=0)
        marker_canvas.pack(side=tk.LEFT)
        marker_canvas.create_oval(6, 6, 14, 14, fill="#2563EB", outline="")

        # Event box
        event_frame = ttk.Frame(frame, padding=(10, 5))
        event_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        lbl_time = ttk.Label(event_frame, text=timestamp, foreground="#6B7280")
        lbl_time.pack(anchor="w")

        lbl_event = ttk.Label(event_frame, text=text, wraplength=600, justify=tk.LEFT)
        lbl_event.pack(anchor="w")

        # Bind click
        lbl_event.bind("<Button-1>", lambda e, content=text: self._handle_select(content))
        lbl_time.bind("<Button-1>", lambda e, content=text: self._handle_select(content))

    # -------------------------------------------------------------
    # Click handler
    # -------------------------------------------------------------
    def _handle_select(self, event_text: str):
        if self._on_select_callback:
            self._on_select_callback(event_text)

    # -------------------------------------------------------------
    # Set callback
    # -------------------------------------------------------------
    def set_on_select(self, callback):
        """Callback receives event_text of clicked timeline item."""
        self._on_select_callback = callback

    # -------------------------------------------------------------
    # Clear timeline
    # -------------------------------------------------------------
    def clear(self):
        for w in self.inner_frame.winfo_children():
            w.destroy()
        self.events = []


# Standalone widget test
if __name__ == "__main__":
    root = tk.Tk()
    root.title("TimelinePanel Test")
    panel = TimelinePanel(root)
    panel.pack(fill=tk.BOTH, expand=True)

    events = [
        "2024-01-25 10:33:22 - Service failed to start",
        "User login failed for admin (wrong password)",
        "Connection timeout occurred at 10:34 AM",
        "System reboot completed successfully",
    ]

    panel.load_events(events)
    panel.set_on_select(lambda t: print("Clicked event:", t))

    root.mainloop()
