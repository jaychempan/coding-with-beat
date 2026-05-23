# Dual Queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single `last_results.json` queue with independent library and search queues, add auto-advance when a track ends naturally, and fall back from search queue to library queue when search is exhausted.

**Architecture:** Two queue files (`library_queue.json`, `search_queue.json`) each containing tracks + current index + expected title. `active_mode.json` tracks which queue is playing (`mode`) and which was last listed/searched (`context`). `now_playing_snapshot` polls detect natural track endings and advance the active queue.

**Tech Stack:** Python 3.11+, existing MCP FastMCP server, pytest/unittest, `unittest.mock`

**Spec:** `docs/superpowers/specs/2026-05-23-dual-queue-design.md`

---

## File Map

| File | Change |
|------|--------|
| `coding_with_beat/server.py` | All queue logic changes (Tasks 1–6) |
| `coding_with_beat/watch.py` | Update `_load_queue` (Task 7) |
| `tests/test_queue_management.py` | New test file (Tasks 1–6) |

---

## Task 1: Queue helper functions

**Files:**
- Modify: `coding_with_beat/server.py` (after line 39, before `mcp = FastMCP(...)`)
- Create: `tests/test_queue_management.py`

### Steps

- [ ] **Step 1.1 — Write failing tests for helper functions**

Create `tests/test_queue_management.py`:

```python
import json
import pathlib
import shutil
import tempfile
import unittest
from unittest import mock

import coding_with_beat.server as srv


def _make_tmp():
    return pathlib.Path(tempfile.mkdtemp())


class TestQueueFile(unittest.TestCase):
    def setUp(self):
        self.tmp = _make_tmp()
        self.patch = mock.patch.object(srv, "DATA_DIR", self.tmp)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_load_queue_file_returns_empty_when_missing(self):
        result = srv._load_queue_file("library")
        self.assertEqual(result, {"tracks": [], "index": 0, "expected_title": ""})

    def test_load_queue_file_returns_empty_when_missing_search(self):
        result = srv._load_queue_file("search")
        self.assertEqual(result, {"tracks": [], "index": 0, "expected_title": ""})

    def test_write_and_load_queue_file_roundtrip(self):
        data = {"tracks": [{"title": "Song A"}], "index": 0, "expected_title": "Song A"}
        srv._write_queue_file("library", data)
        result = srv._load_queue_file("library")
        self.assertEqual(result, data)

    def test_library_and_search_queues_are_independent(self):
        lib = {"tracks": [{"title": "Lib Song"}], "index": 0, "expected_title": ""}
        srch = {"tracks": [{"title": "Search Song"}], "index": 0, "expected_title": ""}
        srv._write_queue_file("library", lib)
        srv._write_queue_file("search", srch)
        self.assertEqual(srv._load_queue_file("library")["tracks"][0]["title"], "Lib Song")
        self.assertEqual(srv._load_queue_file("search")["tracks"][0]["title"], "Search Song")


class TestActiveMode(unittest.TestCase):
    def setUp(self):
        self.tmp = _make_tmp()
        self.patch = mock.patch.object(srv, "DATA_DIR", self.tmp)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_read_active_mode_defaults_to_library(self):
        result = srv._read_active_mode()
        self.assertEqual(result, {"mode": "library", "context": "library"})

    def test_write_active_mode_sets_mode(self):
        srv._write_active_mode(mode="search")
        result = srv._read_active_mode()
        self.assertEqual(result["mode"], "search")
        self.assertEqual(result["context"], "library")  # context unchanged

    def test_write_active_mode_sets_context(self):
        srv._write_active_mode(context="search")
        result = srv._read_active_mode()
        self.assertEqual(result["context"], "search")
        self.assertEqual(result["mode"], "library")  # mode unchanged

    def test_write_active_mode_sets_both(self):
        srv._write_active_mode(mode="search", context="search")
        result = srv._read_active_mode()
        self.assertEqual(result, {"mode": "search", "context": "search"})
```

- [ ] **Step 1.2 — Run tests to confirm they fail**

```bash
cd /Users/jianchengpan/Projects/coding-with-beat
python -m pytest tests/test_queue_management.py -v 2>&1 | head -30
```

Expected: `AttributeError: module 'coding_with_beat.server' has no attribute '_load_queue_file'`

- [ ] **Step 1.3 — Add helper functions to server.py**

In `coding_with_beat/server.py`, replace the block starting at line 39:

```python
_ONE_OFF_FILE = DATA_DIR / "one_off_queue.json"
```

with:

