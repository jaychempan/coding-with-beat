"""Apple Music backend via AppleScript on macOS.

Does NOT require Music.app to be foregrounded; osascript launches it headless
if needed. Subscribed library + local library both work.
"""

from __future__ import annotations

import re
import subprocess
import urllib.parse
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
            r = c.get(f"https://music.163.com/api/search/get/?s={q}&type=1&limit=5")
            data = r.json()
            songs = (data.get("result") or {}).get("songs") or []
            if not songs:
                return None
            song_id = songs[0].get("id")
            if not song_id:
                return None
            r2 = c.get(f"https://music.163.com/api/song/lyric?id={song_id}&lv=-1&kv=-1&tv=-1")
            d2 = r2.json()
            lrc = (d2.get("lrc") or {}).get("lyric") or ""
            return lrc or None
        except Exception:
            return None


_SCRIPT_NOW = """
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
"""

_SCRIPT_ARTWORK = """
tell application "Music"
    if exists current track then
        set artData to (raw data of artwork 1 of current track) as «class PNG »
        return artData
    end if
end tell
"""


def _osa(script: str) -> str:
    p = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=8,
    )
    if p.returncode != 0:
        raise RuntimeError(f"AppleScript failed: {p.stderr.strip()}")
    return p.stdout.strip()


def _osa_silent(script: str) -> None:
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=8)
    except Exception:
        pass


def _osa_quote(text: str) -> str:
    return (text or "").replace('"', '\\"')


def _strip_result_format(query: str) -> str:
    q = (query or "").strip()
    q = re.sub(r"^\s*\d+[\.)]\s*", "", q)
    q = re.sub(r"\s+\[[^\]]+\]\s*$", "", q)
    return q.strip()


def _display_parts(query: str) -> tuple[str, str, str]:
    """Parse copied search rows like 'title — artist · album'."""
    q = _strip_result_format(query)
    m = re.match(r"^\s*(.+?)\s*[—–]\s*(.+?)\s*$", q) or re.match(r"^\s*(.+?)\s+-\s+(.+?)\s*$", q)
    if not m:
        return "", "", ""
    title = m.group(1).strip()
    rest = m.group(2).strip()
    pieces = re.split(r"\s+[·・•]\s+|[·・•]", rest, maxsplit=1)
    artist = pieces[0].strip()
    album = pieces[1].strip() if len(pieces) > 1 else ""
    return title, artist, album


def _catalog_search_query(query: str) -> str:
    title, artist, _ = _display_parts(query)
    if title and artist:
        return f"{title} {artist}"
    return _strip_result_format(query)


def _norm_match_text(text: str) -> str:
    text = (text or "").lower()
    return re.sub(r"[\s\-—–_·・•.,，。:：;；'\"“”‘’\[\]()（）<>《》]+", "", text)


def _contains_norm(haystack: str, needle: str) -> bool:
    h = _norm_match_text(haystack)
    n = _norm_match_text(needle)
    return bool(h and n and (n in h or h in n))


def _query_match_tokens(query: str) -> List[str]:
    title, artist, _ = _display_parts(query)
    if title and artist:
        return [title, artist]
    q = _strip_result_format(query)
    raw = re.split(r"[\s,，;；/|]+", q)
    return [t for t in raw if _norm_match_text(t)]


def _track_matches(
    title: str,
    artist: str,
    *,
    query: str = "",
    target_title: str = "",
    target_artist: str = "",
) -> bool:
    if target_title and not _contains_norm(title, target_title):
        return False
    if target_artist and not _contains_norm(artist, target_artist):
        return False
    if target_title or target_artist:
        return True

    tokens = _query_match_tokens(query)
    if not tokens:
        return bool(title)
    haystack = f"{title} {artist}"
    return all(_contains_norm(haystack, token) for token in tokens)


def _track_matches_target(
    title: str,
    artist: str,
    target_title: str,
    target_artist: str,
    query: str = "",
) -> bool:
    if target_title and not _contains_norm(title, target_title):
        return False
    if not target_artist or _contains_norm(artist, target_artist):
        return True

    # Catalog metadata can return "Joey Yung" while Music.app displays
    # "容祖儿". If the user's query includes the localized artist, accept that
    # after the title has already matched.
    for token in _query_match_tokens(query):
        if target_title and _contains_norm(target_title, token):
            continue
        if _contains_norm(artist, token):
            return True
    return False


