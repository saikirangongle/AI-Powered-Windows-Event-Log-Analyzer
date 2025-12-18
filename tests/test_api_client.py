# tests/test_api_client.py
"""
Tests for GeminiClient (Gemini-only)
"""

import unittest
from unittest.mock import patch, MagicMock
from src.api.api_client_gemini import GeminiClient, GeminiAPIError


class TestGeminiClient(unittest.TestCase):

    @patch("requests.post")
    def test_chat_success(self, mock_post):
        # Mock successful JSON response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"reply": "Hello world"}
        mock_post.return_value = mock_response

        client = GeminiClient(api_key="1234567890ABCDEF")
        result = client.chat("test prompt")

        self.assertEqual(result["reply"], "Hello world")

        # Check that POST was called correctly
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn("/v1/chat", args[0])
        self.assertIn("Authorization", kwargs["headers"])
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer 1234567890ABCDEF")

    @patch("requests.post")
    def test_chat_error_status_code(self, mock_post):
        # Mock 400 error response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_post.return_value = mock_response

        client = GeminiClient(api_key="1234567890ABCDEF")

        with self.assertRaises(GeminiAPIError):
            client.chat("test prompt")

    @patch("requests.post")
    def test_chat_invalid_json(self, mock_post):
        # Mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_post.return_value = mock_response

        client = GeminiClient(api_key="1234567890ABCDEF")

        with self.assertRaises(GeminiAPIError):
            client.chat("test prompt")

    def test_missing_api_key(self):
        with self.assertRaises(ValueError):
            GeminiClient(api_key=None)


if __name__ == "__main__":
    unittest.main()