```python
def _one_off_file():
    return DATA_DIR / "one_off_queue.json"


def _queue_file(name: str):
    return DATA_DIR / ("library_queue.json" if name == "library" else "search_queue.json")


def _load_queue_file(name: str) -> dict:
    """Load library or search queue. Returns dict with tracks, index, expected_title."""
    try:
        return json.loads(_queue_file(name).read_text(encoding="utf-8"))
    except Exception:
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
        return {"mode": "library", "context": "library"}


def _write_active_mode(mode: str | None = None, context: str | None = None) -> None:
    current = _read_active_mode()
    if mode is not None:
        current["mode"] = mode
    if context is not None:
        current["context"] = context
    try:
        (DATA_DIR / "active_mode.json").write_text(json.dumps(current), encoding="utf-8")
    except Exception:
        pass
```

Also update every reference to `_ONE_OFF_FILE` in server.py (there are 6 occurrences) — replace each with `_one_off_file()`:

```python
# Before:
if not _ONE_OFF_FILE.exists():
_ONE_OFF_FILE.unlink(missing_ok=True)
_ONE_OFF_FILE.write_text(...)
data = json.loads(_ONE_OFF_FILE.read_text(...))

# After:
if not _one_off_file().exists():
_one_off_file().unlink(missing_ok=True)
_one_off_file().write_text(...)
data = json.loads(_one_off_file().read_text(...))
```

- [ ] **Step 1.4 — Run tests to confirm they pass**

```bash
python -m pytest tests/test_queue_management.py -v
```

Expected: all 8 tests PASS

- [ ] **Step 1.5 — Run full test suite to confirm no regressions**

```bash
python -m pytest --tb=short -q
```

Expected: all existing tests PASS

- [ ] **Step 1.6 — Commit**

```bash
git add coding_with_beat/server.py tests/test_queue_management.py
git commit -m "feat: add dual-queue helper functions and _one_off_file() accessor"
```

---

## Task 2: Update `list_library` and `search` tools

**Files:**
- Modify: `coding_with_beat/server.py` (`list_library` at line ~352, `search` at line ~372)
- Modify: `tests/test_queue_management.py`

### Steps

- [ ] **Step 2.1 — Add failing tests**

Append to `tests/test_queue_management.py`:

```python
class TestListLibraryWritesQueue(unittest.TestCase):
    def setUp(self):
        self.tmp = _make_tmp()
        self.p_data = mock.patch.object(srv, "DATA_DIR", self.tmp)
        self.p_data.start()

    def tearDown(self):
        self.p_data.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_list_library_writes_library_queue_json(self):
        fake_tracks = [{"title": "A", "artist": "X", "album": "Y"}]

        class FakeSrc:
            name = "apple_music"
            def list_library(self, limit=100):
                return fake_tracks

        with (
            mock.patch.object(srv, "get_source", return_value=FakeSrc()),
            mock.patch.object(srv.state, "load", return_value=srv.state.JukeboxState()),
        ):
            srv.list_library(limit=1)

        data = srv._load_queue_file("library")
        self.assertEqual(data["tracks"], fake_tracks)
        self.assertEqual(data["index"], 0)
        self.assertEqual(srv._read_active_mode()["context"], "library")

    def test_list_library_does_not_touch_search_queue(self):
        search_data = {"tracks": [{"title": "S"}], "index": 2, "expected_title": "S"}
        srv._write_queue_file("search", search_data)

        class FakeSrc:
            name = "apple_music"
            def list_library(self, limit=100):
                return [{"title": "L", "artist": "", "album": ""}]

        with (
            mock.patch.object(srv, "get_source", return_value=FakeSrc()),
            mock.patch.object(srv.state, "load", return_value=srv.state.JukeboxState()),
        ):
            srv.list_library()

        self.assertEqual(srv._load_queue_file("search"), search_data)


class TestSearchWritesQueue(unittest.TestCase):
    def setUp(self):
        self.tmp = _make_tmp()
        self.p_data = mock.patch.object(srv, "DATA_DIR", self.tmp)
        self.p_data.start()

    def tearDown(self):
        self.p_data.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_search_writes_search_queue_json(self):
        fake_hits = [{"title": "Hit", "artist": "B", "album": "C", "source": "library"}]

        class FakeSrc:
            def search(self, query, limit=8):
                return fake_hits

        with (
            mock.patch.object(srv, "get_source", return_value=FakeSrc()),
            mock.patch.object(srv.state, "load", return_value=srv.state.JukeboxState()),
        ):
            srv.search("hit")

        data = srv._load_queue_file("search")
        self.assertEqual(data["tracks"], fake_hits)
        self.assertEqual(srv._read_active_mode()["context"], "search")

    def test_search_does_not_touch_library_queue(self):
        lib_data = {"tracks": [{"title": "L"}], "index": 5, "expected_title": "L"}
        srv._write_queue_file("library", lib_data)

        class FakeSrc:
            def search(self, query, limit=8):
                return [{"title": "S", "artist": "", "album": ""}]

        with (
            mock.patch.object(srv, "get_source", return_value=FakeSrc()),
            mock.patch.object(srv.state, "load", return_value=srv.state.JukeboxState()),
        ):
            srv.search("s")

        self.assertEqual(srv._load_queue_file("library"), lib_data)

    def test_search_does_not_change_active_mode(self):
        srv._write_active_mode(mode="library")

        class FakeSrc:
            def search(self, query, limit=8):
                return [{"title": "S", "artist": "", "album": ""}]

        with (
            mock.patch.object(srv, "get_source", return_value=FakeSrc()),
            mock.patch.object(srv.state, "load", return_value=srv.state.JukeboxState()),
        ):
            srv.search("s")

        self.assertEqual(srv._read_active_mode()["mode"], "library")
```

