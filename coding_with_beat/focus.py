"""Focus Loop — a lightweight pomodoro that lives in the shared state file.

Doesn't run a daemon; instead, every read of `focus_status()` computes the
current phase from `focus_started_at`. The MCP `focus_start` tool flips it on,
`focus_stop` flips it off. Statusline shows the remaining time.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from . import state


WORK_SECONDS = 25 * 60
BREAK_SECONDS = 5 * 60


@dataclass
class FocusStatus:
    active: bool
    phase: str
    remaining: int
    elapsed: int
    cycle: int


def status() -> FocusStatus:
    st = state.load()
    if not st.focus_active or not st.focus_started_at:
        return FocusStatus(active=False, phase="off", remaining=0, elapsed=0, cycle=0)
    elapsed = int(time.time() - st.focus_started_at)
    cycle_len = WORK_SECONDS + BREAK_SECONDS
    cycle = elapsed // cycle_len
    in_cycle = elapsed % cycle_len
    if in_cycle < WORK_SECONDS:
        phase = "work"
        remaining = WORK_SECONDS - in_cycle
    else:
        phase = "break"
        remaining = cycle_len - in_cycle
    return FocusStatus(
        active=True, phase=phase,
        remaining=remaining, elapsed=elapsed, cycle=cycle + 1,
    )


def start() -> FocusStatus:
    st = state.load()
    st.focus_active = True
    st.focus_started_at = time.time()
    st.focus_phase = "work"
    state.save(st)
    return status()


def stop() -> FocusStatus:
    st = state.load()
    st.focus_active = False
    st.focus_started_at = 0
    state.save(st)
    return status()
