"""Shared TUI primitives for watch and karaoke modes."""

from __future__ import annotations

import sys

HIDE_CURSOR = "\x1b[?25l"
SHOW_CURSOR = "\x1b[?25h"
ENTER_ALT = "\x1b[?1049h"
EXIT_ALT = "\x1b[?1049l"
HOME = "\x1b[H"
CLEAR = "\x1b[2J"


def setup_raw_tty():
    try:
        import termios
        import tty

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        tty.setraw(fd)
        return fd, old
    except Exception:
        return None


def restore_tty(raw_state) -> None:
    if raw_state is None:
        return
    try:
        import termios

        fd, old = raw_state
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    except Exception:
        pass


def read_key(raw_state) -> str:
    """Non-blocking single-char read."""
    if raw_state is None:
        return ""
    try:
        import select

        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1)
    except Exception:
        pass
    return ""


def enter_alt_screen() -> None:
    sys.stdout.write(ENTER_ALT + HIDE_CURSOR + CLEAR)
    sys.stdout.flush()


def exit_alt_screen() -> None:
    sys.stdout.write(SHOW_CURSOR + EXIT_ALT)
    sys.stdout.flush()
