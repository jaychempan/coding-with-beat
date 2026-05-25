"""Lyric rendering.

Two input formats are supported:
  - LRC text (`[mm:ss.xx] line`) — produces a timed sequence; the current line
    is the latest cue whose timestamp <= position.
  - Plain text — splits on newlines; the current line is interpolated from
    position/duration so it scrolls karaoke-style without real timing.
"""

from __future__ import annotations

import math
import re
from typing import List, Optional, Tuple

from ..utils import char_width as _char_width
from ..utils import display_width as _display_width

HIGHLIGHT = "\x1b[1;38;2;255;230;100m"
NEXT = "\x1b[38;2;200;200;230m"
DIM = "\x1b[38;2;120;130;130m"
EDGE = "\x1b[38;2;90;90;105m"
RESET = "\x1b[0m"

_PREFIX_W = 2  # "▶ " / "  " prefix display width


def _wrap_text(line: str, max_w: int) -> List[str]:
    """Split line into chunks that each fit within max_w display columns."""
    if max_w <= 0 or _display_width(line) <= max_w:
        return [line]
    chunks, cur, cur_w = [], "", 0
    for ch in line:
        cw = _char_width(ch)
        if cur_w + cw > max_w:
            chunks.append(cur)
            cur, cur_w = ch, cw
        else:
            cur += ch
            cur_w += cw
    if cur:
        chunks.append(cur)
    return chunks or [line]


_LRC_RE = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")
_INLINE_TS_RE = re.compile(r"<(\d+):(\d+(?:\.\d+)?)>")


def parse_lrc(text: str) -> Tuple[List[Tuple[float, str]], bool]:
    """Return (cues, is_lrc). cues is a sorted [(seconds, line)]; empty when
    the text has no LRC timestamps."""
    cues: List[Tuple[float, str]] = []
    has_ts = False
    for raw in text.splitlines():
        stamps = _LRC_RE.findall(raw)
        inline_stamps = _INLINE_TS_RE.findall(raw)
        if not stamps and not inline_stamps:
            continue
        has_ts = True
        body = _LRC_RE.sub("", raw)
        body = _INLINE_TS_RE.sub("", body).strip()
        if stamps:
            for mm, ss in stamps:
                t = int(mm) * 60 + float(ss)
                cues.append((t, body))
        else:
            # Enhanced LRC with only per-character timestamps — use the first as line time
            mm, ss = inline_stamps[0]
            t = int(mm) * 60 + float(ss)
            if body:
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
    width: Optional[int] = None,
) -> str:
    """Render a window of lyrics with the active line highlighted.

    text_or_lines: either an LRC blob (str), a plain-text blob (str), or a
        pre-split list[str]. Backwards-compat: old callers that pass
        (lines, current_index, window) still work via current_index.
    position/duration: used to pick the active line when text is LRC,
        or to interpolate a current line for plain-text lyrics.
    """
    if isinstance(text_or_lines, list):
        lines = [line for line in text_or_lines if line is not None]
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
            lines = [ln for line in text.splitlines() if (ln := _INLINE_TS_RE.sub("", line).strip())]

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

    if width is None:
        import shutil

        width = shutil.get_terminal_size((80, 24)).columns
    text_w = max(1, width - _PREFIX_W)

    out = []
    for i in range(start, end):
        raw = lines[i] or "·"
        chunks = _wrap_text(raw, text_w)
        if i == current_index:
            out.append(f"{HIGHLIGHT}▶ {chunks[0]}{RESET}")
            for chunk in chunks[1:]:
                out.append(f"{HIGHLIGHT}  {chunk}{RESET}")
        elif i == current_index + 1:
            out.append(f"{NEXT}  {chunks[0]}{RESET}")
            for chunk in chunks[1:]:
                out.append(f"{NEXT}  {chunk}{RESET}")
        else:
            out.append(f"{DIM}  {chunks[0]}{RESET}")
            for chunk in chunks[1:]:
                out.append(f"{DIM}  {chunk}{RESET}")
    return "\n".join(out)


def _wave_line(line: str, t: float, flash: float = 0.0) -> str:
    """Render each character of line with a sin-wave colour oscillation.

    flash=1.0 → pure white (used on line-entry); flash=0.0 → animated gold wave.
    """
    out = []
    for i, ch in enumerate(line):
        v = (math.sin(t * 4.0 + i * 0.45) + 1) / 2  # 0..1
        wv_r = 255
        wv_g = int(230 + v * 25)
        wv_b = int(100 + v * 130)
        if flash > 0:
            r = int(wv_r + flash * (255 - wv_r))
            g = int(wv_g + flash * (255 - wv_g))
            b = int(wv_b + flash * (255 - wv_b))
        else:
            r, g, b = wv_r, wv_g, wv_b
        out.append(f"\x1b[1;38;2;{r};{g};{b}m{ch}")
    return "".join(out) + RESET


def render_lyrics_wave(
    text_or_lines,
    position: float = 0.0,
    duration: float = 0.0,
    window: int = 5,
    t: float = 0.0,
    width: Optional[int] = None,
) -> str:
    """Like render_lyrics_window but the active line has a per-character wave
    animation driven by wall-clock time t, plus a brief white flash on entry."""
    if isinstance(text_or_lines, list):
        lines = [line for line in text_or_lines if line is not None]
        cues: List[Tuple[float, str]] = []
        is_lrc = False
    else:
        text = text_or_lines or ""
        cues, is_lrc = parse_lrc(text)
        if is_lrc:
            cues = [(ts, b) for ts, b in cues if b.strip()]
            lines = [c[1] for c in cues]
        else:
            lines = [ln for line in text.splitlines() if (ln := _INLINE_TS_RE.sub("", line).strip())]

    if not lines:
        return f"{DIM}(no lyrics){RESET}"

    if is_lrc:
        current_index = _index_for_position(cues, position)
    elif duration > 0:
        ratio = max(0.0, min(1.0, position / duration))
        current_index = int(ratio * (len(lines) - 1))
    else:
        current_index = 0
    current_index = max(0, min(current_index, len(lines) - 1))

    # Flash brightness: 1→0 in first 0.35 s after the cue starts
    flash = 0.0
    if is_lrc and current_index >= 0:
        cue_time = cues[current_index][0]
        elapsed = position - cue_time
        if 0 <= elapsed < 0.35:
            flash = 1.0 - elapsed / 0.35

    half = window // 2
    start = max(0, current_index - half)
    end = min(len(lines), start + window)
    start = max(0, end - window)

    if width is None:
        import shutil

        width = shutil.get_terminal_size((80, 24)).columns
    text_w = max(1, width - _PREFIX_W)

    out = []
    for i in range(start, end):
        raw = lines[i] or "·"
        chunks = _wrap_text(raw, text_w)
        if i == current_index:
            out.append(f"▶ {_wave_line(chunks[0], t, flash)}")
            for chunk in chunks[1:]:
                out.append(f"  {_wave_line(chunk, t, 0.0)}")
        elif i == current_index + 1:
            out.append(f"{NEXT}  {chunks[0]}{RESET}")
            for chunk in chunks[1:]:
                out.append(f"{NEXT}  {chunk}{RESET}")
        else:
            out.append(f"{DIM}  {chunks[0]}{RESET}")
            for chunk in chunks[1:]:
                out.append(f"{DIM}  {chunk}{RESET}")
    return "\n".join(out)
