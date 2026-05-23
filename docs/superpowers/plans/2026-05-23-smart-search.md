# smart_search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `smart_search()` MCP tool that accepts natural-language music descriptions from AI callers (Claude Code / Codex), searches Apple Music (library + catalog) and local files in one call, and returns annotated results.

**Architecture:** New `smart_search()` tool in `server.py` — docstring instructs the calling LLM to translate natural language into search keywords before invocation; internally calls Apple Music source (returns both library and catalog hits) and local source, merges results, annotates each with `[资料库]` / `[Apple Music]` / `[本地]`. Existing `search()` is unchanged. A new `CLAUDE.md` at project root tells Claude Code when to prefer `smart_search`.

**Tech Stack:** Python, existing `get_source()` pattern, `asyncio.to_thread`, FastMCP `@mcp.tool()`

---

## Files

| Action | Path |
|--------|------|
| Modify | `coding_with_beat/server.py` — add `smart_search()` after `search()` at line ~622 |
| Create | `CLAUDE.md` — project root, music routing instruction |
| Create | `tests/test_smart_search.py` — unit tests |

---

## Task 1: Write failing tests for smart_search

**Files:**
- Create: `tests/test_smart_search.py`

- [ ] **Step 1: Create the test file**

```python
# tests/test_smart_search.py
import asyncio
from types import SimpleNamespace
from unittest import mock

import pytest

from coding_with_beat import server


def _hit(title, artist, source):
    return {"title": title, "artist": artist, "album": "Album", "source": source}


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@mock.patch("coding_with_beat.server._write_active_mode")
@mock.patch("coding_with_beat.server._write_queue_file")
@mock.patch("coding_with_beat.server.state")
@mock.patch("coding_with_beat.server.get_source")
def test_smart_search_annotates_sources(mock_gs, mock_state, mock_wqf, mock_wam):
    mock_state.load.return_value = SimpleNamespace(source="apple_music")

    am_hits = [
        _hit("雨的印记", "李闰珉", "library"),
        _hit("Quiet Library", "FM STAR", "apple_music"),
    ]
    local_hits = [
        _hit("lofi study", "unknown", "local"),
    ]

    def fake_get_source(name):
        src = mock.MagicMock()
        if name == "apple_music":
            src.search.return_value = am_hits
        elif name == "local":
            src.search.return_value = local_hits
        return src

    mock_gs.side_effect = fake_get_source

    result = _run(server.smart_search("something chill for late night coding"))

    assert "雨的印记" in result
    assert "[资料库]" in result
    assert "Quiet Library" in result
    assert "[Apple Music]" in result
    assert "lofi study" in result
    assert "[本地]" in result


@mock.patch("coding_with_beat.server._write_active_mode")
@mock.patch("coding_with_beat.server._write_queue_file")
@mock.patch("coding_with_beat.server.state")
@mock.patch("coding_with_beat.server.get_source")
def test_smart_search_no_results(mock_gs, mock_state, mock_wqf, mock_wam):
    mock_state.load.return_value = SimpleNamespace(source="apple_music")

    def fake_get_source(name):
        src = mock.MagicMock()
        src.search.return_value = []
        return src

    mock_gs.side_effect = fake_get_source

    result = _run(server.smart_search("xyzzy nothing matches"))
    assert "no matches" in result


@mock.patch("coding_with_beat.server._write_active_mode")
@mock.patch("coding_with_beat.server._write_queue_file")
@mock.patch("coding_with_beat.server.state")
@mock.patch("coding_with_beat.server.get_source")
def test_smart_search_deduplicates(mock_gs, mock_state, mock_wqf, mock_wam):
    mock_state.load.return_value = SimpleNamespace(source="apple_music")

    dup = _hit("Song", "Artist", "library")

    def fake_get_source(name):
        src = mock.MagicMock()
        src.search.return_value = [dup]
        return src

    mock_gs.side_effect = fake_get_source

    result = _run(server.smart_search("song"))
    # "Song — Artist" should appear only once
    assert result.count("Song — Artist") == 1


@mock.patch("coding_with_beat.server._write_active_mode")
@mock.patch("coding_with_beat.server._write_queue_file")
@mock.patch("coding_with_beat.server.state")
@mock.patch("coding_with_beat.server.get_source")
def test_smart_search_writes_search_queue(mock_gs, mock_state, mock_wqf, mock_wam):
    mock_state.load.return_value = SimpleNamespace(source="apple_music")

    hits = [_hit("Track", "Artist", "library")]

    def fake_get_source(name):
        src = mock.MagicMock()
        src.search.return_value = hits if name == "apple_music" else []
        return src

    mock_gs.side_effect = fake_get_source

    _run(server.smart_search("something"))

    mock_wqf.assert_called_once()
    args = mock_wqf.call_args[0]
    assert args[0] == "search"
    assert len(args[1]["tracks"]) == 1
```

