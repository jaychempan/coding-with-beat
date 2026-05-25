"""Shared utilities for coding-with-beat."""

from __future__ import annotations

import re
import time

from .config import LOG_FILE, ensure_dirs

_CJK_RANGES = (
    (0x1100, 0x115F),
    (0x2E80, 0xA4CF),
    (0xAC00, 0xD7AF),
    (0xF900, 0xFAFF),
    (0xFE10, 0xFE6F),
    (0xFF01, 0xFF60),
    (0xFFE0, 0xFFE6),
)

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def char_width(ch: str) -> int:
    """Display-cell width of a single character (1 or 2)."""
    cp = ord(ch)
    return 2 if any(lo <= cp <= hi for lo, hi in _CJK_RANGES) else 1


def display_width(s: str) -> int:
    """Total display-cell width of a plain (no ANSI) string."""
    return sum(char_width(c) for c in s)


def strip_ansi(s: str) -> str:
    """Remove ANSI escape sequences from *s*."""
    return _ANSI_RE.sub("", s)


def mmss(seconds: float) -> str:
    """Format *seconds* as MM:SS."""
    s = max(0, int(seconds))
    return f"{s // 60:02d}:{s % 60:02d}"


def log(msg: str, prefix: str = "") -> None:
    """Append a timestamped line to the shared log file."""
    ensure_dirs()
    tag = f" {prefix}" if prefix else ""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}{tag} {msg}\n")
    except Exception:
        pass
