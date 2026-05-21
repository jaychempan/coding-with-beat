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
import subprocess
import sys
import time

from . import state, focus, dj
from .config import DATA_DIR, LYRICS_CACHE
from .sources import get_source
from .ui.lyrics import parse_lrc, _index_for_position
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
    """If the position sample is stale, re-poll the active source.
    Returns (possibly updated state, unsupported reason). Failures fall back to
    cached state silently."""
    base = st.track.position_sampled_at or st.updated_at
    if base and (time.time() - base) < _STALE_AFTER:
        return st, ""
    try:
        src = get_source(st.source)
        np = src.now_playing()
    except Exception:
        return st, ""
    unsupported_reason = getattr(np, "unsupported_reason", None) or ""
    if unsupported_reason:
        st.track.title = ""
        st.track.artist = ""
        st.track.album = ""
        st.track.duration = 0.0
        st.track.position = 0.0
        st.track.position_sampled_at = time.time()
        st.track.artwork_path = None
        st.track.source = np.source
        st.playing = False
        try:
            state.save(st)
        except Exception:
            pass
        return st, unsupported_reason
    if not np.title:
        return st, ""
    st.track.title = np.title
    st.track.artist = np.artist
    st.track.album = np.album
    st.track.duration = np.duration
    st.track.position = np.position
    st.track.position_sampled_at = time.time()
    st.track.artwork_path = np.artwork_path
    st.track.source = np.source
    st.playing = np.playing
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
_SOURCE_PREFIX = {"apple_music": "am", "local": "local", "qq_music": "qq"}


def _cached_lyric_line(st, pos: float):
    """Return the active LRC line for the current track, or None.
    Reads only from the on-disk cache — no network calls in the statusline."""
    t = st.track
    if not t.title:
        return None
    key = _KEY_RE.sub("_", f"{t.artist}_{t.album}_{t.title}").strip("_")[:160]
    prefix = _SOURCE_PREFIX.get(st.source, "am")
    cache = LYRICS_CACHE / f"{prefix}_{key}.txt"
    if not cache.exists():
        return None
    try:
        txt = cache.read_text(encoding="utf-8")
    except Exception:
        return None
    cues, is_lrc = parse_lrc(txt)
    if not is_lrc:
        return None
    cues = [(ts, body) for ts, body in cues if body.strip()]
    if not cues:
        return None
    idx = _index_for_position(cues, pos)
    if idx < 0:
        return None
    return cues[idx][1]


def _bg_fetch_lyrics(st) -> None:
    """Spawn one background process to fetch+cache lyrics when none are cached.
    A lock file under DATA_DIR prevents duplicate fetches for the same track."""
    t = st.track
    if not t.title:
        return
    key = _KEY_RE.sub("_", f"{t.artist}_{t.album}_{t.title}").strip("_")[:160]
    prefix = _SOURCE_PREFIX.get(st.source, "am")
    cache = LYRICS_CACHE / f"{prefix}_{key}.txt"
    if cache.exists():
        return
    lock = DATA_DIR / f".lyfetch_{prefix}_{key}"
    if lock.exists():
        if (time.time() - lock.stat().st_mtime) < 45:
            return  # still fetching
        lock.unlink(missing_ok=True)
    try:
        lock.touch()
        subprocess.Popen(
            [sys.executable, "-m", "coding_with_beat", "_prefetch"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception:
        pass


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
    elif unsupported_reason or st.source == "qq_music":
        track = "\x1b[38;2;120;130;130mqq_music now-playing unsupported\x1b[0m"
    else:
        track = "\x1b[38;2;120;130;130mno track loaded — try /cwb play 周杰伦\x1b[0m"

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
        lyric = _cached_lyric_line(st, pos)
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
            _bg_fetch_lyrics(st)
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
