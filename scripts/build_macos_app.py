#!/usr/bin/env python3
"""Build a local CodeBeat.app wrapper."""

from __future__ import annotations

import json
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
    _write_resource_manifest(resources)
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


def _write_resource_manifest(resources: Path) -> None:
    manifest = {
        "version": 1,
        "appVersion": "0.1.0",
        "resources": {
            "assets": _existing_relative_files(ROOT / "assets", ["waveform_app_icon.svg", "waveform_menu_bar.svg"]),
            "pets": _existing_pet_files(ROOT / "assets" / "pets"),
            "claude": [],
            "codex": [],
            "commands": [],
            "skills": [],
        },
    }
    (resources / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _existing_relative_files(root: Path, names: list[str]) -> list[str]:
    files: list[str] = []
    for name in names:
        if (root / name).exists():
            files.append(f"{root.name}/{name}")
    return files


def _existing_pet_files(root: Path) -> list[str]:
    if not root.exists():
        return []
    files: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            files.append(path.relative_to(root).as_posix())
    return [f"pets/{name}" for name in files]


def _write_icns(path: Path) -> None:
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    images = [_render_waveform_icon(size) for size in sizes]
    images[-1].save(path, format="ICNS", append_images=images[:-1])


def _render_waveform_icon(size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    scale = size / 256
    logo_offset = 32
    logo_scale = 0.96

    def box(x: float, y: float, w: float, h: float, radius: float, fill) -> None:
        draw.rounded_rectangle(
            [round(x * scale), round(y * scale), round((x + w) * scale), round((y + h) * scale)],
            radius=max(1, round(radius * scale)),
            fill=fill,
        )

    def original_box(x: float, y: float, w: float, h: float, radius: float, fill) -> None:
        box(
            logo_offset + x * logo_scale,
            logo_offset + y * logo_scale,
            w * logo_scale,
            h * logo_scale,
            radius * logo_scale,
            fill,
        )

    original_box(0, 0, 200, 200, 32, (8, 8, 16, 255))
    original_box(38, 80, 18, 40, 9, (139, 92, 246, 128))
    original_box(67, 58, 18, 84, 9, (139, 92, 246, 191))
    original_box(91, 30, 18, 140, 9, (139, 92, 246, 255))
    original_box(115, 52, 18, 96, 9, (139, 92, 246, 191))
    original_box(144, 80, 18, 40, 9, (139, 92, 246, 128))
    return image


def main() -> int:
    app_path = build_app()
    print(app_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
