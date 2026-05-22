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
            "CWB · watch",
            f"\x1b[38;2;200;80;80m{str(e).splitlines()[0]}\x1b[0m",
            width=width,
        )


def _control(tool: str) -> None:
    try:
        call_tool(tool)
    except MCPClientError:
        pass


def _setup_raw_tty():
    """Switch stdin to raw mode; returns (fd, old_settings) or None if not a tty."""
    try:
        import termios
        import tty

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        tty.setraw(fd)
        return fd, old
    except Exception:
        return None


def _restore_tty(raw_state) -> None:
    if raw_state is None:
        return
    try:
        import termios

        fd, old = raw_state
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    except Exception:
        pass


def _read_key(raw_state) -> str:
    """Non-blocking single-char read. Returns '' if no key is waiting."""
    if raw_state is None:
        return ""
    try:
        import select

        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1)
    except Exception:
        pass
    return ""


def run(width: int = DEFAULT_WIDTH) -> int:
    import shutil

    _width = [width if width > 0 else shutil.get_terminal_size((80, 24)).columns]
    raw_state = _setup_raw_tty()

    sys.stdout.write(_ENTER_ALT + _HIDE_CURSOR + _CLEAR)
    sys.stdout.flush()

    def _restore(*_):
        _restore_tty(raw_state)
        sys.stdout.write(_SHOW_CURSOR + _EXIT_ALT)
        sys.stdout.flush()
        sys.exit(0)

    def _resize(*_):
        _width[0] = shutil.get_terminal_size((80, 24)).columns
        sys.stdout.write(_CLEAR)

    signal.signal(signal.SIGINT, _restore)
    signal.signal(signal.SIGTERM, _restore)
    signal.signal(signal.SIGWINCH, _resize)

    try:
        while True:
            key = _read_key(raw_state)
            if key in ("q", "Q", "\x03"):
                break
            if key == " ":
                _control("toggle")
            elif key in ("n", "N"):
                _control("next_track")
            elif key in ("p", "P"):
                _control("prev_track")
            elif key in ("l", "L"):
                _control("like_current")

            term_h = shutil.get_terminal_size((80, 24)).lines
            lines = _frame(_width[0]).split("\n")
            clipped = "\n".join(lines[: term_h - 1])
            sys.stdout.write(_HOME + clipped + "\x1b[J")
            sys.stdout.flush()
            time.sleep(POLL_EVERY)
    finally:
        _restore_tty(raw_state)
        sys.stdout.write(_SHOW_CURSOR + _EXIT_ALT)
        sys.stdout.flush()
    return 0
