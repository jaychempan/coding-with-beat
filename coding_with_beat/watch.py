"""Compact real-time watch mode — local render from JSON snapshot.

Layout (adaptive to terminal size):
  ┌─── left 60% ───┬─── right 40% ───┐
  │  player        │                 │
  │  progress      │  queue list     │
  │  spectrum      │  (full height)  │
  ├────────────────┤                 │
  │  lyrics        │                 │
  │  (more lines)  │                 │
  │  DJ buddy      │                 │
  │  hint bar      │                 │
  └────────────────┴─────────────────┘
"""

from __future__ import annotations

import json
import math
import shutil
import signal
import sys
import threading
import time

from . import dj
from ._tui import (
    CLEAR,
    enter_alt_screen,
    exit_alt_screen,
    read_key,
    restore_tty,
    setup_raw_tty,
)
from .config import DATA_DIR, STATE_FILE
from .mcp_client import MCPClientError, call_tool
from .ui.frame import _strip_ansi
from .ui.lyrics import _display_width, render_lyrics_window
from .ui.progress import render_progress, render_spectrum_color

FETCH_EVERY = 2.0
RENDER_EVERY = 0.05
JUMP_ROWS = 3  # max rows the sprite can lift above ground
_SPRITE_W = 10  # visible width of pixel-person frame
_NUM_TIMEOUT = 0.8  # seconds before auto-confirming a typed number

_ACCENT = (155, 188, 15)
_DIM = "\x1b[38;2;100;110;100m"
_BOLD = "\x1b[1;38;2;220;230;220m"
_GREEN = "\x1b[38;2;155;188;15m"
_CUR = "\x1b[1;38;2;255;230;100m"
_RESET = "\x1b[0m"

_CC_QUIP_TTL = 7.0  # seconds a CC quip stays visible in watch
_cc_state_cache: list = [None, 0.0]  # [dict | None, timestamp]
_CC_STATE_CACHE_TTL = 0.8


def _load_cc_state() -> dict:
    """Read dj_mood/dj_quip/dj_quip_at from state.json (cached)."""
    now = time.time()
    if _cc_state_cache[0] is not None and now - _cc_state_cache[1] < _CC_STATE_CACHE_TTL:
        return _cc_state_cache[0]
    try:
        raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        result = {
            "dj_mood": raw.get("dj_mood") or "neutral",
            "dj_quip": raw.get("dj_quip") or "",
            "dj_quip_at": float(raw.get("dj_quip_at") or 0.0),
        }
    except Exception:
        result = {"dj_mood": "neutral", "dj_quip": "", "dj_quip_at": 0.0}
    _cc_state_cache[0] = result
    _cc_state_cache[1] = now
    return result


