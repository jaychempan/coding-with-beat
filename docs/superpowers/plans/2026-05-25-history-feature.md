# History Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add play history recording and history-based recommendations via two new MCP tools — `list_history` and `history_search`.

**Architecture:** Apple Music source reads native `played count` / `played date` via AppleScript (covers all listening, not just CWB sessions). Other sources (QQ Music, local) fall back to a self-written `history.log`. A new `history.py` module centralises analysis logic (frequency, style tags, unheard candidates) and is shared by both paths. Track recording for non-AM sources hooks into `_refresh_now_playing()` in `server.py` — the existing track-change detection point.

**Tech Stack:** Python stdlib only (`datetime`, `collections.Counter`); AppleScript via `osascript` (already used throughout `apple_music.py`); `unittest.mock` for tests; `pytest`.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `coding_with_beat/history.py` | Create | `write`, `read`, `summarize` — all analysis logic |
| `coding_with_beat/sources/apple_music.py` | Modify | Add `play_history(window_days, limit)` method |
| `coding_with_beat/server.py` | Modify | Hook recording into `_refresh_now_playing`; add `list_history` + `history_search` tools |
| `coding_with_beat/state.py` | Modify | Remove dead `write_history` function |
| `tests/test_history.py` | Create | Unit tests for `history.py` |

---

## Task 1: `history.py` — core module

**Files:**
- Create: `coding_with_beat/history.py`
- Test: `tests/test_history.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_history.py
import datetime
from pathlib import Path
from unittest import mock

import pytest

from coding_with_beat import history


# ── write / read ──────────────────────────────────────────────────────────────

def test_read_returns_empty_when_no_log(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "_LOG_FILE", tmp_path / "history.log")
    assert history.read() == []


def test_write_and_read_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "_LOG_FILE", tmp_path / "history.log")
    history.write("Clair de Lune", "Debussy", "Suite bergamasque")
    history.write("夜曲", "周杰伦", "十一月的萧邦")
    entries = history.read()
    assert len(entries) == 2
    # most-recent first
    assert entries[0]["title"] == "夜曲"
    assert entries[0]["artist"] == "周杰伦"
    assert entries[1]["title"] == "Clair de Lune"


def test_write_skips_empty_title(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "_LOG_FILE", tmp_path / "history.log")
    history.write("", "Artist", "Album")
    assert not (tmp_path / "history.log").exists()


def test_read_respects_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "_LOG_FILE", tmp_path / "history.log")
    for i in range(10):
        history.write(f"Track {i}", "Artist", "Album")
    assert len(history.read(limit=3)) == 3


# ── summarize ─────────────────────────────────────────────────────────────────

def _make_track(title, artist, album="Album", days_ago=1):
    ts = datetime.datetime.now() - datetime.timedelta(days=days_ago)
    return {"title": title, "artist": artist, "album": album, "ts": ts}


def test_summarize_top_artists():
    tracks = [
        _make_track("Song A", "周杰伦"),
        _make_track("Song B", "周杰伦"),
        _make_track("Song C", "林俊杰"),
    ]
    result = history.summarize(tracks)
    assert result["top_artists"][0] == ("周杰伦", 2)
    assert result["top_artists"][1] == ("林俊杰", 1)


def test_summarize_style_tags_classical():
    tracks = [_make_track("Nocturne", "Chopin", "Nocturnes")]
    result = history.summarize(tracks)
    assert "classical" in result["style_tags"]


def test_summarize_style_tags_jazz():
    tracks = [_make_track("Blue Note", "Artist", "Jazz Sessions")]
    result = history.summarize(tracks)
    assert "jazz" in result["style_tags"]


def test_summarize_unheard_candidates():
    recent = [_make_track("New Song", "Artist A", days_ago=3)]
    older = [_make_track("Old Song", "Artist B", days_ago=30)]
    result = history.summarize(recent + older, window_days=14)
    titles = [t["title"] for t in result["unheard_candidates"]]
    assert "Old Song" in titles
    assert "New Song" not in titles


def test_summarize_empty_tracks():
    result = history.summarize([])
    assert result["top_artists"] == []
    assert result["style_tags"] == []
    assert result["unheard_candidates"] == []
```

