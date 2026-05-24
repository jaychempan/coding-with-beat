# Multi-Angle Smart Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `smart_search` to accept a `queries` list so multiple keyword angles are searched in one call, writing a single consistent queue that `play_number()` can safely index into.

**Architecture:** Add a `_label_for_query` helper and `_multi_angle_search` async helper in `server.py`. Extend `smart_search` signature with `queries: list[str] | None = None`; when `queries` is provided, delegate to the helper. Update `cmd_smart_search` in `__main__.py` to support `--`-separated multi-angle CLI invocation. Update `cwb/SKILL.md` and `CLAUDE.md` to use the new calling convention.

**Tech Stack:** Python asyncio, FastMCP (`mcp.server.fastmcp`), pytest + `unittest.mock`

---

### Task 1: Add `_label_for_query` helper with tests

**Files:**
- Modify: `coding_with_beat/server.py` (after line 641, before `@mcp.tool()` on line 643)
- Test: `tests/test_smart_search.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_smart_search.py`:

```python
from coding_with_beat.server import _label_for_query


def test_label_lofi():
    assert _label_for_query("lofi hip hop late night coding") == "🎧 Lofi"


def test_label_jazz():
    assert _label_for_query("lofi jazz rain study") == "🎷 Jazz"


def test_label_synthwave():
    assert _label_for_query("synthwave retrowave night drive neon") == "🌆 Synthwave"


def test_label_fallback():
    # No keyword match → first three words title-cased
    assert _label_for_query("choral gospel choir ambient") == "Choral Gospel Choir"


def test_label_fallback_short():
    assert _label_for_query("ambient") == "Ambient"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_smart_search.py::test_label_lofi tests/test_smart_search.py::test_label_jazz tests/test_smart_search.py::test_label_synthwave tests/test_smart_search.py::test_label_fallback tests/test_smart_search.py::test_label_fallback_short -v
```

Expected: ImportError or AttributeError — `_label_for_query` not yet defined.

- [ ] **Step 3: Implement `_QUERY_LABEL_MAP` and `_label_for_query` in `server.py`**

Insert after line 641 (the line `return "\n".join(lines)` in the `search` function) and before the `@mcp.tool()` decorator on line 643:

```python

_QUERY_LABEL_MAP: list[tuple[tuple[str, ...], str]] = [
    (("lofi", "lo-fi", "chillhop"), "🎧 Lofi"),
    (("jazz", "bossa nova", "smooth jazz"), "🎷 Jazz"),
    (("synthwave", "retrowave", "outrun"), "🌆 Synthwave"),
    (("ambient", "drone", "meditation"), "🌫️ Ambient"),
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_smart_search.py::test_label_lofi tests/test_smart_search.py::test_label_jazz tests/test_smart_search.py::test_label_synthwave tests/test_smart_search.py::test_label_fallback tests/test_smart_search.py::test_label_fallback_short -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add coding_with_beat/server.py tests/test_smart_search.py
git commit -m "feat: add _label_for_query helper with keyword→emoji label map"
```

---

### Task 2: Add `_multi_angle_search` async helper with tests

**Files:**
- Modify: `coding_with_beat/server.py` (insert after `_label_for_query`)
- Test: `tests/test_smart_search.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_smart_search.py`:

