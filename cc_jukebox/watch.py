"""Real-time watch mode rendered through the configured HTTP MCP server."""
from __future__ import annotations

import signal
import sys
import time

from .mcp_client import MCPClientError, call_tool
from .ui import boxed


DEFAULT_WIDTH = 44
POLL_EVERY = 1.0

_HIDE_CURSOR = "\x1b[?25l"
_SHOW_CURSOR = "\x1b[?25h"
_ENTER_ALT = "\x1b[?1049h"
_EXIT_ALT = "\x1b[?1049l"
_HOME = "\x1b[H"
_CLEAR = "\x1b[2J"


def _frame(width: int) -> str:
    try:
        return call_tool("show_player", {"width": width, "with_lyrics": True})
    except MCPClientError as e:
        return boxed(
            "CC-JUKEBOX · watch",
            f"\x1b[38;2;200;80;80m{str(e).splitlines()[0]}\x1b[0m",
            width=width,
        )


def run(width: int = DEFAULT_WIDTH) -> int:
    sys.stdout.write(_ENTER_ALT + _HIDE_CURSOR + _CLEAR)
    sys.stdout.flush()

    def _restore(*_):
        sys.stdout.write(_SHOW_CURSOR + _EXIT_ALT)
        sys.stdout.flush()
        sys.exit(0)

    signal.signal(signal.SIGINT, _restore)
    signal.signal(signal.SIGTERM, _restore)

    try:
        while True:
            sys.stdout.write(_HOME + _CLEAR + _frame(width) + "\n")
            sys.stdout.flush()
            time.sleep(POLL_EVERY)
    finally:
        sys.stdout.write(_SHOW_CURSOR + _EXIT_ALT)
        sys.stdout.flush()
    return 0
