"""DJ Buddy — a tiny pixel companion that reacts to your coding state.

Moods map to:
- a compact 3-5 char face for the statusline
- a chunkier ASCII sprite for the player frame
- a pool of short quips DJ Buddy may drop into the chat via the `dj_say` tool
"""

from __future__ import annotations

import random
import time
from typing import Tuple

COMPACT_FACES = {
    "neutral": "(•_•)",
    "focus": "(◉_◉)",
    "happy": "(•‿•)",
    "victory": "\\(^o^)/",
    "sad": "(╥_╥)",
    "panic": "(°O°)",
    "thinking": "(•ᴗ•)",
    "groove": "(♪‿♪)",
    "sleep": "(-_-)zZ",
}

SPRITES = {
    "neutral": [
        "  ╭───╮  ",
        " ◖|•_•|◗ ",
        "  ╰───╯  ",
        "   |||   ",
    ],
    "focus": [
        "  ╭───╮  ",
        " ◖|◉_◉|◗ ",
        "  ╰───╯  ",
        "  ╱│ │╲  ",
    ],
    "happy": [
        "  ╭───╮  ",
        " ◖|•‿•|◗ ",
        "  ╰─v─╯  ",
        "  ╱│ │╲  ",
    ],
    "victory": [
        " \\ ╭─╮ / ",
        "  |^o^|  ",
        "  ╰─v─╯  ",
        "   ╱ ╲   ",
    ],
    "sad": [
        "  ╭───╮  ",
        " ◖|╥_╥|◗ ",
        "  ╰───╯  ",
        "   ...   ",
    ],
    "panic": [
        " ! ╭─╮ ! ",
        "  |O_O|  ",
        "  ╰─o─╯  ",
        "  ╱│|│╲  ",
    ],
    "groove": [
        "  ╭───╮ ♪",
        " ◖|♪‿♪|◗ ",
        "  ╰─v─╯ ♫",
        " ╱╱│ │╲╲ ",
    ],
    "sleep": [
        "  ╭───╮ z",
        " ◖|-_- |◗ ",
        "  ╰───╯  ",
        "   ...   ",
    ],
}


QUIPS = {
    "neutral": ["beat dropping in 3...", "ready when you are", "let's cook"],
    "focus": ["headphones on. let's go.", "zone engaged.", "shhh, deep focus"],
    "happy": ["look at that clean diff!", "we love a green check", "nice."],
    "victory": ["LET'S GOOO 🎉".replace("🎉", "*"), "ship it!", "tests green, vibes greener"],
    "sad": ["welp.", "we'll get it next try", "deep breath — pair with me"],
    "panic": ["stack trace incoming!!", "abort? retry? cry?", "oh no oh no oh no"],
    "thinking": ["hmmm", "consulting the rubber duck", "let me think..."],
    "groove": ["♪ this slaps ♪", "tempo check: locked in", "we are vibing"],
    "sleep": ["...idle...", "wake me when you commit", "battery: low"],
}


