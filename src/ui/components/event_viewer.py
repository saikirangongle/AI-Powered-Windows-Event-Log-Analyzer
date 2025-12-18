# src/ui/components/event_viewer.py
"""
Event Viewer Component
----------------------

A reusable Tkinter component that displays parsed Windows events
in a scrollable listbox with selection support.

Provides:
- load_events(events: list[str])
- get_selected_event() -> str or None
- clear()

Designed to be embedded into any Tkinter frame or window.
"""

import tkinter as tk
from tkinter import ttk


class EventViewer(ttk.Frame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, padding=5, **kwargs)

        # Title label
        ttk.Label(self, text="Event Log (Parsed Events)", font=("Arial", 11, "bold")).pack(anchor="w")

        # Scrollable listbox
        frame = ttk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        self.listbox = tk.Listbox(frame, selectmode=tk.SINGLE, activestyle="dotbox")
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox.config(yscrollcommand=scrollbar.set)

    # --------------------------------------------------------
    # Load a new set of events
    # --------------------------------------------------------
    def load_events(self, events):
        self.listbox.delete(0, tk.END)
        for ev in events:
            self.listbox.insert(tk.END, ev)

    # --------------------------------------------------------
    # Get the currently selected event
    # --------------------------------------------------------
    def get_selected_event(self):
        selection = self.listbox.curselection()
        if not selection:
            return None
        index = selection[0]
        return self.listbox.get(index)

    # --------------------------------------------------------
    # Clear all entries
    # --------------------------------------------------------
    def clear(self):
        self.listbox.delete(0, tk.END)


# Standalone test
if __name__ == "__main__":
    root = tk.Tk()
    root.title("EventViewer Test")

    viewer = EventViewer(root)
    viewer.pack(fill=tk.BOTH, expand=True)

    viewer.load_events(["Event A", "Event B", "Event C"])

    def on_select():
        print("Selected:", viewer.get_selected_event())

    ttk.Button(root, text="Get Selected", command=on_select).pack()

    root.mainloop()
