"""Compact real-time watch mode — local render from JSON snapshot."""

from __future__ import annotations

import json
import shutil
import signal
import sys
import time

from ._tui import (
    CLEAR,
    enter_alt_screen,
    exit_alt_screen,
    read_key,
    restore_tty,
    setup_raw_tty,
)
from .mcp_client import MCPClientError, call_tool
from .ui.lyrics import render_lyrics_window
from .ui.progress import render_progress, render_spectrum_color

FETCH_EVERY = 2.0
RENDER_EVERY = 0.05

_ACCENT = (155, 188, 15)
_DIM = "\x1b[38;2;100;110;100m"
_BOLD = "\x1b[1;38;2;220;230;220m"
_GREEN = "\x1b[38;2;155;188;15m"
_RESET = "\x1b[0m"


def _fetch(known_key: str = "") -> dict:
    raw = call_tool("now_playing_snapshot", {"known_lyrics_key": known_key})
    return json.loads(raw)


def _interp_pos(snap: dict) -> float:
    pos = float(snap.get("position", 0.0))
    if snap.get("playing"):
        pos += time.time() - float(snap.get("sampled_at", time.time()))
    dur = float(snap.get("duration", 0.0))
    return max(0.0, min(pos, dur) if dur > 0 else pos)


def _control(tool: str) -> None:
    try:
        call_tool(tool)
    except MCPClientError:
        pass


def _sep(width: int) -> str:
    return _DIM + "─" * max(1, width) + _RESET


def _render(snap: dict, lyrics_text: str, width: int, t: float) -> str:
    title = snap.get("title") or "—"
    artist = snap.get("artist") or ""
    playing = snap.get("playing", False)
    dur = float(snap.get("duration", 0.0))
    pos = _interp_pos(snap)

    icon = f"{_GREEN}▶{_RESET}" if playing else f"{_DIM}❚❚{_RESET}"
    artist_part = f"  {_DIM}·  {artist}{_RESET}" if artist else ""
    title_line = f" {icon}  {_BOLD}{title}{_RESET}{artist_part}"

    bar_w = max(1, width - 16)
    spec_w = max(1, width - 2)

    rows = [
        "",
        title_line,
        _sep(width),
        " " + render_progress(pos, dur, bar_w, _ACCENT),
        " " + render_spectrum_color(pos, spec_w, t=t),
    ]

    if lyrics_text:
        rows.append(_sep(width))
        lrc = render_lyrics_window(lyrics_text, pos, dur, window=3, width=width)
        for line in lrc.split("\n"):
            rows.append(" " + line)

    rows.append(_sep(width))
    rows.append(f" {_DIM}space pause  n next  p prev  l like  q quit{_RESET}")
    rows.append("")
    return "\n".join(rows)


def run(width: int = 0) -> int:
    sz = [shutil.get_terminal_size((80, 24))]
    _width = [width if width > 0 else sz[0].columns]
    raw = setup_raw_tty()

    enter_alt_screen()

    def _quit(*_):
        restore_tty(raw)
        exit_alt_screen()
        sys.exit(0)

    def _resize(*_):
        sz[0] = shutil.get_terminal_size((80, 24))
        _width[0] = sz[0].columns
        sys.stdout.write(CLEAR)
        sys.stdout.flush()

    signal.signal(signal.SIGINT, _quit)
    signal.signal(signal.SIGTERM, _quit)
    signal.signal(signal.SIGWINCH, _resize)

    snap: dict = {}
    lyrics_text = ""
    lyrics_key = ""
    last_fetch = 0.0
    last_render = 0.0

    try:
        while True:
            key = read_key(raw)
            if key in ("q", "Q", "\x03"):
                break
            if key == " ":
                _control("toggle")
                last_fetch = 0.0
            elif key in ("n", "N"):
                _control("next_track")
                last_fetch = 0.0
            elif key in ("p", "P"):
                _control("prev_track")
                last_fetch = 0.0
            elif key in ("l", "L"):
                _control("like_current")

            now = time.time()

            if now - last_fetch >= FETCH_EVERY:
                try:
                    new = _fetch(lyrics_key)
                    if new.get("lyrics_text"):
                        lyrics_text = new["lyrics_text"]
                        lyrics_key = new.get("lyrics_key", "")
                    elif new.get("lyrics_key") and new["lyrics_key"] != lyrics_key:
                        lyrics_text = ""
                        lyrics_key = new["lyrics_key"]
                    snap = new
                    last_fetch = now
                except MCPClientError:
                    pass

            if snap and now - last_render >= RENDER_EVERY:
                frame = _render(snap, lyrics_text, _width[0], now)
                height = sz[0].lines
                lines = frame.split("\n")
                out = []
                for i, line in enumerate(lines[: height - 1]):
                    out.append(f"\x1b[{i + 1};1H{line}\x1b[K")
                last = min(len(lines), height - 1) + 1
                out.append(f"\x1b[{last};1H\x1b[J")
                sys.stdout.write("".join(out))
                sys.stdout.flush()
                last_render = now

            time.sleep(0.02)
    finally:
        restore_tty(raw)
        exit_alt_screen()
    return 0