# ── Pixel-person sprites (headphones + block body, 10 cols × 7 lines) ──────────
# Each mood has 1–3 animation frames. frame_idx selects the pose.
# The headphone bracket style (═[…]═ / ♪[…]♫ / ╱[…]╲) carries the motion.
PIXEL_FRAMES: dict[str, list[list[str]]] = {
    "groove": [
        [  # 0 — arms wide, grooving
            "  ╔════╗  ",
            "═[│ ♪♪ │]═",
            "  │ ‿‿ │  ",
            "  ╚════╝  ",
            "  ▐████▌  ",
            " ╱▐█  █▌╲ ",
            "  ▐█  █▌  ",
        ],
        [  # 1 — arms up, beat drop, notes flying
            " ♪╔════╗♫ ",
            "╱[│ ♪♪ │]╲",
            "  │ ‿‿ │  ",
            "  ╚════╝  ",
            "  ▐████▌  ",
            "  ▐█  █▌  ",
            " ╱▐█  █▌╲ ",
        ],
        [  # 2 — shimmy, leaning
            "  ╔════╗  ",
            "═[│ ♪~♪│]═",
            "  │  ‿  │ ",
            "  ╚════╝  ",
            " ╲▐████▌╱ ",
            "  ▐█  █▌  ",
            "  ▐█  █▌  ",
        ],
    ],
    "happy": [
        [
            "  ╔════╗  ",
            "═[│ ◉◉ │]═",
            "  │ ‿‿ │  ",
            "  ╚════╝  ",
            "  ▐████▌  ",
            " ╱▐█  █▌╲ ",
            "  ▐█  █▌  ",
        ],
        [
            " /╔════╗\\ ",
            "═[│ ◉‿◉│]═",
            "  │     │  ",
            "  ╚════╝  ",
            "  ▐████▌  ",
            "  ▐█  █▌  ",
            "   ╲  ╱   ",
        ],
    ],
    "victory": [
        [
            " \\╔════╗/ ",
            "╱[│ ^o^ │]╲",
            "  │  ‿  │  ",
            "  ╚════╝   ",
            "  ▐████▌  ",
            " ╱▐█  █▌╲ ",
            "   ╱    ╲  ",
        ],
        [
            "/ ╔════╗ \\",
            "═[│ ^o^ │]═",
            "  │  ‿  │  ",
            "  ╚════╝   ",
            " ╱▐████▌╲ ",
            "  ▐█  █▌  ",
            "  ╱    ╲   ",
        ],
    ],
    "sad": [
        [
            "  ╔════╗  ",
            "═[│ TT │]═",
            "  │ ___ │  ",
            "  ╚════╝  ",
            "  ▐████▌  ",
            "  ▐█  █▌  ",
            "  ▐█  █▌  ",
        ],
    ],
    "panic": [
        [
            " !╔════╗! ",
            "═[│ ◎◎ │]═",
            "  │  o  │  ",
            "  ╚════╝  ",
            "  ▐████▌  ",
            " ╱▐█  █▌╲ ",
            "  ╱│  │╲  ",
        ],
        [
            "!!╔════╗!!",
            "═[│ ◎◎◎│]═",
            "  │  o  │  ",
            "  ╚════╝  ",
            " ╱▐████▌╲ ",
            "  ▐█  █▌  ",
            "  ╱│  │╲  ",
        ],
    ],
    "neutral": [
        [
            "  ╔════╗  ",
            "═[│ ◉◉ │]═",
            "  │ ── │  ",
            "  ╚════╝  ",
            "  ▐████▌  ",
            "  ▐█  █▌  ",
            "  ▐█  █▌  ",
        ],
    ],
}

# Multi-frame dance animations (legacy small sprites, 10 cols × 4 lines).
DANCE_FRAMES: dict[str, list[list[str]]] = {
    "groove": [
        [  # frame 0 — arms wide, notes flying right
            "  ╭───╮ ♪",
            " ◖|♪‿♪|◗ ",
            "  ╰─v─╯ ♫",
            " ╱╱│ │╲╲ ",
        ],
        [  # frame 1 — arms up, beat drop
            "♪ ╭───╮ ♫",
            "◖\\|♪‿♪|/◗",
            "  ╰─v─╯  ",
            "  ╱╱│╲╲  ",
        ],
        [  # frame 2 — shimmy, note left
            "♫ ╭───╮  ",
            " ◖|♪~♪|◗ ",
            "  ╰─v─╯ ♪",
            " ╲╲│ │╱╱ ",
        ],
    ],
    "happy": [
        [  # frame 0 — normal
            "  ╭───╮  ",
            " ◖|•‿•|◗ ",
            "  ╰─v─╯  ",
            "  ╱│ │╲  ",
        ],
        [  # frame 1 — bounce up
            " /╭───╮\\ ",
            " ◖|•‿•|◗ ",
            "  ╰─v─╯  ",
            "   ╲│╱   ",
        ],
    ],
    "victory": [
        [  # frame 0 — classic
            " \\ ╭─╮ / ",
            "  |^o^|  ",
            "  ╰─v─╯  ",
            "   ╱ ╲   ",
        ],
        [  # frame 1 — arms higher
            "/ ╭───╮ \\",
            " ◖|^o^|◗ ",
            "  ╰─v─╯  ",
            "    ╲╱   ",
        ],
    ],
}


