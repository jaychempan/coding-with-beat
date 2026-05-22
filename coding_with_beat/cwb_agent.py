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
    "history",
    "help",
    "welcome",
    "search",
    "list",
    "play_number",
    "update",
}
_SOURCES = {
    # English
    "apple": "apple_music",
    "apple_music": "apple_music",
    "apple music": "apple_music",
    "am": "apple_music",
    "local": "local",
    "files": "local",
    "qq": "qq_music",
    "qq_music": "qq_music",
    "qq music": "qq_music",
    "qqmusic": "qq_music",
    # Chinese
    "苹果": "apple_music",
    "苹果音乐": "apple_music",
    "本地": "local",
    "本地文件": "local",
    "qq音乐": "qq_music",
}
_MODES = {
    # English
    "random": "shuffle",
    "shuffle": "shuffle",
    "sequential": "sequential",
    "sequence": "sequential",
    "repeat": "repeat",
    "repeat_all": "repeat",
    "loop": "repeat",
    "repeat_one": "repeat_one",
    "single": "repeat_one",
    # Chinese
    "随机": "shuffle",
    "随机播放": "shuffle",
    "顺序": "sequential",
    "顺序播放": "sequential",
    "单曲循环": "repeat_one",
    "单曲": "repeat_one",
    "列表循环": "repeat",
    "循环": "repeat",
    "循环播放": "repeat",
}
_ZH_BAR = {"显示": "show", "开启": "show", "隐藏": "hide", "关闭": "hide", "自动": "auto"}

_FAST_PATH: list[tuple] = [
    # (compiled_regex, command, args_fn)
    # args_fn(match) -> tuple[str, ...]
]

def _fp(*patterns: str, cmd: str, args=None):
    import re as _re
    for p in patterns:
        _FAST_PATH.append((_re.compile(p, _re.I | _re.U), cmd, args or (lambda m: ())))

# ── no-arg commands ───────────────────────────────────────────────────────────
_fp(r"^(pause|暂停|停|停止|停止播放|暂停播放)$", cmd="pause")
_fp(r"^(next|下一首|下首|跳过|跳下一首|skip)$", cmd="next")
_fp(r"^(prev|previous|back|上一首|上首|回上一首|前一首)$", cmd="prev")
_fp(r"^(np|now\s*playing|当前|正在播放|在听什么|在听啥|在放什么|现在放什么|现在在听)$", cmd="np")
_fp(r"^(status|状态|当前状态)$", cmd="status")
_fp(r"^(like|收藏|喜欢|favorite|添加喜欢)$", cmd="like")
_fp(r"^(lyrics|歌词|显示歌词|看歌词)$", cmd="lyrics")
_fp(r"^(player|播放器|显示播放器|打开播放器)$", cmd="player")
_fp(r"^(play|播放|继续|继续播放|resume)$", cmd="play")
_fp(r"^(history|播放历史|最近播放|听歌记录|历史)(?:\s+(\d+))?$", cmd="history",
    args=lambda m: (m.group(2),) if m.group(2) else ())
_fp(r"^(?:list|列表|资料库)(?:\s+(\d+))?$", cmd="list",
    args=lambda m: (m.group(1),) if m.group(1) else ())
_fp(r"^(?:search|搜索|找歌|查找)\s+(.+)$", cmd="search",
    args=lambda m: (m.group(1).strip(),))
_fp(r"^(?:play|播放)\s+(\d+)$", cmd="play_number",
    args=lambda m: (m.group(1),))
_CLAUSE_SENTINEL = re.compile(
    r"这个|这首|这种|这部分|这里|如果|不能|为什么|是不是|告诉|手动|弹窗|注意|会弹|会显示|为啥|怎么|可以吗|嘛$|吗$|呢$|啊$"
)

def _extract_play_query(m: "re.Match") -> tuple:
    raw = m.group(1).strip()
    # 1. Split at CJK punctuation
    first = re.split(r"[，；。,;！？!?]", raw)[0].strip()
    # 2. Split at clause-marker words that rarely appear in song/artist names
    sentinel = _CLAUSE_SENTINEL.search(first)
    if sentinel and sentinel.start() > 0:
        candidate = first[: sentinel.start()].strip()
        if candidate:
            first = candidate
    return (first,)