- [ ] **Step 2: Run tests — verify they all fail**

```bash
cd /Users/jianchengpan/Projects/coding-with-beat
pytest tests/test_smart_search.py -v
```

Expected: `AttributeError: module 'coding_with_beat.server' has no attribute 'smart_search'`

---

## Task 2: Implement smart_search in server.py

**Files:**
- Modify: `coding_with_beat/server.py` — insert after the `search()` function (after line 621)

- [ ] **Step 1: Add the smart_search tool**

Insert the following block immediately after the closing of `search()` (after line 621, before the `@mcp.tool()` decorator for `play_number`):

```python
@mcp.tool()
async def smart_search(description: str, limit: int = 8) -> str:
    """Natural-language music search for AI callers (Claude Code / Codex CLI).

    IMPORTANT — translate `description` into music keywords BEFORE calling:

    Mood / emotion
      "安静" / "calm"          → "ambient instrumental chill"
      "想兴奋起来" / "hype"    → "energetic upbeat electronic"
      "放松" / "relax"         → "relaxing calm downtempo"
      "伤感" / "sad"           → "melancholy emotional piano"

    Scene / time
      "深夜写代码"             → "lofi hip hop late night study"
      "早晨跑步"               → "running motivation pop upbeat"
      "专注 / 摸鱼"            → "focus deep work instrumental"
      "通勤路上"               → "podcast commute indie pop"

    Style reference
      "像 Daft Punk 那种"      → "electronic synth funk dance"
      "带点爵士"               → "jazz fusion smooth"
      "复古感"                 → "vintage retro soul funk"
      "纯音乐 / no vocals"     → append "instrumental"

    Pass the expanded keyword string as `description`, not the raw user text.

    Searches Apple Music library (marked [资料库]), Apple Music catalog
    (marked [Apple Music]), and local files (marked [本地]). Results are
    numbered — use play_number() to play by index.
    """
    import asyncio

    st = state.load()

    am_hits, local_hits = await asyncio.gather(
        asyncio.to_thread(get_source("apple_music").search, description, limit),
        asyncio.to_thread(get_source("local").search, description, limit),
    )

    seen: set[str] = set()
    merged: list[dict] = []

    def _dedup_add(hits: list[dict]) -> None:
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
    for i, h in enumerate(merged):
        src = h.get("source", "")
        if src == "library":
            tag = " [资料库]"
        elif src == "apple_music":
            tag = " [Apple Music]"
        elif src == "local":
            tag = " [本地]"
        else:
            tag = ""
        lines.append(
            f"{i + 1}. {h['title']} — {h.get('artist', '?')} · {h.get('album', '?')}{tag}"
        )
    return "\n".join(lines)
```

- [ ] **Step 2: Run tests — verify they all pass**

```bash
cd /Users/jianchengpan/Projects/coding-with-beat
pytest tests/test_smart_search.py -v
```

Expected: 4 tests PASS

- [ ] **Step 3: Run full test suite to check for regressions**

```bash
pytest --tb=short -q
```

Expected: all existing tests still pass

- [ ] **Step 4: Commit**

```bash
git add coding_with_beat/server.py tests/test_smart_search.py
git commit -m "feat: add smart_search MCP tool with natural-language query guidance"
```

---

## Task 3: Create CLAUDE.md at project root

**Files:**
- Create: `CLAUDE.md`

- [ ] **Step 1: Create the file**

```markdown
# Coding With Beat

## Music intent

When the user asks for music by mood, scene, or style description
(e.g. "来首轻松的", "something for late-night coding", "带点爵士的"),
use `smart_search()` instead of `search()`.

Use `search()` only when the user provides a specific track title,
artist name, or album title.
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add CLAUDE.md with music intent routing rule"
```

---

## Task 4: Push to dev

- [ ] **Step 1: Push**

```bash
git push origin dev
```

Expected: branch updated on remote.
