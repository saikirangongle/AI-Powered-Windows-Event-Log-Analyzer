# src/utils/file_loader.py
"""
File Loader Utility (Patched)

Guarantees:
- ALWAYS returns UTF-8 text (str), never bytes
- Handles small and large files safely
- Falls back to 'utf-8' with replacement characters if needed
- Logs helpful messages on failures

Functions:
- file_exists(path: str) -> bool
- load_file(path: str) -> str
"""

import os
from src.main.logger import logger


def file_exists(path: str) -> bool:
    """Return True if file exists and is a regular file."""
    try:
        return os.path.isfile(path)
    except Exception:
        return False


def load_file(path: str) -> str:
    """
    Load a file safely and ALWAYS return UTF-8 TEXT.

    Behavior:
    - If file is small (<4MB), try reading as UTF-8 text first.
    - If UTF-8 read fails or file is large, read bytes then decode to UTF-8.
    - If decoding fails, fall back to 'utf-8' with errors='replace' to ensure a string return.
    - Never returns bytes.

    Raises:
        FileNotFoundError, PermissionError, OSError (propagated)
    """
    if not file_exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    try:
        size = os.path.getsize(path)
    except Exception as exc:
        logger.exception("Could not get file size for '%s': %s", path, exc)
        raise

    logger.debug("Loading file '%s' (%d bytes)", path, size)

    # For small files, attempt text mode first for performance/readability
    if size < 4 * 1024 * 1024:  # <4MB
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            logger.info("UTF-8 decode failed for '%s' when reading as text; falling back to binary decode.", path)
        except Exception as exc:
            logger.error("Failed to read file as text '%s': %s", path, exc)
            raise

    # Fallback: read as bytes and decode to text (always return str)
    try:
        with open(path, "rb") as f:
            data = f.read()
            try:
                return data.decode("utf-8")
            except Exception:
                # Last resort: decode with replacement characters to avoid raising
                return data.decode("utf-8", errors="replace")
    except Exception as exc:
        logger.error("Failed to read file as bytes '%s': %s", path, exc)
        raise
