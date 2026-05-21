"""Full-screen karaoke lyrics mode rendered through HTTP MCP."""
from __future__ import annotations

import signal
import sys
import time

from .mcp_client import MCPClientError, call_tool
from .ui.frame import _strip_ansi


POLL_EVERY = 1.0

_HIDE = "\x1b[?25l"
_SHOW = "\x1b[?25h"
_ALT = "\x1b[?1049h"
_NORM = "\x1b[?1049l"
_HOME = "\x1b[H"
_CLEAR = "\x1b[2J"


def _center_block(text: str, width: int) -> str:
    rows = []
    for line in text.splitlines() or [""]:
        visible = len(_strip_ansi(line))
        rows.append(" " * max(0, (width - visible) // 2) + line)
    return "\n".join(rows)


def _lyrics_frame(width: int) -> str:
    try:
        text = call_tool("show_lyrics", {"window": 7})
    except MCPClientError as e:
        text = f"\x1b[38;2;200;80;80m{str(e).splitlines()[0]}\x1b[0m"
    return _center_block(text, width)


def run(width: int = 0) -> int:
    import shutil

    if width <= 0:
        width = shutil.get_terminal_size((80, 24)).columns

    sys.stdout.write(_ALT + _HIDE)
    sys.stdout.flush()

    def _restore(*_):
        sys.stdout.write(_SHOW + _NORM)
        sys.stdout.flush()
        sys.exit(0)

    signal.signal(signal.SIGINT, _restore)
    signal.signal(signal.SIGTERM, _restore)

    try:
        while True:
            sys.stdout.write(_HOME + _CLEAR + _lyrics_frame(width))
            sys.stdout.flush()
            time.sleep(POLL_EVERY)
    finally:
        sys.stdout.write(_SHOW + _NORM)
        sys.stdout.flush()
    return 0
