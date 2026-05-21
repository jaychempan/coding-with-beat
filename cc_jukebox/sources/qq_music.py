"""QQ Music backend (best-effort).

QQ Music has no AppleScript dictionary on macOS and no stable public consumer
playback API. This backend therefore has two layers:

1. Stable-ish metadata/search/preview playback. Search uses QQ Music's public
   web endpoint, cover art is cached, and playable previews are handed to
   afplay through the local-file backend.
2. Semi-stable desktop controls. The QQMusic app exposes a "播放控制" menu, so
   we can click play/pause/next/etc. through System Events when the user has
   granted Accessibility automation permissions. This cannot read the current
   QQMusic track or play arbitrary search results in the desktop app.
"""
from __future__ import annotations

import base64
import html
import json
import re
import subprocess
import time
from pathlib import Path
from typing import List, Optional

import httpx

from ..config import COVER_CACHE, DATA_DIR, LOG_FILE, LYRICS_CACHE, ensure_dirs
from .apple_music import _netease_lyrics
from .local import LocalFiles, _write, _read, _pid_alive
from .base import NowPlaying, unsupported_now_playing


SEARCH_URL = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
LYRIC_URL = "https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg"
QQ_STATE = DATA_DIR / "qq_music.json"
PREVIEW_FILE = DATA_DIR / "qq_preview.m4a"
QQ_BUNDLE_ID = "com.tencent.QQMusicMac"
QQ_PROCESS = "QQMusic"
QQ_PLAY_MENU = "播放控制"
UNSUPPORTED_NOW_PLAYING = (
    "qq_music cannot read the QQMusic desktop client's current track/state. "
    "Only cc-jukebox QQ preview playback can report now-playing."
)
UNSUPPORTED_FULL_PLAYBACK = (
    "qq_music can search QQ Music metadata, but cannot ask the QQMusic desktop "
    "client to play an arbitrary query or stream the full catalog. No playable "
    "preview was available for this result."
)
HEADERS = {
    "Referer": "https://y.qq.com/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}


def _query_variants(query: str) -> List[str]:
    q = query.strip()
    variants = [q] if q else []
    parts = [p for p in re.split(r"\s+", q) if p]
    if len(parts) > 1:
        variants.extend(parts)
        variants.append(" ".join(parts[:-1]))
    seen = set()
    out = []
    for item in variants:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _hit_score(hit: dict, query: str) -> int:
    tokens = [p.lower() for p in re.split(r"\s+", query.strip()) if p]
    hay = f"{hit.get('title', '')} {hit.get('artist', '')} {hit.get('album', '')}".lower()
    return sum(1 for token in tokens if token in hay)


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


def _log(msg: str) -> None:
    try:
        ensure_dirs()
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} qq_music {msg}\n")
    except Exception:
        pass


