#!/usr/bin/env python3
"""Build a local CodeBeat.app wrapper."""

from __future__ import annotations

import plistlib
import shutil
from pathlib import Path

APP_NAME = "CodeBeat"
BUNDLE_ID = "top.codebeat.CodeBeat"
ROOT = Path(__file__).resolve().parents[1]


def build_app(output_dir: Path | None = None) -> Path:
    output_root = output_dir if output_dir is not None else ROOT / "dist"
    app_path = output_root / f"{APP_NAME}.app"
    contents = app_path / "Contents"
    macos = contents / "MacOS"
    resources = contents / "Resources"

    if app_path.exists():
        shutil.rmtree(app_path)
    macos.mkdir(parents=True)
    resources.mkdir(parents=True)

    _write_info_plist(contents / "Info.plist")
    _write_launcher(macos / APP_NAME)
    _copy_icons(resources)
    return app_path


def _write_info_plist(path: Path) -> None:
    plist = {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleIdentifier": BUNDLE_ID,
        "CFBundleExecutable": APP_NAME,
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": "0.1.0",
        "CFBundleVersion": "1",
        "LSMinimumSystemVersion": "12.0",
        "LSUIElement": True,
        "NSHighResolutionCapable": True,
    }
    with path.open("wb") as f:
        plistlib.dump(plist, f, sort_keys=True)


def _write_launcher(path: Path) -> None:
    text = """#!/bin/zsh
set -euo pipefail

LOG_DIR="$HOME/.coding-with-beat/logs"
mkdir -p "$LOG_DIR"

REPO_FILE="$HOME/.coding-with-beat/repo-path"
if [ -f "$REPO_FILE" ]; then
  REPO="$(cat "$REPO_FILE")"
else
  REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
fi

PY="$HOME/.coding-with-beat/venv/bin/python"
if [ ! -x "$PY" ]; then
  PY="$(command -v python3 || command -v python)"
fi

cd "$REPO"
# Runs the same command users can run manually: python -m coding_with_beat app
exec "$PY" -m coding_with_beat app >>"$LOG_DIR/app.log" 2>>"$LOG_DIR/app.err.log"
"""
    path.write_text(text, encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o755)


def _copy_icons(resources: Path) -> None:
    for name in ("waveform_app_icon.svg", "waveform_menu_bar.svg"):
        shutil.copy2(ROOT / "assets" / name, resources / name)


def main() -> int:
    app_path = build_app()
    print(app_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
