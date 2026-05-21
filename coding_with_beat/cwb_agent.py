"""Private headless Claude controller for the /cwb slash command.

The current Claude Code conversation should not spend context on music control.
This module lets the UserPromptExpansion hook spin up a one-shot Claude process
to interpret the user's /cwb intent, then executes a validated coding-with-beat CLI
command locally.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Optional


_ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_DEFAULT_CLAUDE_TIMEOUT = 90
_DEFAULT_CLI_TIMEOUT = 45
HOOK_TIMEOUT = 180

_COMMAND_ALIASES = {
    "favorite": "like",
    "now_playing": "np",
    "previous": "prev",
    "back": "prev",
}
_ALLOWED_COMMANDS = {
    "status",
    "np",
    "play",
    "pause",
    "next",
    "prev",
    "source",
    "like",
    "mode",
    "lyrics",
    "player",
    "volume",
    "seek",
    "bar",
}
_SOURCES = {
    "apple": "apple_music",
    "apple_music": "apple_music",
    "apple music": "apple_music",
    "local": "local",
    "qq": "qq_music",
    "qq_music": "qq_music",
    "qq music": "qq_music",
    "qqmusic": "qq_music",
}
_MODES = {
    "random": "shuffle",
    "shuffle": "shuffle",
    "sequential": "sequential",
    "sequence": "sequential",
    "repeat": "repeat",
    "repeat_all": "repeat",
    "loop": "repeat",
    "repeat_one": "repeat_one",
    "single": "repeat_one",
}

_FAST_PATH: list[tuple] = [
    # (compiled_regex, command, args_fn)
    # args_fn(match) -> tuple[str, ...]
]

def _fp(*patterns: str, cmd: str, args=None):
    import re as _re
    for p in patterns:
        _FAST_PATH.append((_re.compile(p, _re.I | _re.U), cmd, args or (lambda m: ())))

_fp(r"^(pause|暂停|停止|停止播放)$", cmd="pause")
_fp(r"^(next|下一首|跳过|skip)$", cmd="next")
_fp(r"^(prev|previous|back|上一首|前一首)$", cmd="prev")
_fp(r"^(np|now\s*playing|当前|正在播放|在听什么|在听啥)$", cmd="np")
_fp(r"^(status|状态)$", cmd="status")
_fp(r"^(like|收藏|喜欢|favorite)$", cmd="like")
_fp(r"^(lyrics|歌词)$", cmd="lyrics")
_fp(r"^(player|播放器)$", cmd="player")
_fp(r"^(play|播放|继续|resume)$", cmd="play")
_fp(r"^(?:volume|音量)\s+(\d+)%?$", cmd="volume",
    args=lambda m: (str(max(0, min(100, int(m.group(1))))),))
_fp(r"^(?:seek|跳到|快进)\s+([\d:]+(?:\.\d+)?)$", cmd="seek",
    args=lambda m: (m.group(1),))
_fp(r"^(?:source|切换|切到|switch\s+to)\s+(apple(?:_music)?|qq(?:_music)?|local)$", cmd="source",
    args=lambda m: (_normalize_source(m.group(1)),))
_fp(r"^(?:mode|模式)\s+(shuffle|random|sequential|repeat_one|repeat|single|随机|顺序|单曲循环|列表循环)$",
    cmd="mode", args=lambda m: (_normalize_mode(m.group(1)),))
_fp(r"^bar\s+(show|hide|auto)$", cmd="bar", args=lambda m: (m.group(1),))
_fp(r"^(?:显示|开启)状态栏$", cmd="bar", args=lambda m: ("show",))
_fp(r"^(?:隐藏|关闭)状态栏$", cmd="bar", args=lambda m: ("hide",))
_fp(r"^状态栏自动$", cmd="bar", args=lambda m: ("auto",))


def _fast_path_plan(intent: str) -> "Optional[CwbPlan]":
    s = (intent or "").strip()
    if not s:
        return CwbPlan("status")
    for regex, cmd, args_fn in _FAST_PATH:
        m = regex.match(s)
        if m:
            try:
                return CwbPlan(cmd, args_fn(m))
            except CwbAgentError:
                return None
    return None


_SYSTEM_PROMPT = """You are a private one-shot controller for coding-with-beat.
Your only job is to translate the user's /cwb intent into one safe
coding-with-beat CLI action. You cannot use tools in this session.

