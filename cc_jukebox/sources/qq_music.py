"""QQ Music backend (best-effort).

QQ Music has no AppleScript control on macOS and no official public API.
This backend uses QQ's public search endpoint to fetch metadata + 30-second
previews where available, then plays them via afplay. Full-length playback
of paid tracks requires the QQ Music desktop app (which we cannot script).

Limitations are surfaced in `now_playing()` and tool descriptions so the
LLM/user knows what to expect.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path
from typing import List, Optional

import httpx

from ..config import COVER_CACHE
from .local import LocalFiles, _write, _read, _pid_alive
from .base import NowPlaying


SEARCH_URL = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
HEADERS = {
    "Referer": "https://y.qq.com/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}


class QQMusic(LocalFiles):
    name = "qq_music"

    def __init__(self):
        super().__init__()
        self._client = httpx.Client(headers=HEADERS, timeout=8.0)
        self._last_track: dict = {}

    def _api_search(self, query: str, limit: int) -> List[dict]:
        params = {
            "ct": 24, "qqmusic_ver": 1298, "new_json": 1,
            "remoteplace": "txt.yqq.song", "searchid": 0, "t": 0,
            "aggr": 1, "cr": 1, "catZhida": 1, "lossless": 0,
            "flag_qc": 0, "p": 1, "n": limit, "w": query,
            "format": "json", "inCharset": "utf8", "outCharset": "utf-8",
        }
        try:
            r = self._client.get(SEARCH_URL, params=params)
            data = r.json()
        except Exception:
            return []
        items = (data.get("data", {}).get("song", {}) or {}).get("list", []) or []
        out = []
        for it in items[:limit]:
            singers = ", ".join(s.get("name", "") for s in it.get("singer", []) if s.get("name"))
            out.append({
                "title": it.get("name", ""),
                "artist": singers,
                "album": (it.get("album") or {}).get("name", ""),
                "mid": it.get("mid", ""),
                "albummid": (it.get("album") or {}).get("mid", ""),
            })
        return out

    def _cover_url(self, albummid: str) -> Optional[str]:
        if not albummid:
            return None
        return f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{albummid}.jpg"

    def _download_cover(self, url: str, key: str) -> Optional[str]:
        if not url:
            return None
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
        np = super().now_playing()
        if self._last_track and np.playing:
            np.title = self._last_track.get("title") or np.title
            np.artist = self._last_track.get("artist") or np.artist
            np.album = self._last_track.get("album") or np.album
            np.artwork_path = self._last_track.get("artwork") or np.artwork_path
        np.source = self.name
        return np

    def play_query(self, query: str) -> Optional[NowPlaying]:
        hits = self._api_search(query, limit=1)
        if not hits:
            return None
        h = hits[0]
        artwork = self._download_cover(self._cover_url(h.get("albummid", "")),
                                       key=re.sub(r"\W+", "_", h["title"])[:80])
        # Try preview clip — QQ Music's public preview endpoint format.
        preview = f"https://ws.stream.qqmusic.qq.com/C400{h['mid']}.m4a?fromtag=38"
        # Stage a local file
        tmp = COVER_CACHE.parent / "qq_preview.m4a"
        try:
            r = self._client.get(preview)
            if r.status_code == 200 and r.content:
                tmp.write_bytes(r.content)
            else:
                tmp = None
        except Exception:
            tmp = None
        self._last_track = {
            "title": h["title"], "artist": h["artist"], "album": h["album"],
            "artwork": artwork,
        }
        if tmp and tmp.exists() and tmp.stat().st_size > 1024:
            np = self._start(tmp)
            np.title = h["title"]
            np.artist = h["artist"]
            np.album = h["album"]
            np.artwork_path = artwork
            np.source = self.name
            return np
        # No playable audio — return metadata-only "ghost" now-playing
        return NowPlaying(
            title=h["title"], artist=h["artist"], album=h["album"],
            duration=0, position=0, playing=False,
            artwork_path=artwork, source=self.name,
        )
