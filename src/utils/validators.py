# src/utils/validators.py
"""
Validation utilities for Win Log Interpreter (Gemini-only)

Provides reusable small validation helpers used across:
- settings dialog
- file loading
- API client initialization
- event analysis

Public validators:
- is_valid_api_key(key)
- is_valid_event(event)
- is_valid_event_list(events)
- is_valid_path(path)
- non_empty_string(value)
"""

import os
from typing import Any, List


# -------------------------------------------------
# Gemini API Key Validator (simple heuristic)
# -------------------------------------------------
def is_valid_api_key(key: str) -> bool:
    """
    Validate Gemini API key structure.

    Conditions:
    - must be non-empty
    - must be >= 12 chars (adjust based on real key formats)
    """
    if not key or not isinstance(key, str):
        return False
    return len(key.strip()) >= 12


# -------------------------------------------------
# Event Validators
# -------------------------------------------------
def is_valid_event(event: Any) -> bool:
    """
    Check if an event string is valid.
    """
    if not event:
        return False
    if not isinstance(event, str):
        return False
    if not event.strip():
        return False
    return True


def is_valid_event_list(events: Any) -> bool:
    """
    Check if a list of events is valid.
    Each element must pass is_valid_event().
    """
    if not isinstance(events, list):
        return False
    if not events:
        return False
    return all(is_valid_event(ev) for ev in events)


# -------------------------------------------------
# Path / File Validators
# -------------------------------------------------
def is_valid_path(path: Any) -> bool:
    """
    Basic path validation for use before file loading.
    """
    if not path or not isinstance(path, str):
        return False
    return os.path.exists(path)


# -------------------------------------------------
# Generic validators
# -------------------------------------------------
def non_empty_string(value: Any) -> bool:
    """
    Check if value is a valid non-empty string.
    """
    return isinstance(value, str) and value.strip() != ""


# -------------------------------------------------
# Self-test
# -------------------------------------------------
if __name__ == "__main__":
    print("API key valid?:", is_valid_api_key("1234567890ABC"))
    print("Valid event?:", is_valid_event("Service start failed"))
    print("Valid list?:", is_valid_event_list(["A", "B"]))
    print("Valid path?:", is_valid_path(__file__))
