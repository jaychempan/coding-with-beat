"""Retro GameBoy / NES-flavored UI frames and banners."""
from __future__ import annotations

from typing import List


GB_GREEN = "\x1b[38;2;155;188;15m"
GB_DARK = "\x1b[38;2;15;56;15m"
GB_BG = "\x1b[48;2;15;56;15m"
RESET = "\x1b[0m"

# Block-style chunky border. Reads as "pixel game window".
CORNER_TL = "▛"
CORNER_TR = "▜"
CORNER_BL = "▙"
CORNER_BR = "▟"
EDGE_H = "▀"
EDGE_H_BOT = "▄"
EDGE_V = "▌"
EDGE_V_R = "▐"


def _strip_ansi(s: str) -> str:
    import re
    return re.sub(r"\x1b\[[0-9;]*m", "", s)


def _display_width(s: str) -> int:
    total = 0
    for ch in s:
        cp = ord(ch)
        if (0x1100 <= cp <= 0x115F or 0x2E80 <= cp <= 0x303E or
                0x3040 <= cp <= 0x33FF or 0x3400 <= cp <= 0x4DBF or
                0x4E00 <= cp <= 0x9FFF or 0xA000 <= cp <= 0xA4CF or
                0xAC00 <= cp <= 0xD7AF or 0xF900 <= cp <= 0xFAFF or
                0xFE10 <= cp <= 0xFE6F or 0xFF01 <= cp <= 0xFF60 or
                0xFFE0 <= cp <= 0xFFE6):
            total += 2
        else:
            total += 1
    return total


def boxed(title: str, body: str, width: int = 40, color: str = GB_GREEN) -> str:
    """Wrap body text in a chunky pixel frame with a title bar."""
    body_lines = body.splitlines() or [""]
    inner_w = max(width - 2, _display_width(_strip_ansi(title)) + 2)
    for line in body_lines:
        inner_w = max(inner_w, _display_width(_strip_ansi(line)))
    inner_w = min(inner_w, 120)

    top = f"{color}{CORNER_TL}{EDGE_H * inner_w}{CORNER_TR}{RESET}"
    bot = f"{color}{CORNER_BL}{EDGE_H_BOT * inner_w}{CORNER_BR}{RESET}"

    title_clean = _strip_ansi(title)
    title_pad = inner_w - _display_width(title_clean)
    left = title_pad // 2
    right = title_pad - left
    title_line = f"{color}{EDGE_V}{' ' * left}\x1b[1m{title_clean}\x1b[0m{color}{' ' * right}{EDGE_V_R}{RESET}"

    sep = f"{color}{EDGE_V}{EDGE_H_BOT * inner_w}{EDGE_V_R}{RESET}"

    rows = [top, title_line, sep]
    for line in body_lines:
        visible = _display_width(_strip_ansi(line))
        pad = max(0, inner_w - visible)
        rows.append(f"{color}{EDGE_V}{RESET}{line}{' ' * pad}{color}{EDGE_V_R}{RESET}")
    rows.append(bot)
    return "\n".join(rows)


_BANNER_LINES = [
    "██╗    ██╗██╗████████╗██╗  ██╗    ██████╗ ███████╗ █████╗ ████████╗",
    "██║    ██║██║╚══██╔══╝██║  ██║    ██╔══██╗██╔════╝██╔══██╗╚══██╔══╝",
    "██║ █╗ ██║██║   ██║   ███████║    ██████╔╝█████╗  ███████║   ██║   ",
    "██║███╗██║██║   ██║   ██╔══██║    ██╔══██╗██╔══╝  ██╔══██║   ██║   ",
    "╚███╔███╔╝██║   ██║   ██║  ██║    ██████╔╝███████╗██║  ██║   ██║   ",
    " ╚══╝╚══╝ ╚═╝   ╚═╝   ╚═╝  ╚═╝    ╚═════╝ ╚══════╝╚═╝  ╚═╝   ╚═╝  ",
]