def _play_local_match(query: str) -> bool:
    title, artist, _ = _display_parts(query)
    if title and artist:
        title_esc = _osa_quote(title)
        artist_esc = _osa_quote(artist)
        script = f'''
tell application "Music"
    set candidates to (every track of library playlist 1 whose name contains "{title_esc}" and artist contains "{artist_esc}")
    if (count of candidates) > 0 then
        play item 1 of candidates
        return "ok"
    end if
    return "none"
end tell
'''
        try:
            if _osa(script) == "ok":
                return True
        except Exception:
            pass

    q = _osa_quote(title or _strip_result_format(query))
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
        te = _osa_quote(t)
        conds.append(f'(name contains "{te}" or artist contains "{te}")')
    where = " and ".join(conds)
    script = f"""
tell application "Music"
    set candidates to (every track of library playlist 1 whose {where})
    if (count of candidates) > 0 then
        play item 1 of candidates
        return "ok"
    end if
    return "none"
end tell
"""
    try:
        return _osa(script) == "ok"
    except Exception:
        return False


# Storefronts tried in priority order.  The list is intentionally broad so
# CJK-region music is found even for users whose Apple ID is in a Western
# storefront, and vice-versa.
_ALL_CATALOG_STOREFRONTS = (
    "cn",
    "hk",
    "tw",
    "jp",
    "kr",  # CJK — first for most users of this tool
    "us",
    "gb",
    "au",
    "ca",
    "nz",  # English-speaking
    "sg",
    "my",
    "th",
    "ph",
    "id",
    "vn",  # SE Asia
    "de",
    "fr",
    "es",
    "it",
    "nl",
    "se",  # Europe
    "in",
    "br",
    "mx",
    "sa",
    "ae",  # Global
)