- [ ] **Step 2: Run to confirm tests fail**

```bash
cd /Users/jianchengpan/Projects/coding-with-beat
python -m pytest tests/test_history.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError` or `ImportError` (module doesn't exist yet).

- [ ] **Step 3: Implement `history.py`**

```python
# coding_with_beat/history.py
"""Play history: write (non-AM sources) and analyse (all sources)."""
from __future__ import annotations

import datetime
from collections import Counter

from .config import DATA_DIR, ensure_dirs

_LOG_FILE = DATA_DIR / "history.log"

_STYLE_KEYWORDS: dict[str, list[str]] = {
    "lofi": ["lofi", "lo-fi", "chillhop"],
    "jazz": ["jazz", "bossa", "blues", "swing"],
    "classical": ["classical", "piano", "nocturne", "symphony",
                  "beethoven", "mozart", "bach", "chopin", "satie"],
    "ambient": ["ambient", "drone"],
    "electronic": ["electronic", "电子", "synth", "edm"],
    "华语": ["华语", "国语", "粤语", "中文"],
    "民谣": ["民谣", "folk", "acoustic"],
    "synthwave": ["synthwave", "retrowave", "outrun"],
    "rnb": ["r&b", "rnb", "soul", "funk"],
    "hip-hop": ["hip hop", "hip-hop", "rap", "trap"],
}


def write(title: str, artist: str, album: str) -> None:
    """Append one play record to history.log (non-Apple Music sources only)."""
    if not title:
        return
    ensure_dirs()
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"{ts} | {title} | {artist or '?'} | {album or '?'}\n"
    try:
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def read(limit: int = 100) -> list[dict]:
    """Read the most recent `limit` entries from history.log, most-recent first.
    Each entry: {title, artist, album, ts (datetime)}."""
    try:
        lines = _LOG_FILE.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    result: list[dict] = []
    for line in reversed(lines):
        parts = line.split(" | ", 3)
        if len(parts) < 4:
            continue
        ts_str, title, artist, album = parts
        try:
            ts = datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        result.append({"title": title, "artist": artist, "album": album, "ts": ts})
        if len(result) >= limit:
            break
    return result


def summarize(tracks: list[dict], window_days: int = 14) -> dict:
    """Analyse a flat list of track dicts.

    Each dict must have 'title', 'artist', 'album', and a 'ts' key
    (datetime object). Apple Music dicts from play_history() also work
    because play_history() stores a datetime in 'ts'.

    Returns:
        top_artists: list of (artist, count) sorted by frequency, recent window only
        style_tags: list of style tag strings matched from album/artist text
        unheard_candidates: tracks whose artist hasn't appeared in the recent window
    """
    cutoff = datetime.datetime.now() - datetime.timedelta(days=window_days)

    recent: list[dict] = []
    older: list[dict] = []
    for t in tracks:
        ts = t.get("ts")
        if isinstance(ts, str):
            try:
                ts = datetime.datetime.strptime(ts[:19], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                ts = None
        if ts is None or ts >= cutoff:
            recent.append(t)
        else:
            older.append(t)

    # top artists (recent window)
    artist_counter: Counter = Counter()
    for t in recent:
        a = (t.get("artist") or "").strip()
        if a and a != "?":
            artist_counter[a] += 1
    top_artists = artist_counter.most_common(5)

    # style tags (keyword scan on album + artist of recent tracks)
    tag_counter: Counter = Counter()
    for t in recent:
        text = f"{t.get('artist', '')} {t.get('album', '')}".lower()
        for tag, keywords in _STYLE_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                tag_counter[tag] += 1
    style_tags = [tag for tag, _ in tag_counter.most_common(3)]

    # unheard candidates: artists in older not seen in recent, deduplicated by artist
    recent_artists_lower = {(t.get("artist") or "").strip().lower() for t in recent}
    recent_titles_lower = {(t.get("title") or "").strip().lower() for t in recent}
    seen_unheard: set[str] = set()
    unheard_candidates: list[dict] = []
    for t in older:
        a_lower = (t.get("artist") or "").strip().lower()
        title_lower = (t.get("title") or "").strip().lower()
        if a_lower in recent_artists_lower:
            continue
        if title_lower in recent_titles_lower:
            continue
        if a_lower in seen_unheard:
            continue
        seen_unheard.add(a_lower)
        unheard_candidates.append(t)
        if len(unheard_candidates) >= 5:
            break

    return {
        "top_artists": top_artists,
        "style_tags": style_tags,
        "unheard_candidates": unheard_candidates,
    }
```

- [ ] **Step 4: Run tests — expect all to pass**

```bash
python -m pytest tests/test_history.py -v
```

Expected output: `9 passed`

- [ ] **Step 5: Commit**

```bash
git add coding_with_beat/history.py tests/test_history.py
git commit -m "feat(history): add history.py module with write/read/summarize"
```

---

## Task 2: Apple Music — `play_history()` method

**Files:**
- Modify: `coding_with_beat/sources/apple_music.py`
- Test: `tests/test_history.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_history.py`:

```python
# ── apple_music.play_history ───────────────────────────────────────────────────

def test_play_history_parses_applescript_output():
    from unittest.mock import patch
    from coding_with_beat.sources.apple_music import AppleMusicSource

    fake_osa_output = (
        "Clair de Lune|||Debussy|||Suite bergamasque|||5|||3\n"
        "夜曲|||周杰伦|||十一月的萧邦|||12|||0\n"
    )

    with patch("coding_with_beat.sources.apple_music._osa", return_value=fake_osa_output):
        src = AppleMusicSource()
        result = src.play_history(window_days=14, limit=50)

    assert len(result) == 2
    assert result[0]["title"] == "Clair de Lune"
    assert result[0]["artist"] == "Debussy"
    assert result[0]["played_count"] == 5
    assert isinstance(result[0]["ts"], datetime.datetime)
    assert result[1]["title"] == "夜曲"
    assert result[1]["played_count"] == 12


def test_play_history_returns_empty_on_applescript_error():
    from unittest.mock import patch
    from coding_with_beat.sources.apple_music import AppleMusicSource

    with patch("coding_with_beat.sources.apple_music._osa", side_effect=RuntimeError("fail")):
        src = AppleMusicSource()
        result = src.play_history()

    assert result == []
```

- [ ] **Step 2: Run to confirm tests fail**

```bash
python -m pytest tests/test_history.py::test_play_history_parses_applescript_output tests/test_history.py::test_play_history_returns_empty_on_applescript_error -v
```

Expected: `AttributeError: 'AppleMusicSource' object has no attribute 'play_history'`

- [ ] **Step 3: Find the end of `AppleMusicSource` class in `apple_music.py`**

Locate the last method in the class (around line 800+). Add `play_history` as a new method before the class ends.

- [ ] **Step 4: Implement `play_history` in `apple_music.py`**

Add after the last existing method of `AppleMusicSource` (before any top-level code after the class):

```python
    def play_history(self, window_days: int = 90, limit: int = 100) -> list[dict]:
        """Return tracks played within the last window_days days via AppleScript.

        Each dict has: title, artist, album, played_count (int), ts (datetime).
        Fields are separated by ||| so they survive most title/artist text.
        """
        import datetime as _dt

        script = f"""tell application "Music"
    set cutoff to (current date) - {window_days} * days
    set recentTracks to (every track of library playlist 1 whose played date > cutoff)
    set output to ""
    set n to count of recentTracks
    if n > {limit} then set n to {limit}
    repeat with i from 1 to n
        set t to item i of recentTracks
        set pc to played count of t
        set daysAgo to ((current date) - (played date of t)) div days
        set output to output & (name of t) & "|||" & (artist of t) & "|||" & (album of t) & "|||" & pc & "|||" & daysAgo & linefeed
    end repeat
    return output
end tell"""
        try:
            raw = _osa(script)
        except Exception:
            return []

        now = _dt.datetime.now()
        result: list[dict] = []
        for line in raw.splitlines():
            parts = line.split("|||")
            if len(parts) < 5:
                continue
            title, artist, album, pc_str, days_str = parts[:5]
            try:
                played_count = int(pc_str)
            except ValueError:
                played_count = 0
            try:
                ts = now - _dt.timedelta(days=int(days_str))
            except ValueError:
                ts = now
            result.append({
                "title": title,
                "artist": artist,
                "album": album,
                "played_count": played_count,
                "ts": ts,
            })
        return result
```

- [ ] **Step 5: Run tests — expect all to pass**

```bash
python -m pytest tests/test_history.py -v
```

Expected: `11 passed`

- [ ] **Step 6: Commit**

```bash
git add coding_with_beat/sources/apple_music.py tests/test_history.py
git commit -m "feat(history): add AppleMusicSource.play_history() via AppleScript"
```

---

## Task 3: Record history on track change (non-AM sources)

**Files:**
- Modify: `coding_with_beat/server.py` (lines ~17–18 imports, lines ~266–289 `_refresh_now_playing`)
- Modify: `coding_with_beat/state.py` (remove dead `write_history`)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_history.py`:

```python
# ── server._refresh_now_playing writes history for non-AM ─────────────────────

def test_refresh_now_playing_writes_history_for_non_am_source(tmp_path, monkeypatch):
    import datetime
    from types import SimpleNamespace
    from unittest.mock import MagicMock, patch

    monkeypatch.setattr(history, "_LOG_FILE", tmp_path / "history.log")

    fake_np = SimpleNamespace(
        title="New Song", artist="Artist", album="Album",
        duration=180.0, position=0.0, playing=True,
        artwork_path=None, source="qq_music", unsupported_reason=None,
    )
    fake_state = SimpleNamespace(
        source="qq_music",
        track=SimpleNamespace(
            title="Old Song", artist="Old Artist", album="Old Album",
            duration=200.0, position=0.0, artwork_path=None,
            source="qq_music", lyrics_key="", lyrics_text="",
            lyrics_pending=False, position_sampled_at=0.0,
        ),
        playing=False,
    )

    with (
        patch("coding_with_beat.server.state.load", return_value=fake_state),
        patch("coding_with_beat.server.state.save"),
        patch("coding_with_beat.server.get_source") as mock_gs,
    ):
        src = MagicMock()
        src.now_playing.return_value = fake_np
        mock_gs.return_value = src
        from coding_with_beat.server import _refresh_now_playing
        _refresh_now_playing()

    entries = history.read()
    assert len(entries) == 1
    assert entries[0]["title"] == "New Song"


def test_refresh_now_playing_skips_history_for_apple_music(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import MagicMock, patch

    monkeypatch.setattr(history, "_LOG_FILE", tmp_path / "history.log")

    fake_np = SimpleNamespace(
        title="New Song", artist="Artist", album="Album",
        duration=180.0, position=0.0, playing=True,
        artwork_path=None, source="apple_music", unsupported_reason=None,
    )
    fake_state = SimpleNamespace(
        source="apple_music",
        track=SimpleNamespace(
            title="Old Song", artist="Old Artist", album="Old Album",
            duration=200.0, position=0.0, artwork_path=None,
            source="apple_music", lyrics_key="", lyrics_text="",
            lyrics_pending=False, position_sampled_at=0.0,
        ),
        playing=False,
    )

    with (
        patch("coding_with_beat.server.state.load", return_value=fake_state),
        patch("coding_with_beat.server.state.save"),
        patch("coding_with_beat.server.get_source") as mock_gs,
    ):
        src = MagicMock()
        src.now_playing.return_value = fake_np
        mock_gs.return_value = src
        from coding_with_beat.server import _refresh_now_playing
        _refresh_now_playing()

    assert not (tmp_path / "history.log").exists()
```

- [ ] **Step 2: Run to confirm tests fail**

```bash
python -m pytest tests/test_history.py::test_refresh_now_playing_writes_history_for_non_am_source tests/test_history.py::test_refresh_now_playing_skips_history_for_apple_music -v
```

Expected: both FAIL (no history.write call in server.py yet).

- [ ] **Step 3: Add `history` import to `server.py`**

Find line 17 in `server.py`:
```python
from . import dj, focus, state
```
Change to:
```python
from . import dj, focus, history, state
```

- [ ] **Step 4: Hook history write into `_refresh_now_playing`**

Find this block in `_refresh_now_playing` (around line 267):
```python
def _refresh_now_playing():
    st = state.load()
    old_key = track_key(st.track.source or st.source, st.track.artist, st.track.album, st.track.title)
    src = get_source(st.source)
    np = src.now_playing()
```

Add `prev_title` capture and the history write. The full function after edit:

```python
def _refresh_now_playing():
    st = state.load()
    old_key = track_key(st.track.source or st.source, st.track.artist, st.track.album, st.track.title)
    prev_title = st.track.title
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
            if st.source != "apple_music" and prev_title:
                history.write(np.title, np.artist, np.album)
            st.track.lyrics_key = ""
            st.track.lyrics_text = ""
            st.track.lyrics_pending = False
    st.track.position_sampled_at = time.time()
    st.playing = np.playing
    state.save(st)
    return st, np
```

- [ ] **Step 5: Remove dead `write_history` from `state.py`**

Find and delete this function from `coding_with_beat/state.py`:

```python
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
```

Also remove the `import datetime` in `state.py` if it is only used by `write_history` (check first with `grep -n "datetime" coding_with_beat/state.py`).

- [ ] **Step 6: Run all history tests**

```bash
python -m pytest tests/test_history.py -v
```

Expected: `13 passed`

- [ ] **Step 7: Run full test suite to check for regressions**

```bash
python -m pytest --tb=short -q
```

Expected: all existing tests still pass.

- [ ] **Step 8: Commit**

```bash
git add coding_with_beat/server.py coding_with_beat/state.py tests/test_history.py
git commit -m "feat(history): hook track recording into _refresh_now_playing for non-AM sources"
```

---

## Task 4: `list_history` MCP tool

**Files:**
- Modify: `coding_with_beat/server.py`
- Test: `tests/test_history.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_history.py`:

```python
# ── list_history MCP tool ─────────────────────────────────────────────────────

def test_list_history_apple_music_source(tmp_path, monkeypatch):
    import asyncio
    import datetime
    from types import SimpleNamespace
    from unittest.mock import MagicMock, patch

    fake_tracks = [
        {"title": "天空之城", "artist": "久石譲", "album": "OST", "played_count": 9, "ts": datetime.datetime.now()},
        {"title": "夜曲", "artist": "周杰伦", "album": "十一月的萧邦", "played_count": 3, "ts": datetime.datetime.now()},
    ]

    with (
        patch("coding_with_beat.server.state.load",
              return_value=SimpleNamespace(source="apple_music")),
        patch("coding_with_beat.server.get_source") as mock_gs,
    ):
        src = MagicMock()
        src.play_history.return_value = fake_tracks
        mock_gs.return_value = src
        from coding_with_beat.server import list_history
        result = asyncio.run(list_history())

    assert "天空之城" in result
    assert "9次播放" in result
    assert "夜曲" in result
    assert "3次播放" in result


def test_list_history_empty_returns_friendly_message(tmp_path, monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import MagicMock, patch

    with (
        patch("coding_with_beat.server.state.load",
              return_value=SimpleNamespace(source="apple_music")),
        patch("coding_with_beat.server.get_source") as mock_gs,
    ):
        src = MagicMock()
        src.play_history.return_value = []
        mock_gs.return_value = src
        from coding_with_beat.server import list_history
        result = asyncio.run(list_history())

    assert "还没有" in result


def test_list_history_non_am_reads_log(tmp_path, monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import patch

    monkeypatch.setattr(history, "_LOG_FILE", tmp_path / "history.log")
    history.write("Log Track", "Log Artist", "Log Album")

    with patch("coding_with_beat.server.state.load",
               return_value=SimpleNamespace(source="local")):
        from coding_with_beat.server import list_history
        result = asyncio.run(list_history())

    assert "Log Track" in result
```

- [ ] **Step 2: Run to confirm tests fail**

```bash
python -m pytest tests/test_history.py::test_list_history_apple_music_source tests/test_history.py::test_list_history_empty_returns_friendly_message tests/test_history.py::test_list_history_non_am_reads_log -v
```

Expected: `AttributeError` — `list_history` not yet defined.

- [ ] **Step 3: Add `list_history` tool to `server.py`**

Find the `@mcp.tool()` decorator before `list_loved` (around line 646). Insert the new tool immediately before it:

```python
@mcp.tool()
async def list_history(limit: int = 20) -> str:
    """List recently played tracks from play history.
    For Apple Music: reads native played date / play count (covers all listening).
    For other sources: reads ~/.coding-with-beat/history.log."""
    import asyncio as _asyncio

    st = state.load()
    if st.source == "apple_music":
        src = get_source("apple_music")
        fn = getattr(src, "play_history", None)
        if not callable(fn):
            return "(list_history not supported for this Apple Music version)"
        tracks = await _asyncio.to_thread(fn, 30, limit)
    else:
        tracks = history.read(limit=limit)

    if not tracks:
        return "(还没有播放历史，多听一会儿再来试试吧 🎵)"

    lines = [f"最近播放（{len(tracks)} 首）："]
    for i, t in enumerate(tracks):
        title = t.get("title", "?")
        artist = t.get("artist", "?")
        album = t.get("album", "?")
        pc = t.get("played_count", 0)
        suffix = f" · {pc}次播放" if pc else ""
        lines.append(f"{i + 1}. {title} — {artist} · {album}{suffix}")
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests — expect pass**

```bash
python -m pytest tests/test_history.py -v
```

Expected: `16 passed`

- [ ] **Step 5: Commit**

```bash
git add coding_with_beat/server.py tests/test_history.py
git commit -m "feat(history): add list_history MCP tool"
```

---

## Task 5: `history_search` MCP tool

**Files:**
- Modify: `coding_with_beat/server.py`
- Test: `tests/test_history.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_history.py`:

```python
# ── history_search MCP tool ───────────────────────────────────────────────────

def test_history_search_builds_queries_from_history(tmp_path, monkeypatch):
    import asyncio
    import datetime
    from types import SimpleNamespace
    from unittest.mock import MagicMock, patch

    recent_tracks = [
        {"title": "Nocturne Op.9", "artist": "Chopin", "album": "Nocturnes", "ts": datetime.datetime.now()},
        {"title": "Gymnopédie", "artist": "Satie", "album": "Classical Piano", "ts": datetime.datetime.now()},
    ]

    captured_queries: list = []

    async def _fake_multi_angle(queries, **kwargs):
        captured_queries.extend(queries)
        return "1. Result Track — Artist"

    with (
        patch("coding_with_beat.server.state.load",
              return_value=SimpleNamespace(source="apple_music")),
        patch("coding_with_beat.server.get_source") as mock_gs,
        patch("coding_with_beat.server._multi_angle_search", side_effect=_fake_multi_angle),
    ):
        src = MagicMock()
        src.play_history.return_value = recent_tracks
        mock_gs.return_value = src
        from coding_with_beat.server import history_search
        asyncio.run(history_search())

    assert len(captured_queries) >= 1
    # classical style tag should appear in one of the queries
    assert any("classical" in q.lower() or "piano" in q.lower() for q in captured_queries)


def test_history_search_empty_history_returns_message():
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import MagicMock, patch

    with (
        patch("coding_with_beat.server.state.load",
              return_value=SimpleNamespace(source="apple_music")),
        patch("coding_with_beat.server.get_source") as mock_gs,
    ):
        src = MagicMock()
        src.play_history.return_value = []
        mock_gs.return_value = src
        from coding_with_beat.server import history_search
        result = asyncio.run(history_search())

    assert "还没有" in result


```

- [ ] **Step 2: Run to confirm tests fail**

```bash
python -m pytest tests/test_history.py::test_history_search_builds_queries_from_history tests/test_history.py::test_history_search_empty_history_returns_message -v
```

Expected: `AttributeError` — `history_search` not yet defined.

- [ ] **Step 3: Add `history_search` tool to `server.py`**

Add immediately after the `list_history` tool definition:

```python
@mcp.tool()
async def history_search() -> str:
    """Recommend music based on your play history.
    Analyses what you've been listening to and suggests:
    - More of the same style/artist
    - Artists you haven't heard in a while
    Results are numbered — use play_number() to play."""
    import asyncio as _asyncio

    st = state.load()
    if st.source == "apple_music":
        src = get_source("apple_music")
        fn = getattr(src, "play_history", None)
        if not callable(fn):
            return "(history_search not supported for this Apple Music version)"
        tracks = await _asyncio.to_thread(fn, 90, 100)
    else:
        tracks = history.read(limit=100)

    if not tracks:
        return "(还没有播放历史，多听一会儿再来试试吧 🎵)"

    summary = history.summarize(tracks, window_days=14)
    top_artists = summary["top_artists"]
    style_tags = summary["style_tags"]
    unheard = summary["unheard_candidates"]

    queries: list[str] = []

    # Angle 1: style tags from recent listening
    if style_tags:
        queries.append(" ".join(style_tags[:2]) + " instrumental")
    elif top_artists:
        queries.append(f"{top_artists[0][0]} 风格 类似推荐")

    # Angle 2: similar to top artist
    if top_artists:
        queries.append(f"{top_artists[0][0]} 类似 推荐")

    # Angle 3: artists not heard recently
    if unheard:
        unheard_artists = [
            t.get("artist", "")
            for t in unheard[:2]
            if t.get("artist") and t.get("artist") != "?"
        ]
        if unheard_artists:
            queries.append(" ".join(unheard_artists) + " 经典")

    if not queries:
        return "(历史数据不足，多听几首再试试吧)"

    return await _multi_angle_search(queries, label="History · 为你推荐")
```

- [ ] **Step 4: Run all history tests**

```bash
python -m pytest tests/test_history.py -v
```

Expected: `18 passed`

- [ ] **Step 5: Run full suite**

```bash
python -m pytest --tb=short -q
```

Expected: all existing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add coding_with_beat/server.py tests/test_history.py
git commit -m "feat(history): add history_search MCP tool — history-based recommendations"
```

---

## Task 6: Verify with live Apple Music

This task has no automated test (requires a running Music.app with play history).

- [ ] **Step 1: Start the MCP server**

```bash
python -m coding_with_beat server
```

- [ ] **Step 2: Test `list_history` via MCP client**

```bash
python -m coding_with_beat mcp list_history
```

Expected: numbered list of recent tracks with play counts, e.g.:
```
最近播放（20 首）：
1. 天空之城 — 催眠音乐盒 · OST · 9次播放
2. 酒狂 — 龚一 · 古琴 · 2次播放
...
```

- [ ] **Step 3: Test `history_search` via MCP client**

```bash
python -m coding_with_beat mcp history_search
```

Expected: numbered search results grouped by angle, e.g.:
```
🎶 History · 为你推荐

🎹 Classical
1. Gymnopédie No.1 — Satie
2. Experience — Ludovico Einaudi

🕰️ 许久没听
3. 后会无期 — 徐良
```

- [ ] **Step 4: Final push**

```bash
git push origin dev
```
