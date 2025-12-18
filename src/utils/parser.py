# src/utils/parser.py
"""
Log parser utilities for Win Log Interpreter (Gemini-only).

Primary function:
- parse_log(raw: str | bytes) -> list[str]

Behavior:
- Accepts raw text (or bytes) containing one or many events.
- Detects common structured forms:
    * XML/EventRecord blocks (e.g. exported EVTX via wevtutil / XML)
    * Plainline logs with timestamp-prefixed lines
    * Delimited blocks separated by blank lines
- Attempts to group multi-line events sensibly so each returned string
  represents a single logical event for downstream analysis/AI explanation.

Notes:
- This is a best-effort parser intended for text-based event logs. Proper
  binary EVTX parsing should be done with a specialized library (python-evtx).
- Keep the output friendly for the UI (short strings). Downstream components
  may further normalize or enrich the events.
"""

from typing import List
import re
import xml.etree.ElementTree as ET

# Common timestamp regexes used to split events
_TIMESTAMP_PATTERNS = [
    # 2024-01-25 10:33:22
    r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}",
    # 01/25/2024 10:33 AM OR 1/1/2024 1:02 PM
    r"\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2}(?:[:\d{2}]*)?(?:\s?[AP]M)?",
    # 25-01-2024 12:00:10
    r"\d{1,2}-\d{1,2}-\d{4} \d{2}:\d{2}:\d{2}",
    # ISO time-only e.g. 10:33:22 at start
    r"^\d{2}:\d{2}:\d{2}",
]
_TIMESTAMP_RE = re.compile("|".join([f"({p})" for p in _TIMESTAMP_PATTERNS]), re.IGNORECASE | re.MULTILINE)


def _is_xml_like(text: str) -> bool:
    """Quick heuristic to detect XML-like event exports."""
    if "<Event" in text or "<EventRecord" in text or text.strip().startswith("<?xml"):
        return True
    return False


def _extract_events_from_xml(text: str) -> List[str]:
    """
    Extract event contents from XML blocks.

    Looks for <Event> ... </Event> or <EventRecord> ... </EventRecord> and
    converts each to a compact text string by extracting all text nodes.
    """
    events = []
    try:
        # Wrap in root if necessary to allow parsing fragments
        if not text.strip().startswith("<?xml"):
            wrapped = f"<Root>\n{text}\n</Root>"
        else:
            wrapped = text

        root = ET.fromstring(wrapped)
    except ET.ParseError:
        # If XML parsing fails, fallback to regex-based block extraction
        block_re = re.compile(r"<(?:Event|EventRecord)\b.*?>.*?</(?:Event|EventRecord)>", re.DOTALL | re.IGNORECASE)
        for block in block_re.findall(text):
            # strip tags crudely
            stripped = re.sub(r"<[^>]+>", " ", block)
            cleaned = re.sub(r"\s+", " ", stripped).strip()
            if cleaned:
                events.append(cleaned)
        return events

    # If parsed successfully, find each Event/EventRecord element
    for event_el in root.findall(".//Event") + root.findall(".//EventRecord"):
        # Extract textual content from element (all inner text)
        pieces = []
        for node in event_el.iter():
            if node.text and node.text.strip():
                pieces.append(node.text.strip())
        joined = " | ".join(pieces)
        if joined:
            events.append(re.sub(r"\s+", " ", joined).strip())

    return events


def _split_by_blank_lines(text: str) -> List[str]:
    """Split on two or more newlines (common delimiting) and return non-empty blocks."""
    blocks = re.split(r"\n\s*\n+", text)
    return [b.strip() for b in blocks if b and b.strip()]


def _split_by_timestamp(lines: List[str]) -> List[str]:
    """
    Group lines into events using timestamp detection.
    Whenever a line begins with a timestamp pattern, treat it as a new event.
    Otherwise, append to current event (allowing multiline events).
    """
    events = []
    current = []

    for line in lines:
        if not line.strip():
            # preserve blank lines as potential separators
            if current:
                current.append("")  # keep a blank line inside multiline events
            continue

        # Check if line contains timestamp near start
        if _TIMESTAMP_RE.search(line[:50] if len(line) > 50 else line):
            # Start of a new event if current exists
            if current:
                events.append("\n".join(current).strip())
                current = [line.rstrip()]
            else:
                current = [line.rstrip()]
        else:
            # Continuation of previous event (or first event)
            current.append(line.rstrip())

    if current:
        events.append("\n".join(current).strip())

    # Post-process: collapse excessive whitespace
    return [re.sub(r"\s+\n", "\n", ev).strip() for ev in events if ev and ev.strip()]


def parse_log(raw: str | bytes) -> List[str]:
    """
    Parse raw log content into a list of event strings.

    Args:
        raw: raw content (text or bytes) of a log file or an exported XML string.

    Returns:
        List[str]: list of parsed events (each is a cleaned string).
    """
    # Normalize input to text
    if raw is None:
        return []

    if isinstance(raw, bytes):
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = raw.decode("latin-1")
            except Exception:
                # last resort
                text = str(raw)
    else:
        text = str(raw)

    text = text.strip()
    if not text:
        return []

    # 1) XML-like exports (wevtutil, evtx exported to xml)
    if _is_xml_like(text):
        events = _extract_events_from_xml(text)
        if events:
            return events

    # 2) If the file is plain text, attempt timestamp-based grouping
    # First, split into lines and try timestamp grouping
    lines = text.splitlines()
    ts_grouped = _split_by_timestamp(lines)
    if len(ts_grouped) >= 2:
        return ts_grouped

    # 3) If timestamp grouping didn't produce multiple events, try blank-line split
    blank_split = _split_by_blank_lines(text)
    if len(blank_split) >= 2:
        return blank_split

    # 4) Fallback: treat each non-empty line as an event
    simple_lines = [ln.strip() for ln in lines if ln.strip()]
    if simple_lines:
        return simple_lines

    # 5) Final fallback: return the whole content as a single event
    return [text]


# Utility: a simple summarizer that reduces long events to a one-line preview
def summarize_event(event_text: str, max_len: int = 200) -> str:
    """
    Create a short preview for UI lists. Truncates at word boundaries.
    """
    s = re.sub(r"\s+", " ", event_text).strip()
    if len(s) <= max_len:
        return s
    # Try to cut at sentence end before max_len
    m = re.search(r"(.{50,%d}?)[\.\!\?]\s" % max_len, s)
    if m:
        return m.group(1).strip() + "..."
    # Otherwise cut safely at a space
    cut = s[:max_len].rsplit(" ", 1)[0]
    return cut + "..."


# If run directly, perform a tiny demo
if __name__ == "__main__":
    demo = """
2024-01-25 10:33:22 Service failed to start: Timeout reached
Detail: The service 'ExampleService' failed to start after 3 attempts.
Error code: 0x8007045a

2024-01-25 10:34:10 User login succeeded for user alice
Source: Security subsystem

<Event>
  <System>
    <Provider Name="SampleProvider"/>
    <TimeCreated SystemTime="2024-01-25T10:35:00.000Z"/>
  </System>
  <EventData>
    <Data>Something happened</Data>
  </EventData>
</Event>
    """
    parsed = parse_log(demo)
    for i, p in enumerate(parsed, 1):
        print(f"--- EVENT {i} ---")
        print(p)
        print("SUMMARY:", summarize_event(p, 120))
        print()