- [ ] **Step 2.2 — Run tests to confirm they fail**

```bash
python -m pytest tests/test_queue_management.py::TestListLibraryWritesQueue tests/test_queue_management.py::TestSearchWritesQueue -v 2>&1 | tail -15
```

Expected: FAIL (tools still write `last_results.json`, not queue files)

- [ ] **Step 2.3 — Update `list_library` in server.py**

Replace the `list_library` function body (currently writes to `last_results.json`):

```python
@mcp.tool()
def list_library(limit: int = 100) -> str:
    """List all tracks in the library of the current source."""
    st = state.load()
    src = get_source(st.source)
    fn = getattr(src, "list_library", None)
    if not callable(fn):
        return f"(list not supported for source={st.source})"
    hits = fn(limit=limit)
    if not hits:
        return "(library is empty)"
    _write_queue_file("library", {"tracks": hits, "index": 0, "expected_title": ""})
    _write_active_mode(context="library")
    return "\n".join(
        f"{i + 1}. {h['title']} — {h.get('artist', '?')} · {h.get('album', '?')}" for i, h in enumerate(hits)
    )
```

- [ ] **Step 2.4 — Update `search` in server.py**

Replace the `search` function body:

```python
@mcp.tool()
def search(query: str, limit: int = 8) -> str:
    """Search the current source for tracks matching the query. Returns a
    numbered list. Use this before play_song if multiple matches are likely."""
    st = state.load()
    hits = get_source(st.source).search(query, limit=limit)
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
```

- [ ] **Step 2.5 — Run new tests**

```bash
python -m pytest tests/test_queue_management.py -v
```

Expected: all tests PASS

- [ ] **Step 2.6 — Run full suite**

```bash
python -m pytest --tb=short -q
```

Expected: all existing tests PASS

- [ ] **Step 2.7 — Commit**

```bash
git add coding_with_beat/server.py tests/test_queue_management.py
git commit -m "feat: list_library and search write to independent queue files"
```

---

## Task 3: Update `play_number` and `_play_queue_at`

**Files:**
- Modify: `coding_with_beat/server.py`
- Modify: `tests/test_queue_management.py`

### Steps

- [ ] **Step 3.1 — Add failing tests**

Append to `tests/test_queue_management.py`:

