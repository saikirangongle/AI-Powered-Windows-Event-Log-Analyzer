# src/ui/components/logs_table.py
"""
Logs Table Component
--------------------

A reusable ttk.Treeview-based table for displaying event logs
with columns such as timestamp, severity, and short description.

Features:
- add_row(timestamp, severity, summary, raw_event)
- load_rows(list[dict])
- clear()
- get_selected() -> dict or None
- on_double_click(callback)

Designed to be used together with event analyzer.
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Any


class LogsTable(ttk.Frame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, padding=5, **kwargs)

        ttk.Label(self, text="Log Table", font=("Arial", 11, "bold")).pack(anchor="w")

        # Table setup
        columns = ("timestamp", "severity", "summary")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Column configuration
        self.tree.heading("timestamp", text="Timestamp", command=lambda: self._sort_by("timestamp"))
        self.tree.heading("severity", text="Severity", command=lambda: self._sort_by("severity"))
        self.tree.heading("summary", text="Summary", command=lambda: self._sort_by("summary"))

        self.tree.column("timestamp", width=170, anchor="w")
        self.tree.column("severity", width=100, anchor="center")
        self.tree.column("summary", width=600, anchor="w")

        # Store raw event content for each row
        self._raw_event_map = {}

        # Double-click callback
        self._double_click_callback = None
        self.tree.bind("<Double-1>", self._on_double_click)

    # -----------------------------------------------------
    # Add a row to the table
    # -----------------------------------------------------
    def add_row(self, timestamp: str, severity: str, summary: str, raw_event: str):
        item_id = self.tree.insert("", tk.END, values=(timestamp, severity, summary))
        self._raw_event_map[item_id] = {
            "timestamp": timestamp,
            "severity": severity,
            "summary": summary,
            "raw_event": raw_event,
        }

    # -----------------------------------------------------
    # Load many rows at once
    # -----------------------------------------------------
    def load_rows(self, rows: List[Dict[str, Any]]):
        """
        rows = [
            {
                "timestamp": "...",
                "severity": "...",
                "summary": "...",
                "raw_event": "..."
            },
            ...
        ]
        """
        self.clear()
        for row in rows:
            self.add_row(
                row.get("timestamp", ""),
                row.get("severity", ""),
                row.get("summary", ""),
                row.get("raw_event", ""),
            )

    # -----------------------------------------------------
    # Clear table
    # -----------------------------------------------------
    def clear(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._raw_event_map.clear()

    # -----------------------------------------------------
    # Get selected row’s full data
    # -----------------------------------------------------
    def get_selected(self) -> Dict[str, Any] | None:
        selection = self.tree.selection()
        if not selection:
            return None
        item_id = selection[0]
        return self._raw_event_map.get(item_id)

    # -----------------------------------------------------
    # Double-click handler
    # -----------------------------------------------------
    def on_double_click(self, callback):
        """Callback receives (row_dict)."""
        self._double_click_callback = callback

    def _on_double_click(self, event):
        if not self._double_click_callback:
            return
        row = self.get_selected()
        if row:
            self._double_click_callback(row)

    # -----------------------------------------------------
    # Sorting functionality
    # -----------------------------------------------------
    def _sort_by(self, column: str):
        items = [(self.tree.set(iid, column), iid) for iid in self.tree.get_children("")]

        # Basic alpha sort
        items.sort(key=lambda x: x[0])

        for index, (value, iid) in enumerate(items):
            self.tree.move(iid, "", index)


# Standalone test
if __name__ == "__main__":
    root = tk.Tk()
    root.title("LogsTable Test")

    table = LogsTable(root)
    table.pack(fill=tk.BOTH, expand=True)

    sample = [
        {"timestamp": "2024-01-01 10:00:00", "severity": "error", "summary": "Service failed", "raw_event": "Full event text 1"},
        {"timestamp": "2024-01-01 10:01:00", "severity": "warning", "summary": "High memory usage", "raw_event": "Full event text 2"},
        {"timestamp": "2024-01-01 10:02:00", "severity": "info", "summary": "Login success", "raw_event": "Full event text 3"},
    ]

    table.load_rows(sample)

    def on_click(row):
        print("Double-clicked:", row)

    table.on_double_click(on_click)

    root.mainloop()
