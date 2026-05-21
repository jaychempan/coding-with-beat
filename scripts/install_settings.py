"""Idempotent merger for Claude Code's ~/.claude/settings.json.

Adds (or removes) entries for:
  - mcpServers["cc-jukebox"]
  - statusLine (only if unset, or already ours; we don't clobber other tools)
  - hooks: PreToolUse, PostToolUse, SessionStart, Stop  (with matcher: ".*")

Re-running is safe. Keys we don't own are never touched.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


TAG = "cc-jukebox"


def hook_entry(python: str, repo: str) -> dict:
    return {
        "matcher": ".*",
        "hooks": [
            {
                "type": "command",
                "command": f'{python} -m cc_jukebox hook',
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
                "command": f'{python} -m cc_jukebox hook',
                "timeout": 5,
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


def merge(settings: dict, python: str, repo: str) -> dict:
    # mcpServers
    servers = settings.setdefault("mcpServers", {})
    servers[TAG] = {
        "command": python,
        "args": ["-m", "cc_jukebox.server"],
        "cwd": repo,
    }

    # statusLine — only set if not present OR already ours
    sl = settings.get("statusLine")
    if not sl or (isinstance(sl, dict) and sl.get("_owner") == TAG):
        settings["statusLine"] = {
            "type": "command",
            "command": f"{python} -m cc_jukebox statusline",
            "refreshInterval": 1,
            "_owner": TAG,
        }

    # hooks
    hooks = settings.setdefault("hooks", {})
    for event in ("PreToolUse", "PostToolUse"):
        lst = hooks.setdefault(event, [])
        # remove any prior entries we own
        lst[:] = [e for e in lst if not (isinstance(e, dict) and e.get("_owner") == TAG)]
        lst.append(hook_entry(python, repo))

    for event in ("SessionStart", "Stop"):
        lst = hooks.setdefault(event, [])
        lst[:] = [e for e in lst if not (isinstance(e, dict) and e.get("_owner") == TAG)]
        lst.append(session_hook_entry(python, repo))

    return settings


def remove(settings: dict) -> dict:
    servers = settings.get("mcpServers", {})
    servers.pop(TAG, None)
    if not servers:
        settings.pop("mcpServers", None)

    sl = settings.get("statusLine")
    if isinstance(sl, dict) and sl.get("_owner") == TAG:
        settings.pop("statusLine", None)

    hooks = settings.get("hooks", {})
    for event, lst in list(hooks.items()):
        if isinstance(lst, list):
            lst[:] = [e for e in lst if not (isinstance(e, dict) and e.get("_owner") == TAG)]
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
    ap.add_argument("--remove", action="store_true")
    args = ap.parse_args()

    path = Path(args.settings)
    settings = load_settings(path)

    if args.remove:
        settings = remove(settings)
    else:
        settings = merge(settings, args.python, args.repo)

    save_settings(path, settings)
    return 0


if __name__ == "__main__":
    sys.exit(main())