```python
class TestPlayNumber(unittest.TestCase):
    def setUp(self):
        self.tmp = _make_tmp()
        self.p_data = mock.patch.object(srv, "DATA_DIR", self.tmp)
        self.p_data.start()

    def tearDown(self):
        self.p_data.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _fake_np(self, title="Song A", artist="Art"):
        from coding_with_beat.sources.base import NowPlaying
        np = NowPlaying()
        np.title = title
        np.artist = artist
        np.album = "Alb"
        np.duration = 200.0
        np.position = 0.0
        np.playing = True
        np.source = "apple_music"
        return np

    def test_play_number_reads_from_context_queue(self):
        """play_number uses context (search) not library when context=search."""
        lib_tracks = [{"title": "Lib Song", "artist": "L"}]
        srch_tracks = [{"title": "Search Song", "artist": "S"}]
        srv._write_queue_file("library", {"tracks": lib_tracks, "index": 0, "expected_title": ""})
        srv._write_queue_file("search", {"tracks": srch_tracks, "index": 0, "expected_title": ""})
        srv._write_active_mode(context="search")

        played_queries = []

        class FakeSrc:
            def play_query(self, query):
                played_queries.append(query)
                return self._fake_np("Search Song")
            def _fake_np(self, title):
                from coding_with_beat.sources.base import NowPlaying
                np = NowPlaying()
                np.title = title; np.artist = "S"; np.album = ""; np.duration = 200.0
                np.position = 0.0; np.playing = True; np.source = "apple_music"
                return np

        with (
            mock.patch.object(srv, "get_source", return_value=FakeSrc()),
            mock.patch.object(srv.state, "load", return_value=srv.state.JukeboxState()),
            mock.patch.object(srv, "_refresh_now_playing", return_value=(srv.state.JukeboxState(), FakeSrc()._fake_np("Search Song"))),
        ):
            result = srv.play_number(1)

        self.assertIn("Search Song", result)
        self.assertIn("Search Song", played_queries[0])

    def test_play_number_sets_mode_to_context(self):
        srch_tracks = [{"title": "S", "artist": "A"}]
        srv._write_queue_file("search", {"tracks": srch_tracks, "index": 0, "expected_title": ""})
        srv._write_active_mode(context="search", mode="library")

        class FakeSrc:
            def play_query(self, query):
                from coding_with_beat.sources.base import NowPlaying
                np = NowPlaying()
                np.title = "S"; np.artist = "A"; np.album = ""; np.duration = 200.0
                np.position = 0.0; np.playing = True; np.source = "apple_music"
                return np

        with (
            mock.patch.object(srv, "get_source", return_value=FakeSrc()),
            mock.patch.object(srv.state, "load", return_value=srv.state.JukeboxState()),
            mock.patch.object(srv, "_refresh_now_playing", return_value=(srv.state.JukeboxState(), FakeSrc().play_query(""))),
        ):
            srv.play_number(1)

        self.assertEqual(srv._read_active_mode()["mode"], "search")

    def test_play_number_writes_expected_title_to_queue(self):
        srch_tracks = [{"title": "MySong", "artist": "Art"}]
        srv._write_queue_file("search", {"tracks": srch_tracks, "index": 0, "expected_title": ""})
        srv._write_active_mode(context="search")

        class FakeSrc:
            def play_query(self, query):
                from coding_with_beat.sources.base import NowPlaying
                np = NowPlaying()
                np.title = "MySong"; np.artist = "Art"; np.album = ""; np.duration = 200.0
                np.position = 0.0; np.playing = True; np.source = "apple_music"
                return np

        with (
            mock.patch.object(srv, "get_source", return_value=FakeSrc()),
            mock.patch.object(srv.state, "load", return_value=srv.state.JukeboxState()),
            mock.patch.object(srv, "_refresh_now_playing", return_value=(srv.state.JukeboxState(), FakeSrc().play_query(""))),
        ):
            srv.play_number(1)

        data = srv._load_queue_file("search")
        self.assertEqual(data["expected_title"], "MySong")
        self.assertEqual(data["index"], 0)
```

- [ ] **Step 3.2 — Run tests to confirm they fail**

```bash
python -m pytest tests/test_queue_management.py::TestPlayNumber -v 2>&1 | tail -10
```

Expected: FAIL

- [ ] **Step 3.3 — Replace `_play_queue_at` in server.py**

Replace the entire `_play_queue_at` function:

```python
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
    title = (np.title if np else None) or hit.get("title", "?")
    qdata["index"] = idx
    qdata["expected_title"] = title
    _write_queue_file(queue_name, qdata)
    _write_active_mode(mode=queue_name)
    return f"[{idx + 1}/{len(hits)}] {title}"
```

- [ ] **Step 3.4 — Replace `play_number` in server.py**

Replace the entire `play_number` function:

```python
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
    if not np:
        return f"(no match for '{query}' in source={st.source})"
    if _unsupported_reason(np) == "preview_playing":
        return _preview_message(np)
    if _unsupported_reason(np) == "needs_library_add":
        return _needs_library_add(np)
    if _unsupported_reason(np):
        return _unsupported(np.source or st.source, "play_number", _unsupported_reason(np))
    if not np.title:
        return _unsupported(st.source, "play_number", "The source returned no playable track.")
    qdata["index"] = number - 1
    qdata["expected_title"] = np.title
    _write_queue_file(context, qdata)
    _write_active_mode(mode=context)
    _one_off_file().unlink(missing_ok=True)
    _refresh_now_playing()
    return f"▶ now playing: {np.title} — {np.artist or '—'}  source={np.source}"
```

- [ ] **Step 3.5 — Run new tests**

```bash
python -m pytest tests/test_queue_management.py -v
```

Expected: all tests PASS

- [ ] **Step 3.6 — Run full suite**

```bash
python -m pytest --tb=short -q
```

Expected: all tests PASS

- [ ] **Step 3.7 — Commit**

```bash
git add coding_with_beat/server.py tests/test_queue_management.py
git commit -m "feat: play_number and _play_queue_at use dual-queue state"
```

---

## Task 4: Update `next_track` and `prev_track`

**Files:**
- Modify: `coding_with_beat/server.py`
- Modify: `tests/test_queue_management.py`

### Steps

- [ ] **Step 4.1 — Add failing tests**

Append to `tests/test_queue_management.py`:

