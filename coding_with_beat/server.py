"""MCP server: exposes coding-with-beat tools to Claude Code.

Run with:
    python -m coding_with_beat.server
    python -m coding_with_beat server
"""

from __future__ import annotations

import json
import os
import time
from typing import Optional

from mcp.server.fastmcp import FastMCP

from . import dj, focus, state
from .config import DATA_DIR
from .lyrics_snapshot import current_text as current_lyrics_text
from .lyrics_snapshot import track_key
from .sources import get_source
from .ui import (
    boxed,
    render_cover,
    render_cover_gameboy,
    render_lyrics_window,
    render_progress,
    render_spectrum_color,
    retro_banner,
)

MCP_HTTP_HOST_ENV = "CWB_MCP_HOST"
MCP_HTTP_PORT_ENV = "CWB_MCP_PORT"
MCP_HTTP_PATH_ENV = "CWB_MCP_PATH"
_LEGACY_MCP_HTTP_HOST_ENV = "CC_JUKEBOX_MCP_HOST"
_LEGACY_MCP_HTTP_PORT_ENV = "CC_JUKEBOX_MCP_PORT"
_LEGACY_MCP_HTTP_PATH_ENV = "CC_JUKEBOX_MCP_PATH"
CONTROL_REFRESH_DELAY = 0.4


def _one_off_file():
    return DATA_DIR / "one_off_queue.json"


def _queue_file(name: str):
    if name not in ("library", "search"):
        raise ValueError(f"unknown queue name: {name!r}")
    return DATA_DIR / ("library_queue.json" if name == "library" else "search_queue.json")


def _load_queue_file(name: str) -> dict:
    """Load library or search queue. Returns dict with tracks, index, expected_title."""
    try:
        data = json.loads(_queue_file(name).read_text(encoding="utf-8"))
        if data.get("tracks"):
            return data
    except Exception:
        pass
    # Legacy fallback: last_results.json + queue_index.json for search queue
    if name == "search":
        try:
            raw = json.loads((DATA_DIR / "last_results.json").read_text(encoding="utf-8"))
            if isinstance(raw, list) and raw:
                try:
                    idx = int(json.loads((DATA_DIR / "queue_index.json").read_text(encoding="utf-8")).get("index", -1))
                except Exception:
                    idx = -1
                return {"tracks": raw, "index": idx, "expected_title": ""}
        except Exception:
            pass
    return {"tracks": [], "index": 0, "expected_title": ""}


def _write_queue_file(name: str, data: dict) -> None:
    try:
        _queue_file(name).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _read_active_mode() -> dict:
    """Returns {mode, context}. Defaults to library for both."""
    try:
        return json.loads((DATA_DIR / "active_mode.json").read_text(encoding="utf-8"))
    except Exception:
        # Legacy fallback: if last_results.json exists, treat as search mode
        if (DATA_DIR / "last_results.json").exists():
            return {"mode": "search", "context": "search"}
        return {"mode": "library", "context": "library"}


