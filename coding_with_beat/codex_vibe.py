"""Codex CLI hook adapter for coding-with-beat.

Entry point: python -m coding_with_beat codex_hook

cwb command routing (UserPromptSubmit):
  ACTION commands (play/pause/next/…): hook intercepts → executes cwb CLI →
    brief plain-text stopReason (1 line, fits Codex notification area).
  DISPLAY commands (list/np/status/…): hook does NOT intercept →
    Codex handles via MCP tools → full formatted multi-line output.

Mood / vibe surfacing:
  On significant mood changes (victory / panic / sad) → inject systemMessage so
  the user sees a DJ Buddy reaction even without a statusline.

Codex-specific hooks (not in Claude Code):
  SubagentStart / SubagentStop: react to multi-agent events.
  PermissionRequest: track tool pauses.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from . import cwb_agent, dj, state
from .vibe import handle_hook

_ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")

# Display commands → let Codex handle via MCP (proper multi-line output)
_DISPLAY_COMMANDS = {
    "list", "search", "np", "now_playing", "status",
    "history", "player", "help", "lyrics", "welcome",
}

# Mood changes that deserve a visible notification in Codex
_NOTIFY_MOODS = {"victory", "panic", "sad"}

_MOOD_EMOJI = {"victory": "🎉", "panic": "😱", "sad": "💔", "happy": "😊"}

_CWB_PREFIXES = ("/cwb", "cwb ")


# ── helpers ───────────────────────────────────────────────────────────────────

def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def _prompt_text(event: dict) -> str:
    for key in ("prompt", "message", "user_message", "text"):
        val = event.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def _first_word(text: str) -> str:
    return text.strip().split()[0].lower() if text.strip() else ""


def _music_context() -> str | None:
    """Brief now-playing string for systemMessage injection."""
    try:
        st = state.load()
        if st.track and st.track.title:
            track = st.track.title
            if st.track.artist:
                track += f" — {st.track.artist}"
            return f"🎵 coding-with-beat active. Now playing: {track}."
    except Exception:
        pass
    return None


def _vibe_message(prev_mood: str, new_mood: str, new_vibe: str) -> str | None:
    """Return a systemMessage when mood changes to something worth surfacing."""
    if new_mood not in _NOTIFY_MOODS or new_mood == prev_mood:
        return None
    emoji = _MOOD_EMOJI.get(new_mood, "🎵")
    quip = dj.quip(new_mood)
    vibe_tag = f" [{new_vibe}]" if new_vibe else ""
    return f'{emoji} DJ Buddy: "{quip}"{vibe_tag}'


def _load_project_cfg() -> dict:
    """Read .coding-with-beat.toml from CWD, return empty dict on any error."""
    cfg_file = Path.cwd() / ".coding-with-beat.toml"
    if not cfg_file.exists():
        return {}
    try:
        # tomllib is stdlib in 3.11+; fall back to tomli on 3.10
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]
        return tomllib.loads(cfg_file.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _maybe_auto_play() -> None:
    """Auto-play from project config if auto_play_on_session = true."""
    try:
        cfg = _load_project_cfg()
        if cfg.get("auto_play_on_session") and cfg.get("default_query"):
            plan = cwb_agent.CwbPlan("play", (str(cfg["default_query"]),))
            cwb_agent.execute_plan(plan)
    except Exception:
        pass


# ── UserPromptSubmit → cwb command routing ───────────────────────────────────

def _handle_user_prompt(event: dict) -> dict | None:
    """Route 'cwb …' / '/cwb …' prompts.

    Returns a Codex hook response, or None to let Codex handle naturally.
    """
    prompt = _prompt_text(event)
    if not prompt:
        return None

    lower = prompt.lower()
    intent: str | None = None
    for prefix in _CWB_PREFIXES:
        if lower.startswith(prefix):
            intent = prompt[len(prefix):].strip()
            break
    if intent is None:
        return None

    # Display commands → pass through so Codex gives formatted multi-line output
    if _first_word(intent) in _DISPLAY_COMMANDS:
        return None

    # Action commands → execute via fast-path / cwb CLI, return brief stopReason
    lang = cwb_agent._detect_lang(intent)
    t = cwb_agent._T[lang]
    try:
        plan = cwb_agent._fast_path_plan(intent) or cwb_agent.run_child_claude(intent)
        code, output = cwb_agent.execute_plan(plan)
        clean = _strip_ansi(output).strip()
        if code != 0:
            summary = clean or t["cmd_fail"].format(cmd=plan.command)
        else:
            summary = clean or t["done"]
        first_line = next((line for line in summary.splitlines() if line.strip()), summary)
        stop = f"♩ cwb  {first_line}"
    except cwb_agent.CwbAgentError as e:
        stop = f"♩ cwb  {_strip_ansi(str(e))[:120]}"
    except Exception:
        stop = f"♩ cwb  {t['error']}"

    return {"continue": False, "stopReason": stop}


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    if os.environ.get("CWB_DISABLE_HOOK") == "1":
        return 0

    raw = ""
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except Exception:
        event = {}

    hook = (event.get("hook_event_name") or "").lower()

    # ── cwb command interception ──────────────────────────────────────────────
    if hook == "userpromptsubmit":
        response = _handle_user_prompt(event)
        if response:
            print(json.dumps(response, ensure_ascii=False))
        # None → no output → Codex processes the prompt normally (MCP tools)
        return 0

    # ── session start: auto-play + music context ──────────────────────────────
    if hook == "sessionstart":
        handle_hook(event)
        _maybe_auto_play()
        ctx = _music_context()
        if ctx:
            print(json.dumps({"continue": True, "systemMessage": ctx}))
        return 0

    # ── tool use: vibe tracking + surface significant mood changes ────────────
    if hook in ("pretooluse", "posttooluse"):
        prev_mood = (state.load().dj_mood or "")
        result = handle_hook(event)
        msg = _vibe_message(prev_mood, result.get("mood", ""), result.get("vibe", ""))
        if msg:
            print(json.dumps({"continue": True, "systemMessage": msg}))
        return 0

    # ── session stop ──────────────────────────────────────────────────────────
    if hook == "stop":
        handle_hook(event)
        return 0

    # ── Codex-specific: multi-agent events ───────────────────────────────────
    if hook == "subagentstart":
        handle_hook(event)
        quip = dj.quip("focus")
        print(json.dumps({
            "continue": True,
            "systemMessage": f'🤖 DJ Buddy: "{quip}" (subagent online)',
        }))
        return 0

    if hook == "subagentstop":
        handle_hook(event)
        return 0

    # ── Codex-specific: permission request (track as pause) ──────────────────
    if hook == "permissionrequest":
        try:
            st = state.load()
            st.dj_mood = "neutral"
            state.save(st)
        except Exception:
            pass
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