```python
class TestNextPrev(unittest.TestCase):
    def setUp(self):
        self.tmp = _make_tmp()
        self.p_data = mock.patch.object(srv, "DATA_DIR", self.tmp)
        self.p_data.start()

    def tearDown(self):
        self.p_data.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _fake_play_queue_at(self, calls):
        def _fake(idx, queue_name=None):
            calls.append((idx, queue_name))
            return f"[{idx+1}] played"
        return _fake

    def test_next_track_advances_search_queue(self):
        tracks = [{"title": f"S{i}", "artist": ""} for i in range(3)]
        srv._write_queue_file("search", {"tracks": tracks, "index": 0, "expected_title": "S0"})
        srv._write_active_mode(mode="search")

        calls = []
        with mock.patch.object(srv, "_play_queue_at", side_effect=self._fake_play_queue_at(calls)):
            result = srv.next_track()

        self.assertEqual(calls[0], (1, "search"))
        self.assertIn("next", result)

    def test_next_track_falls_back_to_library_when_search_exhausted(self):
        srch_tracks = [{"title": "S0", "artist": ""}]
        lib_tracks = [{"title": "L0", "artist": ""}, {"title": "L1", "artist": ""}]
        srv._write_queue_file("search", {"tracks": srch_tracks, "index": 0, "expected_title": "S0"})
        srv._write_queue_file("library", {"tracks": lib_tracks, "index": 1, "expected_title": "L1"})
        srv._write_active_mode(mode="search")

        calls = []
        with mock.patch.object(srv, "_play_queue_at", side_effect=self._fake_play_queue_at(calls)):
            result = srv.next_track()

        # Should fall back to library at its current index
        self.assertEqual(calls[0][1], "library")
        self.assertIn("library", result)

    def test_prev_track_goes_back_in_active_queue(self):
        tracks = [{"title": f"S{i}", "artist": ""} for i in range(3)]
        srv._write_queue_file("library", {"tracks": tracks, "index": 2, "expected_title": "S2"})
        srv._write_active_mode(mode="library")

        calls = []
        with mock.patch.object(srv, "_play_queue_at", side_effect=self._fake_play_queue_at(calls)):
            result = srv.prev_track()

        self.assertEqual(calls[0], (1, "library"))

    def test_next_track_clears_one_off_file(self):
        srv._one_off_file().write_text("{}")
        tracks = [{"title": "S0", "artist": ""}, {"title": "S1", "artist": ""}]
        srv._write_queue_file("library", {"tracks": tracks, "index": 0, "expected_title": "S0"})
        srv._write_active_mode(mode="library")

        with mock.patch.object(srv, "_play_queue_at", return_value="ok"):
            srv.next_track()

        self.assertFalse(srv._one_off_file().exists())
```

- [ ] **Step 4.2 — Run tests to confirm they fail**

```bash
python -m pytest tests/test_queue_management.py::TestNextPrev -v 2>&1 | tail -10
```

Expected: FAIL

- [ ] **Step 4.3 — Replace `next_track` in server.py**

```python
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
                _write_active_mode(mode="library")
                result = _play_queue_at(lib_data.get("index", 0), "library")
                return f"⏭ next (→ library)  {result}"
    st = state.load()
    get_source(st.source).next()
    _refresh_after_control()
    return "⏭ next"
```

- [ ] **Step 4.4 — Replace `prev_track` in server.py**

```python
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
    st = state.load()
    get_source(st.source).prev()
    _refresh_after_control()
    return "⏮ prev"
```

- [ ] **Step 4.5 — Remove dead code**

Delete the `_read_queue_index` and `_write_queue_index` functions from server.py (they are no longer called by anything).

- [ ] **Step 4.6 — Run new tests**

```bash
python -m pytest tests/test_queue_management.py -v
```

Expected: all tests PASS

- [ ] **Step 4.7 — Run full suite**

```bash
python -m pytest --tb=short -q
```

Expected: all tests PASS

- [ ] **Step 4.8 — Commit**

```bash
git add coding_with_beat/server.py tests/test_queue_management.py
git commit -m "feat: next/prev use dual-queue mode with search→library fallback"
```

---

## Task 5: Update `play_song` and `_maybe_resume_queue`

**Files:**
- Modify: `coding_with_beat/server.py`
- Modify: `tests/test_queue_management.py`

### Steps

- [ ] **Step 5.1 — Add failing tests**

Append to `tests/test_queue_management.py`:

