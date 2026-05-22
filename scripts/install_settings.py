"""Idempotent merger for Claude Code's ~/.claude/settings.json.

Adds (or removes) entries for:
  - mcpServers["coding-with-beat"]
  - statusLine (only if unset, or already ours; we don't clobber other tools)
  - hooks: PreToolUse, PostToolUse, SessionStart, Stop  (with matcher: ".*")
  - UserPromptExpansion hook for /cwb, so music controls do not enter chat context

Re-running is safe. Keys we don't own are never touched.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from coding_with_beat.cwb_agent import HOOK_TIMEOUT

TAG = "coding-with-beat"
LEGACY_TAGS = {"cc-jukebox"}
OWNERS = {TAG, *LEGACY_TAGS}
DEFAULT_MCP_URL = "http://127.0.0.1:8765/mcp"


def _owned(entry: object) -> bool:
    return isinstance(entry, dict) and entry.get("_owner") in OWNERS


def hook_entry(python: str, repo: str) -> dict:
    return {
        "matcher": ".*",
        "hooks": [
            {
                "type": "command",
                "command": f"{python} -m coding_with_beat hook",
                "timeout": 5,
            }
        ],
        # marker so we can find & remove our own entries later
        "_owner": TAG,
    }


def session_hook_entry(python: str, repo: str) -> dict:
    return {
        "hooks": [
            {
                "type": "command",
                "command": f"{python} -m coding_with_beat hook",
                "timeout": 5,
            }
        ],
        "_owner": TAG,
    }


def cwb_expansion_hook_entry(python: str, repo: str) -> dict:
    return {
        "matcher": "cwb",
        "hooks": [
            {
                "type": "command",
                "command": f"{python} -m coding_with_beat hook",
                "timeout": HOOK_TIMEOUT,
            }
        ],
        "_owner": TAG,
    }


def load_settings(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"WARN: existing {path} is not valid JSON ({e}); backing up to .bak", file=sys.stderr)
        path.with_suffix(path.suffix + ".bak").write_text(path.read_text())
        return {}


def save_settings(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def merge(
    settings: dict,
    python: str,
    repo: str,
    mcp_url: str = DEFAULT_MCP_URL,
) -> dict:
    mcp_url = mcp_url or DEFAULT_MCP_URL

    # mcpServers
    servers = settings.setdefault("mcpServers", {})
    for legacy in LEGACY_TAGS:
        servers.pop(legacy, None)
    server = {
        "type": "http",
        "url": mcp_url,
    }
    servers[TAG] = server

    # statusLine — only set if not present OR already ours
    sl = settings.get("statusLine")
    if not sl or _owned(sl):
        settings["statusLine"] = {
            "type": "command",
            "command": f"{python} -m coding_with_beat statusline",
            "refreshInterval": 1,
            "_owner": TAG,
        }

    # hooks
    hooks = settings.setdefault("hooks", {})
    for event in ("PreToolUse", "PostToolUse"):
        lst = hooks.setdefault(event, [])
        # remove any prior entries we own
        lst[:] = [e for e in lst if not _owned(e)]
        lst.append(hook_entry(python, repo))

    for event in ("SessionStart", "Stop"):
        lst = hooks.setdefault(event, [])
        lst[:] = [e for e in lst if not _owned(e)]
        lst.append(session_hook_entry(python, repo))

    lst = hooks.setdefault("UserPromptExpansion", [])
    lst[:] = [e for e in lst if not _owned(e)]
    lst.append(cwb_expansion_hook_entry(python, repo))

    return settings


def remove(settings: dict) -> dict:
    servers = settings.get("mcpServers", {})
    servers.pop(TAG, None)
    for legacy in LEGACY_TAGS:
        servers.pop(legacy, None)
    if not servers:
        settings.pop("mcpServers", None)

    sl = settings.get("statusLine")
    if _owned(sl):
        settings.pop("statusLine", None)

    hooks = settings.get("hooks", {})
    for event, lst in list(hooks.items()):
        if isinstance(lst, list):
            lst[:] = [e for e in lst if not _owned(e)]
            if not lst:
                hooks.pop(event)
    if not hooks:
        settings.pop("hooks", None)
    return settings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--settings", required=True)
    ap.add_argument("--python", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--mcp-url", default=DEFAULT_MCP_URL)
    ap.add_argument("--remove", action="store_true")
    args = ap.parse_args()

    path = Path(args.settings)
    settings = load_settings(path)

    if args.remove:
        settings = remove(settings)
    else:
        settings = merge(settings, args.python, args.repo, args.mcp_url)

    save_settings(path, settings)
    return 0


if __name__ == "__main__":
    sys.exit(main())
