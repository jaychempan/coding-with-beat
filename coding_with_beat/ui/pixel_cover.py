"""Render album art as pixel ASCII using half-block characters.

A half-block char (▀ U+2580) shows two vertical pixels at once: foreground
color paints the top half, background color paints the bottom half. This
doubles vertical resolution while staying terminal-character aligned.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image

from ..config import GAMEBOY_PALETTE


def _ansi_truecolor(rgb_top: Tuple[int, int, int], rgb_bot: Tuple[int, int, int]) -> str:
    r1, g1, b1 = rgb_top
    r2, g2, b2 = rgb_bot
    return f"\x1b[38;2;{r1};{g1};{b1};48;2;{r2};{g2};{b2}m▀"


def _reset() -> str:
    return "\x1b[0m"


def render_cover(path: Optional[str], width: int = 32, height: int = 16) -> str:
    """Render true-color pixel cover. height is in *character rows*; pixel
    height will be 2*height. Returns a multi-line string with ANSI codes."""
    if not path or not Path(path).exists():
        return _placeholder(width, height)
    try:
        img = Image.open(path).convert("RGB")
    except Exception:
        return _placeholder(width, height)
    img = img.resize((width, height * 2), Image.NEAREST)
    px = img.load()
    rows = []
    for y in range(height):
        row = []
        for x in range(width):
            top = px[x, 2 * y]
            bot = px[x, 2 * y + 1]
            row.append(_ansi_truecolor(top, bot))
        rows.append("".join(row) + _reset())
    return "\n".join(rows)


def render_cover_gameboy(path: Optional[str], width: int = 32, height: int = 16) -> str:
    """4-color GameBoy palette version. Way more pixel-y, less photorealistic."""
    if not path or not Path(path).exists():
        return _placeholder(width, height, gameboy=True)
    try:
        img = Image.open(path).convert("RGB").resize((width, height * 2), Image.NEAREST)
    except Exception:
        return _placeholder(width, height, gameboy=True)
    palette = GAMEBOY_PALETTE
    pal_img = Image.new("P", (1, 1))
    flat = []
    for c in palette:
        flat.extend(c)
    flat.extend([0] * (256 * 3 - len(flat)))
    pal_img.putpalette(flat)
    quant = img.quantize(palette=pal_img, dither=Image.FLOYDSTEINBERG).convert("RGB")
    qpx = quant.load()
    rows = []
    for y in range(height):
        row = []
        for x in range(width):
            top = qpx[x, 2 * y]
            bot = qpx[x, 2 * y + 1]
            row.append(_ansi_truecolor(top, bot))
        rows.append("".join(row) + _reset())
    return "\n".join(rows)


def _placeholder(width: int, height: int, gameboy: bool = False) -> str:
    """No-cover fallback: a striped 'cassette tape' pattern."""
    palette = GAMEBOY_PALETTE if gameboy else [
        (40, 40, 60), (90, 90, 130), (140, 140, 180), (200, 200, 230)
    ]
    rows = []
    for y in range(height):
        row = []
        for x in range(width):
            t = palette[(x + y) % len(palette)]
            b = palette[(x + y + 1) % len(palette)]
            row.append(_ansi_truecolor(t, b))
        rows.append("".join(row) + _reset())
    return "\n".join(rows)
