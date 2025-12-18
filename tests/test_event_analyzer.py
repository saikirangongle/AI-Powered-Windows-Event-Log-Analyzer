# tests/test_event_analyzer.py
"""
Tests for event analyzer component.
"""

import unittest
from src.api.event_analyzer import analyze, analyze_single


class TestEventAnalyzer(unittest.TestCase):

    def test_analyze_single_severity(self):
        ev = "Service failed to start due to timeout"
        result = analyze_single(ev)

        self.assertIn("severity", result)
        self.assertEqual(result["severity"], "error")

    def test_analyze_single_patterns(self):
        ev = "User login failed for admin"
        result = analyze_single(ev)

        self.assertTrue(result["patterns"]["matches"]["authentication_issue"])
        self.assertIn("authentication", result["recommended_focus"])

    def test_analyze_multiple_events(self):
        events = [
            "Network connection timeout on port 445",
            "System reboot completed successfully",
            "User login failed for admin"
        ]

        summary = analyze(events)

        self.assertEqual(summary["total_events"], 3)
        self.assertIn("severities", summary)
        self.assertIn("pattern_counts", summary)
        self.assertEqual(summary["severities"]["error"], 2)  # login fail + network issue

    def test_pattern_detection(self):
        ev = "Malware detection occurred during scan"
        result = analyze_single(ev)

        self.assertTrue(result["patterns"]["matches"]["security_flag"])
        self.assertIn("security", result["recommended_focus"])


if __name__ == "__main__":
    unittest.main()