```python
class TestPlaySongAndResume(unittest.TestCase):
    def setUp(self):
        self.tmp = _make_tmp()
        self.p_data = mock.patch.object(srv, "DATA_DIR", self.tmp)
        self.p_data.start()

    def tearDown(self):
        self.p_data.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_np(self, title, playing=True):
        from coding_with_beat.sources.base import NowPlaying
        np = NowPlaying()
        np.title = title; np.artist = "A"; np.album = "B"
        np.duration = 200.0; np.position = 0.0
        np.playing = playing; np.source = "apple_music"
        return np

    def test_play_song_saves_resume_mode_to_one_off_file(self):
        """play_song with active search queue saves resume_mode=search."""
        srch = {"tracks": [{"title": "S0", "artist": ""}], "index": 0, "expected_title": "S0"}
        srv._write_queue_file("search", srch)
        srv._write_active_mode(mode="search")

        class FakeSrc:
            def play_query(self, q):
                from coding_with_beat.sources.base import NowPlaying
                np = NowPlaying()
                np.title = "One Off"; np.artist = ""; np.album = ""; np.duration = 180.0
                np.position = 0.0; np.playing = True; np.source = "apple_music"
                return np

        with (
            mock.patch.object(srv, "get_source", return_value=FakeSrc()),
            mock.patch.object(srv.state, "load", return_value=srv.state.JukeboxState()),
            mock.patch.object(srv, "_refresh_now_playing", return_value=(srv.state.JukeboxState(), FakeSrc().play_query(""))),
        ):
            srv.play_song("One Off")

        import json as _json
        data = _json.loads(srv._one_off_file().read_text())
        self.assertEqual(data["resume_mode"], "search")
        self.assertEqual(data["one_off_title"], "One Off")

    def test_maybe_resume_queue_uses_resume_mode(self):
        """_maybe_resume_queue resumes the correct queue when title changes."""
        srch = {"tracks": [{"title": "S0", "artist": ""}, {"title": "S1", "artist": ""}],
                "index": 0, "expected_title": "S0"}
        srv._write_queue_file("search", srch)

        import json as _json
        srv._one_off_file().write_text(_json.dumps({
            "one_off_title": "One Off",
            "resume_mode": "search",
            "resume_index": 1,
        }))

        played = []
        with mock.patch.object(srv, "_play_queue_at", side_effect=lambda idx, qn=None: played.append((idx, qn))):
            srv._maybe_resume_queue(self._make_np("S1"))  # title changed from one-off

        self.assertEqual(played[0], (1, "search"))
        self.assertFalse(srv._one_off_file().exists())

    def test_maybe_resume_queue_does_nothing_when_still_on_one_off(self):
        import json as _json
        srv._one_off_file().write_text(_json.dumps({
            "one_off_title": "One Off",
            "resume_mode": "library",
            "resume_index": 2,
        }))
        played = []
        with mock.patch.object(srv, "_play_queue_at", side_effect=lambda idx, qn=None: played.append((idx, qn))):
            srv._maybe_resume_queue(self._make_np("One Off"))  # same title

        self.assertEqual(played, [])
        self.assertTrue(srv._one_off_file().exists())
```

- [ ] **Step 5.2 — Run tests to confirm they fail**

```bash
python -m pytest tests/test_queue_management.py::TestPlaySongAndResume -v 2>&1 | tail -10
```

Expected: FAIL

- [ ] **Step 5.3 — Update `_maybe_resume_queue` in server.py**

Replace the function:

```python
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
```

- [ ] **Step 5.4 — Update `play_song` in server.py**

Replace the `play_song` function:

```python
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
        return _needs_library_add(np)
    if _unsupported_reason(np):
        return _unsupported(np.source or st.source, "play_song", _unsupported_reason(np))
    if not np.title:
        return _unsupported(st.source, "play_song", "The source returned no playable track.")
    if has_queue:
        try:
            _one_off_file().write_text(
                json.dumps({
                    "one_off_title": np.title,
                    "resume_mode": mode,
                    "resume_index": qdata.get("index", 0) + 1,
                }),
                encoding="utf-8",
            )
        except Exception:
            pass
    else:
        _one_off_file().unlink(missing_ok=True)
    _refresh_now_playing()
    return f"▶ now playing: {np.title} — {np.artist or '—'}  source={np.source}"
```

- [ ] **Step 5.5 — Run new tests**

```bash
python -m pytest tests/test_queue_management.py -v
```

Expected: all tests PASS

- [ ] **Step 5.6 — Run full suite**

```bash
python -m pytest --tb=short -q
```

Expected: all tests PASS

- [ ] **Step 5.7 — Commit**

```bash
git add coding_with_beat/server.py tests/test_queue_management.py
git commit -m "feat: play_song saves resume_mode, _maybe_resume_queue respects it"
```

---

## Task 6: Add `_auto_advance_if_needed`

**Files:**
- Modify: `coding_with_beat/server.py`
- Modify: `tests/test_queue_management.py`

### Steps

- [ ] **Step 6.1 — Add failing tests**

Append to `tests/test_queue_management.py`:

