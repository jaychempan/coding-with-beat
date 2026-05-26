"""Idempotent patcher for Codex CLI config.

Writes / updates:
  ~/.codex/config.toml   — [mcp_servers.coding-with-beat] section
  ~/.codex/hooks.json    — PreToolUse / PostToolUse / SessionStart / Stop / UserPromptSubmit

Re-running is safe. Only our own entries (tagged _owner = "coding-with-beat") are touched.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

TAG = "coding-with-beat"
DEFAULT_MCP_URL = "http://127.0.0.1:8765/mcp"
HOOK_TIMEOUT = 180  # UserPromptSubmit (/cwb) may spawn a child claude process

# All MCP tools exposed by the coding-with-beat server.
_CWB_TOOLS = [
    "banner",
    "companion_check",
    "current_source",
    "dj_say",
    "focus_start",
    "focus_status",
    "focus_stop",
    "history_search",
    "like_current",
    "list_history",
    "list_library",
    "list_loved",
    "list_playlists",
    "next_track",
    "now_playing",
    "now_playing_snapshot",
    "pause",
    "play",
    "play_number",
    "play_playlist",
    "play_song",
    "prev_track",
    "resume",
    "search",
    "search_loved",
    "seek",
    "session_intro",
    "set_play_mode",
    "set_source",
    "set_volume",
    "show_cover",
    "show_lyrics",
    "show_player",
    "smart_search",
    "status",
    "tips",
    "toggle",
    "vibe_set",
]

_TOOL_APPROVALS_BEGIN = "# >>> cwb-tool-approvals >>>"
_TOOL_APPROVALS_END = "# <<< cwb-tool-approvals <<<"

_TOOL_APPROVALS_RE = re.compile(
    r"# >>> cwb-tool-approvals >>>.*?# <<< cwb-tool-approvals <<<\n?",
    re.DOTALL,
)

# Also matches old-style individual tool entries written before marker blocks existed.
_INDIVIDUAL_TOOL_RE = re.compile(
    r'\[mcp_servers\.coding-with-beat\.tools\.[^\]]+\]\napproval_mode = "approve"\n?',
)


def _tool_approvals_block() -> str:
    lines = [_TOOL_APPROVALS_BEGIN]
    for tool in _CWB_TOOLS:
        lines.append(f"\n[mcp_servers.coding-with-beat.tools.{tool}]")
        lines.append('approval_mode = "approve"')
    lines.append(_TOOL_APPROVALS_END)
    return "\n".join(lines) + "\n"


# ── TOML patcher (no external deps) ──────────────────────────────────────────

_MCP_SECTION_RE = re.compile(
    r"\[mcp_servers\.coding-with-beat\][^\[]*",
    re.DOTALL,
)


def _mcp_section(url: str) -> str:
    return f'[mcp_servers.coding-with-beat]\nurl = "{url}"\n'


def patch_config_toml(path: Path, mcp_url: str) -> None:
    content = path.read_text(encoding="utf-8") if path.exists() else ""

    # Remove old individually-written tool entries (no markers) so they don't duplicate.
    content = _INDIVIDUAL_TOOL_RE.sub("", content)

    if _MCP_SECTION_RE.search(content):
        content = _MCP_SECTION_RE.sub(_mcp_section(mcp_url), content)
    else:
        if content and not content.endswith("\n"):
            content += "\n"
        content += f"\n{_mcp_section(mcp_url)}"

    # Write / refresh the marked tool-approvals block.
    block = _tool_approvals_block()
    if _TOOL_APPROVALS_RE.search(content):
        content = _TOOL_APPROVALS_RE.sub(block, content)
    else:
        if not content.endswith("\n"):
            content += "\n"
        content += f"\n{block}"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def remove_config_toml(path: Path) -> None:
    if not path.exists():
        return
    content = path.read_text(encoding="utf-8")
    # Remove tool-approvals block first so its begin-marker isn't consumed by
    # the MCP section regex (which matches everything up to the next '[').
    content = _TOOL_APPROVALS_RE.sub("", content)
    content = _MCP_SECTION_RE.sub("", content)
    content = _INDIVIDUAL_TOOL_RE.sub("", content)
    path.write_text(content.strip() + "\n", encoding="utf-8")


# ── hooks.json patcher ────────────────────────────────────────────────────────


def _hook_entry(python: str, timeout: int = 5) -> dict:
    return {
        "type": "command",
        "command": f"{python} -m coding_with_beat codex_hook",
        "timeout": timeout,
        "_owner": TAG,
    }


def _matcher_entry(python: str, timeout: int = 5) -> dict:
    return {
        "matcher": ".*",
        "hooks": [_hook_entry(python, timeout)],
        "_owner": TAG,
    }


def _no_matcher_entry(python: str, timeout: int = 5) -> dict:
    return {
        "hooks": [_hook_entry(python, timeout)],
        "_owner": TAG,
    }


def _owned(entry: object) -> bool:
    return isinstance(entry, dict) and entry.get("_owner") == TAG


def load_hooks(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"WARN: {path} is not valid JSON ({e}); backing up to .bak", file=sys.stderr)
        path.with_suffix(".json.bak").write_text(path.read_text(encoding="utf-8"))
        return {}


def save_hooks(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def merge_hooks(hooks: dict, python: str) -> dict:
    h = hooks.setdefault("hooks", {})

    # PreToolUse / PostToolUse — matcher-based
    for event in ("PreToolUse", "PostToolUse"):
        lst = h.setdefault(event, [])
        lst[:] = [e for e in lst if not _owned(e)]
        lst.append(_matcher_entry(python, timeout=5))

    # SessionStart / Stop — no matcher needed
    for event in ("SessionStart", "Stop"):
        lst = h.setdefault(event, [])
        lst[:] = [e for e in lst if not _owned(e)]
        lst.append(_no_matcher_entry(python, timeout=5))

    # UserPromptSubmit — intercept /cwb commands
    lst = h.setdefault("UserPromptSubmit", [])
    lst[:] = [e for e in lst if not _owned(e)]
    lst.append(_matcher_entry(python, timeout=HOOK_TIMEOUT))

    return hooks


def remove_hooks(hooks: dict) -> dict:
    h = hooks.get("hooks", {})
    for event, lst in list(h.items()):
        if isinstance(lst, list):
            lst[:] = [e for e in lst if not _owned(e)]
            if not lst:
                del h[event]
    if not h:
        hooks.pop("hooks", None)
    return hooks


# ── skill installer ───────────────────────────────────────────────────────────


def install_skill(repo: Path, codex_dir: Path) -> None:
    src = repo / "codex_skills" / "cwb" / "SKILL.md"
    if not src.exists():
        print(f"WARN: skill source not found: {src}", file=sys.stderr)
        return
    dest_dir = codex_dir / "skills" / "cwb"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "SKILL.md"
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def remove_skill(codex_dir: Path) -> None:
    skill_dir = codex_dir / "skills" / "cwb"
    if skill_dir.exists():
        import shutil

        shutil.rmtree(skill_dir)


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(description="Patch ~/.codex/ for coding-with-beat")
    ap.add_argument("--codex-dir", default=str(Path.home() / ".codex"))
    ap.add_argument("--python", required=True, help="Path to venv Python")
    ap.add_argument("--repo", required=True, help="coding-with-beat repo root")
    ap.add_argument("--mcp-url", default=DEFAULT_MCP_URL)
    ap.add_argument("--remove", action="store_true")
    args = ap.parse_args()

    codex_dir = Path(args.codex_dir)
    toml_path = codex_dir / "config.toml"
    hooks_path = codex_dir / "hooks.json"

    if args.remove:
        remove_config_toml(toml_path)
        hooks = load_hooks(hooks_path)
        hooks = remove_hooks(hooks)
        save_hooks(hooks_path, hooks)
        remove_skill(codex_dir)
        print("coding-with-beat removed from Codex config")
    else:
        patch_config_toml(toml_path, args.mcp_url)
        hooks = load_hooks(hooks_path)
        hooks = merge_hooks(hooks, args.python)
        save_hooks(hooks_path, hooks)
        install_skill(Path(args.repo), codex_dir)
        print(f"Codex config patched: {toml_path}")
        print(f"Codex hooks patched:  {hooks_path}")
        print(f"Skill installed:      {codex_dir / 'skills' / 'cwb' / 'SKILL.md'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
