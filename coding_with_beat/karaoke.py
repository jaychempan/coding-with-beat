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


def _control(tool: str) -> None:
    try:
        call_tool(tool)
    except MCPClientError:
        pass


def _setup_raw_tty():
    try:
        import termios, tty
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
    if raw_state is None:
        return ""
    try:
        import select
        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1)
    except Exception:
        pass
    return ""


def run(width: int = 0) -> int:
    import shutil
    _width = [width if width > 0 else shutil.get_terminal_size((80, 24)).columns]
    raw_state = _setup_raw_tty()

    sys.stdout.write(_ALT + _HIDE + _CLEAR)
    sys.stdout.flush()

    def _restore(*_):
        _restore_tty(raw_state)
        sys.stdout.write(_SHOW + _NORM)
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

            sys.stdout.write(_HOME + _CLEAR + _lyrics_frame(_width[0]))
            sys.stdout.flush()
            time.sleep(POLL_EVERY)
    finally:
        _restore_tty(raw_state)
        sys.stdout.write(_SHOW + _NORM)
        sys.stdout.flush()
    return 0