```python
@mock.patch("coding_with_beat.server._write_active_mode")
@mock.patch("coding_with_beat.server._write_queue_file")
@mock.patch("coding_with_beat.server.get_source")
def test_multi_angle_global_numbering(mock_gs, mock_wqf, mock_wam):
    """Three queries × 2 tracks each → output numbers 1–6 sequentially."""
    def fake_get_source(name):
        src = mock.MagicMock()
        if name == "apple_music":
            src.search.side_effect = lambda q, lim: [
                _hit(f"{q[:4]}-am-1", "Artist", "apple_music"),
                _hit(f"{q[:4]}-am-2", "Artist", "apple_music"),
            ]
        else:
            src.search.return_value = []
        return src

    mock_gs.side_effect = fake_get_source

    from coding_with_beat.server import _multi_angle_search
    result = _run(_multi_angle_search(["lofi hip hop", "jazz cozy rain", "synthwave night"]))

    # All 6 tracks should appear globally numbered
    for n in range(1, 7):
        assert f"{n}." in result


@mock.patch("coding_with_beat.server._write_active_mode")
@mock.patch("coding_with_beat.server._write_queue_file")
@mock.patch("coding_with_beat.server.get_source")
def test_multi_angle_single_queue_write(mock_gs, mock_wqf, mock_wam):
    """Queue is written exactly once regardless of query count."""
    def fake_get_source(name):
        src = mock.MagicMock()
        src.search.return_value = [_hit("Track", "Artist", "apple_music")]
        return src

    mock_gs.side_effect = fake_get_source

    from coding_with_beat.server import _multi_angle_search
    _run(_multi_angle_search(["lofi", "jazz", "synthwave"]))

    mock_wqf.assert_called_once()
    args = mock_wqf.call_args[0]
    assert args[0] == "search"


@mock.patch("coding_with_beat.server._write_active_mode")
@mock.patch("coding_with_beat.server._write_queue_file")
@mock.patch("coding_with_beat.server.get_source")
def test_multi_angle_global_dedup(mock_gs, mock_wqf, mock_wam):
    """Same track returned by two queries appears only once."""
    dup = _hit("Same Song", "Same Artist", "apple_music")

    def fake_get_source(name):
        src = mock.MagicMock()
        if name == "apple_music":
            src.search.return_value = [dup]
        else:
            src.search.return_value = []
        return src

    mock_gs.side_effect = fake_get_source

    from coding_with_beat.server import _multi_angle_search
    result = _run(_multi_angle_search(["lofi", "jazz"]))

    assert result.count("Same Song — Same Artist") == 1


@mock.patch("coding_with_beat.server._write_active_mode")
@mock.patch("coding_with_beat.server._write_queue_file")
@mock.patch("coding_with_beat.server.get_source")
def test_multi_angle_label_in_output(mock_gs, mock_wqf, mock_wam):
    """Each group header appears in the output."""
    def fake_get_source(name):
        src = mock.MagicMock()
        src.search.return_value = [_hit("Track", "Artist", "library")]
        return src

    mock_gs.side_effect = fake_get_source

    from coding_with_beat.server import _multi_angle_search
    result = _run(_multi_angle_search(["lofi hip hop", "synthwave retrowave"]))

    assert "🎧" in result  # lofi label
    assert "🌆" in result  # synthwave label


@mock.patch("coding_with_beat.server._write_active_mode")
@mock.patch("coding_with_beat.server._write_queue_file")
@mock.patch("coding_with_beat.server.get_source")
def test_multi_angle_queue_track_order_matches_output(mock_gs, mock_wqf, mock_wam):
    """Tracks in the queue are in the same order as the global numbering."""
    a = _hit("Alpha", "Artist", "library")
    b = _hit("Beta", "Artist", "library")
    c = _hit("Gamma", "Artist", "library")

    tracks_by_query = {"q1": [a], "q2": [b], "q3": [c]}

    def fake_get_source(name):
        src = mock.MagicMock()
        if name == "apple_music":
            src.search.side_effect = lambda q, lim: tracks_by_query.get(q, [])
        else:
            src.search.return_value = []
        return src

    mock_gs.side_effect = fake_get_source

    from coding_with_beat.server import _multi_angle_search
    _run(_multi_angle_search(["q1", "q2", "q3"]))

    written_tracks = mock_wqf.call_args[0][1]["tracks"]
    titles = [t["title"] for t in written_tracks]
    assert titles == ["Alpha", "Beta", "Gamma"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_smart_search.py::test_multi_angle_global_numbering tests/test_smart_search.py::test_multi_angle_single_queue_write tests/test_smart_search.py::test_multi_angle_global_dedup tests/test_smart_search.py::test_multi_angle_label_in_output tests/test_smart_search.py::test_multi_angle_queue_track_order_matches_output -v
```

Expected: ImportError — `_multi_angle_search` not yet defined.

- [ ] **Step 3: Implement `_multi_angle_search` in `server.py`**

Insert after `_label_for_query` (after the line `return " ".join(w.capitalize() for w in words)`):

```python

async def _multi_angle_search(queries: list[str], limit_per_query: int = 6) -> str:
    import asyncio

    async def _search_one(query: str) -> list[dict]:
        am_hits, local_hits = await asyncio.gather(
            asyncio.to_thread(get_source("apple_music").search, query, limit_per_query),
            asyncio.to_thread(get_source("local").search, query, limit_per_query),
        )
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
            lines.append(
                f"{global_idx}. {h['title']} — {h.get('artist', '?')} · {h.get('album', '?')}{tag}"
            )
            global_idx += 1
        lines.append("")

    if has_catalog:
        lines.append("💡 [Apple Music] 曲目需要先添加到资料库才能播放。用 play_number() 尝试，Music.app 会自动打开。")
    lines.append("喜欢哪首？说编号我来播。")

    return "\n".join(lines).rstrip()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_smart_search.py::test_multi_angle_global_numbering tests/test_smart_search.py::test_multi_angle_single_queue_write tests/test_smart_search.py::test_multi_angle_global_dedup tests/test_smart_search.py::test_multi_angle_label_in_output tests/test_smart_search.py::test_multi_angle_queue_track_order_matches_output -v
```

