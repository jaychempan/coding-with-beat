# Loved Tracks Support — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface Apple Music "loved" tracks as a first-class `source="loved"` value: tagged `[♥ 喜欢]`, ranked first in search results, searchable in isolation, and prioritised in companion check-in recommendations.

**Architecture:** Three layers of change — (1) data layer: new AppleScript queries in `apple_music.py`; (2) presentation layer: shared sort/tag helpers in `server.py` consumed by all search paths; (3) routing layer: two new MCP tools + CLAUDE.md rules for intent dispatch.

**Tech Stack:** Python 3.10+, AppleScript via `_osa()`, FastMCP, unittest.mock

---

## File Map

| File | Change |
|---|---|
| `coding_with_beat/sources/base.py` | Add `list_loved` + `search_loved` stubs to Protocol |
| `coding_with_beat/sources/apple_music.py` | Extend `search()` with loved field; add `list_loved()`, `search_loved()` |
| `coding_with_beat/server.py` | Add `_SOURCE_ORDER`, `_source_tag()`, `_sort_by_source()`; update `search`, `_multi_angle_search`, `smart_search`; add `list_loved`, `search_loved` MCP tools; update `companion_check` |
| `install.sh` | Add loved routing rules to CLAUDE.md injection block |
| `tests/test_apple_music.py` | Tests for new apple_music methods |
| `tests/test_smart_search.py` | Tests for sort helpers and loved tag in search output |

---

### Task 1: Base protocol stubs

**Files:**
- Modify: `coding_with_beat/sources/base.py`

- [ ] **Step 1: Add stubs to MusicSource Protocol**

Open `coding_with_beat/sources/base.py`. After the existing `play_query` line (last method in the Protocol), add:

```python
    def list_loved(self, limit: int = 100) -> List[dict]: ...
    def search_loved(self, query: str, limit: int = 8) -> List[dict]: ...
```

The full Protocol tail should now look like:
```python
    def search(self, query: str, limit: int = 8) -> List[dict]: ...
    def play_query(self, query: str, library_only: bool = False) -> Optional[NowPlaying]: ...
    def list_loved(self, limit: int = 100) -> List[dict]: ...
    def search_loved(self, query: str, limit: int = 8) -> List[dict]: ...
```

- [ ] **Step 2: Verify import unchanged**

Run: `python -c "from coding_with_beat.sources.base import MusicSource; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add coding_with_beat/sources/base.py
git commit -m "feat(loved): add list_loved/search_loved stubs to MusicSource Protocol"
```

---

### Task 2: `apple_music.py` — extend `search()` with loved detection

**Files:**
- Modify: `coding_with_beat/sources/apple_music.py`
- Test: `tests/test_apple_music.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_apple_music.py`:

```python
class AppleMusicLovedSearchTest(unittest.TestCase):
    def test_search_marks_loved_tracks(self):
        """search() sets source='loved' for loved tracks, 'library' for others."""
        SEP = "\x1f"
        raw = (
            f"Loved Song{SEP}Artist A{SEP}Album X{SEP}true\n"
            f"Normal Song{SEP}Artist B{SEP}Album Y{SEP}false\n"
        )
        with mock.patch.object(am, "_osa", return_value=raw):
            with mock.patch.object(am, "_search_catalog_api", return_value=[]):
                results = AppleMusic().search("song", limit=8)
        loved = next(r for r in results if r["title"] == "Loved Song")
        normal = next(r for r in results if r["title"] == "Normal Song")
        self.assertEqual(loved["source"], "loved")
        self.assertEqual(normal["source"], "library")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_apple_music.py::AppleMusicLovedSearchTest -v`
Expected: FAIL — `loved["source"]` is `"library"` not `"loved"`

- [ ] **Step 3: Extend `search()` AppleScript to return loved field**

In `coding_with_beat/sources/apple_music.py`, find the `search()` method's AppleScript. Replace the line that builds `out` inside the repeat loop:

Old:
```applescript
        set out to out & (name of t as string) & SEP & (artist of t as string) & SEP & (album of t as string) & linefeed
```

New:
```applescript
        set out to out & (name of t as string) & SEP & (artist of t as string) & SEP & (album of t as string) & SEP & (loved of t as string) & linefeed
```

Then update the Python parsing block in the same method. Replace:
```python
            if len(parts) >= 3:
                items.append({"title": parts[0], "artist": parts[1], "album": parts[2], "source": "library"})
```

