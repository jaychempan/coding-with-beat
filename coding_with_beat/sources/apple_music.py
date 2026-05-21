"""Apple Music backend via AppleScript on macOS.

Does NOT require Music.app to be foregrounded; osascript launches it headless
if needed. Subscribed library + local library both work.
"""
from __future__ import annotations

import base64
import re
import subprocess
import urllib.parse
from pathlib import Path
from typing import List, Optional

from ..config import COVER_CACHE, LYRICS_CACHE
from .base import NowPlaying


_NETEASE_HEADERS = {
    "Referer": "https://music.163.com/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}


def _lrclib_lyrics(title: str, artist: str, album: str, duration: float) -> Optional[str]:
    """Query lrclib.net for synced (LRC) or plain lyrics. Fully open public API."""
    try:
        import httpx
    except ImportError:
        return None
    params: dict = {"track_name": title, "artist_name": artist}
    if album:
        params["album_name"] = album
    if duration > 0:
        params["duration"] = int(duration)
    try:
        with httpx.Client(timeout=6.0, trust_env=False) as c:
            r = c.get(
                "https://lrclib.net/api/get",
                params=params,
                headers={"Lrclib-Client": "coding-with-beat/1.0"},
            )
            if r.status_code != 200:
                return None
            data = r.json()
            synced = (data.get("syncedLyrics") or "").strip()
            if synced:
                return synced
            plain = (data.get("plainLyrics") or "").strip()
            return plain or None
    except Exception:
        return None


def _netease_lyrics(title: str, artist: str) -> Optional[str]:
    """Best-effort lookup against NetEase's public search+lyric endpoints.
    Returns LRC text (with [mm:ss.xx] timestamps) when found, else None.
    Used as a fallback because AppleScript can't read lyrics for Apple Music
    catalog/streaming tracks."""
    try:
        import httpx
    except ImportError:
        return None
    q = urllib.parse.quote(f"{title} {artist}".strip())
    with httpx.Client(headers=_NETEASE_HEADERS, timeout=6.0) as c:
        try:
            r = c.get(
                f"https://music.163.com/api/search/get/?s={q}&type=1&limit=5"
            )
            data = r.json()
            songs = (data.get("result") or {}).get("songs") or []
            if not songs:
                return None
            song_id = songs[0].get("id")
            if not song_id:
                return None
            r2 = c.get(
                f"https://music.163.com/api/song/lyric?id={song_id}&lv=-1&kv=-1&tv=-1"
            )
            d2 = r2.json()
            lrc = (d2.get("lrc") or {}).get("lyric") or ""
            return lrc or None
        except Exception:
            return None


_SCRIPT_NOW = '''
tell application "Music"
    if it is running then
        set SEP to (ASCII character 31)
        set s to player state as string
        if exists current track then
            set t to current track
            set tName to name of t as string
            set tArtist to artist of t as string
            set tAlbum to album of t as string
            set tDur to (duration of t) as string
            set tPos to (player position) as string
            return tName & SEP & tArtist & SEP & tAlbum & SEP & tDur & SEP & tPos & SEP & s
        else
            return SEP & SEP & SEP & "0" & SEP & "0" & SEP & s
        end if
    else
        return "__not_running__"
    end if
end tell
'''

_SCRIPT_ARTWORK = '''
tell application "Music"
    if exists current track then
        set artData to (raw data of artwork 1 of current track) as «class PNG »
        return artData
    end if
end tell
'''


def _osa(script: str) -> str:
    p = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=8,
    )
    if p.returncode != 0:
        raise RuntimeError(f"AppleScript failed: {p.stderr.strip()}")
    return p.stdout.strip()


def _osa_silent(script: str) -> None:
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=8)
    except Exception:
        pass


def _play_local_match(query: str) -> bool:
    q = query.replace('"', '\\"')
    script = f'''
tell application "Music"
    set candidates to (every track of library playlist 1 whose name contains "{q}" or artist contains "{q}")
    if (count of candidates) > 0 then
        play item 1 of candidates
        return "ok"
    end if
    return "none"
end tell
'''
    try:
        return _osa(script) == "ok"
    except Exception:
        return False


def _play_local_tokens(tokens: List[str]) -> bool:
    conds = []
    for t in tokens:
        te = t.replace('"', '\\"')
        conds.append(f'(name contains "{te}" or artist contains "{te}")')
    where = " and ".join(conds)
    script = f'''
tell application "Music"
    set candidates to (every track of library playlist 1 whose {where})
    if (count of candidates) > 0 then
        play item 1 of candidates
        return "ok"
    end if
    return "none"
end tell
'''
    try:
        return _osa(script) == "ok"
    except Exception:
        return False


_CATALOG_STOREFRONTS = ("cn", "jp", "us", "hk", "tw")

