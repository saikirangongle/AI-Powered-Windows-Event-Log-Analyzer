# src/utils/win_event_reader.py
"""
Windows Event Log reader helper with pywin32 + wevtutil fallback.

Provides:
    read_windows_event_log(log_type: str, max_records: int = 1000) -> list[str]

- Preferred path: uses pywin32 (win32evtlog) to read Event Log records.
- Fallback: uses `wevtutil` subprocess and parses its text output.
- Non-Windows platforms: returns an empty list.

Returned event string format (single-line summary suitable for UI):
    "<timestamp>\t<source>\tID:<event_id>\tType:<event_type>\t<message preview>"

Notes:
- Reading the Security log often requires elevated privileges.
- If pywin32 is used, it returns most recent events first (backwards read).
- If wevtutil is used, it requests events in reverse chronological order.
"""

from typing import List, Optional
import platform
import logging
import subprocess
import shlex

# Use the project logger if present, otherwise fall back to std logging
try:
    from src.main.logger import logger
except Exception:
    logger = logging.getLogger("winlog")

# Attempt pywin32 imports (only valid on Windows with pywin32 installed)
_win32_available = False
_win32evtlog = None
try:
    if platform.system().lower() == "windows":
        import win32evtlog  # type: ignore
        import win32con  # type: ignore
        _win32evtlog = win32evtlog
        _win32_available = True
except Exception:
    _win32_available = False
    _win32evtlog = None


def _format_win32_event(evt) -> str:
    """Format a pywin32 EventLogRecord into a single-line string."""
    try:
        time = evt.TimeGenerated.Format() if hasattr(evt, "TimeGenerated") else ""
    except Exception:
        time = str(getattr(evt, "TimeGenerated", ""))

    source = getattr(evt, "SourceName", "") or ""
    try:
        event_id = (getattr(evt, "EventID", 0) & 0xFFFF) if hasattr(evt, "EventID") else ""
    except Exception:
        event_id = getattr(evt, "EventID", "")
    event_type = getattr(evt, "EventType", "")
    # Event strings can be None or list
    try:
        inserts = getattr(evt, "StringInserts", None) or getattr(evt, "Strings", None) or []
        if isinstance(inserts, (list, tuple)):
            message = " ".join([str(s) for s in inserts if s])
        else:
            message = str(inserts)
    except Exception:
        message = ""

    message = message.strip()
    if len(message) > 300:
        message = message[:300] + "..."
    return f"{time}\t{source}\tID:{event_id}\tType:{event_type}\t{message}".strip()


def _read_with_pywin32(log_type: str, max_records: int) -> List[str]:
    """Read using win32evtlog. Returns most recent events first."""
    events: List[str] = []
    if not _win32_available or _win32evtlog is None:
        logger.debug("pywin32 not available; skipping pywin32 reader.")
        return events

    server = None  # local machine
    try:
        hand = _win32evtlog.OpenEventLog(server, log_type)
    except Exception:
        logger.exception("Failed to open Windows Event Log via pywin32: %s", log_type)
        return events

    flags = _win32evtlog.EVENTLOG_BACKWARDS_READ | _win32evtlog.EVENTLOG_SEQUENTIAL_READ
    total = 0
    try:
        while total < max_records:
            try:
                batch = _win32evtlog.ReadEventLog(hand, flags, 0)
            except Exception:
                break
            if not batch:
                break
            for evt in batch:
                try:
                    events.append(_format_win32_event(evt))
                except Exception:
                    logger.exception("Failed to format an event (skipping)")
                total += 1
                if total >= max_records:
                    break
    except Exception:
        logger.exception("Error while reading Windows Event Log via pywin32 (%s)", log_type)
    finally:
        try:
            _win32evtlog.CloseEventLog(hand)
        except Exception:
            pass

    return events