Expected: 5 passed.

- [ ] **Step 5: Run full test suite to verify no regressions**

```bash
python -m pytest tests/test_smart_search.py -v
```

Expected: all pass (9 tests total).

- [ ] **Step 6: Commit**

```bash
git add coding_with_beat/server.py tests/test_smart_search.py
git commit -m "feat: add _multi_angle_search helper — parallel search, global numbering, single queue write"
```

---

### Task 3: Extend `smart_search` MCP tool signature

**Files:**
- Modify: `coding_with_beat/server.py` (the `smart_search` function, currently line 644)
- Test: `tests/test_smart_search.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_smart_search.py`:

```python
@mock.patch("coding_with_beat.server._multi_angle_search")
def test_smart_search_delegates_to_multi_angle_when_queries_given(mock_multi):
    """When queries= is passed, smart_search delegates to _multi_angle_search."""
    import asyncio

    async def fake_multi(queries, limit_per_query=6):
        return "mocked result"

    mock_multi.side_effect = fake_multi

    result = asyncio.run(server.smart_search(queries=["lofi hip hop", "jazz cozy", "synthwave"]))
    mock_multi.assert_called_once_with(["lofi hip hop", "jazz cozy", "synthwave"], limit_per_query=6)
    assert result == "mocked result"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_smart_search.py::test_smart_search_delegates_to_multi_angle_when_queries_given -v
```

Expected: TypeError — `smart_search` does not accept `queries` keyword argument.

- [ ] **Step 3: Update `smart_search` signature and body in `server.py`**

Replace the current `smart_search` function (lines 643–717) with:

```python
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
        lines.append(
            f"{i + 1}. {h['title']} — {h.get('artist', '?')} · {h.get('album', '?')}{tag}"
        )
    if has_catalog:
        lines.append("\n💡 [Apple Music] 曲目需要先添加到资料库才能播放。用 play_number() 尝试，Music.app 会自动打开。")
    return "\n".join(lines)
```

- [ ] **Step 4: Run all smart_search tests**

```bash
python -m pytest tests/test_smart_search.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add coding_with_beat/server.py tests/test_smart_search.py
git commit -m "feat: extend smart_search with queries= parameter for multi-angle mode"
```

---

### Task 4: Update `cmd_smart_search` in `__main__.py`

**Files:**
- Modify: `coding_with_beat/__main__.py` (the `cmd_smart_search` function, lines 211–284)

No new tests needed — this is a CLI wrapper that calls the same server helpers already tested.

- [ ] **Step 1: Replace `cmd_smart_search` in `__main__.py`**

Replace the entire function (lines 211–284) with:

```python
def cmd_smart_search() -> int:
    """smart_search <description> | <q1> -- <q2> -- <q3> — find tracks by mood/scene/vibe."""
    import asyncio

    raw = sys.argv[2:]
    if not raw:
        print("error: usage: smart_search <description>  OR  smart_search <q1> -- <q2> -- <q3>")
        return 2

    # Split on "--" to detect multi-angle mode
    queries: list[str] = []
    current: list[str] = []
    for arg in raw:
        if arg == "--":
            if current:
                queries.append(" ".join(current).strip())
            current = []
        else:
            current.append(arg)
    if current:
        queries.append(" ".join(current).strip())
    queries = [q for q in queries if q]

    from .server import _multi_angle_search, _write_active_mode, _write_queue_file
    from .sources import get_source

    if len(queries) > 1:
        print(f"🔍 多角度搜索: {len(queries)} 个方向", flush=True)
        result = asyncio.run(_multi_angle_search(queries))
        print(result)
        return 0

    # Single-angle (backwards compat)
    query = queries[0]
    print(f"🔍 理解描述: {query}", flush=True)

    import threading

    am_hits: list = []
    local_hits: list = []

    def _search_am() -> None:
        nonlocal am_hits
        print("🎵 搜索 Apple Music...", flush=True)
        am_hits = get_source("apple_music").search(query, 8) or []

    def _search_local() -> None:
        nonlocal local_hits
        print("📁 搜索本地文件...", flush=True)
        local_hits = get_source("local").search(query, 8) or []

    t1 = threading.Thread(target=_search_am, daemon=True)
    t2 = threading.Thread(target=_search_local, daemon=True)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    seen: set[str] = set()
    merged: list[dict] = []
    for h in am_hits + local_hits:
        key = f"{h.get('title', '').lower()}|{h.get('artist', '').lower()}"
        if key not in seen:
            seen.add(key)
            merged.append(h)

    if not merged:
        print(f"(no matches for '{query}')")
        return 1

    print(f"✅ 找到 {len(merged)} 首\n", flush=True)

    _write_queue_file("search", {"tracks": merged, "index": 0, "expected_title": ""})
    _write_active_mode(context="search")

    has_catalog = False
    lines = []
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
    print("\n".join(lines))
    return 0
```

