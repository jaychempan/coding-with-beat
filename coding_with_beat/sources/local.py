"""Local file backend using afplay (macOS built-in).

State is persisted to ~/.coding-with-beat/local.json so we can resume / show position.
The afplay process runs detached; we read PID + start time to compute position.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import List, Optional

from mutagen import File as MFile

from ..config import COVER_CACHE, DATA_DIR, ensure_dirs
from .base import NowPlaying

LOCAL_STATE = DATA_DIR / "local.json"
DEFAULT_LIBRARY = Path(os.environ.get("CCJ_LOCAL_LIBRARY", Path.home() / "Music"))

# In-memory position checkpoints keyed by path string.
# Avoids disk writes during polling and races with pause()/play() state writes.
_last_known_pos: dict[str, float] = {}


def _read() -> dict:
    if LOCAL_STATE.exists():
        try:
            return json.loads(LOCAL_STATE.read_text())
        except Exception:
            return {}
    return {}


def _write(d: dict) -> None:
    ensure_dirs()
    LOCAL_STATE.write_text(json.dumps(d, ensure_ascii=False, indent=2))


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _extract_artwork(path: Path) -> Optional[str]:
    try:
        m = MFile(str(path))
        if m is None:
            return None
        data = None
        # ID3 (mp3)
        if hasattr(m, "tags") and m.tags:
            for k in m.tags.keys() if hasattr(m.tags, "keys") else []:
                if k.startswith("APIC"):
                    data = m.tags[k].data
                    break
        # FLAC
        if data is None and getattr(m, "pictures", None):
            data = m.pictures[0].data
        # MP4
        if data is None and "covr" in (m.tags or {}):
            covr = m.tags["covr"]
            if covr:
                data = bytes(covr[0])
        if not data:
            sibling = path.parent / "cover.jpg"
            if sibling.exists():
                return str(sibling)
            return None
        out = COVER_CACHE / f"local_{path.stem}.bin"
        out.write_bytes(data)
        return str(out)
    except Exception:
        return None


def _duration(path: Path) -> float:
    try:
        m = MFile(str(path))
        return float(getattr(m.info, "length", 0.0)) if m else 0.0
    except Exception:
        return 0.0


class LocalFiles:
    name = "local"

    def __init__(self, library: Path = DEFAULT_LIBRARY):
        self.library = Path(library)

    def _state(self) -> dict:
        return _read()

    def now_playing(self) -> NowPlaying:
        s = self._state()
        pid = s.get("pid")
        path = s.get("path")
        paused_at = s.get("paused_at")

        if not path:
            return NowPlaying(source=self.name)

        def _info(s: dict, playing: bool) -> NowPlaying:
            p = Path(s["path"])
            started = s.get("started_at", time.time())
            pos_end = s.get("paused_at") or time.time()
            position = pos_end - started - s.get("paused_total", 0)
            return NowPlaying(
                title=p.stem,
                artist=s.get("artist", ""),
                album=p.parent.name,
                duration=s.get("duration", 0.0),
                position=max(0.0, position),
                playing=playing,
                artwork_path=s.get("artwork"),
                source=self.name,
            )

        if pid and _pid_alive(pid):
            np = _info(s, playing=True)
            # Checkpoint in memory only — no disk write to avoid racing with pause()/play().
            _last_known_pos[str(path)] = np.position
            return np

        if paused_at is not None:
            return _info(s, playing=False)

        # Process died — distinguish natural end from mid-song interruption.
        if pid:
            last_pos = _last_known_pos.get(str(path), 0.0)
            dur = float(s.get("duration") or 0.0)
            if dur > 0 and last_pos > 0 and last_pos < dur * 0.95:
                # Interrupted before the song ended; treat as paused at last position.
                s["pid"] = None
                s["paused_at"] = (
                    float(s.get("started_at") or time.time()) + float(s.get("paused_total") or 0.0) + last_pos
                )
                _write(s)
                return _info(s, playing=False)
            # Natural end (or unknown duration) → auto-advance.
            self.next()
            s = self._state()
            pid = s.get("pid")
            if pid and s.get("path") and _pid_alive(pid):
                return _info(s, playing=True)

        return NowPlaying(source=self.name)

    def _stop_current(self) -> None:
        s = self._state()
        pid = s.get("pid")
        if pid and _pid_alive(pid):
            try:
                os.kill(pid, signal.SIGTERM)
            except Exception:
                pass

    def _start(self, path: Path) -> NowPlaying:
        self._stop_current()
        proc = subprocess.Popen(
            ["afplay", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        artwork = _extract_artwork(path)
        dur = _duration(path)
        _write(
            {
                "pid": proc.pid,
                "path": str(path),
                "started_at": time.time(),
                "paused_at": None,
                "paused_total": 0,
                "duration": dur,
                "artwork": artwork,
            }
        )
        return NowPlaying(
            title=path.stem,
            album=path.parent.name,
            duration=dur,
            position=0.0,
            playing=True,
            artwork_path=artwork,
            source=self.name,
        )

    def play(self) -> None:
        s = self._state()
        if s.get("pid") and _pid_alive(s["pid"]):
            return
        if not s.get("path"):
            return
        paused_at = s.get("paused_at")
        if paused_at is not None:
            # Resume from the saved position by adjusting started_at backward.
            # afplay always plays from file position 0, so audio restarts, but
            # the computed position (now - started_at - paused_total) is correct.
            started = s.get("started_at", paused_at)
            paused_total = float(s.get("paused_total") or 0.0)
            resume_pos = max(0.0, paused_at - started - paused_total)
            proc = subprocess.Popen(
                ["afplay", str(s["path"])],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            s["pid"] = proc.pid
            s["started_at"] = time.time() - resume_pos
            s["paused_at"] = None
            s["paused_total"] = 0.0
            _write(s)
        else:
            self._start(Path(s["path"]))

    def pause(self) -> None:
        # afplay has no real pause; we kill + remember position
        s = self._state()
        pid = s.get("pid")
        if pid and _pid_alive(pid):
            try:
                os.kill(pid, signal.SIGTERM)
            except Exception:
                pass
            s["paused_at"] = time.time()
            s["pid"] = None
            _write(s)

    def toggle(self) -> None:
        s = self._state()
        if s.get("pid") and _pid_alive(s["pid"]):
            self.pause()
        else:
            self.play()

    def next(self) -> None:
        files = self._scan()
        if not files:
            return
        cur = self._state().get("path")
        idx = 0
        if cur:
            try:
                idx = (files.index(Path(cur)) + 1) % len(files)
            except ValueError:
                idx = 0
        self._start(files[idx])

    def prev(self) -> None:
        files = self._scan()
        if not files:
            return
        cur = self._state().get("path")
        idx = 0
        if cur:
            try:
                idx = (files.index(Path(cur)) - 1) % len(files)
            except ValueError:
                idx = 0
        self._start(files[idx])

    def seek(self, seconds: float) -> None:
        # afplay can't seek; best-effort restart with -t skipping
        s = self._state()
        path = s.get("path")
        if not path:
            return
        self._stop_current()
        proc = subprocess.Popen(
            ["afplay", "-t", "9999", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        s["pid"] = proc.pid
        s["started_at"] = time.time() - max(0.0, float(seconds))
        s["paused_at"] = None
        _write(s)

    def set_volume(self, percent: int) -> None:
        # macOS system volume; afplay has no per-process volume
        p = max(0, min(100, int(percent)))
        subprocess.run(
            ["osascript", "-e", f"set volume output volume {p}"],
            capture_output=True,
        )

    def like_current(self) -> bool:
        raise NotImplementedError("local source does not support liking tracks")

    def set_play_mode(self, mode: str) -> bool:
        raise NotImplementedError("local source does not support play modes")

    def _scan(self) -> List[Path]:
        if not self.library.exists():
            return []
        exts = {".mp3", ".m4a", ".flac", ".wav", ".aac", ".ogg"}
        out = []
        for root, _, files in os.walk(self.library):
            for f in files:
                if Path(f).suffix.lower() in exts:
                    out.append(Path(root) / f)
        out.sort()
        return out

    def search(self, query: str, limit: int = 8) -> List[dict]:
        q = query.lower()
        results = []
        for p in self._scan():
            hay = f"{p.stem} {p.parent.name}".lower()
            if q in hay:
                results.append({"title": p.stem, "artist": "", "album": p.parent.name, "path": str(p)})
                if len(results) >= limit:
                    break
        return results

    def play_query(self, query: str, library_only: bool = False) -> Optional[NowPlaying]:
        hits = self.search(query, limit=1)
        if not hits:
            return None
        return self._start(Path(hits[0]["path"]))
