# app.py (place at project root)
"""
Entry point for Win Log Interpreter (Gemini-only)

- Run GUI by default (allows entering Gemini API key via Settings).
- Headless mode requires GEMINI_API_KEY to be set in env or config.
"""

import os
import sys
import argparse
from src.main.config import load_config
from src.main.logger import setup_logging, logger
from src.api.api_client_gemini import GeminiClient
from src.api.event_analyzer import analyze
# corrected import: use get_explanation (not `explain`)
from src.api.ai_explainer import get_explanation
# ui loader (may raise if UI not implemented)
try:
    from src.ui.main_window import start_ui
except Exception:
    start_ui = None


def run_headless(gemini_client, input_path=None):
    logger.info("Running in headless mode")
    if gemini_client is None:
        raise RuntimeError("Headless mode requires a configured Gemini client (GEMINI_API_KEY).")

    # simple headless flow
    if input_path:
        from src.utils.file_loader import load_file
        from src.utils.parser import parse_log
        try:
            raw = load_file(input_path)
            events = parse_log(raw)
        except Exception as exc:
            logger.exception("Failed to load/parse events: %s", exc)
            events = []
    else:
        events = ["Demo event: System reboot", "Demo event: Service failure"]

    analysis = analyze(events)
    print("=== Local Analysis ===")
    print(analysis)

    # Ask Gemini about the first event
    if events:
        prompt = f"Explain this Windows event for an analyst:\n\n{events[0]}"
        try:
            reply = gemini_client.chat(prompt)
            explanation = get_explanation(gemini_client, events[0], context=None, retries=1)
            print("\n--- AI Explanation ---\n", explanation)
        except Exception as exc:
            logger.exception("Gemini API call failed: %s", exc)
            print("Failed to get explanation from Gemini:", exc)


def main(argv=None):
    argv = argv or sys.argv[1:]
    parser = argparse.ArgumentParser(prog="win-log-interpreter")
    parser.add_argument("--headless", action="store_true", help="Run in headless (CLI) mode")
    parser.add_argument("--input", "-i", help="Path to an event log file to analyze (optional)", default=None)
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args(argv)

    # ensure project root is on sys.path (helps in some environments)
    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)

    # Load config and logging
    cfg = load_config()
    gemini_key_cfg = cfg.get("GEMINI_API_KEY") or ""
    setup_logging(debug=args.debug)
    logger.info("Starting Win Log Interpreter (Gemini-only)")

    # Initialize Gemini client only if key present in config/env
    gemini = None
    if gemini_key_cfg:
        try:
            gemini = GeminiClient(api_key=gemini_key_cfg)
            logger.info("Initialized Gemini client from config.")
        except Exception as exc:
            logger.exception("Failed to initialize Gemini client from config: %s", exc)
            print("Warning: Failed to initialize Gemini client from config:", exc)

    # Mode selection
    if args.headless or start_ui is None:
        # headless requires a key
        if args.headless and gemini is None:
            logger.error("Headless mode requires GEMINI_API_KEY. Set it in environment or config and retry.")
            print("Error: Headless mode requires GEMINI_API_KEY. See .env.example or use the Settings dialog in GUI.")
            return 2
        run_headless(gemini_client=gemini, input_path=args.input)
    else:
        logger.info("Launching UI")
        try:
            start_ui(gemini_client=gemini)
        except TypeError:
            start_ui()

    logger.info("Shutdown complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