Return exactly one JSON object that matches the rules below. Do not include
Markdown, code fences, prose, or a shell command string.

Valid commands and args:
- status: []
- np: []
- play: [] to resume, or ["song / artist / mood query"] to search and play
- pause: []
- next: []
- prev: []
- source: ["apple_music" | "qq_music" | "local"]
- like: []
- mode: ["shuffle" | "sequential" | "repeat" | "repeat_one"]
- lyrics: []
- player: []
- volume: ["0".."100"] — set playback volume
- seek: ["seconds" or "mm:ss"] — seek to position
- bar: ["show" | "hide" | "auto"] — statusline visibility (auto = only when playing)

Choose status for an empty or ambiguous intent. Preserve Chinese song names and
artist names verbatim. Put a play search query in args as one string when
possible. Never output /cwb, claude, shell metacharacters, file paths, or any
command outside this list.

Important interpretation rules:
- "播放下一首", "下一首", "跳过", "next song" => {"command":"next","args":[]}
- "播放上一首", "上一首", "previous song" => {"command":"prev","args":[]}
- "播放"/"继续"/"resume" with no query => {"command":"play","args":[]}
"""


class CwbAgentError(RuntimeError):
    pass


@dataclass(frozen=True)
class CwbPlan:
    command: str
    args: tuple[str, ...] = ()
    note: str = ""


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _clean_text(text: str, limit: int = 3000) -> str:
    cleaned = _ANSI_RE.sub("", text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "..."


def build_agent_prompt(intent: str) -> str:
    intent = (intent or "").strip()
    if not intent:
        intent = "(empty)"
    return (
        "User intent after /cwb:\n"
        f"{intent}\n\n"
        "Return the JSON plan now."
    )


def build_claude_command(prompt: str) -> list[str]:
    claude = os.environ.get("CWB_CLAUDE", "claude")
    cmd = [
        claude,
        "-p",
        "--no-session-persistence",
        "--disable-slash-commands",
        "--strict-mcp-config",
        "--mcp-config",
        '{"mcpServers":{}}',
        "--tools",
        "",
        "--max-turns",
        "1",
        "--system-prompt",
        _SYSTEM_PROMPT,
        prompt,
    ]
    # --bare skips OAuth/keychain auth in current Claude Code builds, so keep it
    # opt-in for users who authenticate headless Claude via ANTHROPIC_API_KEY.
    if _truthy_env("CWB_AGENT_BARE"):
        cmd.insert(1, "--bare")
    return cmd


def _json_from_text(text: str) -> Any:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(cleaned[start : end + 1])


def parse_claude_plan(raw: str) -> CwbPlan:
    data = _json_from_text(raw)
    if isinstance(data, dict) and "result" in data:
        result = data["result"]
        data = _json_from_text(result) if isinstance(result, str) else result
    if not isinstance(data, dict):
        raise CwbAgentError("Claude returned a non-object plan")
    return normalize_plan(data)


def normalize_plan(data: dict[str, Any]) -> CwbPlan:
    command = str(data.get("command") or "").strip().lower().replace("-", "_")
    command = _COMMAND_ALIASES.get(command, command)
    if command not in _ALLOWED_COMMANDS:
        raise CwbAgentError(f"Unsupported cwb command: {command or '(empty)'}")

    raw_args = data.get("args") or []
    if not isinstance(raw_args, list):
        raise CwbAgentError("Plan args must be a list")
    args_list = []
    for item in raw_args:
        arg = _clean_arg(item)
        if arg:
            args_list.append(arg)
    args = tuple(args_list)
    note = str(data.get("note") or "").strip()

    if command == "source":
        if len(args) != 1:
            raise CwbAgentError("source requires exactly one argument")
        return CwbPlan(command, (_normalize_source(args[0]),), note)
    if command == "mode":
        if len(args) != 1:
            raise CwbAgentError("mode requires exactly one argument")
        return CwbPlan(command, (_normalize_mode(args[0]),), note)
    if command == "volume":
        if len(args) != 1:
            raise CwbAgentError("volume requires exactly one argument")
        try:
            vol = max(0, min(100, int(args[0])))
        except ValueError:
            raise CwbAgentError("volume argument must be an integer 0-100")
        return CwbPlan(command, (str(vol),), note)
    if command == "seek":
        if len(args) != 1:
            raise CwbAgentError("seek requires exactly one argument")
        return CwbPlan(command, args, note)
    if command == "bar":
        if len(args) != 1 or args[0] not in ("show", "hide", "auto"):
            raise CwbAgentError("bar requires exactly one argument: show | hide | auto")
        return CwbPlan(command, args, note)
    if command != "play" and args:
        raise CwbAgentError(f"{command} does not accept arguments")
    if command == "play" and any(len(arg) > 300 for arg in args):
        raise CwbAgentError("play query is too long")
    return CwbPlan(command, args, note)


def _clean_arg(value: Any) -> str:
    arg = str(value).strip()
    arg = arg.replace("\x00", "")
    if any(ch in arg for ch in "\r\n"):
        raise CwbAgentError("Arguments cannot contain newlines")
    return arg


def _normalize_source(value: str) -> str:
    key = value.strip().lower().replace("-", "_")
    key = key.replace("_", " ") if key not in _SOURCES else key
    if key not in _SOURCES:
        raise CwbAgentError(f"Unsupported source: {value}")
    return _SOURCES[key]


def _normalize_mode(value: str) -> str:
    key = value.strip().lower().replace("-", "_").replace(" ", "_")
    if key not in _MODES:
        raise CwbAgentError(f"Unsupported mode: {value}")
    return _MODES[key]


def run_child_claude(intent: str, *, timeout: Optional[int] = None) -> CwbPlan:
    prompt = build_agent_prompt(intent)
    cmd = build_claude_command(prompt)
    timeout = timeout or int(os.environ.get("CWB_AGENT_TIMEOUT", _DEFAULT_CLAUDE_TIMEOUT))
    try:
        env = os.environ.copy()
        env["CWB_DISABLE_HOOK"] = "1"
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            env=env,
        )
    except FileNotFoundError as e:
        raise CwbAgentError("Claude CLI was not found on PATH") from e
    except subprocess.TimeoutExpired as e:
        raise CwbAgentError(f"cwb agent timed out after {timeout}s") from e
    if proc.returncode != 0:
        detail = _clean_text(proc.stdout, limit=800)
        raise CwbAgentError(f"cwb agent failed: {detail or f'exit {proc.returncode}'}")
    return parse_claude_plan(proc.stdout)


_PASSTHROUGH_COMMANDS = {"player", "status", "lyrics"}


def _spectrum_bar(width: int = 26) -> str:
    import time
    from .ui.progress import render_spectrum_color
    return render_spectrum_color(time.time() % 120, width=width)


def _buddy_card(mood: str, right_lines: list) -> str:
    """Render a dancing pixel-person (left) with info lines (right)."""
    from . import dj
    sprite_str = dj.dancing_sprite(mood)
    sprite_lines = sprite_str.splitlines()
    sprite_w = 10  # visible width of pixel-person sprite
    pad = "  "
    # Center right-side text vertically on the sprite
    offset = max(0, (len(sprite_lines) - len(right_lines)) // 2)
    rows = []
    n = max(len(sprite_lines), len(right_lines) + offset)
    for i in range(n):
        sl = sprite_lines[i] if i < len(sprite_lines) else " " * sprite_w
        ri = i - offset
        rl = right_lines[ri] if 0 <= ri < len(right_lines) else ""
        rows.append(f"{sl}{pad}{rl}" if rl else sl)
    return "\n".join(rows)


def execute_plan(plan: CwbPlan, *, timeout: Optional[int] = None) -> tuple[int, str]:
    timeout = timeout or int(os.environ.get("CWB_CLI_TIMEOUT", _DEFAULT_CLI_TIMEOUT))
    proc = subprocess.run(
        [sys.executable, "-m", "coding_with_beat", plan.command, *plan.args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,  # Separate stderr so technical messages don't leak into output
        text=True,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout


def _format_result(plan: CwbPlan, code: int, output: str) -> str:
    from . import dj
    clean = _clean_text(output).strip()

    if plan.command in _PASSTHROUGH_COMMANDS:
        if code != 0:
            return _buddy_card("sad", [clean or f"{plan.command} 失败"])
        return clean

    if code != 0:
        if plan.command == "play":
            query = " ".join(plan.args) if plan.args else ""
            if query:
                return _buddy_card("sad", [
                    f"找不到「{query}」",
                    "试试加上艺术家名",
                    "或换个搜索词",
                    f'"{dj.quip("sad")}"',
                ])
            return _buddy_card("sad", ["没有正在播放的歌曲", f'"{dj.quip("sad")}"'])
        if plan.command in ("np", "pause", "next", "prev", "like"):
            return _buddy_card("neutral", [
                "当前没有正在播放的歌曲",
                f'"{dj.quip("neutral")}"',
            ])
        return _buddy_card("sad", [clean or f"{plan.command} 失败"])

    track = clean or ""
    if plan.command in ("play", "next", "prev"):
        action = {
            "next": "⏭  下一首",
            "prev": "⏮  上一首",
        }.get(plan.command, "▶  继续播放" if not plan.args else "▶  正在播放")
        lines = [action]
        if track:
            lines.append(f"   ♪ {track}")
        lines.append(_spectrum_bar(26))
        lines.append(f'"{dj.quip("groove")}"')
        return _buddy_card("groove", lines)
    if plan.command == "np":
        if track:
            return _buddy_card("groove", [
                "▶  正在播放",
                f"   ♪ {track}",
                _spectrum_bar(26),
                f'"{dj.quip("groove")}"',
            ])
        return _buddy_card("neutral", ["当前没有正在播放的歌曲", f'"{dj.quip("neutral")}"'])
    if plan.command == "pause":
        lines = ["❚❚  已暂停"]
        if track:
            lines.append(f"   ♪ {track}")
        lines.append(f'"{dj.quip("neutral")}"')
        return _buddy_card("neutral", lines)
    if plan.command == "like":
        return _buddy_card("happy", [f"已收藏 ♥", track, f'"{dj.quip("happy")}"'])
    if plan.command == "source":
        return _buddy_card("neutral", [f"音源 → {track}"])
    if plan.command == "mode":
        return _buddy_card("neutral", [f"播放模式 → {track}"])
    if plan.command == "volume":
        vol = plan.args[0] if plan.args else "?"
        return _buddy_card("neutral", [f"音量 → {vol}%"])
    if plan.command == "seek":
        pos = plan.args[0] if plan.args else "?"
        return _buddy_card("neutral", [f"跳转至 {pos}"])
    if plan.command == "bar":
        mode = plan.args[0] if plan.args else "?"
        label = {"show": "状态栏已开启", "hide": "状态栏已隐藏", "auto": "状态栏自动（有歌时显示）"}.get(mode, mode)
        return _buddy_card("neutral", [label])
    return _buddy_card("neutral", [track or "完成"])


def run_intent(intent: str) -> str:
    plan = _fast_path_plan(intent) or run_child_claude(intent)
    code, output = execute_plan(plan)
    return _format_result(plan, code, output)


def handle_prompt_expansion(event: dict) -> Optional[dict]:
    hook = (event.get("hook_event_name") or "").lower()
    if hook != "userpromptexpansion":
        return None
    if (event.get("command_name") or "").lower() != "cwb":
        return None
    try:
        message = run_intent(event.get("command_args") or "")
    except CwbAgentError as e:
        err = _clean_text(str(e), limit=200)
        message = _buddy_card("panic", [
            "解析失败，请重试",
            err[:60] if err else "",
        ])
    except Exception:
        message = _buddy_card("panic", ["出了点问题，请重试"])
    return {
        "decision": "block",
        "reason": message,
        "suppressOutput": True,
    }
