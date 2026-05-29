#!/usr/bin/env python3
"""Build a local CodeBeat.app wrapper."""

from __future__ import annotations

import plistlib
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw

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
        "CFBundleIconFile": "CodeBeat.icns",
        "CFBundleExecutable": APP_NAME,
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": "0.1.0",
        "CFBundleVersion": "1",
        "LSMinimumSystemVersion": "12.0",
        "LSUIElement": False,
        "NSHighResolutionCapable": True,
    }
    with path.open("wb") as f:
        plistlib.dump(plist, f, sort_keys=True)


def _write_launcher(path: Path) -> None:
    text = f"""#!/bin/zsh
set -euo pipefail

LOG_DIR="$HOME/.coding-with-beat/logs"
mkdir -p "$LOG_DIR"

BUILT_REPO="{ROOT}"
BUILT_PY="{sys.executable}"
REPO_FILE="$HOME/.coding-with-beat/repo-path"
if [ -d "$BUILT_REPO/coding_with_beat" ]; then
  REPO="$BUILT_REPO"
elif [ -f "$REPO_FILE" ]; then
  REPO="$(cat "$REPO_FILE")"
else
  REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
fi

PY="$BUILT_PY"
if [ ! -x "$PY" ]; then
  PY="$HOME/.coding-with-beat/venv/bin/python"
fi
if [ ! -x "$PY" ]; then
  PY="$(command -v python3 || command -v python)"
fi

cd "$REPO"
export PYTHONPATH="$REPO${{PYTHONPATH:+:$PYTHONPATH}}"
# Runs the same command users can run manually: python -m coding_with_beat app
exec "$PY" -m coding_with_beat app >>"$LOG_DIR/app.log" 2>>"$LOG_DIR/app.err.log"
"""
    path.write_text(text, encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o755)


def _copy_icons(resources: Path) -> None:
    for name in ("waveform_app_icon.svg", "waveform_menu_bar.svg"):
        shutil.copy2(ROOT / "assets" / name, resources / name)
    _write_icns(resources / "CodeBeat.icns")


def _write_icns(path: Path) -> None:
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    images = [_render_waveform_icon(size) for size in sizes]
    images[-1].save(path, format="ICNS", append_images=images[:-1])


def _render_waveform_icon(size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    scale = size / 256

    def box(x: float, y: float, w: float, h: float, radius: float, fill) -> None:
        draw.rounded_rectangle(
            [round(x * scale), round(y * scale), round((x + w) * scale), round((y + h) * scale)],
            radius=max(1, round(radius * scale)),
            fill=fill,
        )

    box(28, 28, 200, 200, 40, (8, 8, 16, 255))
    box(70, 112, 16, 50, 8, (139, 92, 246, 140))
    box(98, 86, 17, 104, 8.5, (139, 92, 246, 195))
    box(119, 62, 18, 132, 9, (139, 92, 246, 255))
    box(141, 86, 17, 104, 8.5, (139, 92, 246, 195))
    box(170, 112, 16, 50, 8, (139, 92, 246, 140))
    return image


def main() -> int:
    app_path = build_app()
    print(app_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
