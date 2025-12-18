# src/api/api_client_gemini.py
"""
Google Gemini API Client (Official REST Format)
"""

import os
import json
import requests
from src.main.constants import (
    GEMINI_DEFAULT_BASE_URL,
    GEMINI_DEFAULT_MODEL,
    GEMINI_API_VERSION,
)
from src.main.logger import logger


class GeminiAPIError(Exception):
    pass


class GeminiClient:
    def __init__(self, api_key: str = None, base_url: str = None, timeout: int = 20):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Gemini API key missing")

        self.base_url = base_url or GEMINI_DEFAULT_BASE_URL
        self.model = GEMINI_DEFAULT_MODEL
        self.api_version = GEMINI_API_VERSION
        self.timeout = timeout

    # --------------------------
    # Internal request method
    # --------------------------
    def _generate_url(self):
        return (
            f"{self.base_url}/{self.api_version}/{self.model}:generateContent"
            f"?key={self.api_key}"
        )

    def _post(self, payload: dict):
        url = self._generate_url()

        try:
            logger.debug("POST %s | Payload: %s", url, payload)

            response = requests.post(
                url, json=payload, timeout=self.timeout
            )

        except Exception as exc:
            logger.exception("Network error: %s", exc)
            raise GeminiAPIError(f"Network/connection failure: {exc}")

        if response.status_code >= 400:
            logger.error("Gemini API error: %s", response.text)
            raise GeminiAPIError(
                f"Gemini API error {response.status_code}: {response.text}"
            )

        try:
            return response.json()
        except Exception:
            raise GeminiAPIError("Invalid JSON response")

    # --------------------------
    # Public chat method
    # --------------------------
    def chat(self, prompt: str) -> str:
        """
        Sends a text prompt to Google Gemini using generateContent.
        Returns a string response.
        """

        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ]
        }

        data = self._post(payload)

        try:
            # Gemini returns text in:
            # data["candidates"][0]["content"]["parts"][0]["text"]
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            raise GeminiAPIError("Unexpected Gemini response format")