# Descriptive suffixes that confuse iTunes Search (it does literal substring
# matching on title/artist, not semantic search). When a query ends with one
# of these we retry once with it stripped.
_CATALOG_NOISE_SUFFIXES = (
    "主题曲", "主题歌", "片头曲", "片尾曲", "插曲", "主题",
    "OST", "BGM", "OP", "ED", "原声", "原声带",
)


def _catalog_query_variants(query: str):
    """Yield search-term variants to try in order. Original first, then
    progressively stripped of trailing descriptive modifiers."""
    yield query
    q = query.strip()
    for suffix in _CATALOG_NOISE_SUFFIXES:
        if q.endswith(suffix) and len(q) > len(suffix):
            stripped = q[: -len(suffix)].strip()
            if stripped and stripped != query:
                yield stripped


def _play_catalog(query: str) -> bool:
    """Hit Apple's public iTunes Search API and ask Music.app to open the top
    song hit. Tries multiple storefronts because the default US store often
    misses CJK catalog entries. Returns True iff playback actually started
    (Music.app reports 'playing' afterwards). If a song was found but Music
    couldn't play it (typical when no Apple Music subscription), prints a
    diagnostic to stderr and returns False."""
    import sys, time
    try:
        import httpx
    except ImportError:
        return False
    hit = None
    storefront = "us"
    try:
        with httpx.Client(timeout=6.0) as c:
            for term in _catalog_query_variants(query):
                for sf in _CATALOG_STOREFRONTS:
                    try:
                        r = c.get(
                            "https://itunes.apple.com/search",
                            params={"term": term, "entity": "song", "limit": 1, "country": sf},
                        )
                        data = r.json()
                    except Exception:
                        continue
                    hits = data.get("results") or []
                    if hits and hits[0].get("trackId"):
                        hit = hits[0]
                        storefront = sf
                        break
                if hit:
                    break
    except Exception:
        return False
    if not hit:
        return False
    tid = hit["trackId"]
    title = hit.get("trackName") or "?"
    artist = hit.get("artistName") or "?"
    url = f"https://music.apple.com/{storefront}/song/{tid}"
    _osa_silent(f'tell application "Music" to open location "{url}"')
    time.sleep(1.4)
    _osa_silent('tell application "Music" to play')
    time.sleep(0.6)
    try:
        state = _osa('tell application "Music" to get player state as text')
    except Exception:
        state = ""
    # When no Apple Music subscription, Music.app enters a degenerate state:
    # player_state may read 'playing' but the "current track" is just a stub
    # whose name is the numeric storeID and whose artist is empty. Detect
    # that and report honest failure.
    current_name = ""
    try:
        current_name = _osa('tell application "Music" to get name of current track')
    except Exception:
        pass
    real_playback = (state == "playing" and current_name and current_name != str(tid))
    if real_playback:
        return True
    # Stop the stub playback so the player doesn't keep "playing" garbage.
    _osa_silent('tell application "Music" to stop')
    print(
        f"! catalog hit: {title} — {artist} ({url})\n"
        f"  Music.app couldn't actually play it — "
        f"this almost always means no active Apple Music subscription, "
        f"or you're not signed in with the subscribing Apple ID.\n"
        f"  Add the song to your library manually, or pick something local.",
        file=sys.stderr,
    )
    return False


