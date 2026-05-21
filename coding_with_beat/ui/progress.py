"""Retro progress bar + deterministic pseudo-spectrum.

The "spectrum" isn't real FFT — we don't have access to the audio stream from
Apple Music. Instead we use a smooth hash of (position, bar_index) so the bars
animate as the song progresses, looking reactive without being fake-random.
"""
from __future__ import annotations

import math
from typing import Tuple


SPECTRUM_GLYPHS = " ▁▂▃▄▅▆▇█"
BAR_FILLED = "█"
BAR_EMPTY = "░"


def _mmss(seconds: float) -> str:
    s = max(0, int(seconds))
    return f"{s // 60:02d}:{s % 60:02d}"


def render_progress(position: float, duration: float, width: int = 28,
                    accent: tuple = (155, 188, 15)) -> str:
    duration = max(0.0, duration)
    position = max(0.0, min(position, duration if duration else position))
    ratio = (position / duration) if duration > 0 else 0.0
    filled = int(round(ratio * width))
    bar = BAR_FILLED * filled + BAR_EMPTY * (width - filled)
    r, g, b = accent
    return f"\x1b[38;2;{r};{g};{b}m{bar}\x1b[0m  \x1b[38;2;200;200;200m{_mmss(position)} / {_mmss(duration)}\x1b[0m"


def render_spectrum(position: float, width: int = 28, energy: float = 0.85) -> str:
    """Deterministic pseudo-spectrum driven by position. Looks alive."""
    bars = []
    for i in range(width):
        phase = position * 2.3 + i * 0.51
        v = (
            0.55 + 0.45 * math.sin(phase)
            + 0.30 * math.sin(phase * 1.7 + i * 0.13)
            + 0.20 * math.sin(phase * 0.4 + i * 0.31)
        ) / 1.6
        v = max(0.0, min(1.0, v * energy))
        idx = int(round(v * (len(SPECTRUM_GLYPHS) - 1)))
        bars.append(SPECTRUM_GLYPHS[idx])
    return "\x1b[38;2;48;98;48m" + "".join(bars) + "\x1b[0m"


def render_spectrum_color(position: float, width: int = 28, energy: float = 0.85,
                          t: float = 0.0) -> str:
    """Spectrum with a green-to-yellow-to-red gradient.
    `t` is wall-clock seconds; when nonzero, the spectrum keeps animating even
    if `position` is stationary (e.g., between AppleScript polls)."""
    bars = []
    drive = position * 2.3 + t * 3.7
    for i in range(width):
        phase = drive + i * 0.51
        v = (
            0.55 + 0.45 * math.sin(phase)
            + 0.30 * math.sin(phase * 1.7 + i * 0.13)
            + 0.20 * math.sin(phase * 0.4 + i * 0.31)
        ) / 1.6
        v = max(0.0, min(1.0, v * energy))
        idx = int(round(v * (len(SPECTRUM_GLYPHS) - 1)))
        if v < 0.5:
            r, g, b = int(48 + v * 215), 188, 15
        elif v < 0.8:
            r, g, b = 220, int(188 - (v - 0.5) * 200), 15
        else:
            r, g, b = 220, 60, 15
        bars.append(f"\x1b[38;2;{r};{g};{b}m{SPECTRUM_GLYPHS[idx]}")
    return "".join(bars) + "\x1b[0m"


# LED-style 7-segment-ish glyphs (composed of half-blocks) for time HUD.
_LED_DIGITS = {
    "0": ("█▀▀█", "█  █", "█▄▄█"),
    "1": ("  █ ", "  █ ", "  █ "),
    "2": ("▀▀▀█", "█▀▀ ", "█▄▄▄"),
    "3": ("▀▀▀█", " ▀▀█", "▄▄▄█"),
    "4": ("█  █", "█▄▄█", "   █"),
    "5": ("█▀▀▀", "▀▀▀█", "▄▄▄█"),
    "6": ("█▀▀▀", "█▀▀█", "█▄▄█"),
    "7": ("▀▀▀█", "   █", "   █"),
    "8": ("█▀▀█", "█▀▀█", "█▄▄█"),
    "9": ("█▀▀█", "█▄▄█", "▄▄▄█"),
    ":": ("    ", " ▀  ", " ▄  "),
}


def render_led_time(seconds: float, color: str = "155;188;15",
                    dim: str = "30;50;30") -> str:
    """Render mm:ss as a 3-row chunky 7-segment-style display."""
    s = max(0, int(seconds))
    text = f"{s // 60:02d}:{s % 60:02d}"
    rows = ["", "", ""]
    for ch in text:
        glyph = _LED_DIGITS.get(ch, ("    ", "    ", "    "))
        for r in range(3):
            rows[r] += glyph[r] + " "
    out = []
    for row in rows:
        out.append(f"\x1b[38;2;{color}m{row}\x1b[0m")
    return "\n".join(out)


def render_hud_chip(track_key: str, vibe: str = "build", playing: bool = True) -> str:
    """Fake-audiophile readout: deterministic per-track BPM / sample-rate /
    bit-depth + a live REC/TX indicator. Stable across renders, looks legit."""
    import hashlib
    h = int(hashlib.md5(track_key.encode()).hexdigest()[:8], 16)
    bpm = 72 + (h % 80)               # 72-152 BPM, song-feel range
    sr = (44100, 48000, 96000)[h % 3]
    bit = (16, 24, 24)[h % 3]
    codec = ("AAC", "ALAC", "FLAC")[h % 3]
    sr_label = f"{sr//1000}.{(sr%1000)//100}k" if sr % 1000 else f"{sr//1000}k"
    dot_color = "0;255;100" if playing else "120;120;120"
    return (
        f"\x1b[38;2;{dot_color}m●\x1b[0m "
        f"\x1b[38;2;130;200;230m{codec}\x1b[0m "
        f"\x1b[38;2;90;150;180m│\x1b[0m "
        f"\x1b[38;2;180;200;220m{sr_label}/{bit}b\x1b[0m "
        f"\x1b[38;2;90;150;180m│\x1b[0m "
        f"\x1b[38;2;255;200;100m{bpm}BPM\x1b[0m "
        f"\x1b[38;2;90;150;180m│\x1b[0m "
        f"\x1b[38;2;180;220;120m[{vibe}]\x1b[0m"
    )