# Generic play <query>: trim complaint text mixed into the command.
_fp(r"^(?:play|播放|听|放|来一首)\s+(.+)$", cmd="play", args=_extract_play_query)
_fp(r"^(help|usage|commands)$", cmd="help", args=lambda m: ("en",))
_fp(r"^(帮助|命令|命令列表|怎么用)$", cmd="help", args=lambda m: ("zh",))
_fp(r"^(welcome|欢迎|欢迎界面|启动界面)$", cmd="welcome")
_fp(r"^(update|更新|升级)$", cmd="update")

# ── volume ─────────────────────────────────────────────────────────────────
_fp(r"^(?:volume|音量|调音量(?:到)?|把音量(?:调)?(?:到)?|设置音量(?:为)?)\s*(\d+)%?$", cmd="volume",
    args=lambda m: (str(max(0, min(100, int(m.group(1))))),))

# ── seek ───────────────────────────────────────────────────────────────────
_fp(r"^(?:seek|跳到|快进|跳至|进度跳到)\s*([\d:]+(?:\.\d+)?)$", cmd="seek",
    args=lambda m: (m.group(1),))

# ── source ─────────────────────────────────────────────────────────────────
_SRC_PAT = r"(apple(?:_music)?|qq(?:_music)?|local|苹果(?:音乐)?|qq音乐|本地(?:文件)?|am)"
_fp(rf"^(?:source|切换|切到|switch\s+to|换成|改用|换到|用)\s*{_SRC_PAT}$", cmd="source",
    args=lambda m: (_normalize_source(m.group(1)),))

# ── mode ───────────────────────────────────────────────────────────────────
_MODE_PAT = r"(shuffle|random|sequential|repeat_one|repeat|single|随机(?:播放)?|顺序(?:播放)?|单曲(?:循环)?|列表循环|循环(?:播放)?)"
_fp(rf"^(?:mode|模式|播放模式|设置模式(?:为)?)\s*{_MODE_PAT}$", cmd="mode",
    args=lambda m: (_normalize_mode(m.group(1)),))

# ── bar ────────────────────────────────────────────────────────────────────
_BAR_PAT = r"(show|hide|auto|显示|隐藏|自动|开启|关闭)"
_fp(rf"^bar\s+{_BAR_PAT}$", cmd="bar",
    args=lambda m: (_ZH_BAR.get(m.group(1), m.group(1)),))
_fp(r"^(?:显示|开启)状态栏$", cmd="bar", args=lambda m: ("show",))
_fp(r"^(?:隐藏|关闭)状态栏$", cmd="bar", args=lambda m: ("hide",))
_fp(r"^状态栏自动$", cmd="bar", args=lambda m: ("auto",))
_fp(r"^statusline\s+(show|hide|auto)$", cmd="bar", args=lambda m: (m.group(1),))


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
- history: [] or ["n"] — show last n played tracks
- search: ["query"] — list matching tracks from library and Apple Music catalog
- list: [] or ["n"] — list all library tracks (default 100)

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
    if command == "help":
        lang = args[0] if args and args[0] in ("en", "zh") else "en"
        return CwbPlan(command, (lang,), note)
    if command == "play_number":
        if len(args) != 1:
            raise CwbAgentError("play_number requires exactly one argument (a number)")
        try:
            n = int(args[0])
            if n < 1:
                raise ValueError
        except ValueError:
            raise CwbAgentError("play_number argument must be a positive integer")
        return CwbPlan(command, (str(n),), note)
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
    s = value.strip().lower()
    for variant in (s, s.replace("-", "_"), s.replace("-", " "), s.replace("_", " ")):
        if variant in _SOURCES:
            return _SOURCES[variant]
    raise CwbAgentError(f"Unsupported source: {value}")


def _normalize_mode(value: str) -> str:
    s = value.strip().lower()
    for variant in (s, s.replace("-", "_"), s.replace(" ", "_"), s.replace("_", "")):
        if variant in _MODES:
            return _MODES[variant]
    raise CwbAgentError(f"Unsupported mode: {value}")


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