def _read_qq_state() -> dict:
    if QQ_STATE.exists():
        try:
            return json.loads(QQ_STATE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _write_qq_state(data: dict) -> None:
    ensure_dirs()
    QQ_STATE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _script_quote(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def _run_osascript(script: str, timeout: float = 8.0) -> bool:
    try:
        p = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=timeout,
        )
    except Exception as e:
        _log(f"osascript exception: {e}")
        return False
    if p.returncode != 0:
        _log(f"osascript failed: {p.stderr.strip() or p.stdout.strip()}")
        return False
    return True


def _decode_qq_lyric(value: str) -> str:
    if not value:
        return ""
    text = value.strip()
    try:
        compact = "".join(text.split())
        text = base64.b64decode(compact, validate=True).decode("utf-8", errors="replace")
    except Exception:
        pass
    return html.unescape(text).replace("\r\n", "\n").strip()


def _valid_audio_file(path: Path) -> bool:
    try:
        if not path.exists() or path.stat().st_size <= 2048:
            return False
        with path.open("rb") as f:
            head = f.read(64).lstrip()
        return not (head.startswith(b"{") or head.startswith(b"<"))
    except Exception:
        return False


class QQMusic(LocalFiles):
    name = "qq_music"

    def __init__(self):
        super().__init__()
        self._client = httpx.Client(headers=HEADERS, timeout=8.0)

    def _save_track(self, track: dict, artwork: Optional[str], mode: str) -> None:
        _write_qq_state({
            "track": {
                "title": track.get("title", ""),
                "artist": track.get("artist", ""),
                "album": track.get("album", ""),
                "mid": track.get("mid", ""),
                "albummid": track.get("albummid", ""),
                "duration": _to_float(track.get("duration")),
                "artwork": artwork,
            },
            "mode": mode,
            "updated_at": time.time(),
        })

    def _current_track(self) -> dict:
        return (_read_qq_state().get("track") or {})

    def _state_mode(self) -> str:
        return str(_read_qq_state().get("mode") or "")

    def _normalize_hit(self, it: dict) -> dict:
        album = it.get("album") or {}
        singers = ", ".join(s.get("name", "") for s in it.get("singer", []) if s.get("name"))
        title = it.get("name") or it.get("title") or it.get("songname") or ""
        mid = it.get("mid") or it.get("songmid") or ""
        return {
            "title": title,
            "artist": singers,
            "album": album.get("name") or it.get("albumname", ""),
            "mid": mid,
            "media_mid": it.get("media_mid") or it.get("strMediaMid") or "",
            "albummid": album.get("mid") or it.get("albummid", ""),
            "duration": _to_float(it.get("interval")),
            "url": f"https://y.qq.com/n/ryqq/songDetail/{mid}" if mid else "",
        }

    def _api_search_once(self, query: str, limit: int, *, new_json: bool) -> List[dict]:
        params = {
            "ct": 24, "qqmusic_ver": 1298,
            "remoteplace": "txt.yqq.song", "searchid": 0, "t": 0,
            "aggr": 1, "cr": 1, "catZhida": 1, "lossless": 0,
            "flag_qc": 0, "p": 1, "n": limit, "w": query,
            "format": "json", "inCharset": "utf8", "outCharset": "utf-8",
        }
        if new_json:
            params["new_json"] = 1
        try:
            r = self._client.get(SEARCH_URL, params=params)
            data = r.json()
        except Exception:
            return []
        items = (data.get("data", {}).get("song", {}) or {}).get("list", []) or []
        return [self._normalize_hit(it) for it in items[:limit]]

    def _api_search(self, query: str, limit: int) -> List[dict]:
        hits = []
        seen = set()
        for variant in _query_variants(query):
            for new_json in (True, False):
                for hit in self._api_search_once(variant, limit, new_json=new_json):
                    key = hit.get("mid") or f"{hit.get('title')}::{hit.get('artist')}"
                    if key in seen:
                        continue
                    seen.add(key)
                    hits.append(hit)
            if len(hits) >= limit and _hit_score(hits[0], query) > 0:
                break
        hits.sort(key=lambda h: _hit_score(h, query), reverse=True)
        return hits[:limit]

    def _cover_url(self, albummid: str) -> Optional[str]:
        if not albummid:
            return None
        return f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{albummid}.jpg"

    def _download_cover(self, url: str, key: str) -> Optional[str]:
        if not url:
            return None
        ensure_dirs()
        out = COVER_CACHE / f"qq_{key}.jpg"
        if out.exists():
            return str(out)
        try:
            r = self._client.get(url)
            if r.status_code == 200 and r.content:
                out.write_bytes(r.content)
                return str(out)
        except Exception:
            return None
        return None

    def search(self, query: str, limit: int = 8) -> List[dict]:
        return self._api_search(query, limit)

    def now_playing(self) -> NowPlaying:
        np = super().now_playing() if self._preview_selected() else NowPlaying(source=self.name)
        track = self._current_track()
        if track and (np.playing or np.title):
            np.title = track.get("title") or np.title
            np.artist = track.get("artist") or np.artist
            np.album = track.get("album") or np.album
            np.duration = np.duration or track.get("duration") or 0.0
            np.artwork_path = track.get("artwork") or np.artwork_path
        elif track and self._state_mode() == "preview":
            np = NowPlaying(
                title=track.get("title", ""),
                artist=track.get("artist", ""),
                album=track.get("album", ""),
                duration=_to_float(track.get("duration")),
                position=0.0,
                playing=False,
                artwork_path=track.get("artwork"),
                source=self.name,
            )
        else:
            return unsupported_now_playing(self.name, UNSUPPORTED_NOW_PLAYING)
        np.source = self.name
        return np

    def _mark_local_preview(self) -> None:
        s = _read()
        s["source"] = self.name
        _write(s)

    def play_query(self, query: str) -> Optional[NowPlaying]:
        hits = self._api_search(query, limit=1)
        if not hits:
            return None
        h = hits[0]
        artwork = self._download_cover(self._cover_url(h.get("albummid", "")),
                                       key=re.sub(r"\W+", "_", h["title"])[:80])
        # Try preview clip — QQ Music's public preview endpoint format.
        stream_mid = h.get("media_mid") or h.get("mid")
        preview = f"https://ws.stream.qqmusic.qq.com/C400{stream_mid}.m4a?fromtag=38"
        # Stage a local file
        tmp = PREVIEW_FILE
        try:
            r = self._client.get(preview)
            if r.status_code == 200 and r.content:
                tmp.write_bytes(r.content)
            else:
                tmp = None
        except Exception:
            tmp = None
        self._save_track(h, artwork, mode="preview")
        if tmp and _valid_audio_file(tmp):
            np = self._start(tmp)
            self._mark_local_preview()
            np.title = h["title"]
            np.artist = h["artist"]
            np.album = h["album"]
            np.duration = np.duration or h.get("duration") or 0.0
            np.artwork_path = artwork
            np.source = self.name
            return np
        # No playable audio: cache metadata for lyrics/artwork lookup, but do
        # not surface it as now-playing. QQMusic desktop state is not readable.
        self._save_track(h, artwork, mode="metadata_only")
        return unsupported_now_playing(self.name, UNSUPPORTED_FULL_PLAYBACK)

    def lyrics(self) -> Optional[str]:
        track = self._current_track()
        title = track.get("title", "")
        artist = track.get("artist", "")
        album = track.get("album", "")
        if not title:
            return None
        key = re.sub(
            r"[^a-zA-Z0-9一-鿿]+", "_",
            track.get("mid") or f"{artist}_{album}_{title}",
        ).strip("_")[:160]
        cache = LYRICS_CACHE / f"qq_{key}.txt"
        if cache.exists():
            text = cache.read_text(encoding="utf-8")
            if text.strip():
                return text

        text = ""
        mid = track.get("mid")
        if mid:
            params = {
                "songmid": mid,
                "pcachetime": int(time.time() * 1000),
                "g_tk": 5381,
                "loginUin": 0,
                "hostUin": 0,
                "format": "json",
                "inCharset": "utf8",
                "outCharset": "utf-8",
                "notice": 0,
                "platform": "yqq",
                "needNewCode": 0,
            }
            try:
                r = self._client.get(LYRIC_URL, params=params)
                data = r.json()
                text = _decode_qq_lyric(data.get("lyric", ""))
            except Exception:
                text = ""
        if not text:
            text = _netease_lyrics(title, artist) or ""
        if not text.strip():
            return None
        cache.write_text(text, encoding="utf-8")
        return text

    def _desktop_menu_item(self, item: str | int) -> bool:
        target = (
            f"menu item {item}"
            if isinstance(item, int)
            else f'menu item "{_script_quote(item)}"'
        )
        menu = _script_quote(QQ_PLAY_MENU)
        process = _script_quote(QQ_PROCESS)
        script = f'''
tell application id "{QQ_BUNDLE_ID}" to activate
delay 0.2
tell application "System Events"
    if not (exists process "{process}") then return "qqmusic_not_running"
    tell process "{process}"
        set frontmost to true
        tell menu "{menu}" of menu bar item "{menu}" of menu bar 1
            click {target}
        end tell
    end tell
end tell
'''
        return _run_osascript(script)

    def _desktop_play_mode(self, index: int) -> bool:
        menu = _script_quote(QQ_PLAY_MENU)
        process = _script_quote(QQ_PROCESS)
        script = f'''
tell application id "{QQ_BUNDLE_ID}" to activate
delay 0.2
tell application "System Events"
    if not (exists process "{process}") then return "qqmusic_not_running"
    tell process "{process}"
        set frontmost to true
        tell menu "{menu}" of menu bar item "{menu}" of menu bar 1
            click menu item {index} of menu 1 of menu item 7
        end tell
    end tell
end tell
'''
        return _run_osascript(script)

    def _preview_active(self) -> bool:
        s = _read()
        pid = s.get("pid")
        path = s.get("path")
        return bool(
            s.get("source") == self.name
            and path == str(PREVIEW_FILE)
            and pid
            and _pid_alive(pid)
        )

    def _preview_selected(self) -> bool:
        s = _read()
        return bool(s.get("source") == self.name and s.get("path") == str(PREVIEW_FILE))

    def play(self) -> None:
        if self._preview_selected():
            super().play()
            self._mark_local_preview()
            return
        self._desktop_menu_item("播放")

    def pause(self) -> None:
        if self._preview_selected():
            super().pause()
            return
        self._desktop_menu_item("暂停")

    def toggle(self) -> None:
        if self._preview_selected():
            super().toggle()
            self._mark_local_preview()
            return
        self._desktop_menu_item(1)

    def next(self) -> None:
        self._desktop_menu_item("下一首")

    def prev(self) -> None:
        self._desktop_menu_item("上一首")

    def seek(self, seconds: float) -> None:
        if self._preview_active():
            super().seek(seconds)

    def set_volume(self, percent: int) -> None:
        # QQMusic only exposes step volume controls in its menu. Use a coarse
        # approximation so the shared set_volume tool has visible behavior.
        p = max(0, min(100, int(percent)))
        if p == 0:
            self._desktop_menu_item("静音")
            return
        current = int(_read_qq_state().get("volume_hint", 50))
        if p == current:
            return
        step = "音量加" if p > current else "音量减"
        count = max(1, min(10, abs(p - current) // 10))
        ok = True
        for _ in range(count):
            ok = self._desktop_menu_item(step) and ok
        if not ok:
            return
        data = _read_qq_state()
        data["volume_hint"] = p
        data["updated_at"] = time.time()
        _write_qq_state(data)

    def like_current(self) -> bool:
        return self._desktop_menu_item("喜欢歌曲")

    def toggle_lyrics_panel(self) -> bool:
        return self._desktop_menu_item(8)

    def set_play_mode(self, mode: str) -> bool:
        modes = {
            "shuffle": 1,
            "random": 1,
            "sequential": 3,
            "sequence": 3,
            "normal": 3,
            "off": 3,
            "repeat": 2,
            "loop": 2,
        }
        normalized = (mode or "").lower().replace("-", "_")
        idx = modes.get(normalized)
        if not idx:
            raise NotImplementedError(f"unsupported QQMusic play mode: {mode}")
        ok = self._desktop_play_mode(idx)
        if ok:
            self._desktop_menu_item("播放")
        return ok
