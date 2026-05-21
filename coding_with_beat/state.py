import datetime
import json
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Optional

from .config import DATA_DIR, STATE_FILE, ensure_dirs


@dataclass
class Track:
    title: str = ""
    artist: str = ""
    album: str = ""
    duration: float = 0.0
    position: float = 0.0
    # Wall-clock time `position` was last sampled from the source. Decoupled
    # from `JukeboxState.updated_at` so unrelated saves (hooks, vibe changes)
    # don't poison the extrapolation base used by the statusline.
    position_sampled_at: float = 0.0
    artwork_path: Optional[str] = None
    source: str = ""


@dataclass
class JukeboxState:
    playing: bool = False
    source: str = "apple_music"
    volume: int = 60
    track: Track = field(default_factory=Track)
    vibe: str = "focus"
    dj_mood: str = "neutral"
    focus_active: bool = False
    focus_phase: str = "work"            # work | break
    focus_started_at: float = 0.0
    updated_at: float = 0.0
    dj_quip: str = ""
    dj_quip_at: float = 0.0
    last_tool_at: float = 0.0
    statusline_mode: str = "show"   # show | hide | auto


def load() -> JukeboxState:
    ensure_dirs()
    if not STATE_FILE.exists():
        return JukeboxState()
    try:
        raw = json.loads(STATE_FILE.read_text())
        track = Track(**raw.pop("track", {}))
        return JukeboxState(track=track, **raw)
    except Exception:
        return JukeboxState()


def save(state: JukeboxState) -> None:
    ensure_dirs()
    state.updated_at = time.time()
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(state), ensure_ascii=False, indent=2))
    os.replace(tmp, STATE_FILE)


def write_history(title: str, artist: str, album: str) -> None:
    if not title:
        return
    ensure_dirs()
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"{ts} | {title} | {artist or '?'} | {album or '?'}\n"
    try:
        with open(DATA_DIR / "history.log", "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def update(**fields) -> JukeboxState:
    st = load()
    for k, v in fields.items():
        if k == "track" and isinstance(v, dict):
            for tk, tv in v.items():
                setattr(st.track, tk, tv)
        else:
            setattr(st, k, v)
    save(st)
    return st
