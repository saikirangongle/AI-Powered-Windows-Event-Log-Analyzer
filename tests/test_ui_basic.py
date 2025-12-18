# tests/test_ui_basic.py
"""
Basic UI tests for Tkinter components.

These tests DO NOT open visible windows.
They verify:
- Components can be created
- No exceptions are thrown during initialization
- Basic widget interactions work

Tkinter windows are created with `withdraw()` so they remain invisible.
"""

import unittest
import tkinter as tk

from src.ui.main_window import MainWindow
from src.ui.components.event_viewer import EventViewer
from src.ui.components.explanation_panel import ExplanationPanel
from src.ui.components.timeline_panel import TimelinePanel
from src.ui.components.logs_table import LogsTable


class TestUIBasic(unittest.TestCase):

    def setUp(self):
        """
        Create an invisible Tk root window before each test.
        """
        self.root = tk.Tk()
        self.root.withdraw()  # Prevent actual UI from appearing

    def tearDown(self):
        """
        Destroy Tk root to avoid resource leaks.
        """
        self.root.destroy()

    def test_main_window_initializes(self):
        """
        Ensure main UI window can be created.
        """
        win = MainWindow(self.root, gemini_client=None)
        self.assertIsNotNone(win)

    def test_event_viewer_initializes(self):
        viewer = EventViewer(self.root)
        self.assertIsNotNone(viewer)
        viewer.load_events(["Event A", "Event B"])
        self.assertEqual(viewer.get_selected_event(), None)

    def test_explanation_panel_initializes_and_sets_text(self):
        panel = ExplanationPanel(self.root)
        self.assertIsNotNone(panel)
        panel.set_text("Sample explanation")
        content = panel.get_text()
        self.assertIn("Sample explanation", content)

    def test_timeline_panel_initializes(self):
        panel = TimelinePanel(self.root)
        self.assertIsNotNone(panel)
        panel.load_events(["2025-01-01 10:00:00 Service failed"])
        self.assertEqual(len(panel.events), 1)

    def test_logs_table_initializes_and_loads_rows(self):
        table = LogsTable(self.root)
        self.assertIsNotNone(table)

        rows = [
            {
                "timestamp": "2025-01-01 12:00:00",
                "severity": "warning",
                "summary": "High CPU usage",
                "raw_event": "Raw event text here"
            }
        ]

        table.load_rows(rows)
        selected = table.get_selected()
        self.assertIsNone(selected)  # nothing selected yet

        # Simulate selecting first row
        first_item = table.tree.get_children()[0]
        table.tree.selection_set(first_item)

        selected2 = table.get_selected()
        self.assertIsNotNone(selected2)
        self.assertEqual(selected2["severity"], "warning")


if __name__ == "__main__":
    unittest.main()