def _parse_wevtutil_output_block(block: str) -> Optional[str]:
    """
    Given a block of text from wevtutil's /f:text output, produce a single-line summary.
    We do a best-effort extraction of Date, Provider, Event ID, Level, and the message lines.
    """
    if not block or not block.strip():
        return None
    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    # Attempt to find some known fields
    date = ""
    provider = ""
    event_id = ""
    level = ""
    message_lines: List[str] = []

    for ln in lines:
        # Example prefixes in wevtutil text output: "Date:", "Provider:", "Event ID:", "Level:", "Message:"
        low = ln.lower()
        if low.startswith("date:"):
            date = ln.split(":", 1)[1].strip()
            continue
        if low.startswith("provider:"):
            provider = ln.split(":", 1)[1].strip()
            continue
        if low.startswith("event id:") or low.startswith("eventid:"):
            event_id = ln.split(":", 1)[1].strip()
            continue
        if low.startswith("level:"):
            level = ln.split(":", 1)[1].strip()
            continue
        # After "Message:" the following lines are the message; we conservatively collect other lines too
        if low.startswith("message:"):
            msg = ln.split(":", 1)[1].strip()
            if msg:
                message_lines.append(msg)
            continue
        # Heuristic: lines that are not structural may be part of the message
        # Append these as possible message content (limit length later)
        message_lines.append(ln)

    # Build message preview
    message = " ".join(message_lines).strip()
    if len(message) > 300:
        message = message[:300] + "..."

    parts = [p for p in [date, provider, f"ID:{event_id}" if event_id else None, f"Level:{level}" if level else None, message] if p]
    summary = "\t".join(parts)
    return summary if summary else None


def _read_with_wevtutil(log_type: str, max_records: int) -> List[str]:
    """
    Use `wevtutil qe <log_type> /f:text /c:<max_records> /rd:true` to export recent events.
    Parse blocks separated by blank lines. Returns list of summaries (most recent first).
    """
    events: List[str] = []
    # wevtutil exists only on Windows
    if platform.system().lower() != "windows":
        return events

    # Build command: use reverse-direction (/rd:true) to get most recent first
    cmd = f"wevtutil qe {shlex.quote(log_type)} /f:text /c:{int(max_records)} /rd:true"
    try:
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, errors="replace", timeout=30)
        out = proc.stdout or ""
        if not out:
            # Sometimes wevtutil prints to stderr
            out = proc.stderr or ""
        if not out:
            logger.debug("wevtutil produced no output for log %s", log_type)
            return events
        # Blocks are separated by two or more newlines; normalize line endings
        normalized = out.replace("\r\n", "\n").replace("\r", "\n")
        blocks = [b.strip() for b in normalized.split("\n\n") if b.strip()]
        for block in blocks[:max_records]:
            parsed = _parse_wevtutil_output_block(block)
            if parsed:
                events.append(parsed)
    except subprocess.TimeoutExpired:
        logger.exception("wevtutil command timed out while reading %s", log_type)
    except Exception:
        logger.exception("Failed to run wevtutil for log %s", log_type)
    return events


def read_windows_event_log(log_type: str, max_records: int = 1000) -> List[str]:
    """
    Read recent events from a Windows Event Log.

    Args:
        log_type: "System", "Application", or "Security" (case sensitive as Windows expects)
        max_records: maximum number of events to return (most recent first)

    Returns:
        List[str]: list of event summary strings (most recent first)
    """
    if platform.system().lower() != "windows":
        logger.debug("read_windows_event_log called on non-Windows platform")
        return []

    # Prefer pywin32 if available
    if _win32_available:
        try:
            events = _read_with_pywin32(log_type, max_records)
            if events:
                return events
            # fall through to wevtutil if empty (or if permission limited)
            logger.debug("pywin32 reader returned %d events; falling back to wevtutil if necessary", len(events))
        except Exception:
            logger.exception("pywin32 reader failed; attempting wevtutil fallback")

    # Fallback to wevtutil parsing
    events = _read_with_wevtutil(log_type, max_records)
    if not events:
        logger.info("No events returned for %s (pywin32 and wevtutil both returned empty or failed).", log_type)
    return events
