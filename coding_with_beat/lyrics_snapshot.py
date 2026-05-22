"""Fast lyric lookup for MCP snapshots.

The snapshot path must not block on network lyric lookups. It reads the whole
song lyric cache when available and starts one background fetch per track when
the cache is missing.
"""

from __future__ import annotations

import re
import threading
import time
from pathlib import Path
from typing import Optional

from .config import LYRICS_CACHE
from .ui.lyrics import _index_for_position, parse_lrc

_KEY_RE = re.compile(r"[^a-zA-Z0-9一-鿿]+")
_SOURCE_PREFIX = {"apple_music": "am", "local": "local", "qq_music": "qq"}
_PREFETCH_RETRY_AFTER = 600.0
_LOCK = threading.Lock()
_PREFETCHING: set[str] = set()
_ATTEMPTED_AT: dict[str, float] = {}


def current_text(
    source: str,
    artist: str,
    album: str,
    title: str,
) -> tuple[str, bool]:
    """Return (whole lyrics text, prefetch pending)."""
    if not title:
        return "", False
    text = _read_cached(source, artist, album, title)
    if text.strip():
        return text, False
    return "", _prefetch_once(source, artist, album, title)


def track_key(source: str, artist: str, album: str, title: str) -> str:
    if not title:
        return ""
    return "\0".join([source or "", artist or "", album or "", title or ""])


def cache_path(source: str, artist: str, album: str, title: str) -> Optional[Path]:
    key = _KEY_RE.sub("_", f"{artist}_{album}_{title}").strip("_")[:160]
    if not key:
        return None
    prefix = _SOURCE_PREFIX.get(source, source or "am")
    return LYRICS_CACHE / f"{prefix}_{key}.txt"


def _read_cached(source: str, artist: str, album: str, title: str) -> str:
    path = cache_path(source, artist, album, title)
    if path is None or not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def line_from_text(text: str, position: float, duration: float) -> str:
    cues, is_lrc = parse_lrc(text or "")
    if is_lrc:
        cues = [(ts, body) for ts, body in cues if body.strip()]
        idx = _index_for_position(cues, position)
        return cues[idx][1] if idx >= 0 else ""

    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if not lines:
        return ""
    if duration > 0:
        ratio = max(0.0, min(1.0, float(position or 0.0) / float(duration)))
        idx = int(ratio * (len(lines) - 1))
    else:
        idx = 0
    return lines[max(0, min(idx, len(lines) - 1))]


def _prefetch_once(source: str, artist: str, album: str, title: str) -> bool:
    key = track_key(source, artist, album, title)
    if not key:
        return False
    now = time.time()
    with _LOCK:
        if key in _PREFETCHING:
            return True
        attempted_at = _ATTEMPTED_AT.get(key)
        if attempted_at is not None and (now - attempted_at) < _PREFETCH_RETRY_AFTER:
            return False
        _PREFETCHING.add(key)

    def worker() -> None:
        cached = False
        try:
            from .sources import get_source

            src = get_source(source)
            fn = getattr(src, "lyrics", None)
            if callable(fn):
                fn()
            cached = bool(_read_cached(source, artist, album, title).strip())
        finally:
            with _LOCK:
                _PREFETCHING.discard(key)
                if cached:
                    _ATTEMPTED_AT.pop(key, None)
                else:
                    _ATTEMPTED_AT[key] = time.time()

    threading.Thread(target=worker, name="coding-with-beat-lyrics-prefetch", daemon=True).start()
    return True
