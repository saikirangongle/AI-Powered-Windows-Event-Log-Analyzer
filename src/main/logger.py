# src/main/logger.py
"""
Centralized logging setup for Win Log Interpreter (Gemini-only).

Features:
- Console logging
- Optional debug mode
- Unified logger name: 'win-log-interpreter'
"""

import logging
import sys

LOGGER_NAME = "win-log-interpreter"
logger = logging.getLogger(LOGGER_NAME)


def setup_logging(debug: bool = False):
    """Configure application logging."""
    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Formatter
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console Handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    ch.setLevel(logging.DEBUG if debug else logging.INFO)

    # Clear existing handlers to avoid duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.addHandler(ch)

    logger.debug("Logging initialized (debug mode: %s)", debug)
