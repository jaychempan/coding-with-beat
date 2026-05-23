#!/usr/bin/env bash
# coding-with-beat one-liner installer for Claude Code.
#
# Usage:
#   curl -LsSf https://raw.githubusercontent.com/jaychempan/coding-with-beat/main/bootstrap.sh | sh
#
# What it does:
#   1. Makes sure git is available.
#   2. Sparse-clones only the files needed for installation into ~/.coding-with-beat/src
#      (skips tests/, docs/, assets/, README files — install-only footprint).
#   3. Runs install.sh, which handles the rest — including bootstrapping
#      Python via uv if your machine doesn't have one.
#
# Override the repo URL with CWB_REPO=... if you've forked it.
set -euo pipefail

REPO_URL="${CWB_REPO:-https://github.com/jaychempan/coding-with-beat.git}"
DEST="${CWB_SRC:-$HOME/.coding-with-beat/src}"

# Only the files install.sh actually needs — nothing else is fetched.
_SPARSE_PATHS=(
  coding_with_beat
  commands
  scripts/install_settings.py
  pyproject.toml
  install.sh
  uninstall.sh
)

if ! command -v git >/dev/null 2>&1; then
  echo "git not found. On macOS, run: xcode-select --install" >&2
  exit 1
fi

mkdir -p "$(dirname "$DEST")"
if [ -d "$DEST/.git" ]; then
  echo "↻ updating coding-with-beat at $DEST"
  git -C "$DEST" checkout -- '*.egg-info/' 2>/dev/null || true
  git -C "$DEST" sparse-checkout set "${_SPARSE_PATHS[@]}"
  git -C "$DEST" pull --ff-only
else
  echo "⤓ cloning coding-with-beat (sparse) into $DEST"
  git clone --depth 1 --filter=blob:none --sparse "$REPO_URL" "$DEST"
  git -C "$DEST" sparse-checkout set "${_SPARSE_PATHS[@]}"
fi

exec bash "$DEST/install.sh" "$@"
