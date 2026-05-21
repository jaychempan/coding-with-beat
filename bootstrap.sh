#!/usr/bin/env bash
# cc-jukebox one-liner installer.
#
# Usage:
#   curl -LsSf https://raw.githubusercontent.com/jaychempan/cc-jukebox/main/bootstrap.sh | sh
#
# What it does:
#   1. Makes sure git is available.
#   2. Clones cc-jukebox into ~/.cc-jukebox/src (or pulls if it's already there).
#   3. Runs install.sh, which handles the rest — including bootstrapping a
#      Python via uv if your machine doesn't have one.
#
# Override the repo URL with CC_JUKEBOX_REPO=... if you've forked it.
set -euo pipefail

REPO_URL="${CC_JUKEBOX_REPO:-https://github.com/jaychempan/cc-jukebox.git}"
DEST="${CC_JUKEBOX_SRC:-$HOME/.cc-jukebox/src}"

if ! command -v git >/dev/null 2>&1; then
  echo "git not found. On macOS, run: xcode-select --install" >&2
  exit 1
fi

mkdir -p "$(dirname "$DEST")"
if [ -d "$DEST/.git" ]; then
  echo "↻ updating cc-jukebox at $DEST"
  git -C "$DEST" pull --ff-only
else
  echo "⤓ cloning cc-jukebox into $DEST"
  git clone --depth 1 "$REPO_URL" "$DEST"
fi

exec bash "$DEST/install.sh"