# Descriptive suffixes that confuse iTunes Search (it does literal substring
# matching on title/artist, not semantic search). When a query ends with one
# of these we retry once with it stripped.
_CATALOG_NOISE_SUFFIXES = (
    "主题曲",
    "主题歌",
    "片头曲",
    "片尾曲",
    "插曲",
    "主题",
    "OST",
    "BGM",
    "OP",
    "ED",
    "原声",
    "原声带",
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


def _detect_storefront() -> Optional[str]:
    """Infer the user's Apple Music storefront from the currently playing
    track's store URL (e.g. music.apple.com/cn/album/…  →  'cn').
    Returns None when Music.app isn't running or has no catalog track."""
    try:
        url = _osa('tell application "Music" to get store URL of current track')
        m = re.search(r"music\.apple\.com/([a-z]{2,3})/", url or "")
        if m:
            return m.group(1)
    except Exception:
        pass
    return None


def _best_hit(results: list, query: str) -> Optional[dict]:
    """Pick the most relevant result from an iTunes Search response list.
    Prefers exact title matches; falls back to first result."""
    if not results:
        return None
    q_lower = query.lower()
    for hit in results:
        name = (hit.get("trackName") or "").lower()
        if name == q_lower or name.startswith(q_lower):
            return hit
    for hit in results:
        if _track_matches(
            hit.get("trackName") or "",
            hit.get("artistName") or "",
            query=query,
        ):
            return hit
    return results[0]


def _play_preview(preview_url: str, title: str, artist: str) -> bool:
    """Play a 30-second iTunes preview via afplay (works without subscription).
    Pauses Music.app first so the audio doesn't clash."""
    import time

    if not preview_url:
        return False
    try:
        _osa_silent('tell application "Music" to pause')
        proc = subprocess.Popen(
            ["afplay", preview_url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(0.5)
        return proc.poll() is None
    except Exception:
        return False


def _music_now_if_matches(
    target_title: str,
    target_artist: str,
    query: str = "",
    target_track_id: str = "",
) -> Optional[NowPlaying]:
    try:
        raw = _osa(_SCRIPT_NOW)
    except Exception:
        return None
    if raw == "__not_running__" or not raw:
        return None
    parts = raw.split("\x1f")
    if len(parts) < 6:
        return None
    title, artist, album, dur, pos, state = parts[:6]
    if state.strip().lower() != "playing":
        return None
    if not title or title.strip().isdigit():
        return None
    matched_by_store_url = False
    if target_track_id:
        try:
            store_url = _osa('tell application "Music" to get store URL of current track')
            matched_by_store_url = bool(re.search(rf"(?<!\d){re.escape(str(target_track_id))}(?!\d)", store_url or ""))
        except Exception:
            matched_by_store_url = False
    if not matched_by_store_url and not _track_matches_target(
        title,
        artist,
        target_title,
        target_artist,
        query,
    ):
        return None
    try:
        duration = float(dur or 0)
        position = float(pos or 0)
    except ValueError:
        duration, position = 0.0, 0.0
    return NowPlaying(
        title=title,
        artist=artist,
        album=album,
        duration=duration,
        position=position,
        playing=True,
        source="apple_music",
    )


def _play_catalog(query: str) -> "Optional[NowPlaying]":
    """Search the Apple Music catalog via the public iTunes Search API and ask
    Music.app to open the best hit.

    Strategy:
    1. Auto-detect the user's storefront from the current track's store URL;
       put it first in the attempt list so regional catalog content is found
       immediately (important for CN/KR/JP users).
    2. Try up to _ALL_CATALOG_STOREFRONTS until a hit is found.
    3. Attempt full playback via `music.apple.com` URL (requires subscription).
    4. If Music.app can't play the full track (no subscription / wrong Apple ID),
       fall back to a 30-second afplay preview using the iTunes previewUrl.

    Returns a NowPlaying with iTunes metadata on success, None on failure.
    Callers should prefer a live now_playing() query but can use this as fallback.
    """
    import time

    try:
        import httpx
    except ImportError:
        return None

    # Build ordered storefront list: detected region first
    detected = _detect_storefront()
    storefronts: list[str] = list(_ALL_CATALOG_STOREFRONTS)
    if detected and detected in storefronts:
        storefronts.remove(detected)
        storefronts.insert(0, detected)
    elif detected:
        storefronts.insert(0, detected)

    hit: Optional[dict] = None
    storefront = "us"
    try:
        with httpx.Client(timeout=6.0) as c:
            for term in _catalog_query_variants(query):
                for sf in storefronts:
                    try:
                        r = c.get(
                            "https://itunes.apple.com/search",
                            params={"term": term, "entity": "song", "limit": 5, "country": sf},
                        )
                        data = r.json()
                    except Exception:
                        continue
                    candidate = _best_hit(data.get("results") or [], term)
                    if candidate and candidate.get("trackId"):
                        hit = candidate
                        storefront = sf
                        break
                if hit:
                    break
    except Exception:
        return None

    if not hit:
        return None

    tid = hit["trackId"]
    title = hit.get("trackName") or "?"
    artist = hit.get("artistName") or "?"
    preview_url = hit.get("previewUrl") or ""
    # music:// scheme routes directly to Music.app and triggers library add for subscribers
    url = f"music://music.apple.com/{storefront}/song/{tid}"

    # open -g opens the URL in Music.app WITHOUT bringing it to the foreground.
    # This adds the catalog track to the library and starts playback, all in background.
    subprocess.run(["open", "-g", url], capture_output=True, timeout=10)
    # Wait for Music.app to fetch metadata and register track in library
    time.sleep(3.0)
    # Ensure playback started (open -g may not auto-play on all macOS versions)
    _osa_silent('tell application "Music" to play')

    # Poll up to ~6.4s for Music.app to confirm the requested track, not just
    # any already-playing track.
    for _ in range(8):
        time.sleep(0.8)
        matched = _music_now_if_matches(title, artist, query, str(tid))
        if matched:
            return matched

    # open location may have added the track to the library even if current track is inaccessible.
    # Search the library by exact title + artist from the iTunes API response.
    title_esc = _osa_quote(title)
    artist_esc = _osa_quote(artist)
    lib_script = f'''
tell application "Music"
    set cands to (every track of library playlist 1 whose (name contains "{title_esc}" and artist contains "{artist_esc}"))
    if (count of cands) = 0 then
        set cands to (every track of library playlist 1 whose name contains "{title_esc}")
    end if
    if (count of cands) > 0 then
        play item 1 of cands
        return "ok"
    end if
    return "none"
end tell
'''
    try:
        if _osa(lib_script) == "ok":
            for _ in range(5):
                time.sleep(0.5)
                matched = _music_now_if_matches(title, artist, query, str(tid))
                if matched:
                    return matched
    except Exception:
        pass

    # Full playback failed — clean up stub track
    tid_esc = _osa_quote(str(tid))
    _osa_silent(f'''tell application "Music"
        stop
        try
            set badTracks to (every track of library playlist 1 whose name is "{tid_esc}")
            repeat with t in badTracks
                delete t
            end repeat
        end try
    end tell''')

    # Fallback: play 30-second preview if available
    if preview_url and _play_preview(preview_url, title, artist):
        return NowPlaying(
            title=title,
            artist=artist,
            source="apple_music",
            playing=True,
            unsupported_reason="preview_playing",
        )

    # Track was found on Apple Music catalog but couldn't be played directly.
    # Open the Music.app search results page so the user can find the song and add to library.
    encoded = urllib.parse.quote(query)
    search_url = f"music://music.apple.com/{storefront}/search?term={encoded}"
    subprocess.run(["open", search_url], capture_output=True, timeout=10)
    return NowPlaying(
        source="apple_music",
        title=title,
        artist=artist,
        unsupported_reason="needs_library_add",
    )


def _search_catalog_api(query: str, limit: int = 8, timeout: float = 3.0) -> List[dict]:
    """Search the Apple Music catalog via iTunes Search API.
    Returns dicts with title/artist/album/source='apple_music'."""
    try:
        import httpx
    except ImportError:
        return []
    detected = _detect_storefront()
    # Build storefront priority: detected region first, then CJK fallbacks, then us.
    # CJK storefronts (cn/hk/tw) are always included so Chinese songs are found
    # even when nothing is playing and the storefront cannot be auto-detected.
    seen: set[str] = set()
    storefronts: list[str] = []
    for sf in ([detected] if detected else []) + ["cn", "hk", "tw", "us"]:
        if sf and sf not in seen:
            seen.add(sf)
            storefronts.append(sf)
    try:
        with httpx.Client(timeout=timeout) as c:
            for sf in storefronts:
                try:
                    r = c.get(
                        "https://itunes.apple.com/search",
                        params={"term": query, "entity": "song", "limit": limit, "country": sf},
                    )
                    results = r.json().get("results") or []
                    if results:
                        return [
                            {
                                "title": h.get("trackName") or "?",
                                "artist": h.get("artistName") or "?",
                                "album": h.get("collectionName") or "?",
                                "source": "apple_music",
                            }
                            for h in results[:limit]
                        ]
                except Exception:
                    continue
    except Exception:
        pass
    return []


class AppleMusic:
    name = "apple_music"

    def _wait_for_match(
        self,
        query: str = "",
        *,
        target_title: str = "",
        target_artist: str = "",
        attempts: int = 4,
        delay: float = 0.5,
    ) -> Optional[NowPlaying]:
        import time

        for _ in range(attempts):
            np = self.now_playing()
            if (
                np.title
                and np.playing
                and (
                    _track_matches(np.title, np.artist, query=query)
                    if not (target_title or target_artist)
                    else _track_matches_target(
                        np.title,
                        np.artist,
                        target_title,
                        target_artist,
                        query,
                    )
                )
            ):
                return np
            time.sleep(delay)
        return None

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
            title=title,
            artist=artist,
            album=album,
            duration=duration,
            position=position,
            playing=playing,
            source=self.name,
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

    def play(self) -> None:
        _osa_silent('tell application "Music" to play')

    def pause(self) -> None:
        _osa_silent('tell application "Music" to pause')

    def toggle(self) -> None:
        _osa_silent('tell application "Music" to playpause')

    def next(self) -> None:
        _osa_silent('tell application "Music" to next track')

    def prev(self) -> None:
        _osa_silent('tell application "Music" to previous track')

    def seek(self, seconds: float) -> None:
        _osa_silent(f'tell application "Music" to set player position to {float(seconds)}')

    def set_volume(self, percent: int) -> None:
        p = max(0, min(100, int(percent)))
        _osa_silent(f'tell application "Music" to set sound volume to {p}')

    def like_current(self) -> bool:
        script = """
tell application "Music"
    if not (exists current track) then return "no_track"
    set favorited of current track to true
    return "ok"
end tell
"""
        try:
            return _osa(script) == "ok"
        except Exception:
            return False

    def set_play_mode(self, mode: str) -> bool:
        normalized = (mode or "").lower().replace("-", "_")
        if normalized in ("shuffle", "random"):
            script = """
tell application "Music"
    set shuffle enabled to true
    set song repeat to off
    return "ok"
end tell
"""
        elif normalized in ("sequential", "sequence", "normal", "off"):
            script = """
tell application "Music"
    set shuffle enabled to false
    set song repeat to off
    return "ok"
end tell
"""
        elif normalized in ("repeat", "loop", "repeat_all", "all"):
            script = """
tell application "Music"
    set shuffle enabled to false
    set song repeat to all
    return "ok"
end tell
"""
        elif normalized in ("repeat_one", "one", "single"):
            script = """
tell application "Music"
    set shuffle enabled to false
    set song repeat to one
    return "ok"
end tell
"""
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
        set out to out & (name of t as string) & SEP & (artist of t as string) & SEP & (album of t as string) & SEP & (favorited of t as string) & linefeed
    end repeat
    return out
end tell
'''
        try:
            raw = _osa(script)
        except Exception:
            raw = ""
        items = []
        for line in raw.splitlines():
            if not line.strip():
                continue
            parts = line.split("\x1f")
            if len(parts) >= 3:
                is_loved = len(parts) >= 4 and parts[3].strip().lower() == "true"
                items.append({
                    "title": parts[0],
                    "artist": parts[1],
                    "album": parts[2],
                    "source": "loved" if is_loved else "library",
                })
        # Fill remaining slots with Apple Music catalog results
        remaining = limit - len(items)
        if remaining > 0:
            items.extend(_search_catalog_api(query, remaining))
        return items

    def list_library(self, limit: int = 100) -> List[dict]:
        """Return all tracks in the library, sorted by name, up to limit."""
        script = f"""
tell application "Music"
    set SEP to (ASCII character 31)
    set out to ""
    set allTracks to every track of library playlist 1
    set n to count of allTracks
    if n > {limit} then set n to {limit}
    repeat with i from 1 to n
        set t to item i of allTracks
        set out to out & (name of t as string) & SEP & (artist of t as string) & SEP & (album of t as string) & linefeed
    end repeat
    return out
end tell
"""
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

    def list_loved(self, limit: int = 100) -> List[dict]:
        """Return all loved/hearted tracks in the library, up to limit."""
        script = f"""
tell application "Music"
    set SEP to (ASCII character 31)
    set out to ""
    set lovedTracks to (every track of library playlist 1 whose favorited is true)
    set n to count of lovedTracks
    if n > {limit} then set n to {limit}
    repeat with i from 1 to n
        set t to item i of lovedTracks
        set out to out & (name of t as string) & SEP & (artist of t as string) & SEP & (album of t as string) & linefeed
    end repeat
    return out
end tell
"""
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
                items.append({"title": parts[0], "artist": parts[1], "album": parts[2], "source": "loved"})
        return items

    def search_loved(self, query: str, limit: int = 8) -> List[dict]:
        """Search only within loved/hearted tracks."""
        q = query.replace('"', '\\"')
        script = f'''
tell application "Music"
    set SEP to (ASCII character 31)
    set out to ""
    set results to (every track of library playlist 1 whose favorited is true and (name contains "{q}" or artist contains "{q}" or album contains "{q}"))
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
                items.append({"title": parts[0], "artist": parts[1], "album": parts[2], "source": "loved"})
        return items

    def lyrics(self) -> Optional[str]:
        """Static lyrics for the current track via AppleScript. Synced timing
        isn't reliably exposed, so callers should estimate the current line
        from position/duration."""
        script = """
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
"""
        np = self.now_playing()
        if not np.title:
            return None
        key = re.sub(r"[^a-zA-Z0-9一-鿿]+", "_", f"{np.artist}_{np.album}_{np.title}").strip("_")[:160]
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

    def play_query(self, query: str, library_only: bool = False) -> Optional[NowPlaying]:
        """Three-tier search:
        1. Full-string substring match in local library (fast).
        2. If query has multiple whitespace-separated tokens, AND-match each
           token against name OR artist (so '青花瓷 周杰伦' matches a track
           named 青花瓷 by 周杰伦 even though no single field contains the
           whole string).
        3. Fall back to the public iTunes Search API and ask Music to open
           the top hit's catalog URL. Skipped when library_only=True to avoid
           interrupting current playback with a catalog popup.
        """
        if _play_local_match(query):
            np = self._wait_for_match(query=query, attempts=12, delay=0.5)
            if np:
                return np
        tokens = _query_match_tokens(query)

        if len(tokens) > 1 and _play_local_tokens(tokens):
            np = self._wait_for_match(query=query, attempts=12, delay=0.5)
            if np:
                return np

        if library_only:
            return None  # no local match; caller decides — do NOT touch the player

        # Fall back to iTunes catalog: search, add to library, and play.
        catalog_query = _catalog_search_query(query)
        catalog_np = _play_catalog(catalog_query)
        if catalog_np is not None:
            if catalog_np.unsupported_reason:
                return catalog_np  # found on catalog but couldn't play; caller handles messaging
            np = self._wait_for_match(
                query=query,
                target_title=catalog_np.title,
                target_artist=catalog_np.artist,
                attempts=5,
                delay=0.8,
            )
            if np:
                return np
            return catalog_np
        return None
