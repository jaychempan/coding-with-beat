#!/usr/bin/env bash
# coding-with-beat one-liner installer for Codex CLI.
#
# Usage:
#   curl -LsSf https://raw.githubusercontent.com/jaychempan/coding-with-beat/main/bootstrap_codex.sh | sh
#
# What it does:
#   1. Makes sure git is available.
#   2. Clones coding-with-beat into ~/.coding-with-beat/src (or pulls if already there).
#   3. Runs install_codex.sh, which handles the rest.
#
# Override the repo URL with CWB_REPO=... if you've forked it.
set -euo pipefail

REPO_URL="${CWB_REPO:-https://github.com/jaychempan/coding-with-beat.git}"
DEST="${CWB_SRC:-$HOME/.coding-with-beat/src}"

if ! command -v git >/dev/null 2>&1; then
  echo "git not found. On macOS, run: xcode-select --install" >&2
  exit 1
fi

mkdir -p "$(dirname "$DEST")"
if [ -d "$DEST/.git" ]; then
  echo "↻ updating coding-with-beat at $DEST"
  git -C "$DEST" checkout -- '*.egg-info/' 2>/dev/null || true
  git -C "$DEST" pull --ff-only
else
  echo "⤓ cloning coding-with-beat into $DEST"
  git clone --depth 1 "$REPO_URL" "$DEST"
fi

exec bash "$DEST/install_codex.sh" "$@"