_PASSTHROUGH_COMMANDS = {"player", "status", "lyrics", "history", "help", "welcome", "search", "list", "update"}

_CJK_RE = re.compile(r"[　-鿿豈-﫿]")


_ZH_VERBS = re.compile(
    r"^(播放|听|放|来一首|暂停|停止|下一首|上一首|跳过|切换|收藏|喜欢|搜索|找歌|模式|音量|歌词|播放器|状态|历史|帮助|命令|状态栏|来源|卡拉)"
)

def _detect_lang(text: str) -> str:
    """'zh' if the leading command verb is Chinese, else 'en'.
    'play 周杰伦' → en;  '播放 周杰伦' → zh."""
    return "zh" if _ZH_VERBS.match((text or "").strip()) else "en"


_T: dict[str, dict[str, str]] = {
    "zh": {
        "play_resume": "▶  继续播放",
        "play_now":    "▶  正在播放",
        "next":        "⏭  下一首",
        "prev":        "⏮  上一首",
        "paused":      "❚❚  已暂停",
        "liked":       "已收藏 ♥",
        "no_track":    "当前没有正在播放的歌曲",
        "not_found":   "找不到「{q}」",
        "hint1":       "试试加上艺术家名",
        "hint2":       "或换个搜索词",
        "needs_library":  "「{q}」在 Apple Music 找到了",
        "needs_library_hint": "已打开搜索页面，点击歌曲旁「...」→「添加到资料库」后再试",
        "source":      "音源 → {v}",
        "mode":        "播放模式 → {v}",
        "volume":      "音量 → {v}%",
        "seek":        "跳转至 {v}",
        "bar_show":    "状态栏已开启",
        "bar_hide":    "状态栏已隐藏",
        "bar_auto":    "状态栏自动（有歌时显示）",
        "done":        "完成",
        "cmd_fail":    "{cmd} 失败",
        "parse_fail":  "解析失败，请重试",
        "error":       "出了点问题，请重试",
    },
    "en": {
        "play_resume": "▶  Resumed",
        "play_now":    "▶  Now Playing",
        "next":        "⏭  Next Track",
        "prev":        "⏮  Previous Track",
        "paused":      "❚❚  Paused",
        "liked":       "Liked ♥",
        "no_track":    "Nothing is playing right now",
        "not_found":   'Not found: "{q}"',
        "hint1":       "Try adding the artist name",
        "hint2":       "or use different search terms",
        "needs_library":  '"{q}" found on Apple Music',
        "needs_library_hint": "Search opened — click \"...\" → \"Add to Library\", then retry",
        "source":      "Source → {v}",
        "mode":        "Mode → {v}",
        "volume":      "Volume → {v}%",
        "seek":        "Seek to {v}",
        "bar_show":    "Statusline visible",
        "bar_hide":    "Statusline hidden",
        "bar_auto":    "Statusline auto (shows when playing)",
        "done":        "Done",
        "cmd_fail":    "{cmd} failed",
        "parse_fail":  "Parse error, please retry",
        "error":       "Something went wrong, please retry",
    },
}


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