With:
```python
            if len(parts) >= 3:
                is_loved = len(parts) >= 4 and parts[3].strip().lower() == "true"
                items.append({
                    "title": parts[0],
                    "artist": parts[1],
                    "album": parts[2],
                    "source": "loved" if is_loved else "library",
                })
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_apple_music.py::AppleMusicLovedSearchTest -v`
Expected: PASS

- [ ] **Step 5: Run full suite**

Run: `pytest tests/ -q`
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add coding_with_beat/sources/apple_music.py tests/test_apple_music.py
git commit -m "feat(loved): detect loved status in apple_music search() via AppleScript field"
```

---

### Task 3: `apple_music.py` — add `list_loved()`

**Files:**
- Modify: `coding_with_beat/sources/apple_music.py`
- Test: `tests/test_apple_music.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_apple_music.py`:

```python
class AppleMusicListLovedTest(unittest.TestCase):
    def test_list_loved_returns_loved_tracks(self):
        SEP = "\x1f"
        raw = (
            f"Heart Song{SEP}DJ A{SEP}Vol 1\n"
            f"Fave Track{SEP}DJ B{SEP}Vol 2\n"
        )
        with mock.patch.object(am, "_osa", return_value=raw):
            results = AppleMusic().list_loved(limit=10)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["title"], "Heart Song")
        self.assertEqual(results[0]["source"], "loved")

    def test_list_loved_returns_empty_on_error(self):
        with mock.patch.object(am, "_osa", side_effect=RuntimeError("no music")):
            results = AppleMusic().list_loved()
        self.assertEqual(results, [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_apple_music.py::AppleMusicListLovedTest -v`
Expected: FAIL — `AttributeError: 'AppleMusic' object has no attribute 'list_loved'`

- [ ] **Step 3: Implement `list_loved()`**

In `coding_with_beat/sources/apple_music.py`, add after the `list_library()` method:

```python
    def list_loved(self, limit: int = 100) -> List[dict]:
        """Return all loved/hearted tracks in the library, up to limit."""
        script = f"""
tell application "Music"
    set SEP to (ASCII character 31)
    set out to ""
    set lovedTracks to (every track of library playlist 1 whose loved is true)
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_apple_music.py::AppleMusicListLovedTest -v`
Expected: PASS

- [ ] **Step 5: Run full suite**

Run: `pytest tests/ -q`
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add coding_with_beat/sources/apple_music.py tests/test_apple_music.py
git commit -m "feat(loved): add list_loved() to AppleMusic source"
```

---

### Task 4: `apple_music.py` — add `search_loved()`

**Files:**
- Modify: `coding_with_beat/sources/apple_music.py`
- Test: `tests/test_apple_music.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_apple_music.py`:

```python
class AppleMusicSearchLovedTest(unittest.TestCase):
    def test_search_loved_returns_matching_loved_tracks(self):
        SEP = "\x1f"
        raw = f"Rain Song{SEP}Piano Artist{SEP}Calm Album\n"
        with mock.patch.object(am, "_osa", return_value=raw) as mock_osa:
            results = AppleMusic().search_loved("rain", limit=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Rain Song")
        self.assertEqual(results[0]["source"], "loved")
        # Verify AppleScript filtered by loved=true
        script = mock_osa.call_args[0][0]
        self.assertIn("loved is true", script)

    def test_search_loved_returns_empty_on_no_match(self):
        with mock.patch.object(am, "_osa", return_value=""):
            results = AppleMusic().search_loved("xyz", limit=5)
        self.assertEqual(results, [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_apple_music.py::AppleMusicSearchLovedTest -v`
Expected: FAIL — `AttributeError: 'AppleMusic' object has no attribute 'search_loved'`

- [ ] **Step 3: Implement `search_loved()`**

In `coding_with_beat/sources/apple_music.py`, add after `list_loved()`:

```python
    def search_loved(self, query: str, limit: int = 8) -> List[dict]:
        """Search only within loved/hearted tracks."""
        q = query.replace('"', '\\"')
        script = f'''
tell application "Music"
    set SEP to (ASCII character 31)
    set out to ""
    set results to (every track of library playlist 1 whose loved is true and (name contains "{q}" or artist contains "{q}" or album contains "{q}"))
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_apple_music.py::AppleMusicSearchLovedTest -v`
Expected: PASS

- [ ] **Step 5: Run full suite**

Run: `pytest tests/ -q`
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add coding_with_beat/sources/apple_music.py tests/test_apple_music.py
git commit -m "feat(loved): add search_loved() to AppleMusic source"
```

---

### Task 5: `server.py` — source sort/tag helpers

**Files:**
- Modify: `coding_with_beat/server.py`
- Test: `tests/test_smart_search.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_smart_search.py`:

```python
from coding_with_beat.server import _source_tag, _sort_by_source


def test_source_tag_loved():
    assert _source_tag("loved") == " [♥ 喜欢]"


def test_source_tag_library():
    assert _source_tag("library") == " [资料库]"


def test_source_tag_local():
    assert _source_tag("local") == " [本地]"


def test_source_tag_apple_music():
    assert _source_tag("apple_music") == " [Apple Music]"


def test_source_tag_unknown():
    assert _source_tag("") == ""


def test_sort_by_source_order():
    tracks = [
        {"title": "C", "source": "apple_music"},
        {"title": "A", "source": "loved"},
        {"title": "D", "source": "local"},
        {"title": "B", "source": "library"},
    ]
    result = _sort_by_source(tracks)
    assert [t["title"] for t in result] == ["A", "B", "D", "C"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_smart_search.py::test_source_tag_loved tests/test_smart_search.py::test_sort_by_source_order -v`
Expected: FAIL — `ImportError: cannot import name '_source_tag'`

- [ ] **Step 3: Add helpers to `server.py`**

In `coding_with_beat/server.py`, find the `_QUERY_LABEL_MAP` definition (around line 723). Add the following **before** it:

```python
_SOURCE_ORDER: dict[str, int] = {"loved": 0, "library": 1, "local": 2, "apple_music": 3}


def _source_tag(src: str) -> str:
    return {
        "loved": " [♥ 喜欢]",
        "library": " [资料库]",
        "local": " [本地]",
        "apple_music": " [Apple Music]",
    }.get(src, "")


def _sort_by_source(tracks: list[dict]) -> list[dict]:
    return sorted(tracks, key=lambda h: _SOURCE_ORDER.get(h.get("source", ""), 99))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_smart_search.py::test_source_tag_loved tests/test_smart_search.py::test_sort_by_source_order -v`
Expected: PASS

- [ ] **Step 5: Run full suite**

Run: `pytest tests/ -q`
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add coding_with_beat/server.py tests/test_smart_search.py
git commit -m "feat(loved): add _source_tag/_sort_by_source helpers to server.py"
```

---

### Task 6: `server.py` — apply helpers to all search paths

**Files:**
- Modify: `coding_with_beat/server.py`
- Test: `tests/test_smart_search.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_smart_search.py`:

```python
@mock.patch("coding_with_beat.server._write_active_mode")
@mock.patch("coding_with_beat.server._write_queue_file")
@mock.patch("coding_with_beat.server.state")
@mock.patch("coding_with_beat.server.get_source")
def test_smart_search_loved_ranked_first_and_tagged(mock_gs, mock_state, mock_wqf, mock_wam):
    mock_state.load.return_value = SimpleNamespace(source="apple_music")

    am_hits = [
        _hit("Normal Song", "Artist B", "library"),
        _hit("Loved Song", "Artist A", "loved"),
        _hit("Catalog Song", "Artist C", "apple_music"),
    ]

    def fake_get_source(name):
        src = mock.MagicMock()
        src.search.return_value = am_hits if name == "apple_music" else []
        return src

    mock_gs.side_effect = fake_get_source

    result = _run(server.smart_search("late night chill"))

    lines = [l for l in result.splitlines() if l.startswith(("1.", "2.", "3."))]
    assert lines[0].startswith("1.") and "Loved Song" in lines[0]
    assert "[♥ 喜欢]" in lines[0]
    assert "[资料库]" in lines[1]
    assert "[Apple Music]" in lines[2]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_smart_search.py::test_smart_search_loved_ranked_first_and_tagged -v`
Expected: FAIL — loved not ranked first, tag not showing

- [ ] **Step 3: Update `search` MCP tool**

Find the `@mcp.tool() async def search(...)` function in `server.py`. Replace its tag-building block and result return:

Old:
```python
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

New:
```python
    hits = _sort_by_source(hits)
    _write_queue_file("search", {"tracks": hits, "index": 0, "expected_title": ""})
    _write_active_mode(context="search")
    lines = []
    has_catalog = False
    for i, h in enumerate(hits):
        src = h.get("source", "")
        if src == "apple_music":
            has_catalog = True
        lines.append(f"{i + 1}. {h['title']} — {h.get('artist', '?')} · {h.get('album', '?')}{_source_tag(src)}")
    if has_catalog:
        lines.append("\n💡 [Apple Music] 曲目需要先添加到资料库才能播放。用 play_number() 尝试，Music.app 会自动打开。")
    return "\n".join(lines)
```

Also remove the two `_write_queue_file` / `_write_active_mode` lines that appeared before the old `lines = []` block (they are now handled after sort).

- [ ] **Step 4: Update `_multi_angle_search`**

In `_multi_angle_search`, inside `_search_one`, add sort before returning:

Old:
```python
        return merged
```

New:
```python
        return _sort_by_source(merged)
```

Then in the display loop, replace the tag-building block:

Old:
```python
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
```

New:
```python
            src = h.get("source", "")
            if src == "apple_music":
                has_catalog = True
            tag = _source_tag(src)
```

- [ ] **Step 5: Update `smart_search` single-angle mode**

In the `smart_search` function body, find the single-angle path (the `else` branch after `if queries:`). After `_dedup_add(local_hits or [])`, add:

```python
    merged = _sort_by_source(merged)
```

Then in the display loop, replace the tag block:

Old:
```python
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
```

New:
```python
        src = h.get("source", "")
        if src == "apple_music":
            has_catalog = True
        tag = _source_tag(src)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_smart_search.py -v`
Expected: all pass

- [ ] **Step 7: Run full suite**

Run: `pytest tests/ -q`
Expected: all pass

- [ ] **Step 8: Commit**

```bash
git add coding_with_beat/server.py tests/test_smart_search.py
git commit -m "feat(loved): apply source sort and [♥ 喜欢] tag to search, smart_search, multi_angle_search"
```

---

### Task 7: `server.py` — `list_loved` and `search_loved` MCP tools

**Files:**
- Modify: `coding_with_beat/server.py`
- Test: `tests/test_smart_search.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_smart_search.py`:

```python
@mock.patch("coding_with_beat.server._write_active_mode")
@mock.patch("coding_with_beat.server._write_queue_file")
@mock.patch("coding_with_beat.server.state")
@mock.patch("coding_with_beat.server.get_source")
def test_list_loved_returns_numbered_loved_tracks(mock_gs, mock_state, mock_wqf, mock_wam):
    mock_state.load.return_value = SimpleNamespace(source="apple_music")
    src = mock.MagicMock()
    src.list_loved.return_value = [
        {"title": "Heart Song", "artist": "DJ A", "album": "Vol 1", "source": "loved"},
        {"title": "Fave Track", "artist": "DJ B", "album": "Vol 2", "source": "loved"},
    ]
    mock_gs.return_value = src

    result = _run(server.list_loved())

    assert "1. Heart Song" in result
    assert "[♥ 喜欢]" in result
    assert "2. Fave Track" in result


@mock.patch("coding_with_beat.server._write_active_mode")
@mock.patch("coding_with_beat.server._write_queue_file")
@mock.patch("coding_with_beat.server.state")
@mock.patch("coding_with_beat.server.get_source")
def test_search_loved_returns_numbered_results(mock_gs, mock_state, mock_wqf, mock_wam):
    mock_state.load.return_value = SimpleNamespace(source="apple_music")
    src = mock.MagicMock()
    src.search_loved.return_value = [
        {"title": "Rain Song", "artist": "Piano", "album": "Calm", "source": "loved"},
    ]
    mock_gs.return_value = src

    result = _run(server.search_loved("rain"))

    assert "1. Rain Song" in result
    assert "[♥ 喜欢]" in result
    src.search_loved.assert_called_once_with("rain", 8)


@mock.patch("coding_with_beat.server._write_active_mode")
@mock.patch("coding_with_beat.server._write_queue_file")
@mock.patch("coding_with_beat.server.state")
@mock.patch("coding_with_beat.server.get_source")
def test_search_loved_no_results(mock_gs, mock_state, mock_wqf, mock_wam):
    mock_state.load.return_value = SimpleNamespace(source="apple_music")
    src = mock.MagicMock()
    src.search_loved.return_value = []
    mock_gs.return_value = src

    result = _run(server.search_loved("zzz"))
    assert "no loved tracks" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_smart_search.py::test_list_loved_returns_numbered_loved_tracks tests/test_smart_search.py::test_search_loved_returns_numbered_results -v`
Expected: FAIL — `AttributeError: module 'coding_with_beat.server' has no attribute 'list_loved'`

- [ ] **Step 3: Add `list_loved` MCP tool**

In `coding_with_beat/server.py`, add after the `list_library` MCP tool:

```python
@mcp.tool()
async def list_loved(limit: int = 50) -> str:
    """List all loved/hearted tracks in the current source's library.
    Returns a numbered list tagged [♥ 喜欢]. Use play_number() to play."""
    import asyncio

    st = state.load()
    src = get_source(st.source)
    fn = getattr(src, "list_loved", None)
    if not callable(fn):
        return f"(list_loved not supported for source={st.source})"
    hits = await asyncio.to_thread(fn, limit)
    if not hits:
        return "(no loved tracks found — heart some songs in Music.app first)"
    _write_queue_file("search", {"tracks": hits, "index": 0, "expected_title": ""})
    _write_active_mode(context="search")
    return "\n".join(
        f"{i + 1}. {h['title']} — {h.get('artist', '?')} · {h.get('album', '?')} [♥ 喜欢]"
        for i, h in enumerate(hits)
    )
```

- [ ] **Step 4: Add `search_loved` MCP tool**

In `coding_with_beat/server.py`, add after `list_loved`:

```python
@mcp.tool()
async def search_loved(query: str, limit: int = 8) -> str:
    """Search only within the user's loved/hearted tracks.
    Call this when the user says 从喜欢里找/收藏里搜/loved only/play from liked.
    Returns a numbered list. Use play_number() to play."""
    import asyncio

    st = state.load()
    src = get_source(st.source)
    fn = getattr(src, "search_loved", None)
    if not callable(fn):
        return f"(search_loved not supported for source={st.source})"
    hits = await asyncio.to_thread(fn, query, limit)
    if not hits:
        return f"(no loved tracks match '{query}')"
    _write_queue_file("search", {"tracks": hits, "index": 0, "expected_title": ""})
    _write_active_mode(context="search")
    return "\n".join(
        f"{i + 1}. {h['title']} — {h.get('artist', '?')} · {h.get('album', '?')} [♥ 喜欢]"
        for i, h in enumerate(hits)
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_smart_search.py -v`
Expected: all pass

- [ ] **Step 6: Run full suite**

Run: `pytest tests/ -q`
Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add coding_with_beat/server.py tests/test_smart_search.py
git commit -m "feat(loved): add list_loved and search_loved MCP tools"
```

---

### Task 8: `server.py` — companion_check loved priority

**Files:**
- Modify: `coding_with_beat/server.py`
- Test: `tests/test_companion_check.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_companion_check.py`:

```python
@mock.patch("coding_with_beat.server.state")
@mock.patch("coding_with_beat.server._multi_angle_search")
@mock.patch("coding_with_beat.server.get_source")
def test_companion_check_shows_loved_picks_when_available(self, mock_gs, mock_search, mock_state):
    mock_state.load.return_value = _mock_state()
    mock_search.return_value = "1. Song — Artist [资料库]"

    loved_src = mock.MagicMock()
    loved_src.list_loved.return_value = [
        {"title": "My Fave", "artist": "DJ X", "album": "A", "source": "loved"},
        {"title": "Heart Track", "artist": "DJ Y", "album": "B", "source": "loved"},
        {"title": "Love This", "artist": "DJ Z", "album": "C", "source": "loved"},
    ]
    mock_gs.return_value = loved_src

    result = _run(server.companion_check("session_start"))
    assert result != "(not needed right now)"
    # At least one loved track should appear in the card
    assert "[♥ 喜欢]" in result or any(
        t in result for t in ["My Fave", "Heart Track", "Love This"]
    )


@mock.patch("coding_with_beat.server.state")
@mock.patch("coding_with_beat.server._multi_angle_search")
@mock.patch("coding_with_beat.server.get_source")
def test_companion_check_falls_back_when_no_loved(self, mock_gs, mock_search, mock_state):
    mock_state.load.return_value = _mock_state()
    mock_search.return_value = "1. Song — Artist [资料库]"

    loved_src = mock.MagicMock()
    loved_src.list_loved.return_value = []
    mock_gs.return_value = loved_src

    result = _run(server.companion_check("session_start"))
    assert result != "(not needed right now)"
    # Falls back to regular search results
    assert "Song" in result
```

Note: these tests go inside `TestCompanionCheck` class. The `self` parameter reflects that.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_companion_check.py::TestCompanionCheck::test_companion_check_shows_loved_picks_when_available -v`
Expected: FAIL

- [ ] **Step 3: Update `companion_check` in `server.py`**

Find the `companion_check` async function. Replace the block that calls `_multi_angle_search`:

Old:
```python
    queries = _companion.get_queries(trigger)
    try:
        music_results = await _multi_angle_search(queries, limit_per_query=4)
    except Exception:
        music_results = "(music search unavailable — say what you'd like to hear)"
```

New:
```python
    import asyncio
    import random as _random

    # Try loved tracks for a personal touch
    loved_section = ""
    try:
        am_src = get_source("apple_music")
        fn = getattr(am_src, "list_loved", None)
        if callable(fn):
            all_loved = await asyncio.to_thread(fn, 30)
            if all_loved:
                picks = _random.sample(all_loved, min(3, len(all_loved)))
                loved_section = "♥ 从你的喜欢列表:\n" + "\n".join(
                    f"  · {h['title']} — {h.get('artist', '?')} [♥ 喜欢]"
                    for h in picks
                ) + "\n直接说歌名播放，或选下面编号\n"
    except Exception:
        loved_section = ""

    queries = _companion.get_queries(trigger)
    try:
        music_results = await _multi_angle_search(queries, limit_per_query=4)
    except Exception:
        music_results = "(music search unavailable — say what you'd like to hear)"

    if loved_section:
        music_results = loved_section + "\n" + music_results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_companion_check.py -v`
Expected: all pass

- [ ] **Step 5: Run full suite**

Run: `pytest tests/ -q`
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add coding_with_beat/server.py tests/test_companion_check.py
git commit -m "feat(loved): companion_check prioritises loved picks before search results"
```

---

### Task 9: `install.sh` — CLAUDE.md loved routing rules

**Files:**
- Modify: `install.sh`

- [ ] **Step 1: Add loved routing section to the `inject_claude_md` heredoc**

In `install.sh`, find the `inject_claude_md` function's `cat >> "$GLOBAL_CLAUDE_MD" <<'CLAUDEMD'` block. Inside that block, add the following section **before** the closing `# <<< coding-with-beat <<<` line:

```bash
## Loved / 喜欢列表

When user says: 从喜欢里 / 收藏里找 / 我喜欢的 / loved only / play from liked / 心动歌单
→ call `search_loved(query)` instead of `smart_search()`

When user says: 列出收藏 / 我的喜欢 / show liked / list loved / 喜欢列表
→ call `list_loved()`

Normal `smart_search()` already includes loved tracks (ranked first, tagged [♥ 喜欢]).
```

- [ ] **Step 2: Verify shell script syntax**

Run: `bash -n install.sh`
Expected: no output (no syntax errors)

- [ ] **Step 3: Commit**

```bash
git add install.sh
git commit -m "feat(loved): add loved routing rules to CLAUDE.md injection in install.sh"
```

---

### Task 10: Final integration check and push

- [ ] **Step 1: Run full test suite**

Run: `pytest tests/ -v`
Expected: all pass (130+ tests)

- [ ] **Step 2: Verify loved tag appears in smart_search output manually**

Run: `python -c "
import asyncio
from unittest import mock
from types import SimpleNamespace
from coding_with_beat import server

with mock.patch('coding_with_beat.server.state') as ms, \
     mock.patch('coding_with_beat.server._write_queue_file'), \
     mock.patch('coding_with_beat.server._write_active_mode'), \
     mock.patch('coding_with_beat.server.get_source') as mg:
    ms.load.return_value = SimpleNamespace(source='apple_music')
    src = mock.MagicMock()
    src.search.return_value = [
        {'title': 'Loved Song', 'artist': 'A', 'album': 'B', 'source': 'loved'},
        {'title': 'Library Song', 'artist': 'C', 'album': 'D', 'source': 'library'},
        {'title': 'Catalog Song', 'artist': 'E', 'album': 'F', 'source': 'apple_music'},
    ]
    mg.return_value = src
    result = asyncio.run(server.smart_search('chill night'))
    print(result)
"`

Expected output: Loved Song ranked first with `[♥ 喜欢]`, Library Song second with `[资料库]`, Catalog Song last with `[Apple Music]`.

- [ ] **Step 3: Push to dev and merge to main**

```bash
git push origin dev
git checkout main
git pull origin main
git merge dev --no-edit
git push origin main
git checkout dev
```