def retro_banner(subtitle: str = "press any key to play") -> str:
    # "CODING" in spaced small caps above the big "WITH BEAT" wordmark
    coding = "C  O  D  I  N  G"
    out = [f"\x1b[1;38;2;200;200;230m{coding.center(70)}{RESET}"]
    for line in _BANNER_LINES:
        out.append(f"{GB_GREEN}{line}{RESET}")
    out.append(f"\x1b[38;2;155;188;15m{'· · · coding  with  beat · · ·'.center(70)}{RESET}")
    if subtitle not in ("press any key to play",):
        out.append(f"\x1b[38;2;180;180;200m{subtitle.center(70)}{RESET}")
    return "\n".join(out)


# Vinyl record: three concentric rounded rectangles (outer ring / grooves / label).
# All lines are exactly 19 chars wide — centered over the 76-wide wordmark at indent 28.
_VINYL = [
    "╭─────────────────╮",
    "│ ╭─────────────╮ │",
    "│ │  ╭───────╮  │ │",
    "│ │  │   ◉   │  │ │",
    "│ │  ╰───────╯  │ │",
    "│ ╰─────────────╯ │",
    "╰─────────────────╯",
]


def welcome_screen() -> str:
    """Welcome splash displayed on first install."""
    # Coral → golden amber gradient across the 6 wordmark rows
    GRAD = [
        "\x1b[38;2;200;95;65m",
        "\x1b[38;2;202;112;70m",
        "\x1b[38;2;204;130;75m",
        "\x1b[38;2;207;150;65m",
        "\x1b[38;2;210;170;57m",
        "\x1b[38;2;214;190;50m",
    ]
    RING  = "\x1b[38;2;80;48;32m"    # dark outer vinyl ring
    GROVE = "\x1b[38;2;130;78;52m"   # mid groove ring
    LABEL = "\x1b[38;2;200;95;65m"   # coral center label
    HOLE  = "\x1b[38;2;214;190;50m"  # amber hole
    DIM   = "\x1b[38;2;108;65;40m"
    MID   = "\x1b[38;2;172;110;68m"
    CREAM = "\x1b[38;2;248;238;222m"
    R  = "\x1b[0m"

    def colorize_vinyl(line: str, depth: int) -> str:
        color = [RING, GROVE, LABEL][min(depth, 2)]
        out = [color]
        for ch in line:
            if ch == "◉":
                out.append(f"{R}{HOLE}{ch}{R}{color}")
            else:
                out.append(ch)
        out.append(R)
        return "".join(out)

    # Depth 0 = outer ring, 1 = groove ring, 2 = label
    depths = [0, 0, 1, 2, 1, 0, 0]
    vinyl_lines = [colorize_vinyl(ln, depths[i]) for i, ln in enumerate(_VINYL)]

    # Banner wordmark (1 space prefix, ~75 chars wide → 76 total visible)
    coding_hdr = f" \x1b[1;38;2;200;200;230m{'C  O  D  I  N  G'.center(76)}{R}"
    banner = [coding_hdr] + [f" {GRAD[i]}{ln}{R}" for i, ln in enumerate(_BANNER_LINES)]

    rule = f" {DIM}{'─' * 76}{R}"

    # Center the 19-wide vinyl over 76-wide block: indent = (76-19)//2 = 28
    vinyl_block = "\n".join(f"{' ' * 28}{ln}" for ln in vinyl_lines)

    tag    = f" {CREAM}{'(♪‿♪)   a pixel companion for vibecoding   (♪‿♪)'.center(76)}{R}"
    check1 = f" {MID}   ✓  MCP server registered                ✓  /cwb command installed{R}"
    check2 = f" {MID}   ✓  CC hooks active                      ✓  statusline ready{R}"
    hint   = f" {DIM}   open Claude Code and say: \"play some lofi\"  ·  or /cwb play lofi beats{R}"

    return "\n".join([
        rule,
        "",
        vinyl_block,
        "",
        tag,
        "",
        *banner,
        "",
        rule,
        check1,
        check2,
        rule,
        "",
        hint,
        "",
    ])