```python
class TestAutoAdvance(unittest.TestCase):
    def setUp(self):
        self.tmp = _make_tmp()
        self.p_data = mock.patch.object(srv, "DATA_DIR", self.tmp)
        self.p_data.start()
        # Reset module-level state tracker
        srv._np_state.update({"title": "", "position": 0.0, "duration": 0.0})

    def tearDown(self):
        self.p_data.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_np(self, title, position=0.0, duration=200.0, playing=True):
        from coding_with_beat.sources.base import NowPlaying
        np = NowPlaying()
        np.title = title; np.artist = "A"; np.album = "B"
        np.duration = duration; np.position = position
        np.playing = playing; np.source = "apple_music"
        return np

    def test_auto_advance_triggers_on_natural_end(self):
        """Title change after position near duration → advance queue."""
        tracks = [{"title": "S0", "artist": ""}, {"title": "S1", "artist": ""}]
        srv._write_queue_file("library", {"tracks": tracks, "index": 0, "expected_title": "S0"})
        srv._write_active_mode(mode="library")

        # Simulate previous snapshot: S0 at 198s / 200s (near end)
        srv._np_state.update({"title": "S0", "position": 198.0, "duration": 200.0})

        played = []
        with mock.patch.object(srv, "_play_queue_at", side_effect=lambda idx, qn=None: played.append((idx, qn))):
            srv._auto_advance_if_needed(self._make_np("S1", position=0.0, duration=200.0))

        self.assertEqual(played[0], (1, "library"))

    def test_auto_advance_does_not_trigger_on_external_switch(self):
        """Title change when position was mid-song → external switch, no advance."""
        tracks = [{"title": "S0", "artist": ""}, {"title": "S1", "artist": ""}]
        srv._write_queue_file("library", {"tracks": tracks, "index": 0, "expected_title": "S0"})
        srv._write_active_mode(mode="library")

        # Simulate previous snapshot: S0 at 60s / 200s (mid-song)
        srv._np_state.update({"title": "S0", "position": 60.0, "duration": 200.0})

        played = []
        with mock.patch.object(srv, "_play_queue_at", side_effect=lambda idx, qn=None: played.append((idx, qn))):
            srv._auto_advance_if_needed(self._make_np("External Song"))

        self.assertEqual(played, [])

    def test_auto_advance_does_not_trigger_when_title_unchanged(self):
        srv._np_state.update({"title": "S0", "position": 198.0, "duration": 200.0})
        played = []
        with mock.patch.object(srv, "_play_queue_at", side_effect=lambda idx, qn=None: played.append((idx, qn))):
            srv._auto_advance_if_needed(self._make_np("S0"))
        self.assertEqual(played, [])

    def test_auto_advance_falls_back_to_library_when_search_exhausted(self):
        srch = [{"title": "S0", "artist": ""}]
        lib = [{"title": "L0", "artist": ""}, {"title": "L1", "artist": ""}]
        srv._write_queue_file("search", {"tracks": srch, "index": 0, "expected_title": "S0"})
        srv._write_queue_file("library", {"tracks": lib, "index": 1, "expected_title": "L1"})
        srv._write_active_mode(mode="search")

        srv._np_state.update({"title": "S0", "position": 198.0, "duration": 200.0})

        played = []
        with mock.patch.object(srv, "_play_queue_at", side_effect=lambda idx, qn=None: played.append((idx, qn))):
            srv._auto_advance_if_needed(self._make_np("something new"))

        # Should fall back to library at its saved index
        self.assertEqual(played[0][1], "library")
        self.assertEqual(srv._read_active_mode()["mode"], "library")

    def test_auto_advance_skips_when_one_off_active(self):
        import json as _json
        srv._one_off_file().write_text(_json.dumps({"one_off_title": "OO", "resume_mode": "library", "resume_index": 0}))
        srv._np_state.update({"title": "OO", "position": 198.0, "duration": 200.0})

        played = []
        with mock.patch.object(srv, "_play_queue_at", side_effect=lambda idx, qn=None: played.append((idx, qn))):
            srv._auto_advance_if_needed(self._make_np("Next Song"))

        self.assertEqual(played, [])

    def test_auto_advance_only_fires_for_cwb_managed_tracks(self):
        """If expected_title doesn't match prev title, it's not a cwb track."""
        tracks = [{"title": "CWB Song", "artist": ""}]
        srv._write_queue_file("library", {"tracks": tracks, "index": 0, "expected_title": "CWB Song"})
        srv._write_active_mode(mode="library")

        # Previous track was something else (not cwb-managed)
        srv._np_state.update({"title": "External Track", "position": 198.0, "duration": 200.0})

        played = []
        with mock.patch.object(srv, "_play_queue_at", side_effect=lambda idx, qn=None: played.append((idx, qn))):
            srv._auto_advance_if_needed(self._make_np("Another External"))

        self.assertEqual(played, [])
```

