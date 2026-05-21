"""DJ Buddy — a tiny pixel companion that reacts to your coding state.

Moods map to:
- a compact 3-5 char face for the statusline
- a chunkier ASCII sprite for the player frame
- a pool of short quips DJ Buddy may drop into the chat via the `dj_say` tool
"""
from __future__ import annotations

import random
from typing import List, Tuple


COMPACT_FACES = {
    "neutral":  "(•_•)",
    "focus":    "(◉_◉)",
    "happy":    "(•‿•)",
    "victory":  "\\(^o^)/",
    "sad":      "(╥_╥)",
    "panic":    "(°O°)",
    "thinking": "(•ᴗ•)",
    "groove":   "(♪‿♪)",
    "sleep":    "(-_-)zZ",
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
    "neutral":  ["beat dropping in 3...", "ready when you are", "let's cook"],
    "focus":    ["headphones on. let's go.", "zone engaged.", "shhh, deep focus"],
    "happy":    ["look at that clean diff!", "we love a green check", "nice."],
    "victory":  ["LET'S GOOO 🎉".replace("🎉", "*"), "ship it!", "tests green, vibes greener"],
    "sad":      ["welp.", "we'll get it next try", "deep breath — pair with me"],
    "panic":    ["stack trace incoming!!", "abort? retry? cry?", "oh no oh no oh no"],
    "thinking": ["hmmm", "consulting the rubber duck", "let me think..."],
    "groove":   ["♪ this slaps ♪", "tempo check: locked in", "we are vibing"],
    "sleep":    ["...idle...", "wake me when you commit", "battery: low"],
}


def face(mood: str) -> str:
    return COMPACT_FACES.get(mood, COMPACT_FACES["neutral"])


def sprite(mood: str) -> str:
    lines = SPRITES.get(mood, SPRITES["neutral"])
    return "\n".join(lines)


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
