# tests/test_ai_explainer.py
"""
Tests for ai_explainer module.
"""

import unittest
from unittest.mock import MagicMock, patch
from src.api.ai_explainer import (
    build_explain_prompt,
    parse_gemini_response,
    get_explanation,
)


class TestAIExplainer(unittest.TestCase):
    def test_build_explain_prompt_contains_event_and_instructions(self):
        event = "Service failed to start: timeout"
        context = {"source": "server1", "timestamp": "2025-01-01 12:00:00", "related_events": ["ev1", "ev2", "ev3", "ev4"]}
        prompt = build_explain_prompt(event, context)
        self.assertIn("Explain the event below", prompt)
        self.assertIn(event, prompt)
        self.assertIn("related_events", prompt)
        self.assertIn("Provide the explanation in sections", prompt)

    def test_parse_gemini_response_various_shapes(self):
        # shape: direct reply
        resp1 = {"reply": "This is an explanation."}
        self.assertEqual(parse_gemini_response(resp1), "This is an explanation.")

        # shape: choices -> message -> content
        resp2 = {"choices": [{"message": {"content": "Choice content here"}}]}
        self.assertEqual(parse_gemini_response(resp2), "Choice content here")

        # shape: output key
        resp3 = {"output": "Output text"}
        self.assertEqual(parse_gemini_response(resp3), "Output text")

        # shape: text key
        resp4 = {"text": "Some text"}
        self.assertEqual(parse_gemini_response(resp4), "Some text")

        # shape: nested data
        resp5 = {"data": {"text": "Nested text"}}
        self.assertEqual(parse_gemini_response(resp5), "Nested text")

        # string input returns itself
        self.assertEqual(parse_gemini_response("plain string"), "plain string")

        # fallback to str() when nothing standard present
        resp6 = {"weird": 123}
        self.assertIn("123", parse_gemini_response(resp6))

    def test_parse_gemini_response_raises_on_empty(self):
        with self.assertRaises(ValueError):
            parse_gemini_response(None)

    @patch("time.sleep", return_value=None)
    def test_get_explanation_success_and_retries(self, _sleep):
        # Mock client that fails first then succeeds
        fake_client = MagicMock()
        fake_client.chat.side_effect = [
            Exception("Temporary failure"),
            {"reply": "Final explanation from Gemini"}
        ]

        explanation = get_explanation(fake_client, "Test event", context={"source": "s"}, retries=2, backoff_seconds=0.01)
        self.assertIn("Final explanation", explanation)
        self.assertEqual(fake_client.chat.call_count, 2)

    def test_get_explanation_propagates_error_when_all_retries_fail(self):
        fake_client = MagicMock()
        fake_client.chat.side_effect = Exception("Permanent failure")

        with self.assertRaises(Exception):
            get_explanation(fake_client, "Test event", retries=0)

    def test_get_explanation_parses_various_response_shapes(self):
        fake_client = MagicMock()
        fake_client.chat.return_value = {"choices": [{"message": {"content": "Explained text"}}]}

        explanation = get_explanation(fake_client, "Some event", retries=0)
        self.assertEqual(explanation, "Explained text")


if __name__ == "__main__":
    unittest.main()