def _format_result(plan: CwbPlan, code: int, output: str, lang: str = "zh") -> str:
    from . import dj
    t = _T[lang]
    clean = _clean_text(output).strip()

    def _needs_library_card(fallback: str) -> Optional[str]:
        if "needs_library_add" not in clean and "full playback did not start" not in clean:
            return None
        # Found on Apple Music catalog but can't auto-add/play fully.
        import re as _re
        _m = _re.search(r"needs_library_add:(.+?):(.+)", clean)
        if not _m:
            _m = _re.search(r'Found "(.+?) — (.+?)" in the Apple Music catalog', clean)
        song_info = f"{_m.group(1)} — {_m.group(2)}" if _m else fallback
        return _buddy_card("neutral", [
            t["needs_library"].format(q=song_info),
            t["needs_library_hint"],
            f'"{dj.quip("neutral")}"',
        ])

    if plan.command in _PASSTHROUGH_COMMANDS:
        if code != 0:
            return _buddy_card("sad", [clean or t["cmd_fail"].format(cmd=plan.command)])
        return (output or "").strip()

    if code != 0:
        if plan.command == "play":
            query = " ".join(plan.args) if plan.args else ""
            if query:
                # Distinguish "found on Apple Music catalog but not in library" from "not found at all"
                needs_library = _needs_library_card(query)
                if needs_library:
                    return needs_library
                return _buddy_card("sad", [
                    t["not_found"].format(q=query),
                    t["hint1"],
                    t["hint2"],
                    f'"{dj.quip("sad")}"',
                ])
            return _buddy_card("sad", [t["no_track"], f'"{dj.quip("sad")}"'])
        if plan.command == "play_number":
            needs_library = _needs_library_card(f"#{plan.args[0]}" if plan.args else "selected track")
            if needs_library:
                return needs_library
            return _buddy_card("sad", [clean or t["cmd_fail"].format(cmd="play_number"), f'"{dj.quip("sad")}"'])
        if plan.command in ("np", "pause", "next", "prev", "like"):
            return _buddy_card("neutral", [t["no_track"], f'"{dj.quip("neutral")}"'])
        return _buddy_card("sad", [clean or t["cmd_fail"].format(cmd=plan.command)])

    track = clean or ""
    if plan.command in ("play", "next", "prev", "play_number"):
        action = {
            "next": t["next"],
            "prev": t["prev"],
        }.get(plan.command, t["play_resume"] if not plan.args else t["play_now"])
        lines = [action]
        if track:
            lines.append(f"   ♪ {track}")
        lines.append(_spectrum_bar(26))
        lines.append(f'"{dj.quip("groove")}"')
        return _buddy_card("groove", lines)
    if plan.command == "np":
        if track:
            return _buddy_card("groove", [
                t["play_now"],
                f"   ♪ {track}",
                _spectrum_bar(26),
                f'"{dj.quip("groove")}"',
            ])
        return _buddy_card("neutral", [t["no_track"], f'"{dj.quip("neutral")}"'])
    if plan.command == "pause":
        lines = [t["paused"]]
        if track:
            lines.append(f"   ♪ {track}")
        lines.append(f'"{dj.quip("neutral")}"')
        return _buddy_card("neutral", lines)
    if plan.command == "like":
        return _buddy_card("happy", [t["liked"], track, f'"{dj.quip("happy")}"'])
    if plan.command == "source":
        return _buddy_card("neutral", [t["source"].format(v=track)])
    if plan.command == "mode":
        return _buddy_card("neutral", [t["mode"].format(v=track)])
    if plan.command == "volume":
        vol = plan.args[0] if plan.args else "?"
        return _buddy_card("neutral", [t["volume"].format(v=vol)])
    if plan.command == "seek":
        pos = plan.args[0] if plan.args else "?"
        return _buddy_card("neutral", [t["seek"].format(v=pos)])
    if plan.command == "bar":
        mode = plan.args[0] if plan.args else "?"
        label = {"show": t["bar_show"], "hide": t["bar_hide"], "auto": t["bar_auto"]}.get(mode, mode)
        return _buddy_card("neutral", [label])
    return _buddy_card("neutral", [track or t["done"]])


def run_intent(intent: str) -> str:
    lang = _detect_lang(intent)
    plan = _fast_path_plan(intent) or run_child_claude(intent)
    code, output = execute_plan(plan)
    return _format_result(plan, code, output, lang=lang)


_CWB_HEADER = (
    "\x1b[38;2;155;188;15m"
    "♩ · · · coding  with  beat · · · ♩"
    "\x1b[0m"
)


def handle_prompt_expansion(event: dict) -> Optional[dict]:
    hook = (event.get("hook_event_name") or "").lower()
    if hook != "userpromptexpansion":
        return None
    if (event.get("command_name") or "").lower() != "cwb":
        return None
    intent = event.get("command_args") or ""
    lang = _detect_lang(intent)
    t = _T[lang]
    try:
        message = run_intent(intent)
    except CwbAgentError as e:
        err = _clean_text(str(e), limit=200)
        message = _buddy_card("panic", [t["parse_fail"], err[:60] if err else ""])
    except Exception:
        message = _buddy_card("panic", [t["error"]])
    return {
        "decision": "block",
        "reason": f"{_CWB_HEADER}\n{message}",
    }
