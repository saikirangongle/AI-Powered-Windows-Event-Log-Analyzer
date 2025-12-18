# src/api/ai_explainer.py
"""
AI explanation helpers for Win Log Interpreter (Gemini-only).

This module builds prompts for Gemini, calls the Gemini client and returns
a clean textual explanation suitable for UI display.

Assumptions:
- gemini_client has a method `.chat(prompt: str) -> Union[str, dict]`.
  The updated Google Gemini client provided returns a string in the common case,
  but parse_gemini_response remains tolerant to handle dict shapes too.

Public functions:
- build_explain_prompt(event: str, context: dict|None = None) -> str
- parse_gemini_response(resp: Any) -> str
- get_explanation(gemini_client, event: str, context: dict|None = None, retries: int = 1) -> str
"""

from typing import Optional, Dict, Any
import time

from src.main.logger import logger


def build_explain_prompt(event: str, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Build a concise, structured prompt for Gemini to explain a Windows event.

    Args:
        event: The raw or parsed event text to explain.
        context: Optional dictionary with extra hints (e.g., timestamp, related_events).

    Returns:
        Prompt string.
    """
    lines = [
        "You are an experienced Windows systems analyst. Explain the event below",
        "in clear, concise language suitable for another analyst. Include:",
        "- What the event likely means",
        "- Possible causes",
        "- Immediate triage steps (what to check first)",
        "- Indicators of compromise or false positives (if applicable)",
        "- Short summary (1-2 sentences)",
        "",
        "Event:",
        event,
        "",
    ]

    if context:
        lines.append("Context:")
        for k, v in context.items():
            if k == "related_events" and isinstance(v, list):
                lines.append(f"- related_events: {len(v)} items (top 3 shown)")
                for idx, it in enumerate(v[:3], 1):
                    lines.append(f"  {idx}. {it}")
            else:
                lines.append(f"- {k}: {v}")
        lines.append("")

    lines.append("Provide the explanation in sections with headings. Keep it concise.")
    return "\n".join(lines)


def parse_gemini_response(resp: Any) -> str:
    """
    Extract a plain-text explanation from Gemini response.

    Accepts:
    - str: returned directly (common case for updated Gemini client)
    - dict: attempts several known shapes and returns the first text found

    Raises:
        ValueError if no textual content can be extracted.
    """
    if resp is None:
        raise ValueError("Empty response from Gemini")

    # If it's already a string, return it
    if isinstance(resp, str):
        return resp.strip()

    # If it's bytes, decode
    if isinstance(resp, (bytes, bytearray)):
        try:
            return resp.decode("utf-8", errors="replace").strip()
        except Exception:
            return str(resp)

    # If it's a dict, try common locations
    if isinstance(resp, dict):
        # common google/generative response shape handled by client already,
        # but we keep this tolerant for other providers:
        # - candidates -> content -> parts -> text
        # - output / reply / text / content keys
        # - choices -> message -> content
        try:
            # candidates path
            if "candidates" in resp and isinstance(resp["candidates"], (list, tuple)) and resp["candidates"]:
                first = resp["candidates"][0]
                if isinstance(first, dict):
                    content = first.get("content") or first.get("output") or first
                    if isinstance(content, dict):
                        parts = content.get("parts") or content.get("textParts") or None
                        if isinstance(parts, (list, tuple)) and parts:
                            part0 = parts[0]
                            if isinstance(part0, dict) and "text" in part0:
                                return str(part0["text"]).strip()
                            if isinstance(part0, str):
                                return part0.strip()
                    # try flattened keys
                    for key in ("text", "content", "output"):
                        if key in first and isinstance(first[key], str):
                            return first[key].strip()
            # fallback simple keys
            for key in ("reply", "text", "output", "content", "message"):
                val = resp.get(key)
                if isinstance(val, str):
                    return val.strip()
                if isinstance(val, dict):
                    # try nested text
                    for sk in ("text", "content", "reply"):
                        s = val.get(sk)
                        if isinstance(s, str):
                            return s.strip()
            # Chat-like choices message content
            if "choices" in resp and isinstance(resp["choices"], list) and resp["choices"]:
                c0 = resp["choices"][0]
                if isinstance(c0, dict):
                    msg = c0.get("message") or c0.get("delta") or c0
                    if isinstance(msg, dict):
                        content = msg.get("content") or msg.get("text")
                        if isinstance(content, str):
                            return content.strip()
        except Exception:
            logger.exception("Error parsing Gemini dict response; falling back to stringify")

    # Fallback: stringify whatever we have
    try:
        txt = str(resp)
        if txt:
            return txt.strip()
    except Exception:
        pass

    raise ValueError("Could not extract text from Gemini response")


def get_explanation(
    gemini_client,
    event: str,
    context: Optional[Dict[str, Any]] = None,
    retries: int = 1,
    backoff_seconds: float = 1.0,
) -> str:
    """
    Build a prompt, call Gemini, and return a cleaned explanation string.

    Args:
        gemini_client: GeminiClient-like object with .chat(prompt) -> str|dict
        event: Event text to explain
        context: Optional context dict
        retries: number of retries on transient errors
        backoff_seconds: base sleep for exponential backoff

    Returns:
        Cleaned explanation string.

    Raises:
        Propagates exceptions from the client after retries are exhausted.
    """
    prompt = build_explain_prompt(event, context)
    attempt = 0
    last_exc = None

    while attempt <= retries:
        try:
            logger.debug("Requesting explanation from Gemini (attempt %d)", attempt + 1)
            resp = gemini_client.chat(prompt)
            explanation = parse_gemini_response(resp)
            # Clean / normalize whitespace & remove excessive blank lines
            lines = [line.rstrip() for line in explanation.strip().splitlines() if line.strip()]
            return "\n".join(lines)
        except Exception as exc:
            last_exc = exc
            logger.warning("Failed to get explanation (attempt %d): %s", attempt + 1, exc)
            attempt += 1
            if attempt > retries:
                break
            sleep = backoff_seconds * (2 ** (attempt - 1))
            logger.debug("Sleeping %.1fs before retry", sleep)
            time.sleep(sleep)

    logger.exception("All attempts to get explanation failed. Last error: %s", last_exc)
    # Re-raise the last exception so callers (UI) can show meaningful messages
    raise last_exc