- [ ] **Step 6.2 — Run tests to confirm they fail**

```bash
python -m pytest tests/test_queue_management.py::TestAutoAdvance -v 2>&1 | tail -15
```

Expected: FAIL (`AttributeError: module has no attribute '_np_state'`)

- [ ] **Step 6.3 — Add `_np_state` and `_auto_advance_if_needed` to server.py**

Add after the `_write_active_mode` function (before `mcp = FastMCP(...)`):

```python
_NATURAL_END_THRESHOLD = 5.0
_np_state: dict = {"title": "", "position": 0.0, "duration": 0.0}


def _auto_advance_if_needed(np) -> None:
    """Auto-advance the active queue when a cwb-managed track ends naturally.

    Distinguishes natural end (position near duration) from external switch
    (position mid-song) so cwb does not steal control when the user clicks
    a different song in Music.app.
    """
    current_title = np.title or ""
    current_position = float(np.position or 0.0)
    current_duration = float(np.duration or 0.0)

    prev_title = _np_state["title"]
    prev_position = _np_state["position"]
    prev_duration = _np_state["duration"]

    _np_state["title"] = current_title
    _np_state["position"] = current_position
    _np_state["duration"] = current_duration

    if not current_title or current_title == prev_title:
        return
    if _one_off_file().exists():
        return  # _maybe_resume_queue handles one-off resumption
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
```

- [ ] **Step 6.4 — Wire into `now_playing_snapshot`**

In `now_playing_snapshot`, add `_auto_advance_if_needed(np)` after `_maybe_resume_queue`:

```python
@mcp.tool()
def now_playing_snapshot(known_lyrics_key: str = "") -> str:
    """Return structured now-playing data as JSON for terminal integrations."""
    st, np = _refresh_now_playing()
    _maybe_resume_queue(np)
    _auto_advance_if_needed(np)
    return json.dumps(_now_playing_payload(st, np, known_lyrics_key), ensure_ascii=False)
```

- [ ] **Step 6.5 — Run new tests**

```bash
python -m pytest tests/test_queue_management.py -v
```

Expected: all tests PASS

- [ ] **Step 6.6 — Run full suite**

```bash
python -m pytest --tb=short -q
```

Expected: all tests PASS

- [ ] **Step 6.7 — Commit**

```bash
git add coding_with_beat/server.py tests/test_queue_management.py
git commit -m "feat: auto-advance queue on natural track end, skip external switches"
```

---

## Task 7: Update `watch.py` `_load_queue`

**Files:**
- Modify: `coding_with_beat/watch.py` (line 121)

### Steps

- [ ] **Step 7.1 — Replace `_load_queue` in watch.py**

Replace the entire `_load_queue` function:

```python
def _load_queue() -> tuple[list[dict], int]:
    try:
        am = json.loads((DATA_DIR / "active_mode.json").read_text(encoding="utf-8"))
        mode = am.get("mode", "library")
    except Exception:
        mode = "library"
    fname = "library_queue.json" if mode == "library" else "search_queue.json"
    try:
        data = json.loads((DATA_DIR / fname).read_text(encoding="utf-8"))
        tracks = data.get("tracks", [])
        cur_idx = int(data.get("index", -1))
    except Exception:
        tracks = []
        cur_idx = -1
    return tracks, cur_idx
```

- [ ] **Step 7.2 — Run full suite**

```bash
python -m pytest --tb=short -q
```

Expected: all tests PASS

- [ ] **Step 7.3 — Commit**

```bash
git add coding_with_beat/watch.py
git commit -m "feat: watch _load_queue reads from active mode queue file"
```

---

## Self-Review

**Spec coverage:**
- ✅ Library and search queues independent (`library_queue.json`, `search_queue.json`)
- ✅ `list_library` writes library queue, `search` writes search queue — Task 2
- ✅ `play_number` reads from `context` queue — Task 3
- ✅ `next`/`prev` use `mode` queue with search→library fallback — Task 4
- ✅ `play_song` saves `resume_mode` — Task 5
- ✅ `_maybe_resume_queue` uses `resume_mode` — Task 5
- ✅ Auto-advance on natural end — Task 6
- ✅ External switch detection (position threshold) — Task 6
- ✅ watch.py right panel shows active queue — Task 7
- ✅ Default state = library for both mode and context — handled by `_read_active_mode` fallback

**Placeholder scan:** No TBDs or incomplete steps.

**Type consistency:** `_play_queue_at(idx: int, queue_name: str | None = None)` used consistently in Tasks 3, 4, 5, 6. `_load_queue_file` / `_write_queue_file` take `"library"` or `"search"` string throughout.
