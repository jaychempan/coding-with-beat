"""Vibe Engine: rules to map Claude Code activity → mood + playlist intent.

Inputs come from CC hooks (SessionStart, PreToolUse, PostToolUse, Stop) as
JSON on stdin. We translate the event to a (mood, vibe) tuple and update the
shared state. A background "auto-switch" can optionally retrigger playback.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

from . import cwb_agent, dj, state
from .config import FILE_KIND_VIBES, LOG_FILE, ensure_dirs


def _file_kind(path: str) -> Optional[str]:
    if not path:
        return None
    suffix = Path(path).suffix.lstrip(".").lower()
    return FILE_KIND_VIBES.get(suffix)


def _is_test_file(path: str) -> bool:
    if not path:
        return False
    name = Path(path).name.lower()
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or name.endswith("_test.ts")
        or name.endswith(".test.ts")
        or name.endswith(".test.js")
        or name.endswith(".spec.ts")
        or name.endswith(".spec.js")
        or "/test/" in path
        or "/tests/" in path
        or "\\test\\" in path
        or "\\tests\\" in path
    )


def classify(event: dict) -> Tuple[str, str]:
    """Return (mood, vibe). Pure function for testability."""
    hook = (event.get("hook_event_name") or "").lower()
    tool = (event.get("tool_name") or "").lower()
    tool_input = event.get("tool_input") or {}
    tool_response = event.get("tool_response") or {}

    if hook == "sessionstart":
        return ("happy", "focus")
    if hook == "stop":
        return ("sleep", "idle")

    # Test detection — Bash with "test" / "pytest" / "npm test" etc.
    if tool == "bash":
        cmd = (tool_input.get("command") or "").lower()
        if any(k in cmd for k in ["pytest", "npm test", "jest", "go test", "cargo test", " test", "vitest"]):
            ok = bool(tool_response.get("success", True)) and not tool_response.get("interrupted")
            stderr = (tool_response.get("stderr") or "").lower()
            failed = ("fail" in stderr or "error" in stderr or "✗" in stderr) and "0 failures" not in stderr
            if failed or not ok:
                return ("sad", "fail")
            return ("victory", "victory")
        if "git commit" in cmd:
            return ("victory", "victory")
        if "git push" in cmd:
            return ("happy", "victory")

    if tool in ("edit", "write", "multiedit"):
        path = tool_input.get("file_path") or ""
        if _is_test_file(path):
            return ("focus", "debug")
        kind = _file_kind(path)
        return ("focus", kind or "build")

    if tool in ("read", "grep", "glob"):
        return ("thinking", "review")

    return dj.mood_from_event(event)


def handle_cwb_prompt_expansion(event: dict) -> Optional[dict]:
    return cwb_agent.handle_prompt_expansion(event)


def handle_hook(event: dict) -> dict:
    mood, vibe = classify(event)
    st = state.load()
    prev_mood = st.dj_mood
    st.dj_mood = mood
    st.vibe = vibe

    # Fire a DJ quip when something significant happens
    hook = (event.get("hook_event_name") or "").lower()
    if hook in ("pretooluse", "posttooluse"):
        st.last_tool_at = time.time()
    if mood != prev_mood and mood in ("victory", "sad", "panic", "happy", "groove"):
        st.dj_quip = dj.quip(mood)
        st.dj_quip_at = time.time()
    elif hook == "stop":
        st.dj_quip = dj.quip("sleep")
        st.dj_quip_at = time.time()

    state.save(st)
    _log(f"hook {event.get('hook_event_name')} tool={event.get('tool_name')} → mood={mood} vibe={vibe}")
    return {"mood": mood, "vibe": vibe}


def _log(msg: str) -> None:
    ensure_dirs()
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
    except Exception:
        pass


def main() -> int:
    """Hook entry point. Reads JSON from stdin, updates state, exits 0."""
    if os.environ.get("CWB_DISABLE_HOOK") == "1":
        return 0
    raw = ""
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except Exception:
        event = {}
    cwb_response = handle_cwb_prompt_expansion(event)
    if cwb_response is not None:
        print(json.dumps(cwb_response, ensure_ascii=False))
        return 0
    handle_hook(event)
    return 0


if __name__ == "__main__":
    sys.exit(main())