def _speech_bubble(text: str, sprite_x: int, width: int) -> list[str]:
    """Return 3 display lines: top border, text, downward pointer — bubble above sprite."""
    max_t = max(4, min(width - sprite_x - 4, 28))
    if len(text) > max_t:
        text = text[: max_t - 1] + "…"
    inner = len(text) + 2  # one space padding each side
    # Center bubble over the sprite
    bx = max(0, min(sprite_x + _SPRITE_W // 2 - (inner + 2) // 2, width - inner - 2))
    ptr_x = sprite_x + _SPRITE_W // 2  # ▼ points at sprite center

    top = " " * bx + _DIM + "╭" + "─" * inner + "╮" + _RESET
    mid = " " * bx + _DIM + "│" + _RESET + " " + _BOLD + text + _RESET + " " + _DIM + "│" + _RESET
    bot = " " * ptr_x + _DIM + "▼" + _RESET

    return [_pad(top, width), _pad(mid, width), _pad(bot, width)]


def _snap_from_state_file() -> dict:
    """Build a minimal snap from state.json so watch has something to show before
    the first server response arrives (covers server restarts and cold starts)."""
    try:
        data = json.loads((DATA_DIR / "state.json").read_text(encoding="utf-8"))
        track = data.get("track", {})
        if not track.get("title"):
            return {}
        return {
            "title": track.get("title", ""),
            "artist": track.get("artist", ""),
            "album": track.get("album", ""),
            "duration": float(track.get("duration") or 0.0),
            "position": float(track.get("position") or 0.0),
            "playing": bool(data.get("playing", False)),
            "source": track.get("source") or data.get("source", ""),
            "artwork_path": track.get("artwork_path") or "",
            "sampled_at": float(track.get("position_sampled_at") or 0.0),
        }
    except Exception:
        return {}


def _fetch(known_key: str = "") -> dict:
    raw = call_tool("now_playing_snapshot", {"known_lyrics_key": known_key})
    return json.loads(raw)


def _interp_pos(snap: dict) -> float:
    pos = float(snap.get("position", 0.0))
    if snap.get("playing"):
        pos += time.time() - float(snap.get("sampled_at", time.time()))
    dur = float(snap.get("duration", 0.0))
    return max(0.0, min(pos, dur) if dur > 0 else pos)


_control_lock = threading.Lock()
_fetch_lock = threading.Lock()
_fetch_result: list[dict | None] = [None]  # [0] holds latest completed fetch


def _fetch_async(known_key: str) -> None:
    """Fire a snapshot fetch in a background thread; store result in _fetch_result."""
    if not _fetch_lock.acquire(blocking=False):
        return  # previous fetch still in flight; skip — render loop uses old snap

    def _run():
        try:
            _fetch_result[0] = _fetch(known_key)
        except MCPClientError:
            pass
        finally:
            _fetch_lock.release()

    threading.Thread(target=_run, daemon=True).start()


def _control(tool: str) -> None:
    try:
        call_tool(tool)
    except MCPClientError:
        pass


def _control_async(tool: str) -> None:
    """Fire a control command in a background thread so the render loop stays live."""
    if not _control_lock.acquire(blocking=False):
        return  # previous command still running; skip

    def _run():
        try:
            call_tool(tool)
        except MCPClientError:
            pass
        finally:
            _control_lock.release()

    threading.Thread(target=_run, daemon=True).start()


def _sep(width: int) -> str:
    return _DIM + "─" * max(1, width) + _RESET


def _vis_len(s: str) -> int:
    return _display_width(_strip_ansi(s))


def _pad(s: str, width: int) -> str:
    """Pad an ANSI string to exactly `width` visible columns."""
    return s + " " * max(0, width - _vis_len(s))


def _trunc(s: str, width: int) -> str:
    """Truncate a plain string to `width` visible chars."""
    if _display_width(s) <= width:
        return s
    lo, hi = 0, len(s)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _display_width(s[:mid]) <= width - 1:
            lo = mid
        else:
            hi = mid - 1
    return s[:lo] + "…"


def _load_queue() -> tuple[list[dict], int, str]:
    # Use context (last listed/searched) for display, not mode (currently playing).
    # This mirrors the old last_results.json behaviour: the panel always shows
    # whatever the user most recently loaded, whether or not playback has started.
    try:
        am = json.loads((DATA_DIR / "active_mode.json").read_text(encoding="utf-8"))
        context = am.get("context", "library")
        label = am.get("label", "Library" if context == "library" else "Queue")
    except Exception:
        context = "library"
        label = "Library"
    fname = "library_queue.json" if context == "library" else "search_queue.json"
    try:
        data = json.loads((DATA_DIR / fname).read_text(encoding="utf-8"))
        tracks = data.get("tracks", [])
        cur_idx = int(data.get("index", -1))
    except Exception:
        tracks = []
        cur_idx = -1
    # Fall back to legacy last_results.json (plain list) if no new-format file exists.
    if not tracks:
        try:
            raw = json.loads((DATA_DIR / "last_results.json").read_text(encoding="utf-8"))
            if isinstance(raw, list):
                tracks = raw
        except Exception:
            pass
    return tracks, cur_idx, label


def _render_player_top(snap: dict, width: int, height: int, t: float) -> list[str]:
    """Top-left panel: title, progress, spectrum (compact, no sprite)."""
    title = snap.get("title") or "—"
    artist = snap.get("artist") or ""
    playing = snap.get("playing", False)
    dur = float(snap.get("duration", 0.0))
    pos = _interp_pos(snap)

    icon = f"{_GREEN}▶{_RESET}" if playing else f"{_DIM}❚❚{_RESET}"
    rows: list[str] = [
        "",
        f" {icon}  {_BOLD}{_trunc(title, width - 6)}{_RESET}",
    ]
    if artist:
        rows.append(f"    {_DIM}{_trunc(artist, width - 5)}{_RESET}")
    rows += [
        _sep(width),
        " " + render_progress(pos, dur, max(1, width - 17), _ACCENT),
        " " + render_spectrum_color(pos, max(1, width - 2), t=t),
    ]

    while len(rows) < height:
        rows.append("")
    return [_pad(r, width) for r in rows[:height]]


def _render_lyrics_bottom(
    lyrics_text: str,
    pos: float,
    dur: float,
    width: int,
    height: int,
    playing: bool,
    t: float = 0.0,
    cc_mood: str = "",
    cc_quip: str = "",
) -> list[str]:
    """Bottom-left panel: lyrics (top) + animated pixel person walking/jumping below."""
    has_quip = bool(cc_quip)
    if cc_mood and cc_mood != "neutral":
        mood = cc_mood
    else:
        mood = "groove" if playing else "neutral"
    sprite_h = 7  # pixel-person frames are always 7 lines
    stage_h = sprite_h + JUMP_ROWS  # rows reserved for sprite + jump headroom

    show_sprite = height > stage_h + 1  # need at least 1 lyric row + separator
    if not show_sprite:
        stage_h = 0

    lyrics_h = max(1, height - stage_h - (1 if show_sprite else 0))

    if lyrics_text:
        raw = render_lyrics_window(lyrics_text, pos, dur, window=lyrics_h, width=width - 1)
        content = [" " + ln for ln in raw.split("\n")]
    else:
        content = [f" {_DIM}(no lyrics){_RESET}"]

    while len(content) < lyrics_h:
        content.append("")
    content = content[:lyrics_h]

    if show_sprite:
        # ── jump: suppressed while CC quip is showing ──
        if has_quip:
            will_jump = False
            y = 0
        else:
            bucket = int(t / 4.0)
            will_jump = (math.sin(bucket * 1.6180339) + 1.0) / 2.0 > 0.4
            if will_jump:
                t_local = (t % 4.0) / 4.0
                y_lift = max(0.0, math.sin(t_local * math.pi))
                y = int(y_lift * JUMP_ROWS)
            else:
                y = 0

        # ── horizontal walk: two incommensurable sine waves ──
        max_x = max(0, width - _SPRITE_W)
        x_frac = 0.5 + 0.4 * math.sin(t * 0.31) + 0.1 * math.sin(t * 0.73)
        x_frac = max(0.0, min(1.0, x_frac))
        x_offset = int(x_frac * max_x)

        # ── frame: arms-up when airborne, shimmy direction otherwise ──
        if will_jump and y > 0:
            frame_idx = 1
        else:
            frame_idx = 2 if math.sin(t * 0.31) < 0 else 0

        sprite_lines = dj.pixel_person_frame(mood, frame_idx).split("\n")

        # ── speech bubble occupies the jump-headroom rows ──
        if has_quip:
            bubble = _speech_bubble(cc_quip, x_offset, width)
            stage_rows = bubble + sprite_lines
        else:
            top_blank = JUMP_ROWS - y
            bottom_blank = y
            stage_rows = [""] * top_blank + sprite_lines + [""] * bottom_blank

        # Apply horizontal offset to sprite lines (bubble already full-width)
        if has_quip:
            positioned = stage_rows  # bubble rows are already _pad-ded
        else:
            positioned = [_pad(" " * x_offset + line, width) for line in stage_rows]
        rows = content + [_sep(width)] + positioned
    else:
        rows = content

    while len(rows) < height:
        rows.append("")
    return [_pad(r, width) for r in rows[:height]]


def _render_queue_lines(tracks: list[dict], cur_idx: int, width: int, height: int, label: str = "Queue") -> list[str]:
    """Right panel: scrollable queue list, no line wrapping."""
    header = _pad(f" {_DIM}{label}  ({len(tracks)}){_RESET}", width)
    rows: list[str] = ["", header, _sep(width)]

    if not tracks:
        rows.append(_pad(f" {_DIM}cwb list / cwb loved / cwb search{_RESET}", width))
    else:
        visible = max(1, height - len(rows))
        # Scroll so current track is centered
        start = max(0, cur_idx - visible // 2) if cur_idx >= 0 else 0
        end = min(len(tracks), start + visible)
        start = max(0, end - visible)

        # Right-align numbers so "1." and "22." end at the same column.
        # Prefix is always 3 visible chars (" > " or "   ") + num_w + 1 space.
        # Using ">" (ASCII) instead of "▶" avoids East-Asian ambiguous-width rendering.
        num_w = len(str(len(tracks))) + 1  # chars for "N." at max track count
        title_w = max(1, width - num_w - 4)  # 3 (indicator) + 1 (space after num)

        for i in range(start, end):
            num = f"{i + 1}."
            num_str = f"{num:>{num_w}}"
            track = tracks[i]
            title_str = _trunc(track.get("title", "?"), title_w)
            artist = track.get("artist", "")
            spare = title_w - _display_width(title_str) - 2
            art_sfx = f"  {_DIM}{_trunc(artist, spare)}{_RESET}" if artist and spare > 0 else ""
            if i == cur_idx:
                line = _pad(f" {_CUR}> {num_str} {title_str}{_RESET}{art_sfx}", width)
            else:
                line = _pad(f"   {_DIM}{num_str}{_RESET} {title_str}{art_sfx}", width)
            rows.append(line)

    while len(rows) < height:
        rows.append(" " * width)
    return [_pad(r, width) for r in rows[:height]]


def _compose3(
    top_left: list[str],
    bot_left: list[str],
    right: list[str],
    left_w: int,
    total_h: int,
) -> str:
    """Merge three panels into a frame.

    Rows 0..top_h-1  : top_left │ right
    Row  top_h       : ──────────┤ right   (horizontal divider)
    Rows top_h+1..   : bot_left  │ right
    """
    vsep = f"{_DIM}│{_RESET}"
    top_h = len(top_left)
    hjunction = _DIM + "─" * left_w + "┤" + _RESET

    out = []
    for i in range(total_h):
        r = right[i] if i < len(right) else ""
        if i < top_h:
            lc = top_left[i]
            out.append(f"{lc}{vsep}{r}")
        elif i == top_h:
            out.append(f"{hjunction}{r}")
        else:
            bi = i - top_h - 1
            lc = bot_left[bi] if bi < len(bot_left) else " " * left_w
            out.append(f"{lc}{vsep}{r}")
    return "\n".join(out)


def run(width: int = 0) -> int:
    sz = [shutil.get_terminal_size((80, 24))]
    _width = [width if width > 0 else sz[0].columns]
    raw = setup_raw_tty()

    enter_alt_screen()
    # Re-read after alt screen is established; the first read may be stale.
    sz[0] = shutil.get_terminal_size((80, 24))
    _width[0] = sz[0].columns

    def _quit(*_):
        restore_tty(raw)
        exit_alt_screen()
        sys.exit(0)

    _pending_resize = [False]

    def _resize(*_):
        _pending_resize[0] = True

    signal.signal(signal.SIGINT, _quit)
    signal.signal(signal.SIGTERM, _quit)
    signal.signal(signal.SIGWINCH, _resize)

    # Seed snap from state.json so the display is never blank on startup or
    # after a server restart — the server's _np_state resets but state.json persists.
    snap: dict = _snap_from_state_file()
    lyrics_text = ""
    lyrics_key = ""
    last_fetch = 0.0
    last_render = 0.0
    queue: list[dict] = []
    cur_idx = -1
    queue_label = "Queue"
    _active_mode_file = DATA_DIR / "active_mode.json"
    _queue_mtime: float = 0.0
    num_buf = ""
    num_ts = 0.0

    try:
        while True:
            key = read_key(raw)

            # Flush number buffer on timeout even without new key
            if num_buf and time.time() - num_ts >= _NUM_TIMEOUT:
                n = int(num_buf)
                num_buf = ""

                def _play_n(n=n):
                    if not _control_lock.acquire(blocking=False):
                        return
                    try:
                        call_tool("play_number", {"number": n})
                    except MCPClientError:
                        pass
                    finally:
                        _control_lock.release()

                threading.Thread(target=_play_n, daemon=True).start()
                last_fetch = time.time() - FETCH_EVERY + 1.5

            if key in ("q", "Q", "\x03"):
                break
            if key == " ":
                _control_async("toggle")
                last_fetch = time.time() - FETCH_EVERY + 0.8
            elif key in ("n", "N"):
                _control_async("next_track")
                last_fetch = time.time() - FETCH_EVERY + 1.5
            elif key in ("p", "P"):
                _control_async("prev_track")
                last_fetch = time.time() - FETCH_EVERY + 1.5
            elif key in ("l", "L"):
                _control_async("like_current")
            elif key and key.isdigit():
                num_buf += key
                num_ts = time.time()
            elif key in ("\r", "\n") and num_buf:
                n = int(num_buf)
                num_buf = ""

                def _play_n(n=n):
                    if not _control_lock.acquire(blocking=False):
                        return
                    try:
                        call_tool("play_number", {"number": n})
                    except MCPClientError:
                        pass
                    finally:
                        _control_lock.release()

                threading.Thread(target=_play_n, daemon=True).start()
                last_fetch = time.time() - FETCH_EVERY + 1.5
            elif key == "\x1b":  # ESC cancels number input
                num_buf = ""

            now = time.time()

            # Kick off a background fetch when it's time; never block the loop.
            if now - last_fetch >= FETCH_EVERY:
                _fetch_async(lyrics_key)
                last_fetch = now

            # Drain the latest completed fetch result (may be None if none ready).
            new = _fetch_result[0]
            if new is not None:
                _fetch_result[0] = None
                # If the player reports no title (stopped / transitioning), keep the
                # last known song info so the display never goes blank.
                if not new.get("title") and snap.get("title"):
                    new = {
                        **new,
                        "title": snap["title"],
                        "artist": snap.get("artist", ""),
                        "album": snap.get("album", ""),
                        "duration": snap.get("duration", 0.0),
                        "position": snap.get("position", 0.0),
                        "sampled_at": snap.get("sampled_at", 0.0),
                        # playing intentionally NOT preserved — use server's value
                        # so paused/stopped state is reflected correctly
                    }
                if new.get("lyrics_text"):
                    lyrics_text = new["lyrics_text"]
                    lyrics_key = new.get("lyrics_key", "")
                elif new.get("lyrics_key") and new["lyrics_key"] != lyrics_key:
                    lyrics_text = ""
                    if not new.get("lyrics_pending"):
                        lyrics_key = new["lyrics_key"]
                snap = new

            # Reload queue whenever active_mode.json changes on disk — this
            # fires immediately when cwb list / cwb loved / cwb search runs,
            # without waiting for the next MCP fetch cycle.
            try:
                _mt = _active_mode_file.stat().st_mtime
            except OSError:
                _mt = 0.0
            if new is not None or _mt != _queue_mtime:
                _queue_mtime = _mt
                queue, cur_idx, queue_label = _load_queue()
                # Only rescan when something is actively playing — if paused/stopped,
                # trust the queue's stored index so cwb next/prev stays in sync.
                if snap.get("playing") and snap.get("title") and queue:
                    playing_title = snap["title"]
                    need_scan = cur_idx < 0 or cur_idx >= len(queue) or queue[cur_idx].get("title", "") != playing_title
                    if need_scan:
                        for j, t in enumerate(queue):
                            if t.get("title", "") == playing_title:
                                cur_idx = j
                                break

            if snap and now - last_render >= RENDER_EVERY:
                total_w = _width[0]
                h = sz[0].lines
                # usable_h: everything except the very last terminal line.
                # sep_h:     full-width ── separator closing the panels.
                # panels_h:  two rows less — panels end before the separator.
                usable_h = h - 1
                sep_h = usable_h - 1
                panels_h = sep_h - 1
                left_w = max(20, int(total_w * 0.65))
                right_w = max(10, total_w - left_w - 1)  # 1 col for │

                # Player section height = exactly its content rows — no blank
                # padding before the ────────┤ junction.
                _player_rows = 5 + (1 if snap.get("artist") else 0)
                top_h = _player_rows
                bot_h = max(3, panels_h - top_h - 1)

                pos = _interp_pos(snap)
                dur = float(snap.get("duration", 0.0))
                playing = snap.get("playing", False)

                cc = _load_cc_state()
                cc_quip = cc["dj_quip"] if now - cc["dj_quip_at"] < _CC_QUIP_TTL else ""
                cc_mood = cc["dj_mood"]

                player_lines = _render_player_top(snap, left_w, top_h, now)
                lyrics_lines = _render_lyrics_bottom(
                    lyrics_text,
                    pos,
                    dur,
                    left_w,
                    bot_h,
                    playing,
                    now,
                    cc_mood=cc_mood,
                    cc_quip=cc_quip,
                )
                queue_lines = _render_queue_lines(queue, cur_idx, right_w, panels_h, queue_label)
                frame = _compose3(player_lines, lyrics_lines, queue_lines, left_w, panels_h)

                if num_buf:
                    if total_w >= 38:
                        hint_text = f">> {num_buf}_   Enter confirm  Esc cancel"
                    else:
                        hint_text = f">> {num_buf}_  ↵ ok  Esc×"
                    hint_styled = f"{_GREEN}{hint_text}{_RESET}"
                else:
                    if total_w >= 56:
                        hint_text = "space pause  n next  p prev  l like  q quit  0-9 go to #"
                    elif total_w >= 40:
                        hint_text = "spc  n next  p prev  l like  q quit  0-9 #"
                    elif total_w >= 26:
                        hint_text = "spc  n/p  l  q  0-9 #"
                    else:
                        hint_text = "spc n p l q"
                    hint_styled = f"{_DIM}{hint_text}{_RESET}"
                hint_pad = max(0, (total_w - len(hint_text)) // 2)
                hint_line = " " * hint_pad + hint_styled

                lines = frame.split("\n")
                out = []
                for i, line in enumerate(lines[:panels_h]):
                    out.append(f"\x1b[{i + 1};1H{line}\x1b[K")
                out.append(f"\x1b[{sep_h};1H{_DIM}{'─' * total_w}{_RESET}\x1b[K")
                out.append(f"\x1b[{usable_h};1H{_pad(hint_line, total_w)}\x1b[K")
                out.append(f"\x1b[{usable_h + 1};1H\x1b[J")
                sys.stdout.write("".join(out))
                sys.stdout.flush()
                last_render = now

            if _pending_resize[0]:
                _pending_resize[0] = False
                sz[0] = shutil.get_terminal_size((80, 24))
                _width[0] = sz[0].columns
                sys.stdout.write(CLEAR)
                sys.stdout.flush()

            time.sleep(0.02)
    finally:
        restore_tty(raw)
        exit_alt_screen()
    return 0
