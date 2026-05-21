"""Render a compact single-line statusline for Claude Code.

CC invokes the configured `statusLine.command`, passes JSON context on stdin,
and renders the program's stdout as the bottom bar. We must:
  - be fast (<200ms)
  - return short ANSI-coloured text (one line, plus an optional lyric line)
  - prefer cached state, but opportunistically re-poll when stale so the bar
    stays synced after seeks/restarts/external GUI changes
"""
from __future__ import annotations

import json
import re
import sys
import time

from . import state, focus, dj
from .mcp_client import MCPClientError, call_tool
from .lyrics_snapshot import line_from_text
from .ui.progress import render_progress


# If our cached position sample is older than this, do a fast re-poll
# of the source before rendering. ~50–150ms for AppleScript; acceptable.
_STALE_AFTER = 2.5
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _vlen(s: str) -> int:
    """Visible character count — strips ANSI escape sequences."""
    return len(_ANSI_RE.sub("", s))


def _mmss(seconds: float) -> str:
    s = max(0, int(seconds))
    return f"{s // 60:02d}:{s % 60:02d}"


def _maybe_refresh(st):
    """Refresh track state through the configured HTTP MCP endpoint."""
    base = st.track.position_sampled_at or st.updated_at
    if st.track.title and base and (time.time() - base) < _STALE_AFTER:
        return st, ""
    try:
        known_lyrics_key = st.track.lyrics_key if st.track.lyrics_text else ""
        data = json.loads(call_tool("now_playing_snapshot", {"known_lyrics_key": known_lyrics_key}))
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
    st, unsupported_reason = _maybe_refresh(st)
    f = focus.status()

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
        title = st.track.title[:28]
        artist = (st.track.artist or "—")[:18]
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
        track = "\x1b[38;2;120;130;130mno track loaded — try /juke play 周杰伦\x1b[0m"

    focus_chip = ""
    if f.active:
        emoji = "🍅" if f.phase == "work" else "☕"
        focus_chip = f"  \x1b[38;2;255;180;120m{emoji} {f.phase} {_mmss(f.remaining)}\x1b[0m"

    vibe_chip = f"  \x1b[38;2;{ar};{ag};{ab}m[{st.vibe or 'build'}]\x1b[0m"

    line1 = f"{face_part}  {track}{vibe_chip}{focus_chip}"

    # ── lyric / DJ quip chip (width-aware) ─────────────────────
    # Available chars for chip text = terminal_width - visible(line1) - overhead.
    # overhead: "  │ " = 4 visible chars; prefix "♪ " or "✦ " = 2 each.
    avail = (term_width - _vlen(line1) - 4) if term_width > 0 else 999

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

    return f"{line1}{chip}"


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
