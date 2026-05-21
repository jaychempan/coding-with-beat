"""Lyric rendering.

Two input formats are supported:
  - LRC text (`[mm:ss.xx] line`) — produces a timed sequence; the current line
    is the latest cue whose timestamp <= position.
  - Plain text — splits on newlines; the current line is interpolated from
    position/duration so it scrolls karaoke-style without real timing.
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple


HIGHLIGHT = "\x1b[1;38;2;255;230;100m"
NEXT      = "\x1b[38;2;200;200;230m"
DIM       = "\x1b[38;2;120;130;130m"
EDGE      = "\x1b[38;2;90;90;105m"
RESET     = "\x1b[0m"


_LRC_RE = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")


def parse_lrc(text: str) -> Tuple[List[Tuple[float, str]], bool]:
    """Return (cues, is_lrc). cues is a sorted [(seconds, line)]; empty when
    the text has no LRC timestamps."""
    cues: List[Tuple[float, str]] = []
    has_ts = False
    for raw in text.splitlines():
        stamps = _LRC_RE.findall(raw)
        if not stamps:
            continue
        has_ts = True
        body = _LRC_RE.sub("", raw).strip()
        for mm, ss in stamps:
            t = int(mm) * 60 + float(ss)
            cues.append((t, body))
    cues.sort(key=lambda x: x[0])
    return cues, has_ts


def _index_for_position(cues: List[Tuple[float, str]], pos: float) -> int:
    """Latest cue whose timestamp <= pos. -1 if none yet."""
    idx = -1
    for i, (t, _) in enumerate(cues):
        if t <= pos:
            idx = i
        else:
            break
    return idx


def render_lyrics_window(
    text_or_lines,
    position: float = 0.0,
    duration: float = 0.0,
    window: int = 5,
    current_index: int = -1,
) -> str:
    """Render a window of lyrics with the active line highlighted.

    text_or_lines: either an LRC blob (str), a plain-text blob (str), or a
        pre-split list[str]. Backwards-compat: old callers that pass
        (lines, current_index, window) still work via current_index.
    position/duration: used to pick the active line when text is LRC,
        or to interpolate a current line for plain-text lyrics.
    """
    if isinstance(text_or_lines, list):
        lines = [l for l in text_or_lines if l is not None]
        cues: List[Tuple[float, str]] = []
        is_lrc = False
    else:
        text = text_or_lines or ""
        cues, is_lrc = parse_lrc(text)
        if is_lrc:
            # Keep only non-blank cues so empty separators don't show as `·`
            cues = [(t, b) for t, b in cues if b.strip()]
            lines = [c[1] for c in cues]
        else:
            lines = [l.strip() for l in text.splitlines() if l.strip()]

    if not lines:
        return f"{DIM}(no lyrics){RESET}"

    if current_index < 0:
        if is_lrc:
            current_index = _index_for_position(cues, position)
        elif duration > 0:
            ratio = max(0.0, min(1.0, position / duration))
            current_index = int(ratio * (len(lines) - 1))
        else:
            current_index = 0
    current_index = max(0, min(current_index, len(lines) - 1))

    half = window // 2
    start = max(0, current_index - half)
    end = min(len(lines), start + window)
    start = max(0, end - window)

    out = []
    for i in range(start, end):
        line = lines[i] or "·"
        if i == current_index:
            out.append(f"{HIGHLIGHT}▶ {line}{RESET}")
        elif i == current_index + 1:
            out.append(f"{NEXT}  {line}{RESET}")
        else:
            out.append(f"{DIM}  {line}{RESET}")
    return "\n".join(out)
