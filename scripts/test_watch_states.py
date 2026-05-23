"""Test watch states by cycling through CC moods with speech bubbles.

Usage:
    python scripts/test_watch_states.py
    python scripts/test_watch_states.py --once   # print all states once and exit
"""

from __future__ import annotations

import re
import sys
import time

sys.path.insert(0, __file__.rsplit("/scripts/", 1)[0])

from coding_with_beat.watch import _render_lyrics_bottom

ANSI = re.compile(r"\x1b\[[0-9;]*m")

STATES = [
    # (label, cc_mood, cc_quip, playing)
    ("Claude idle", "neutral", "ready when you are", False),
    ("Claude editing", "focus", "zone engaged.", False),
    ("Claude reading", "thinking", "consulting the rubber duck", False),
    ("Tests PASS", "victory", "tests green, vibes greener", False),
    ("Tests FAIL / error", "panic", "stack trace incoming!!", False),
    ("Music playing", "groove", "", True),
    ("Sad / debug", "sad", "we'll get it next try", False),
    ("Happy", "happy", "look at that clean diff!", False),
]

PANEL_W = 52
PANEL_H = 18


def strip(s: str) -> str:
    return ANSI.sub("", s)


def render_state(label: str, cc_mood: str, cc_quip: str, playing: bool) -> list[str]:
    rows = _render_lyrics_bottom(
        lyrics_text="",
        pos=0.0,
        dur=0.0,
        width=PANEL_W,
        height=PANEL_H,
        playing=playing,
        t=time.time(),
        cc_mood=cc_mood,
        cc_quip=cc_quip,
    )
    return rows


def print_frame(label: str, rows: list[str], idx: int, total: int) -> None:
    DIM = "\x1b[38;2;100;110;100m"
    R = "\x1b[0m"
    GREEN = "\x1b[38;2;155;188;15m"

    border_top = DIM + "┌" + "─" * PANEL_W + "┐" + R
    border_bot = DIM + "└" + "─" * PANEL_W + "┘" + R

    title = f"  {GREEN}{label}{R}  {DIM}({idx}/{total}){R}"
    title_plain = f"  {label}  ({idx}/{total})"
    pad = max(0, PANEL_W - len(title_plain))
    header = DIM + "│" + R + title + " " * pad + DIM + "│" + R

    print(border_top)
    print(header)
    print(DIM + "├" + "─" * PANEL_W + "┤" + R)
    for row in rows:
        visible = strip(row)
        # pad visible to PANEL_W, then add border
        rpad = max(0, PANEL_W - len(visible))
        print(DIM + "│" + R + row + " " * rpad + DIM + "│" + R)
    print(border_bot)


def run_once() -> None:
    for i, (label, mood, quip, playing) in enumerate(STATES, 1):
        rows = render_state(label, mood, quip, playing)
        print_frame(label, rows, i, len(STATES))
        print()


def run_loop() -> None:
    print("\x1b[?25l", end="")  # hide cursor
    try:
        i = 0
        while True:
            label, mood, quip, playing = STATES[i % len(STATES)]
            rows = render_state(label, mood, quip, playing)

            # Rewind cursor to top of frame each time
            frame_h = PANEL_H + 4  # borders + header
            sys.stdout.write(f"\x1b[{frame_h}A\x1b[J")

            print_frame(label, rows, (i % len(STATES)) + 1, len(STATES))
            DIM = "\x1b[38;2;100;110;100m"
            R = "\x1b[0m"
            print(f"\n  {DIM}cycling states... Ctrl+C to stop{R}")

            time.sleep(2.5)
            i += 1
    except KeyboardInterrupt:
        pass
    finally:
        print("\x1b[?25h", end="")  # restore cursor
        print()


if __name__ == "__main__":
    if "--once" in sys.argv:
        run_once()
    else:
        # Print one frame first so the loop has something to rewind over
        label, mood, quip, playing = STATES[0]
        rows = render_state(label, mood, quip, playing)
        print_frame(label, rows, 1, len(STATES))
        DIM = "\x1b[38;2;100;110;100m"
        R = "\x1b[0m"
        print(f"\n  {DIM}cycling states... Ctrl+C to stop{R}")
        run_loop()
