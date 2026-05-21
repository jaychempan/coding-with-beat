import os
from pathlib import Path

HOME = Path.home()
DATA_DIR = HOME / ".coding-with-beat"
STATE_FILE = DATA_DIR / "state.json"
PROJECTS_DIR = DATA_DIR / "projects"
LOG_FILE = DATA_DIR / "cwb.log"
COVER_CACHE = DATA_DIR / "covers"
LYRICS_CACHE = DATA_DIR / "lyrics"
MCP_URL_FILE = DATA_DIR / "mcp-url"

DEFAULT_SOURCE = os.environ.get("CWB_SOURCE", "apple_music")

GAMEBOY_PALETTE = [(15, 56, 15), (48, 98, 48), (139, 172, 15), (155, 188, 15)]

VIBE_GENRES = {
    "focus":   ["lofi", "ambient", "post-rock"],
    "build":   ["synthwave", "electronic", "upbeat"],
    "debug":   ["dark ambient", "tense"],
    "victory": ["chiptune", "j-pop", "celebration"],
    "fail":    ["sad piano", "blues"],
    "idle":    ["lofi", "jazz"],
    "review":  ["classical", "acoustic"],
}

FILE_KIND_VIBES = {
    "sql":      "focus",
    "py":       "build",
    "ts":       "build",
    "tsx":      "build",
    "js":       "build",
    "jsx":      "build",
    "go":       "build",
    "rs":       "build",
    "md":       "review",
    "yaml":     "review",
    "yml":      "review",
    "json":     "review",
    "toml":     "review",
}


def ensure_dirs() -> None:
    for d in (DATA_DIR, PROJECTS_DIR, COVER_CACHE, LYRICS_CACHE):
        d.mkdir(parents=True, exist_ok=True)