- [ ] **Step 2: Verify existing tests still pass**

```bash
python -m pytest tests/ -q
```

Expected: all pass, no regressions.

- [ ] **Step 3: Smoke-test CLI multi-angle (optional, requires Apple Music)**

```bash
python -m coding_with_beat smart_search "lofi hip hop" -- "jazz cozy" -- "synthwave night"
```

Expected: labeled groups printed, global numbers 1-N.

- [ ] **Step 4: Commit**

```bash
git add coding_with_beat/__main__.py
git commit -m "feat: update cmd_smart_search to support multi-angle -- separator"
```

---

### Task 5: Update `codex_skills/cwb/SKILL.md` scene dispatch table

**Files:**
- Modify: `codex_skills/cwb/SKILL.md`

- [ ] **Step 1: Update the scene dispatch section**

Find the paragraph that begins `Call all three smart_search(query) for the matched scene.` and replace it with:

```markdown
Call `smart_search` **once** with `queries=[angle1, angle2, angle3]` for the matched scene. Do NOT call `smart_search` three separate times — each call overwrites the queue, corrupting the index. Display results grouped by angle with emoji labels (returned by the tool), number globally across groups (1, 2, 3…), end with: 喜欢哪首？说编号我来播。 Do NOT auto-play.
```

- [ ] **Step 2: Verify the file looks correct**

```bash
grep -A5 "Call.*smart_search" codex_skills/cwb/SKILL.md
```

Expected: only one sentence, no "three times" language.

- [ ] **Step 3: Commit**

```bash
git add codex_skills/cwb/SKILL.md
git commit -m "docs(skill): update cwb scene dispatch to use smart_search(queries=[...])"
```

---

### Task 6: Update `CLAUDE.md` multi-angle instructions

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Replace the `## Smart search: multi-angle display` section**

Find and replace the entire section:

```markdown
## Smart search: multi-angle display

When handling a mood/vibe/scene music request, **always search with 2–3 different
keyword angles in parallel**, display all results grouped by direction, then ask
the user to pick by number. Do NOT auto-play or pre-select a track.

Example angles for "深夜写代码":
- `lofi hip hop late night coding instrumental`
- `lofi jazz late night rain cozy`
- `synthwave retrowave night drive electronic`

Label each group clearly (e.g. **🎷 Lofi Jazz 方向**, **🌆 Synthwave 方向**) and end
with "喜欢哪首？说编号我来播。"
```

Replace with:

```markdown
## Smart search: multi-angle display

When handling a mood/vibe/scene music request, call `smart_search()` **once** with
the `queries` parameter containing 2–3 keyword angles. Do NOT call `smart_search()`
multiple times — each call overwrites the queue, so `play_number()` will index into
the wrong results.

Example for "深夜写代码":
```python
smart_search(queries=[
    "lofi hip hop late night coding instrumental",
    "lofi jazz late night rain cozy",
    "synthwave retrowave night drive electronic",
])
```

The tool returns globally numbered results grouped by direction with emoji labels.
Ask the user to pick by number and call `play_number(N)`. Do NOT auto-play.
```

- [ ] **Step 2: Verify the change**

```bash
grep -A15 "Smart search" CLAUDE.md
```

Expected: new text with `queries=` example, no "in parallel" language.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md smart search instructions to use queries= parameter"
```

---

### Task 7: Final verification

- [ ] **Step 1: Run full test suite**

```bash
python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 2: Verify MCP tool schema includes `queries` parameter**

```bash
python -c "
import asyncio, inspect
from coding_with_beat.server import smart_search
sig = inspect.signature(smart_search)
print(sig)
assert 'queries' in sig.parameters, 'queries param missing'
assert 'description' in sig.parameters, 'description param missing'
print('OK')
"
```

Expected: signature printed, `OK` on last line.

- [ ] **Step 3: Final commit if anything remains unstaged**

```bash
git status
```

If clean, done. Otherwise commit remaining changes.
