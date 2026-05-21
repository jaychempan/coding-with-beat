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


def boxed(title: str, body: str, width: int = 40, color: str = GB_GREEN) -> str:
    """Wrap body text in a chunky pixel frame with a title bar."""
    body_lines = body.splitlines() or [""]
    inner_w = max(width - 2, len(_strip_ansi(title)) + 2)
    for line in body_lines:
        inner_w = max(inner_w, len(_strip_ansi(line)))
    inner_w = min(inner_w, 120)

    top = f"{color}{CORNER_TL}{EDGE_H * inner_w}{CORNER_TR}{RESET}"
    bot = f"{color}{CORNER_BL}{EDGE_H_BOT * inner_w}{CORNER_BR}{RESET}"

    title_clean = _strip_ansi(title)
    title_pad = inner_w - len(title_clean)
    left = title_pad // 2
    right = title_pad - left
    title_line = f"{color}{EDGE_V}{' ' * left}\x1b[1m{title_clean}\x1b[0m{color}{' ' * right}{EDGE_V_R}{RESET}"

    sep = f"{color}{EDGE_V}{EDGE_H_BOT * inner_w}{EDGE_V_R}{RESET}"

    rows = [top, title_line, sep]
    for line in body_lines:
        visible = len(_strip_ansi(line))
        pad = max(0, inner_w - visible)
        rows.append(f"{color}{EDGE_V}{RESET}{line}{' ' * pad}{color}{EDGE_V_R}{RESET}")
    rows.append(bot)
    return "\n".join(rows)


_BANNER_LINES = [
    " ██████╗ ██████╗     ██╗██╗   ██╗██╗  ██╗███████╗██████╗  ██████╗ ██╗  ██╗",
    "██╔════╝██╔════╝     ██║██║   ██║██║ ██╔╝██╔════╝██╔══██╗██╔═══██╗╚██╗██╔╝",
    "██║     ██║          ██║██║   ██║█████╔╝ █████╗  ██████╔╝██║   ██║ ╚███╔╝ ",
    "██║     ██║     ██   ██║██║   ██║██╔═██╗ ██╔══╝  ██╔══██╗██║   ██║ ██╔██╗ ",
    "╚██████╗╚██████╗╚█████╔╝╚██████╔╝██║  ██╗███████╗██████╔╝╚██████╔╝██╔╝ ██╗",
    " ╚═════╝ ╚═════╝ ╚════╝  ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═════╝  ╚═════╝ ╚═╝  ╚═╝",
]


def retro_banner(subtitle: str = "press any key to play") -> str:
    out = []
    for line in _BANNER_LINES:
        out.append(f"{GB_GREEN}{line}{RESET}")
    out.append(f"\x1b[38;2;200;200;230m{subtitle.center(70)}{RESET}")
    return "\n".join(out)


def welcome_screen() -> str:
    """Full welcome splash shown on first install / cc-jukebox welcome."""
    C   = "\x1b[38;2;204;120;92m"   # Claude coral
    A   = "\x1b[38;2;220;175;80m"   # amber
    W   = "\x1b[38;2;250;235;215m"  # warm cream
    DIM = "\x1b[38;2;140;85;55m"
    B   = "\x1b[1m"
    R   = "\x1b[0m"

    def body_row(content: str) -> str:
        raw = _strip_ansi(content)
        pad = max(0, 27 - len(raw))
        lpad = pad // 2
        rpad = pad - lpad
        return f"        {C}║{R}{' ' * lpad}{content}{' ' * rpad}{C}║{R}"

    # Head inner width = 15. Center col = 22.
    # Body inner width = 27. ╩ connector at col 22.
    return "\n".join([
        "",
        f"  {A}♩  ♪  ♫  ♬  ♩  ♪  ♫  ♬  ♩  ♪  ♫  ♬{R}",
        "",
        f"              {C}╔{'═' * 15}╗{R}",
        f"        {C}◄═════╣               ╠═════►{R}",
        f"              {C}║   {A}◉{C}       {A}◉{C}   ║{R}",
        f"              {C}║               ║{R}",
        f"              {C}║   {A}╰───────╯{C}   ║{R}",
        f"              {C}╚{'═' * 15}╝{R}",
        f"                      {C}║{R}",
        f"        {C}╔{'═' * 13}╩{'═' * 13}╗{R}",
        body_row(f"{B}{W}♫   CC-JUKEBOX   ♫{R}"),
        body_row(f"{W}vibecode with soul{R}"),
        f"        {C}╚{'═' * 27}╝{R}",
        "",
        f"  {DIM}✓ installed — try: cc-jukebox player   or   /juke play 周杰伦{R}",
        "",
    ])
