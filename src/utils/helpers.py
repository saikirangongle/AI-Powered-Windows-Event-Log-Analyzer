# src/utils/helpers.py
"""
General helper utilities for Win Log Interpreter (Gemini-only).

Useful utilities:
- pretty_print(obj)               -> human-friendly print (uses pprint)
- ensure_dir(path, exist_ok=True) -> create directory if missing
- now_iso()                       -> current ISO timestamp
- safe_write_json(path, obj)      -> atomically write JSON (returns True/False)
- safe_load_json(path, default)   -> load JSON with graceful fallback
- chunk_text(text, size)          -> split text into chunks <= size (word-safe)
- truncate(text, max_len)         -> safely truncate with ellipsis
- ensure_list(obj)                -> coerce to list
"""

from pathlib import Path
from typing import Any, Iterable, List, Optional
import json
import os
import time
import pprint
from datetime import datetime

from src.main.logger import logger


def pretty_print(obj: Any, compact: bool = False) -> None:
    """Pretty-print an object to stdout (for debugging)."""
    if compact:
        print(pprint.pformat(obj, compact=True))
    else:
        pprint.pprint(obj)


def ensure_dir(path: str | Path, exist_ok: bool = True) -> Path:
    """Ensure a directory exists; return Path object."""
    p = Path(path)
    if p.exists() and not p.is_dir():
        raise NotADirectoryError(f"Path exists and is not a directory: {p}")
    p.mkdir(parents=True, exist_ok=exist_ok)
    return p


def now_iso(with_ms: bool = True) -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    if with_ms:
        return datetime.utcnow().isoformat(timespec="milliseconds") + "Z"
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def safe_write_json(path: str | Path, obj: Any, indent: int = 2) -> bool:
    """
    Safely write JSON to disk using an atomic replace.

    Returns True on success, False on failure.
    """
    try:
        p = Path(path)
        ensure_dir(p.parent)
        tmp = p.with_suffix(p.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=indent, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        tmp.replace(p)
        logger.debug("Wrote JSON to %s", p)
        return True
    except Exception as exc:
        logger.exception("Failed to write JSON to %s: %s", path, exc)
        return False


def safe_load_json(path: str | Path, default: Optional[Any] = None) -> Any:
    """Load JSON from path, returning default on error."""
    p = Path(path)
    if not p.exists():
        return default
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("Failed to load JSON from %s: %s", p, exc)
        return default


def chunk_text(text: str, size: int = 1000) -> List[str]:
    """
    Split text into chunks no larger than `size` characters, attempting to split on whitespace
    to avoid breaking words where possible.
    """
    if not text:
        return []
    if len(text) <= size:
        return [text]

    words = text.split()
    chunks: List[str] = []
    current = []
    cur_len = 0

    for w in words:
        wlen = len(w) + (1 if current else 0)  # add space if not first
        if cur_len + wlen <= size:
            current.append(w)
            cur_len += wlen
        else:
            # flush current
            chunks.append(" ".join(current))
            current = [w]
            cur_len = len(w)

    if current:
        chunks.append(" ".join(current))

    # As a fallback, if any chunk is still larger than size (rare), hard-split it
    final_chunks: List[str] = []
    for c in chunks:
        if len(c) <= size:
            final_chunks.append(c)
        else:
            # hard split
            for i in range(0, len(c), size):
                final_chunks.append(c[i : i + size])
    return final_chunks


def truncate(text: Optional[str], max_len: int = 200) -> str:
    """Truncate text to max_len characters, adding an ellipsis if truncated."""
    if text is None:
        return ""
    s = str(text)
    if len(s) <= max_len:
        return s
    if max_len <= 3:
        return s[:max_len]
    return s[: max_len - 3].rstrip() + "..."


def ensure_list(obj: Any) -> List[Any]:
    """Ensure the returned value is a list. Coerce None -> [], other iterables -> list, scalars -> [obj]."""
    if obj is None:
        return []
    if isinstance(obj, list):
        return obj
    if isinstance(obj, (tuple, set)):
        return list(obj)
    if isinstance(obj, Iterable) and not isinstance(obj, (str, bytes, bytearray)):
        return list(obj)
    return [obj]


# Small self-test when executed directly
if __name__ == "__main__":
    pretty_print({"now": now_iso(), "chunks": chunk_text("one two three " * 50, 50)})
    p = Path("tmp_test_dir/subdir")
    ensure_dir(p)
    data = {"a": 1, "b": [1, 2, 3]}
    print("write ok:", safe_write_json(p / "test.json", data))
    print("load:", safe_load_json(p / "test.json"))
    print("truncate:", truncate("abcdefghijklmnopqrstuvwxyz", 10))