class AppleMusic:
    name = "apple_music"

    def now_playing(self) -> NowPlaying:
        try:
            raw = _osa(_SCRIPT_NOW)
        except Exception:
            return NowPlaying(source=self.name)
        if raw == "__not_running__" or not raw:
            return NowPlaying(source=self.name)
        parts = raw.split("\x1f")
        if len(parts) < 6:
            return NowPlaying(source=self.name)
        title, artist, album, dur, pos, state = parts[:6]
        playing = state.strip().lower() == "playing"
        try:
            duration = float(dur or 0)
            position = float(pos or 0)
        except ValueError:
            duration, position = 0.0, 0.0
        np = NowPlaying(
            title=title, artist=artist, album=album,
            duration=duration, position=position,
            playing=playing, source=self.name,
        )
        np.artwork_path = self._fetch_artwork(title, artist, album)
        return np

    def _fetch_artwork(self, title: str, artist: str, album: str) -> Optional[str]:
        if not (title or album):
            return None
        key = re.sub(r"[^a-zA-Z0-9]+", "_", f"{artist}_{album}_{title}").strip("_")[:120]
        out = COVER_CACHE / f"am_{key}.png"
        if out.exists():
            return str(out)
        # Apple Music returns artwork in « class PNG » format; osascript returns bytes.
        # Easier path: shell out to use `osascript` to write the file directly.
        script = f'''
tell application "Music"
    if exists current track then
        try
            set artData to raw data of artwork 1 of current track
            set f to open for access POSIX file "{out}" with write permission
            set eof of f to 0
            write artData to f
            close access f
            return "ok"
        on error
            try
                close access POSIX file "{out}"
            end try
            return "err"
        end try
    else
        return "no_track"
    end if
end tell
'''
        try:
            r = _osa(script)
            if r == "ok" and out.exists() and out.stat().st_size > 0:
                return str(out)
        except Exception:
            return None
        return None

    def play(self) -> None: _osa_silent('tell application "Music" to play')
    def pause(self) -> None: _osa_silent('tell application "Music" to pause')
    def toggle(self) -> None: _osa_silent('tell application "Music" to playpause')
    def next(self) -> None: _osa_silent('tell application "Music" to next track')
    def prev(self) -> None: _osa_silent('tell application "Music" to previous track')

    def seek(self, seconds: float) -> None:
        _osa_silent(f'tell application "Music" to set player position to {float(seconds)}')

    def set_volume(self, percent: int) -> None:
        p = max(0, min(100, int(percent)))
        _osa_silent(f'tell application "Music" to set sound volume to {p}')

    def like_current(self) -> bool:
        script = '''
tell application "Music"
    if not (exists current track) then return "no_track"
    set favorited of current track to true
    return "ok"
end tell
'''
        try:
            return _osa(script) == "ok"
        except Exception:
            return False

    def set_play_mode(self, mode: str) -> bool:
        normalized = (mode or "").lower().replace("-", "_")
        if normalized in ("shuffle", "random"):
            script = '''
tell application "Music"
    set shuffle enabled to true
    set song repeat to off
    return "ok"
end tell
'''
        elif normalized in ("sequential", "sequence", "normal", "off"):
            script = '''
tell application "Music"
    set shuffle enabled to false
    set song repeat to off
    return "ok"
end tell
'''
        elif normalized in ("repeat", "loop", "repeat_all", "all"):
            script = '''
tell application "Music"
    set shuffle enabled to false
    set song repeat to all
    return "ok"
end tell
'''
        elif normalized in ("repeat_one", "one", "single"):
            script = '''
tell application "Music"
    set shuffle enabled to false
    set song repeat to one
    return "ok"
end tell
'''
        else:
            raise NotImplementedError(f"unsupported Apple Music play mode: {mode}")
        try:
            return _osa(script) == "ok"
        except Exception:
            return False

    def search(self, query: str, limit: int = 8) -> List[dict]:
        q = query.replace('"', '\\"')
        script = f'''
tell application "Music"
    set SEP to (ASCII character 31)
    set out to ""
    set results to (every track of library playlist 1 whose name contains "{q}" or artist contains "{q}" or album contains "{q}")
    set n to count of results
    if n > {limit} then set n to {limit}
    repeat with i from 1 to n
        set t to item i of results
        set out to out & (name of t as string) & SEP & (artist of t as string) & SEP & (album of t as string) & linefeed
    end repeat
    return out
end tell
'''
        try:
            raw = _osa(script)
        except Exception:
            return []
        items = []
        for line in raw.splitlines():
            if not line.strip():
                continue
            parts = line.split("\x1f")
            if len(parts) >= 3:
                items.append({"title": parts[0], "artist": parts[1], "album": parts[2]})
        return items

    def lyrics(self) -> Optional[str]:
        """Static lyrics for the current track via AppleScript. Synced timing
        isn't reliably exposed, so callers should estimate the current line
        from position/duration."""
        script = '''
tell application "Music"
    if not (exists current track) then return "__no_track__"
    try
        set L to lyrics of current track
        if L is missing value then return ""
        return L as string
    on error
        return ""
    end try
end tell
'''
        np = self.now_playing()
        if not np.title:
            return None
        key = re.sub(r"[^a-zA-Z0-9一-鿿]+", "_",
                     f"{np.artist}_{np.album}_{np.title}").strip("_")[:160]
        cache = LYRICS_CACHE / f"am_{key}.txt"
        if cache.exists():
            txt = cache.read_text(encoding="utf-8")
            if txt.strip():
                return txt
        try:
            raw = _osa(script)
        except Exception:
            raw = ""
        if raw == "__no_track__":
            return None
        if not raw.strip():
            raw = _lrclib_lyrics(np.title, np.artist or "", np.album or "", np.duration) or ""
        if not raw.strip():
            raw = _netease_lyrics(np.title, np.artist) or ""
        if not raw.strip():
            return None
        cache.write_text(raw, encoding="utf-8")
        return raw

    def play_query(self, query: str) -> Optional[NowPlaying]:
        """Three-tier search:
          1. Full-string substring match in local library (fast).
          2. If query has multiple whitespace-separated tokens, AND-match each
             token against name OR artist (so '青花瓷 周杰伦' matches a track
             named 青花瓷 by 周杰伦 even though no single field contains the
             whole string).
          3. Fall back to the public iTunes Search API and ask Music to open
             the top hit's catalog URL. Requires an active Apple Music
             subscription for actual playback.
        """
        if _play_local_match(query):
            return self.now_playing()
        tokens = [t for t in query.split() if t.strip()]
        if len(tokens) > 1 and _play_local_tokens(tokens):
            return self.now_playing()
        if _play_catalog(query):
            import time
            time.sleep(0.6)
            return self.now_playing()
        return None