def _write_active_mode(mode: str | None = None, context: str | None = None) -> None:
    if mode is None and context is None:
        return
    current = _read_active_mode()
    if mode is not None:
        current["mode"] = mode
    if context is not None:
        current["context"] = context
    try:
        (DATA_DIR / "active_mode.json").write_text(json.dumps(current, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


_NATURAL_END_THRESHOLD = 5.0
# Max gap between two consecutive polls before auto-advance is suppressed.
# A large gap (e.g. server busy during a slow search) makes position data
# unreliable, so we skip auto-advance to avoid false positives.
_MAX_POLL_GAP = 12.0
_np_state: dict = {"title": "", "position": 0.0, "duration": 0.0, "sampled_at": 0.0}


def _auto_advance_if_needed(np) -> None:
    """Auto-advance the active queue when a cwb-managed track ends naturally.

    Distinguishes natural end (position near duration) from external switch
    (position mid-song) so cwb does not steal control when the user clicks
    a different song in Music.app.
    """
    now = time.time()
    current_title = np.title or ""
    current_position = float(np.position or 0.0)
    current_duration = float(np.duration or 0.0)

    prev_title = _np_state["title"]
    prev_position = _np_state["position"]
    prev_duration = _np_state["duration"]
    prev_sampled_at = _np_state["sampled_at"]

    _np_state["title"] = current_title
    _np_state["position"] = current_position
    _np_state["duration"] = current_duration
    _np_state["sampled_at"] = now

    if current_title == prev_title or not prev_title:
        return
    if _one_off_file().exists():
        return  # _maybe_resume_queue handles one-off resumption
    # If the server was busy (e.g. slow search) the position sample is stale —
    # skip to avoid triggering a false auto-advance.
    if prev_sampled_at > 0 and now - prev_sampled_at > _MAX_POLL_GAP:
        return
    if prev_duration <= 0 or prev_position < prev_duration - _NATURAL_END_THRESHOLD:
        return  # external switch

    am = _read_active_mode()
    mode = am.get("mode", "library")
    qdata = _load_queue_file(mode)
    if qdata.get("expected_title", "") != prev_title:
        return  # track was not cwb-managed

    hits = qdata.get("tracks", [])
    next_idx = qdata.get("index", 0) + 1

    if mode == "search" and next_idx >= len(hits):
        lib_data = _load_queue_file("library")
        if lib_data.get("tracks"):
            _write_active_mode(mode="library")
            _play_queue_at(lib_data.get("index", 0), "library")
    elif next_idx < len(hits):
        _play_queue_at(next_idx, mode)


def _env_first(name: str, legacy_name: str, default: str) -> str:
    return os.environ.get(name) or os.environ.get(legacy_name) or default


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name, "")
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _normalize_path(path: str) -> str:
    return path if path.startswith("/") else f"/{path}"


mcp = FastMCP(
    "coding-with-beat",
    host=_env_first(MCP_HTTP_HOST_ENV, _LEGACY_MCP_HTTP_HOST_ENV, "127.0.0.1"),
    port=_env_int(MCP_HTTP_PORT_ENV, _env_int(_LEGACY_MCP_HTTP_PORT_ENV, 8765)),
    streamable_http_path=_normalize_path(
        _env_first(MCP_HTTP_PATH_ENV, _LEGACY_MCP_HTTP_PATH_ENV, "/mcp"),
    ),
)


def _unsupported(source: str, feature: str, reason: str) -> str:
    return f"(unsupported — source={source}, feature={feature})\n{reason}"


def _unsupported_reason(obj) -> str:
    return getattr(obj, "unsupported_reason", None) or ""


def _preview_message(np) -> str:
    return (
        f"♪ 30s preview: {np.title or '?'} — {np.artist or '—'}\n"
        "  Apple Music full playback did not start; opened/attempted the catalog track."
    )


def _needs_library_add(np, retry_query: str = "") -> str:
    title = np.title or "?"
    artist = np.artist or "—"
    msg = (
        f'Opened Music.app for "{title} — {artist}".\n'
        'Add the track to your library, then just say "play it" and I\'ll start it right away.'
    )
    if retry_query:
        msg += f'\n\nIf the queue has changed by then, use play_song("{retry_query}") to play directly.'
    return msg


def _companion_card(message: str, music_results: str) -> str:
    frame_idx = int(time.time() * 2) % 3
    sprite = dj.pixel_person_frame("groove", frame_idx)  # colored=True, shown in CC terminal
    sprite_lines = sprite.splitlines()
    sprite_w = 10
    pad = "  "
    music_lines = music_results.splitlines()[:12]
    right_lines = [message, ""] + music_lines
    offset = max(0, (len(sprite_lines) - len(right_lines)) // 2)
    rows = []
    total = max(len(sprite_lines), len(right_lines) + offset)
    for i in range(total):
        sl = sprite_lines[i] if i < len(sprite_lines) else " " * sprite_w
        ri = i - offset
        rl = right_lines[ri] if 0 <= ri < len(right_lines) else ""
        rows.append(f"{sl}{pad}{rl}" if rl else sl)
    return "\n".join(rows)


def _wait_and_play_from_library(src, title: str, artist: str, timeout: int = 15, interval: int = 3) -> Optional[str]:
    """Poll until the track appears in the local library, then play it.

    Returns a '▶ now playing' string on success, or None on timeout.
    """
    import time

    query = f"{title} {artist}".strip()
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(interval)
        hits = src.search(query, 3)
        library_hit = next((h for h in (hits or []) if h.get("source") == "library"), None)
        if library_hit:
            np2 = src.play_query(query)
            if np2 and not _unsupported_reason(np2) and np2.title:
                return f"▶ now playing: {np2.title} — {np2.artist or '—'}  source={np2.source}"
    return None


def _refresh_now_playing():
    st = state.load()
    old_key = track_key(st.track.source or st.source, st.track.artist, st.track.album, st.track.title)
    src = get_source(st.source)
    np = src.now_playing()
    new_key = track_key(np.source or st.source, np.artist, np.album, np.title)
    if np.title:
        st.track.title = np.title
        st.track.artist = np.artist
        st.track.album = np.album
        st.track.duration = np.duration
        st.track.position = np.position
        if np.artwork_path:
            st.track.artwork_path = np.artwork_path
        if np.source:
            st.track.source = np.source
        if old_key != new_key:
            st.track.lyrics_key = ""
            st.track.lyrics_text = ""
            st.track.lyrics_pending = False
    st.track.position_sampled_at = time.time()
    st.playing = np.playing
    state.save(st)
    return st, np


def _refresh_after_control(delay: float = CONTROL_REFRESH_DELAY):
    if delay > 0:
        time.sleep(delay)
    return _refresh_now_playing()


def _queue_expected_hit() -> dict:
    """Return the queue's current expected track dict, or {} if unavailable."""
    try:
        am = _read_active_mode()
        qdata = _load_queue_file(am.get("mode", "library"))
        expected = qdata.get("expected_title", "")
        if not expected:
            return {}
        idx = qdata.get("index", 0)
        hits = qdata.get("tracks", [])
        hit = hits[idx] if 0 <= idx < len(hits) else {}
        hit["_expected_title"] = expected
        return hit
    except Exception:
        return {}


def _now_playing_payload(st, np, known_lyrics_key: str = "") -> dict:
    source = np.source or st.source
    unsupported = _unsupported_reason(np)
    if not np.title and not unsupported and st.track.title:
        # Source reports nothing (stopped / transitioning): fall back to last known state.
        title = st.track.title
        artist = st.track.artist or ""
        album = st.track.album or ""
        duration = float(st.track.duration or 0.0)
        cached_pos = float(st.track.position or 0.0)
        sampled_at = float(st.track.position_sampled_at or 0.0)
        if st.playing and sampled_at > 0:
            position = min(cached_pos + (time.time() - sampled_at), duration)
        else:
            position = cached_pos
        source = st.track.source or source
    elif not np.playing and not unsupported:
        # Paused: if cwb's queue has moved to a different track, show that track
        # so the display stays in sync with next/prev even when playback is stuck.
        qhit = _queue_expected_hit()
        expected = qhit.get("_expected_title", "")
        if expected and expected != (np.title or ""):
            title = expected
            artist = qhit.get("artist", "") or (np.artist or "")
            album = qhit.get("album", "") or (np.album or "")
            duration = float(qhit.get("duration", 0.0) or np.duration or 0.0)
            position = 0.0
        else:
            title = np.title or ""
            artist = np.artist or ""
            album = np.album or ""
            duration = float(np.duration or 0.0)
            position = float(np.position or 0.0)
    else:
        title = np.title or ""
        artist = np.artist or ""
        album = np.album or ""
        duration = float(np.duration or 0.0)
        position = float(np.position or 0.0)
    lyrics_key = track_key(source, artist, album, title)
    lyrics_text = ""
    lyrics_pending = False
    if title and not unsupported:
        lyrics_text, lyrics_pending = current_lyrics_text(source, artist, album, title)
        if lyrics_key and lyrics_key == known_lyrics_key:
            lyrics_text = ""
    return {
        "source": source,
        "title": title,
        "artist": artist,
        "album": album,
        "duration": duration,
        "position": position,
        "playing": bool(np.playing),
        "artwork_path": np.artwork_path or "",
        "lyrics_key": lyrics_key,
        "lyrics_text": lyrics_text,
        "lyrics_pending": lyrics_pending,
        "unsupported_reason": _unsupported_reason(np),
        "sampled_at": time.time(),
    }


@mcp.tool()
def now_playing() -> str:
    """Return the currently playing track from the active source.
    Output: a short text block with title, artist, album, position, source.
    Use this whenever the user asks 'what's playing' or before deciding to
    skip/replay."""
    st, np = _refresh_now_playing()
    if _unsupported_reason(np):
        return _unsupported(np.source or st.source, "now_playing", _unsupported_reason(np))
    if not np.title:
        return f"(nothing playing — source: {st.source})"
    return (
        f"♪ {np.title}\n"
        f"  by {np.artist or '—'} · {np.album or '—'}\n"
        f"  {int(np.position):>4}s / {int(np.duration):>4}s  source={np.source}  {'▶ playing' if np.playing else '❚❚ paused'}"
    )


def _maybe_resume_queue(np) -> None:
    """If a one-off song just ended (title changed), resume the saved queue."""
    if not _one_off_file().exists():
        return
    try:
        data = json.loads(_one_off_file().read_text(encoding="utf-8"))
    except Exception:
        _one_off_file().unlink(missing_ok=True)
        return
    one_off_title = data.get("one_off_title", "")
    resume_mode = data.get("resume_mode", "library")
    resume_index = int(data.get("resume_index", 0))
    if not np.title or np.title == one_off_title:
        return
    _one_off_file().unlink(missing_ok=True)
    _write_active_mode(mode=resume_mode)
    _play_queue_at(resume_index, resume_mode)


@mcp.tool()
def now_playing_snapshot(known_lyrics_key: str = "") -> str:
    """Return structured now-playing data as JSON for terminal integrations."""
    st, np = _refresh_now_playing()
    _maybe_resume_queue(np)
    _auto_advance_if_needed(np)
    return json.dumps(_now_playing_payload(st, np, known_lyrics_key), ensure_ascii=False)


@mcp.tool()
def current_source() -> str:
    """Return the currently selected music source name."""
    return state.load().source


@mcp.tool()
def play() -> str:
    """Resume playback on the active source."""
    st = state.load()
    get_source(st.source).play()
    _refresh_after_control()
    return "▶ play"


def _resume_from_state(st, src, np) -> str:
    """Resume or unpause. If the right track is already paused, just unpause.
    Otherwise re-search for the last known track and seek to its saved position."""
    if np.title and np.title == st.track.title:
        src.play()
        _refresh_now_playing()
        return "▶ play"
    if not st.track.title:
        src.play()
        _refresh_now_playing()
        return "▶ play"
    query = f"{st.track.title} {st.track.artist or ''}".strip()
    played = src.play_query(query)
    if not played or not played.title:
        return f"(could not resume '{st.track.title}' — not found in source={st.source})"
    last_pos = float(st.track.position or 0.0)
    if last_pos > 5:
        for _ in range(4):
            time.sleep(0.6)
            try:
                src.seek(last_pos)
            except Exception:
                pass
            check = src.now_playing()
            if check.position >= last_pos - 3:
                break
    _refresh_now_playing()
    return f"▶ resumed: {played.title} — {played.artist or '—'} at {int(last_pos)}s"


@mcp.tool()
def resume() -> str:
    """Resume the last known track from its saved position.
    If the right track is already paused, just unpauses it.
    Useful after an interruption (e.g. catalog popup) cleared the player."""
    st = state.load()
    if not st.track.title:
        return "(nothing to resume — no last track recorded)"
    src = get_source(st.source)
    np = src.now_playing()
    if np.title == st.track.title and np.playing:
        return f"▶ already playing: {np.title}"
    return _resume_from_state(st, src, np)


@mcp.tool()
def pause() -> str:
    """Pause playback on the active source."""
    st = state.load()
    get_source(st.source).pause()
    _refresh_now_playing()
    return "❚❚ paused"


@mcp.tool()
def toggle() -> str:
    """Toggle play/pause. If interrupted (nothing loaded in the player), resumes
    the last known track from its saved position instead of doing nothing."""
    st = state.load()
    src = get_source(st.source)
    np = src.now_playing()
    if np.playing:
        src.pause()
        _refresh_now_playing()
        return "❚❚ paused"
    return _resume_from_state(st, src, np)


def _play_queue_at(idx: int, queue_name: str | None = None) -> str:
    """Play queue_name[idx]. queue_name defaults to the active mode."""
    if queue_name is None:
        queue_name = _read_active_mode().get("mode", "library")
    qdata = _load_queue_file(queue_name)
    hits = qdata.get("tracks", [])
    if not hits:
        return ""
    idx = idx % len(hits)
    hit = hits[idx]
    query = f"{hit['title']} {hit.get('artist', '')}".strip()
    st = state.load()
    src = get_source(st.source)
    np = src.play_query(query)
    _refresh_after_control()
    title = (np.title if np and not _unsupported_reason(np) else None) or hit.get("title", "?")
    qdata["index"] = idx
    qdata["expected_title"] = title
    _write_queue_file(queue_name, qdata)
    _write_active_mode(mode=queue_name)
    return f"[{idx + 1}/{len(hits)}] {title}"


@mcp.tool()
def next_track() -> str:
    """Skip to the next track."""
    _one_off_file().unlink(missing_ok=True)
    am = _read_active_mode()
    mode = am.get("mode", "library")
    qdata = _load_queue_file(mode)
    hits = qdata.get("tracks", [])
    if hits:
        next_idx = qdata.get("index", 0) + 1
        if next_idx < len(hits):
            result = _play_queue_at(next_idx, mode)
            return f"⏭ next  {result}"
        if mode == "search":
            lib_data = _load_queue_file("library")
            if lib_data.get("tracks"):
                _write_active_mode(mode="library", context="library")
                result = _play_queue_at(lib_data.get("index", 0), "library")
                return f"⏭ next (→ library)  {result}"
        if mode == "library":
            result = _play_queue_at(0, "library")
            return f"⏭ next (wrap → 1)  {result}"
    st = state.load()
    get_source(st.source).next()
    _refresh_after_control()
    return "⏭ next"


@mcp.tool()
def prev_track() -> str:
    """Go to the previous track."""
    _one_off_file().unlink(missing_ok=True)
    am = _read_active_mode()
    mode = am.get("mode", "library")
    qdata = _load_queue_file(mode)
    hits = qdata.get("tracks", [])
    if hits:
        prev_idx = qdata.get("index", 0) - 1
        if prev_idx >= 0:
            result = _play_queue_at(prev_idx, mode)
            return f"⏮ prev  {result}"
        if mode == "search":
            lib_data = _load_queue_file("library")
            if lib_data.get("tracks"):
                _write_active_mode(mode="library", context="library")
                result = _play_queue_at(lib_data.get("index", 0), "library")
                return f"⏮ prev (→ library)  {result}"
        if mode == "library":
            result = _play_queue_at(len(hits) - 1, "library")
            return f"⏮ prev (wrap → {len(hits)})  {result}"
    st = state.load()
    get_source(st.source).prev()
    _refresh_after_control()
    return "⏮ prev"


@mcp.tool()
def seek(seconds: float) -> str:
    """Jump to position (seconds) in the current track."""
    st = state.load()
    get_source(st.source).seek(seconds)
    _refresh_now_playing()
    return f"⇥ seek {int(seconds)}s"


@mcp.tool()
def set_volume(percent: int) -> str:
    """Set source/system volume (0-100)."""
    st = state.load()
    get_source(st.source).set_volume(percent)
    st.volume = max(0, min(100, int(percent)))
    state.save(st)
    return f"🔊 volume={st.volume}"


@mcp.tool()
def like_current() -> str:
    """Like/favorite the current track on the active source.
    Apple Music uses Music.app AppleScript. QQMusic uses macOS System Events
    menu automation. Sources that do not support this raise NotImplementedError."""
    st = state.load()
    ok = get_source(st.source).like_current()
    return f"♥ liked current track  source={st.source}" if ok else f"error: like failed  source={st.source}"


@mcp.tool()
def set_play_mode(mode: str) -> str:
    """Set play mode on the active source.
    Common modes: shuffle, sequential, repeat. Apple Music also supports
    repeat_one and repeat_all. Unsupported modes/sources raise
    NotImplementedError from the source backend."""
    st = state.load()
    ok = get_source(st.source).set_play_mode(mode)
    return f"play mode = {mode}  source={st.source}" if ok else f"error: play mode failed  source={st.source}"


@mcp.tool()
async def list_library(limit: int = 100) -> str:
    """List all tracks in the library of the current source."""
    import asyncio

    st = state.load()
    src = get_source(st.source)
    fn = getattr(src, "list_library", None)
    if not callable(fn):
        return f"(list not supported for source={st.source})"
    hits = await asyncio.to_thread(fn, limit)
    _write_queue_file("library", {"tracks": hits or [], "index": 0, "expected_title": ""})
    _write_active_mode(context="library")
    if not hits:
        return "(library is empty)"
    return "\n".join(
        f"{i + 1}. {h['title']} — {h.get('artist', '?')} · {h.get('album', '?')}" for i, h in enumerate(hits)
    )


@mcp.tool()
async def search(query: str, limit: int = 8) -> str:
    """Search the current source for tracks matching the query. Returns a
    numbered list. Does NOT affect current playback. Only call play_number
    or play_song if the user explicitly asks to play a specific result."""
    import asyncio

    st = state.load()
    hits = await asyncio.to_thread(get_source(st.source).search, query, limit)
    if not hits:
        return f"(no matches for '{query}' in source={st.source})"
    _write_queue_file("search", {"tracks": hits, "index": 0, "expected_title": ""})
    _write_active_mode(context="search")
    lines = []
    for i, h in enumerate(hits):
        tag = (
            " [Library]"
            if h.get("source") == "library"
            else " [Apple Music]"
            if h.get("source") == "apple_music"
            else ""
        )
        lines.append(f"{i + 1}. {h['title']} — {h.get('artist', '?')} · {h.get('album', '?')}{tag}")
    return "\n".join(lines)


_QUERY_LABEL_MAP: list[tuple[tuple[str, ...], str]] = [
    (("jazz", "bossa nova", "smooth jazz"), "🎷 Jazz"),
    (("lofi", "lo-fi", "chillhop"), "🎧 Lofi"),
    (("synthwave", "retrowave", "outrun"), "🌆 Synthwave"),
    (("drone", "meditation"), "🌫️ Ambient"),
    (("classical", "piano", "nocturne", "string"), "🎹 Classical"),
    (("hype", "workout", "energetic", "edm"), "🔥 Hype"),
    (("sleep", "lullaby", "white noise"), "🌙 Sleep"),
    (("sad", "melancholy", "heartbreak"), "💙 Sad"),
    (("party", "celebrat"), "🎉 Party"),
    (("chinese", "中国", "古风", "国风"), "🏮 Chinese"),
    (("focus", "study", "concentration"), "🧠 Focus"),
    (("relax", "unwind", "calm"), "🌅 Relax"),
]


def _label_for_query(query: str) -> str:
    q_lower = query.lower()
    for keywords, label in _QUERY_LABEL_MAP:
        if any(kw in q_lower for kw in keywords):
            return label
    words = query.split()[:3]
    return " ".join(w.capitalize() for w in words)


async def _multi_angle_search(queries: list[str], limit_per_query: int = 6) -> str:
    import asyncio

    async def _search_one(query: str) -> list[dict]:
        try:
            am_hits, local_hits = await asyncio.gather(
                asyncio.to_thread(get_source("apple_music").search, query, limit_per_query),
                asyncio.to_thread(get_source("local").search, query, limit_per_query),
            )
        except Exception:
            return []
        seen: set[str] = set()
        merged: list[dict] = []
        for h in (am_hits or []) + (local_hits or []):
            key = f"{h.get('title', '').lower()}|{h.get('artist', '').lower()}"
            if key not in seen:
                seen.add(key)
                merged.append(h)
        return merged

    per_query_results = await asyncio.gather(*[_search_one(q) for q in queries])

    global_seen: set[str] = set()
    groups: list[tuple[str, list[dict]]] = []
    all_tracks: list[dict] = []

    for query, hits in zip(queries, per_query_results):
        label = _label_for_query(query)
        group_tracks: list[dict] = []
        for h in hits:
            key = f"{h.get('title', '').lower()}|{h.get('artist', '').lower()}"
            if key not in global_seen:
                global_seen.add(key)
                group_tracks.append(h)
                all_tracks.append(h)
        if group_tracks:
            groups.append((label, group_tracks))

    if not all_tracks:
        return f"(no matches for queries: {', '.join(queries)})"

    _write_queue_file("search", {"tracks": all_tracks, "index": 0, "expected_title": ""})
    _write_active_mode(context="search")

    lines: list[str] = []
    has_catalog = False
    global_idx = 1

    for label, tracks in groups:
        lines.append(label)
        for h in tracks:
            src = h.get("source", "")
            if src == "library":
                tag = " [资料库]"
            elif src == "apple_music":
                tag = " [Apple Music]"
                has_catalog = True
            elif src == "local":
                tag = " [本地]"
            else:
                tag = ""
            lines.append(f"{global_idx}. {h['title']} — {h.get('artist', '?')} · {h.get('album', '?')}{tag}")
            global_idx += 1
        lines.append("")

    if has_catalog:
        lines.append("💡 [Apple Music] 曲目需要先添加到资料库才能播放。用 play_number() 尝试，Music.app 会自动打开。")
    lines.append("喜欢哪首？说编号我来播。")

    return "\n".join(lines).rstrip()


@mcp.tool()
async def smart_search(
    description: str = "",
    queries: list[str] | None = None,
    limit: int = 8,
) -> str:
    """Natural-language music search for AI callers (Claude Code / Codex CLI).

    **Multi-angle mode (preferred for mood/vibe requests):**
    Pass `queries` with 2–3 keyword expansions of the user's request.
    All queries run in parallel; results are merged, deduplicated, and
    written to a single queue so play_number() indices are correct.

      smart_search(queries=[
          "lofi hip hop late night coding instrumental",
          "lofi jazz late night rain cozy",
          "synthwave retrowave night drive electronic",
      ])

    **Single-angle mode (backwards compat):**
    Pass `description` with pre-expanded music keywords.

      smart_search(description="lofi hip hop late night study")

    IMPORTANT — translate raw user text into music keywords BEFORE calling.

    Mood / emotion
      "安静" / "calm"          → "ambient instrumental chill"
      "想兴奋起来" / "hype"    → "energetic upbeat electronic"
      "放松" / "relax"         → "relaxing calm downtempo"
      "伤感" / "sad"           → "melancholy emotional piano"

    Scene / time
      "深夜写代码"             → "lofi hip hop late night study"
      "早晨跑步"               → "running motivation pop upbeat"
      "专注 / 摸鱼"            → "focus deep work instrumental"
      "通勤路上"               → "commute indie pop"

    Style reference
      "像 Daft Punk 那种"      → "electronic synth funk dance"
      "带点爵士"               → "jazz fusion smooth"
      "复古感"                 → "vintage retro soul funk"
      "纯音乐 / no vocals"     → append "instrumental"

    Results are numbered — use play_number() to play by index.
    """
    import asyncio

    if queries:
        return await _multi_angle_search(queries, limit_per_query=min(limit, 6))

    am_hits, local_hits = await asyncio.gather(
        asyncio.to_thread(get_source("apple_music").search, description, limit),
        asyncio.to_thread(get_source("local").search, description, limit),
    )

    seen: set[str] = set()
    merged: list[dict] = []

    def _dedup_add(hits: list) -> None:
        for h in hits:
            key = f"{h.get('title', '').lower()}|{h.get('artist', '').lower()}"
            if key not in seen:
                seen.add(key)
                merged.append(h)

    _dedup_add(am_hits or [])
    _dedup_add(local_hits or [])

    if not merged:
        return f"(no matches for '{description}')"

    _write_queue_file("search", {"tracks": merged, "index": 0, "expected_title": ""})
    _write_active_mode(context="search")

    lines = []
    has_catalog = False
    for i, h in enumerate(merged):
        src = h.get("source", "")
        if src == "library":
            tag = " [资料库]"
        elif src == "apple_music":
            tag = " [Apple Music]"
            has_catalog = True
        elif src == "local":
            tag = " [本地]"
        else:
            tag = ""
        lines.append(f"{i + 1}. {h['title']} — {h.get('artist', '?')} · {h.get('album', '?')}{tag}")
    if has_catalog:
        lines.append("\n💡 [Apple Music] 曲目需要先添加到资料库才能播放。用 play_number() 尝试，Music.app 会自动打开。")
    return "\n".join(lines)


@mcp.tool()
def play_number(number: int) -> str:
    """Play a track by its 1-based index from the last search or list results."""
    am = _read_active_mode()
    context = am.get("context", "library")
    qdata = _load_queue_file(context)
    hits = qdata.get("tracks", [])
    if not hits or number < 1 or number > len(hits):
        count = len(hits) if hits else 0
        return f"(no match — #{number} out of range, last results had {count} items)"
    hit = hits[number - 1]
    query = f"{hit['title']} {hit.get('artist', '')}".strip()
    st = state.load()
    src = get_source(st.source)
    np = src.play_query(query)

    # Always update queue position so next/prev stay aligned, even when the
    # track can't be played (catalog track, no subscription, etc.).
    effective_title = (np.title if np and not _unsupported_reason(np) else None) or hit.get("title", "?")
    qdata["index"] = number - 1
    qdata["expected_title"] = effective_title
    _write_queue_file(context, qdata)
    _write_active_mode(mode=context)
    _one_off_file().unlink(missing_ok=True)

    if not np:
        return f"(no match for '{query}' in source={st.source})"
    if _unsupported_reason(np) == "preview_playing":
        return _preview_message(np)
    if _unsupported_reason(np) == "needs_library_add":
        title = np.title or hit.get("title", "")
        artist = np.artist or hit.get("artist", "")
        result = _wait_and_play_from_library(src, title, artist)
        if result:
            return result
        return _needs_library_add(np, retry_query=f"{title} {artist}".strip())
    if _unsupported_reason(np):
        return _unsupported(np.source or st.source, "play_number", _unsupported_reason(np))
    if not np.title:
        return _unsupported(st.source, "play_number", "The source returned no playable track.")
    _refresh_now_playing()
    return f"▶ now playing: {np.title} — {np.artist or '—'}  source={np.source}"


@mcp.tool()
def play_song(query: str) -> str:
    """Search for and start playing the first match for 'query'."""
    am = _read_active_mode()
    mode = am.get("mode", "library")
    qdata = _load_queue_file(mode)
    has_queue = bool(qdata.get("tracks"))
    st = state.load()
    src = get_source(st.source)
    np = src.play_query(query)
    if not np:
        return f"(no match for '{query}' in source={st.source})"
    if _unsupported_reason(np) == "preview_playing":
        return _preview_message(np)
    if _unsupported_reason(np) == "needs_library_add":
        result = _wait_and_play_from_library(src, np.title or "", np.artist or "")
        if result:
            return result
        retry = f"{np.title or ''} {np.artist or ''}".strip()
        return _needs_library_add(np, retry_query=retry)
    if _unsupported_reason(np):
        return _unsupported(np.source or st.source, "play_song", _unsupported_reason(np))
    if not np.title:
        return _unsupported(st.source, "play_song", "The source returned no playable track.")
    if has_queue:
        try:
            _one_off_file().write_text(
                json.dumps(
                    {
                        "one_off_title": np.title,
                        "resume_mode": mode,
                        "resume_index": qdata.get("index", 0) + 1,
                    }
                ),
                encoding="utf-8",
            )
        except Exception:
            pass
    else:
        _one_off_file().unlink(missing_ok=True)
    _refresh_now_playing()
    return f"▶ now playing: {np.title} — {np.artist or '—'}  source={np.source}"


@mcp.tool()
def set_source(name: str) -> str:
    """Switch the active music source. name ∈ {apple_music, local, qq_music}."""
    try:
        src = get_source(name)
    except ValueError as e:
        return f"error: {e}"
    st = state.load()
    st.source = src.name
    state.save(st)
    return f"source = {src.name}"


@mcp.tool()
def show_cover(style: str = "rgb", width: int = 32, height: int = 16) -> str:
    """Render the current track's album cover as pixel ASCII.
    style: 'rgb' (true-color photo) or 'gameboy' (4-color retro)."""
    st, np = _refresh_now_playing()
    if _unsupported_reason(np):
        return _unsupported(np.source or st.source, "show_cover", _unsupported_reason(np))
    if style == "gameboy":
        art = render_cover_gameboy(np.artwork_path, width=width, height=height)
    else:
        art = render_cover(np.artwork_path, width=width, height=height)
    return art


def _current_lyrics() -> Optional[str]:
    """Get LRC/plain lyric text from the active source, if it supports it."""
    st = state.load()
    src = get_source(st.source)
    fn = getattr(src, "lyrics", None)
    if not callable(fn):
        return None
    try:
        return fn()
    except Exception:
        return None


@mcp.tool()
def show_player(width: int = 36, with_lyrics: bool = True) -> str:
    """Render the full retro player: pixel cover + title + progress + spectrum +
    DJ Buddy sprite + (optionally) live lyrics. The 'whole experience' in one call."""
    st, np = _refresh_now_playing()
    if _unsupported_reason(np):
        return _unsupported(np.source or st.source, "show_player", _unsupported_reason(np))
    cover = render_cover(np.artwork_path, width=width, height=int(width * 0.45))
    title = np.title or "(no track)"
    artist = np.artist or "—"
    progress = render_progress(np.position, np.duration, width=width - 2)
    spec = render_spectrum_color(np.position, width=width - 2)
    buddy = dj.sprite(st.dj_mood or "neutral")
    quip = dj.quip(st.dj_mood or "neutral")
    lines = [
        cover,
        f"\x1b[1;38;2;255;230;100m♪ {title}\x1b[0m",
        f"\x1b[38;2;180;180;200m  {artist}\x1b[0m",
        progress,
        spec,
    ]
    box_width = max(width + 4, 40)
    inner_w = box_width - 2
    if with_lyrics and np.title:
        lrc = _current_lyrics()
        if lrc:
            lines.append("\x1b[38;2;90;90;105m─── lyrics ───\x1b[0m")
            lines.append(
                render_lyrics_window(
                    lrc,
                    position=np.position,
                    duration=np.duration,
                    window=5,
                    width=inner_w,
                )
            )
    lines.append(f"\x1b[38;2;155;188;15m{buddy}\x1b[0m")
    lines.append(f'\x1b[3;38;2;200;200;230m  "{quip}"\x1b[0m')
    body = "\n".join(lines)
    return boxed(f"CWB · {st.source}", body, width=box_width)


@mcp.tool()
def show_lyrics(window: int = 7, width: int = 0) -> str:
    """Render a karaoke-style lyrics window for the currently playing track.
    Pulls timed LRC lyrics from the active source (Apple Music falls back to
    NetEase's public lyric API when AppleScript can't read catalog lyrics).
    Active line is picked by current playback position.
    width: terminal column count for wrapping (0 = auto-detect)."""
    st, np = _refresh_now_playing()
    if _unsupported_reason(np):
        return _unsupported(np.source or st.source, "show_lyrics", _unsupported_reason(np))
    if not np.title:
        return "(no track playing)"
    lrc = _current_lyrics()
    if not lrc:
        return f"(no lyrics found for: {np.title} — {np.artist})"
    return render_lyrics_window(
        lrc,
        position=np.position,
        duration=np.duration,
        window=window,
        width=width if width > 0 else None,
    )


@mcp.tool()
def dj_say(mood: str = "") -> str:
    """DJ Buddy drops a one-liner in character. If mood is empty, uses the
    current vibe-derived mood. Useful for breaking up long debugging sessions."""
    st = state.load()
    m = mood or st.dj_mood or "neutral"
    return f"{dj.face(m)}  “{dj.quip(m)}”"


@mcp.tool()
async def companion_check(trigger: str) -> str:
    """DJ Buddy companion check-in.

    trigger must be one of: session_start, debug_struggle, victory,
    idle_checkin, session_end.

    Call this proactively at key moments:
    - session_start: in your first reply of a new session
    - debug_struggle: after observing 3+ consecutive test/command failures
    - victory: right after a successful git commit or all tests passing
    - idle_checkin: after 20+ tool calls with no music suggestion in 25+ min
    - session_end: when the user signals they are done (bye, 收工, 下班, etc.)

    Returns a companion card with a caring message and music suggestions,
    or '(not needed right now)' if cooldown is active or conditions unmet.
    When '(not needed right now)' is returned, do NOT mention it to the user.
    """
    from . import companion as _companion

    st = state.load()
    if not _companion.can_trigger(st, trigger):
        return "(not needed right now)"
    queries = _companion.get_queries(trigger)
    try:
        music_results = await _multi_angle_search(queries, limit_per_query=4)
    except Exception:
        music_results = "(music search unavailable — say what you'd like to hear)"
    st.companion_last_at = time.time()
    state.save(st)
    message = _companion.get_message(trigger)
    return _companion_card(message, music_results)


@mcp.tool()
def vibe_set(name: str) -> str:
    """Manually set the vibe (focus|build|debug|victory|fail|idle|review)."""
    st = state.load()
    st.vibe = name
    state.save(st)
    return f"vibe = {name}"


@mcp.tool()
def focus_start() -> str:
    """Start a 25/5 pomodoro loop. Status visible in statusline."""
    s = focus.start()
    return f"🍅 focus on — {s.phase} {s.remaining}s remaining"


@mcp.tool()
def focus_stop() -> str:
    """Stop the pomodoro loop."""
    focus.stop()
    return "focus off"


@mcp.tool()
def focus_status() -> str:
    """Get current focus loop status."""
    s = focus.status()
    if not s.active:
        return "focus off"
    return f"🍅 {s.phase} — {s.remaining}s remaining (cycle {s.cycle})"


@mcp.tool()
def banner() -> str:
    """Print the giant CWB retro banner. Use on SessionStart or when
    the user wants the full intro."""
    return retro_banner("a pixel companion for vibecoding")


@mcp.tool()
def session_intro() -> str:
    """One-shot greeting: banner + current state + a DJ Buddy hello."""
    st, np = _refresh_now_playing()
    parts = [retro_banner("a pixel companion for vibecoding")]
    if np.title:
        parts.append(f"\n♪ {np.title} — {np.artist}  ({st.source})")
    parts.append(f"\n{dj.face('happy')}  {dj.quip('happy')}")
    return "\n".join(parts)


@mcp.tool()
def status() -> str:
    """Return a human-readable coding-with-beat status block."""
    st, np = _refresh_now_playing()
    f = focus.status()
    lines = [
        f"source : {st.source}",
        f"vibe   : {st.vibe}  (mood={st.dj_mood})",
        "focus  : " + (f"{f.phase} — {f.remaining}s left" if f.active else "off"),
    ]
    if _unsupported_reason(np):
        lines.append(f"track  : {_unsupported(np.source or st.source, 'now_playing', _unsupported_reason(np))}")
    elif np.title:
        lines.append(f"track  : {np.title} — {np.artist}")
        lines.append(f"         {int(np.position)}s / {int(np.duration)}s " + ("▶" if np.playing else "❚❚"))
    else:
        lines.append("track  : (none)")
    return "\n".join(lines)


def main(
    host: str | None = None,
    port: int | None = None,
    path: str | None = None,
    stateless_http: bool | None = None,
    log_level: str | None = None,
) -> None:
    if host is not None:
        mcp.settings.host = host
    if port is not None:
        mcp.settings.port = int(port)
    if path is not None:
        mcp.settings.streamable_http_path = _normalize_path(path)
    if stateless_http is not None:
        mcp.settings.stateless_http = stateless_http
    if log_level is not None:
        mcp.settings.log_level = log_level.upper()
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