_C = {
    "amber": "\x1b[38;2;214;190;50m",
    "coral": "\x1b[38;2;200;95;65m",
    "green": "\x1b[38;2;155;188;15m",
    "ltgrn": "\x1b[38;2;120;200;80m",
    "yellow": "\x1b[38;2;255;230;80m",
    "cream": "\x1b[38;2;230;220;200m",
    "dim": "\x1b[38;2;90;90;110m",
    "R": "\x1b[0m",
}


def _colorize_pixel(line: str) -> str:
    """Apply per-character ANSI color to a pixel-person sprite line."""
    out = []
    R = _C["R"]
    for ch in line:
        if ch in "╔╗╚╝═║":
            out.append(_C["amber"] + ch + R)
        elif ch in "[]":
            out.append(_C["coral"] + ch + R)
        elif ch in "│":
            out.append(_C["dim"] + ch + R)
        elif ch in "█":
            out.append(_C["green"] + ch + R)
        elif ch in "▐▌":
            out.append(_C["ltgrn"] + ch + R)
        elif ch in "♪♫":
            out.append(_C["yellow"] + ch + R)
        elif ch in "◉◎•‿~^oOTo_":
            out.append(_C["cream"] + ch + R)
        elif ch in "╱╲/\\":
            out.append(_C["dim"] + ch + R)
        elif ch == "!":
            out.append(_C["coral"] + ch + R)
        else:
            out.append(ch)
    return "".join(out)


def face(mood: str) -> str:
    return COMPACT_FACES.get(mood, COMPACT_FACES["neutral"])


def sprite(mood: str) -> str:
    lines = SPRITES.get(mood, SPRITES["neutral"])
    return "\n".join(lines)


def sprite_frame(mood: str, frame_idx: int = 0) -> str:
    """Return one animation frame of the legacy small sprite for `mood`."""
    frames = DANCE_FRAMES.get(mood)
    if frames:
        lines = frames[frame_idx % len(frames)]
    else:
        lines = SPRITES.get(mood, SPRITES["neutral"])
    return "\n".join(lines)


def pixel_person_frame(mood: str, frame_idx: int = 0, colored: bool = True) -> str:
    """Return one animation frame of the tall pixel-person sprite for `mood`."""
    frames = PIXEL_FRAMES.get(mood, PIXEL_FRAMES["neutral"])
    lines = frames[frame_idx % len(frames)]
    if colored:
        lines = [_colorize_pixel(line) for line in lines]
    return "\n".join(lines)


def dancing_sprite(mood: str) -> str:
    """Pick a dance frame based on wall-clock time (≈2 Hz flip), colored pixel person."""
    n_frames = len(PIXEL_FRAMES.get(mood, PIXEL_FRAMES["neutral"]))
    frame_idx = int(time.time() * 2) % max(1, n_frames)
    return pixel_person_frame(mood, frame_idx)


def quip(mood: str) -> str:
    options = QUIPS.get(mood, QUIPS["neutral"])
    return random.choice(options)


def mood_from_event(event: dict) -> Tuple[str, str]:
    """Map a hook event payload to (mood, vibe). Heuristic, intentionally loose."""
    tool = (event.get("tool_name") or "").lower()
    success = event.get("success", True)
    hook = (event.get("hook_event_name") or "").lower()

    if hook == "sessionstart":
        return "happy", "focus"
    if not success:
        return "panic", "debug"
    if tool in ("bash",) and "test" in (event.get("command", "").lower()):
        return ("victory" if success else "sad", "victory" if success else "fail")
    if tool in ("edit", "write", "multiedit"):
        return "focus", "build"
    if tool in ("read", "grep", "glob"):
        return "thinking", "review"
    if tool in ("webfetch", "websearch"):
        return "thinking", "review"
    return "neutral", "build"
