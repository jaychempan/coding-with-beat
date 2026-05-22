"""Render a compact single-line statusline for Claude Code.

CC invokes the configured `statusLine.command`, passes JSON context on stdin,
and renders the program's stdout as the bottom bar. We must:
  - be fast (<200ms)
  - return short ANSI-coloured text (one line, plus an optional lyric line)
  - prefer cached state, but opportunistically re-poll when stale so the bar
    stays synced after seeks/restarts/external GUI changes
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time

from . import state, focus, dj
from .mcp_client import MCPClientError, call_tool
from .lyrics_snapshot import line_from_text
from .ui.progress import render_progress, render_beat_wave


# If our cached position sample is older than this, do a fast re-poll
# of the source before rendering. ~50–150ms for AppleScript; acceptable.
_STALE_AFTER = 2.5
_STATUSLINE_MCP_TIMEOUT_ENV = "CWB_STATUSLINE_MCP_TIMEOUT"
_LEGACY_STATUSLINE_MCP_TIMEOUT_ENV = "CC_JUKEBOX_STATUSLINE_MCP_TIMEOUT"
_STATUSLINE_MCP_TIMEOUT_DEFAULT = 1.5
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _vlen(s: str) -> int:
    """Visible character count — strips ANSI escape sequences."""
    return len(_ANSI_RE.sub("", s))


_CJK_RANGES = (
    (0x1100, 0x115F), (0x2E80, 0xA4CF), (0xAC00, 0xD7AF),
    (0xF900, 0xFAFF), (0xFE10, 0xFE6F), (0xFF01, 0xFF60), (0xFFE0, 0xFFE6),
)


def _cw(ch: str) -> int:
    """Display-cell width of a single character (1 or 2)."""
    cp = ord(ch)
    return 2 if any(lo <= cp <= hi for lo, hi in _CJK_RANGES) else 1


def _dw(s: str) -> int:
    """Total display-cell width of a plain (no ANSI) string."""
    return sum(_cw(c) for c in s)


def _marquee(text: str, width: int, t: float, speed: float = 4.0) -> str:
    """Return a fixed-`width`-cell slice of text, scrolling over time if too wide."""
    dw = _dw(text)
    if dw <= width:
        return text
    loop   = text + "  "          # two-space gap before the repeat
    total  = _dw(loop)
    offset = int(t * speed) % total
    # Advance to `offset` display cells
    doubled = loop * 2
    start, acc = 0, 0
    for i, ch in enumerate(doubled):
        if acc >= offset:
            start = i
            break
        acc += _cw(ch)
    # Collect exactly `width` display cells from `start`
    result, w = [], 0
    for ch in doubled[start:]:
        cw = _cw(ch)
        if w + cw > width:
            break
        result.append(ch)
        w += cw
    if w < width:
        result.append(" " * (width - w))
    return "".join(result)


def _mmss(seconds: float) -> str:
    s = max(0, int(seconds))
    return f"{s // 60:02d}:{s % 60:02d}"


def _statusline_mcp_timeout() -> float:
    raw = (
        os.environ.get(_STATUSLINE_MCP_TIMEOUT_ENV, "")
        or os.environ.get(_LEGACY_STATUSLINE_MCP_TIMEOUT_ENV, "")
    )
    if not raw:
        return _STATUSLINE_MCP_TIMEOUT_DEFAULT
    try:
        return max(0.1, float(raw))
    except ValueError:
        return _STATUSLINE_MCP_TIMEOUT_DEFAULT


def _maybe_refresh(st):
    """Refresh track state through the configured HTTP MCP endpoint."""
    # For no-track/unsupported states, only a real source/MCP sample should
    # throttle refreshes. Hook saves update st.updated_at and must not mask a
    # newly started track.
    base = st.track.position_sampled_at or (st.updated_at if st.track.title else 0)
    if base and (time.time() - base) < _STALE_AFTER:
        return st, ""
    try:
        known_lyrics_key = st.track.lyrics_key if st.track.lyrics_text else ""
        data = json.loads(call_tool(
            "now_playing_snapshot",
            {"known_lyrics_key": known_lyrics_key},
            timeout=_statusline_mcp_timeout(),
        ))
    except MCPClientError as e:
        return st, f"MCP offline: {str(e).splitlines()[0]}"
    except Exception as e:
        return st, f"MCP snapshot failed: {e}"

    unsupported_reason = str(data.get("unsupported_reason") or "")
    source = str(data.get("source") or st.source)
    if unsupported_reason:
        st.track.title = ""
        st.track.artist = ""
        st.track.album = ""
        st.track.duration = 0.0
        st.track.position = 0.0
        st.track.position_sampled_at = time.time()
        st.track.lyrics_key = ""
        st.track.lyrics_text = ""
        st.track.lyrics_pending = False
        st.track.artwork_path = None
        st.track.source = source
        st.source = source
        st.playing = False
        try:
            state.save(st)
        except Exception:
            pass
        return st, unsupported_reason
    if not data.get("title"):
        # Preserve the last known track instead of blanking it — a failed
        # search or brief gap shouldn't clear what the user was listening to.
        st.track.position_sampled_at = time.time()
        st.track.source = source
        st.source = source
        st.playing = bool(data.get("playing"))
        try:
            state.save(st)
        except Exception:
            pass
        return st, ""
    st.source = source
    st.track.title = str(data.get("title") or "")
    st.track.artist = str(data.get("artist") or "")
    st.track.album = str(data.get("album") or "")
    st.track.duration = float(data.get("duration") or 0.0)
    st.track.position = float(data.get("position") or 0.0)
    # Use the local receive time as the extrapolation base. In SSH setups the
    # Mac MCP server and the remote shell can have different wall clocks.
    st.track.position_sampled_at = time.time()
    lyrics_key = str(data.get("lyrics_key") or "")
    if lyrics_key != st.track.lyrics_key:
        st.track.lyrics_text = ""
    st.track.lyrics_key = lyrics_key
    lyrics_text = data.get("lyrics_text")
    if isinstance(lyrics_text, str) and lyrics_text:
        st.track.lyrics_text = lyrics_text
    st.track.lyrics_pending = bool(data.get("lyrics_pending"))
    st.track.artwork_path = str(data.get("artwork_path") or "") or None
    st.track.source = source
    st.playing = bool(data.get("playing"))
    try:
        state.save(st)
    except Exception:
        pass
    return st, ""


def _live_position(st) -> float:
    """Extrapolate position from the last source sample so the bar keeps
    moving between polls."""
    pos = st.track.position
    base = st.track.position_sampled_at or st.updated_at
    if st.playing and base and st.track.duration:
        pos = min(st.track.duration, pos + (time.time() - base))
    return pos


_KEY_RE = re.compile(r"[^a-zA-Z0-9一-鿿]+")
# Accent colour per vibe — tints the progress bar, play icon, vibe chip, and quip.
_VIBE_ACCENT: dict[str, tuple[int, int, int]] = {
    "build":   (155, 188,  15),  # GameBoy green
    "focus":   ( 80, 140, 210),  # cobalt blue
    "debug":   (220, 155,  30),  # amber
    "victory": (255, 205,  50),  # gold
    "fail":    (200,  70,  70),  # soft red
    "idle":    (120, 120, 140),  # slate
    "review":  ( 60, 190, 165),  # teal
}
_PLAY_PULSE = ("▶", "▷")  # alternates every second when playing
_FLOW_HOT   = 15   # seconds since last tool → ⚡ (in the zone)
_FLOW_WARM  = 90   # seconds since last tool → · (still warm)
_QUIP_TTL   = 4.0  # seconds to show DJ quip before falling back to lyric


def render(term_width: int = 0) -> str:
    st = state.load()

    mode = st.statusline_mode or "show"
    if mode == "hide":
        return ""

    st, unsupported_reason = _maybe_refresh(st)
    f = focus.status()

    if mode == "auto" and not st.playing and not f.active:
        return ""

    ar, ag, ab = _VIBE_ACCENT.get(st.vibe or "build", (155, 188, 15))
    pos = _live_position(st)
    now = time.time()

    # ── DJ face + flow indicator ────────────────────────────────
    face_str = dj.face(st.dj_mood or "neutral")
    since_tool = now - (st.last_tool_at or 0)
    if since_tool < _FLOW_HOT:
        flow = f"\x1b[1;38;2;{ar};{ag};{ab}m⚡\x1b[0m"
    elif since_tool < _FLOW_WARM:
        dim = max(40, ar // 3), max(40, ag // 3), max(40, ab // 3)
        flow = f"\x1b[38;2;{dim[0]};{dim[1]};{dim[2]}m·\x1b[0m"
    else:
        flow = ""
    face_part = f"{face_str}{(' ' + flow) if flow else ''}"

    # ── track line ─────────────────────────────────────────────
    if st.track.title:
        title  = _marquee(st.track.title,          20, now)
        artist = _marquee(st.track.artist or "—",  12, now)
        bar = render_progress(pos, st.track.duration, width=14, accent=(ar, ag, ab))
        if st.playing:
            icon = _PLAY_PULSE[int(now) & 1]
            icon_seq = f"\x1b[1;38;2;{ar};{ag};{ab}m{icon}\x1b[0m"
        else:
            icon_seq = "\x1b[1;38;2;120;130;130m❚❚\x1b[0m"
        track = f"{icon_seq} \x1b[38;2;200;200;230m{title}\x1b[0m \x1b[38;2;120;130;130m— {artist}\x1b[0m {bar}"
    elif unsupported_reason:
        msg = unsupported_reason.splitlines()[0][:54]
        track = f"\x1b[38;2;120;130;130m{msg}\x1b[0m"
    elif st.source == "qq_music":
        track = "\x1b[38;2;120;130;130mqq_music now-playing unsupported\x1b[0m"
    else:
        track = "\x1b[38;2;120;130;130mno track loaded — try /cwb play lofi beats\x1b[0m"

    focus_chip = ""
    if f.active:
        emoji = "🍅" if f.phase == "work" else "☕"
        focus_chip = f"  \x1b[38;2;255;180;120m{emoji} {f.phase} {_mmss(f.remaining)}\x1b[0m"

    vibe_chip = f"  \x1b[38;2;{ar};{ag};{ab}m[{st.vibe or 'build'}]\x1b[0m"

    line1 = f"{face_part}  {track}{vibe_chip}{focus_chip}"

    # ── beat wave chip (far right) ─────────────────────────────
    beat_chip = ""
    beat_chip_visible = 0
    if st.track.title:
        _key = _KEY_RE.sub("_", f"{st.track.artist}_{st.track.album}_{st.track.title}").strip("_")[:160]
        _h = int(hashlib.md5(_key.encode()).hexdigest()[:8], 16)
        _bpm = 72 + (_h % 80)
        beat_chip = f"  {render_beat_wave(_bpm, now, accent=(ar, ag, ab), playing=st.playing)}"
        beat_chip_visible = _vlen(beat_chip)  # 2 spaces + 5 wave chars = 7

    # ── lyric / DJ quip chip (width-aware) ─────────────────────
    # Available chars for chip text = terminal_width - visible(line1) - overhead - beat wave.
    # overhead: "  │ " = 4 visible chars; prefix "♪ " or "✦ " = 2 each.
    avail = (term_width - _vlen(line1) - 4 - beat_chip_visible) if term_width > 0 else 999

    quip_age = now - (st.dj_quip_at or 0)
    if st.dj_quip and quip_age < _QUIP_TTL:
        content = st.dj_quip
        if avail >= len(content) + 2:
            chip = (
                f"  \x1b[38;2;70;72;90m│\x1b[0m"
                f" \x1b[38;2;{ar};{ag};{ab}m✦ {content}\x1b[0m"
            )
        elif avail >= 3:
            chip = f"  \x1b[38;2;{ar};{ag};{ab}m✦\x1b[0m"
        else:
            chip = ""
    elif st.track.title:
        lyric = line_from_text(st.track.lyrics_text, pos, st.track.duration).strip()
        if lyric:
            max_lyric = max(0, avail - 2)  # "♪ " prefix = 2 chars
            if max_lyric <= 0:
                chip = f"  \x1b[38;2;55;58;72m♪\x1b[0m" if avail >= 3 else ""
            else:
                if len(lyric) > max_lyric:
                    lyric = lyric[:max_lyric - 1] + "…"
                chip = (
                    f"  \x1b[38;2;70;72;90m│\x1b[0m"
                    f" \x1b[3;38;2;180;180;200m♪ {lyric}\x1b[0m"
                )
        else:
            chip = f"  \x1b[38;2;55;58;72m♪\x1b[0m" if avail >= 3 else ""
    else:
        chip = f"  \x1b[38;2;55;58;72m♪\x1b[0m" if avail >= 3 else ""

    return f"{line1}{beat_chip}{chip}"


def main() -> int:
    term_width = 0
    try:
        raw = sys.stdin.read()
        ctx = json.loads(raw) if raw.strip() else {}
        # CC may provide terminal dimensions under various keys
        term_width = int(
            ctx.get("columns") or ctx.get("terminalWidth") or
            ctx.get("terminal_width") or ctx.get("cols") or 0
        )
    except Exception:
        pass
    if not term_width:
        try:
            import shutil
            term_width = shutil.get_terminal_size((0, 0)).columns
        except Exception:
            pass
    sys.stdout.write(render(term_width=term_width))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
