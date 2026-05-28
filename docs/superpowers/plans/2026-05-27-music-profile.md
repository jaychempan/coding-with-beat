# Music Profile Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `generate_profile()` MCP tool + `cwb profile` CLI command + `cwb-profile` Skill that generates periodic listening reports, user music profiles, and personalized recommendation queries from play and search history.

**Architecture:** New `profile.py` module handles all analysis logic (pure functions, no async). `history.py` gains `write_search()` / `read_search()` for search log I/O. `server.py` gets a new `generate_profile()` MCP tool and captures search queries inside `smart_search()`. `__main__.py` gets a `cwb profile [period]` command.

**Tech Stack:** Python 3.10+, existing `history._STYLE_KEYWORDS`, `sources.get_source()`, `mcp.server.fastmcp.FastMCP`, `collections.Counter`, `re`, `datetime`

---

## Task 1: Add `write_search` / `read_search` to `history.py`

**Files:**
- Modify: `coding_with_beat/history.py:1-10` (add `_SEARCH_LOG_FILE` constant)
- Modify: `coding_with_beat/history.py` (append two functions at end of file)
- Test: `tests/test_history.py` (append new test functions)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_history.py`:

```python
# ── write_search / read_search ────────────────────────────────────────────────

def test_read_search_returns_empty_when_no_log(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "_SEARCH_LOG_FILE", tmp_path / "search_history.log")
    assert history.read_search() == []


def test_write_search_and_read_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "_SEARCH_LOG_FILE", tmp_path / "search_history.log")
    monkeypatch.setattr(history, "ensure_dirs", lambda: None)
    history.write_search("lofi jazz coding instrumental focus")
    history.write_search("synthwave night drive neon")
    records = history.read_search()
    assert len(records) == 2
    # most-recent first
    assert records[0]["query"] == "synthwave night drive neon"
    assert records[1]["query"] == "lofi jazz coding instrumental focus"
    assert isinstance(records[0]["ts"], __import__("datetime").datetime)


def test_write_search_skips_empty_query(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "_SEARCH_LOG_FILE", tmp_path / "search_history.log")
    monkeypatch.setattr(history, "ensure_dirs", lambda: None)
    history.write_search("")
    assert not (tmp_path / "search_history.log").exists()


def test_read_search_respects_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "_SEARCH_LOG_FILE", tmp_path / "search_history.log")
    monkeypatch.setattr(history, "ensure_dirs", lambda: None)
    for i in range(10):
        history.write_search(f"query {i}")
    assert len(history.read_search(limit=3)) == 3
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/jianchengpan/Projects/coding-with-beat
python -m pytest tests/test_history.py::test_read_search_returns_empty_when_no_log tests/test_history.py::test_write_search_and_read_round_trip -v
```

Expected: `FAILED` — `AttributeError: module 'coding_with_beat.history' has no attribute '_SEARCH_LOG_FILE'`

- [ ] **Step 3: Implement `_SEARCH_LOG_FILE`, `write_search`, `read_search` in `history.py`**

Add `_SEARCH_LOG_FILE` after `_LOG_FILE` at line 10:

```python
_SEARCH_LOG_FILE = DATA_DIR / "search_history.log"
```

Append at the end of `coding_with_beat/history.py`:

```python
def write_search(query: str) -> None:
    """Append one search record to search_history.log."""
    if not query:
        return
    ensure_dirs()
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"{ts} | {query} | smart_search\n"
    try:
        with open(_SEARCH_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def read_search(limit: int = 500) -> list[dict]:
    """Read the most recent `limit` entries from search_history.log, most-recent first.
    Each entry: {query: str, ts: datetime}."""
    try:
        lines = _SEARCH_LOG_FILE.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    result: list[dict] = []
    for line in reversed(lines):
        parts = line.split(" | ", 2)
        if len(parts) < 2:
            continue
        ts_str, query = parts[0], parts[1]
        try:
            ts = datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        result.append({"query": query, "ts": ts})
        if len(result) >= limit:
            break
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_history.py -v
```

Expected: all history tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add coding_with_beat/history.py tests/test_history.py
git commit -m "feat(history): add write_search and read_search for search_history.log"
```

---

## Task 2: Capture search queries in `smart_search()`

**Files:**
- Modify: `coding_with_beat/server.py:965-1010` (add capture at top of `smart_search`)
- Test: `tests/test_smart_search.py` (append capture test)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_smart_search.py`:

```python
def test_smart_search_writes_search_history(tmp_path, monkeypatch):
    """smart_search must write each query to search_history.log."""
    from coding_with_beat import history as _history
    monkeypatch.setattr(_history, "_SEARCH_LOG_FILE", tmp_path / "search_history.log")
    monkeypatch.setattr(_history, "ensure_dirs", lambda: None)

    import asyncio
    from unittest.mock import AsyncMock, patch

    async def _run():
        with patch("coding_with_beat.server._multi_angle_search", new=AsyncMock(return_value="ok")):
            from coding_with_beat.server import smart_search
            await smart_search(queries=["lofi jazz focus", "ambient drone"])

    asyncio.run(_run())

    records = _history.read_search()
    queries_written = [r["query"] for r in records]
    assert "lofi jazz focus" in queries_written
    assert "ambient drone" in queries_written
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_smart_search.py::test_smart_search_writes_search_history -v
```

Expected: `FAILED` — no records written

- [ ] **Step 3: Add capture to `smart_search()` in `server.py`**

In `coding_with_beat/server.py`, inside `smart_search()` function body, add capture lines right after the opening docstring (before the `if queries:` branch). The function body starts after line 1010. Add:

```python
    # Capture queries for search history profile
    if queries:
        for _q in queries:
            history.write_search(_q)
    elif description:
        history.write_search(description)
```

The full start of the function body becomes:
```python
    """...docstring..."""
    import asyncio

    # Capture queries for search history profile
    if queries:
        for _q in queries:
            history.write_search(_q)
    elif description:
        history.write_search(description)

    if queries:
        _q0 = queries[0][:22] + ("…" if len(queries[0]) > 22 else "")
        return await _multi_angle_search(queries, limit_per_query=min(limit, 6), label=f"Search · {_q0}")
    # ... rest unchanged
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_smart_search.py -v
```

Expected: all smart_search tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add coding_with_beat/server.py tests/test_smart_search.py
git commit -m "feat(server): capture smart_search queries to search_history.log"
```

---

## Task 3: Create `profile.py` with `build_profile()`

**Files:**
- Create: `coding_with_beat/profile.py`
- Create: `tests/test_profile.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_profile.py`:

```python
# tests/test_profile.py
import datetime
from unittest import mock

import pytest

from coding_with_beat import history, profile


# ── helpers ───────────────────────────────────────────────────────────────────

def _track(title, artist, hours_ago, album="", played_count=1):
    ts = datetime.datetime.now() - datetime.timedelta(hours=hours_ago)
    return {
        "title": title, "artist": artist, "album": album,
        "ts": ts, "played_count": played_count,
    }


def _weekly_tracks():
    return [
        _track("Track 1", "Hans Zimmer", 10,  "lofi jazz ambient"),
        _track("Track 2", "Hans Zimmer", 20,  "lofi hip hop"),
        _track("Track 3", "Hans Zimmer", 30,  "lofi"),
        _track("Track 4", "周杰伦",       40,  "华语"),
        _track("Track 5", "周杰伦",       50,  "华语"),
        _track("Track 6", "ODESZA",       60,  "electronic"),
        _track("Track 7", "ODESZA",       80,  "electronic synthwave"),
        _track("Track 8", "Debussy",      100, "classical piano"),
        _track("Track 9", "Debussy",      110, "classical"),
        _track("Track 10", "Tycho",       120, "ambient"),
    ]


# ── build_profile ─────────────────────────────────────────────────────────────

def test_build_profile_raises_on_insufficient_history(monkeypatch):
    monkeypatch.setattr(history, "read", lambda limit=500: [])
    monkeypatch.setattr(history, "read_search", lambda limit=500: [])
    with mock.patch("coding_with_beat.profile.get_source", side_effect=Exception("no AM")):
        with pytest.raises(ValueError, match="insufficient_history"):
            profile.build_profile("weekly")


def test_build_profile_weekly_top_artists(monkeypatch):
    monkeypatch.setattr(history, "read", lambda limit=500: _weekly_tracks())
    monkeypatch.setattr(history, "read_search", lambda limit=500: [])
    with mock.patch("coding_with_beat.profile.get_source", side_effect=Exception("no AM")):
        prof = profile.build_profile("weekly")
    top_artist_names = [a for a, _ in prof["top_artists"]]
    assert "Hans Zimmer" in top_artist_names
    assert prof["play_count"] == 10


def test_build_profile_top_genres_detected(monkeypatch):
    monkeypatch.setattr(history, "read", lambda limit=500: _weekly_tracks())
    monkeypatch.setattr(history, "read_search", lambda limit=500: [])
    with mock.patch("coding_with_beat.profile.get_source", side_effect=Exception("no AM")):
        prof = profile.build_profile("weekly")
    genre_names = [g for g, _ in prof["top_genres"]]
    assert "lofi" in genre_names or "classical" in genre_names


def test_build_profile_period_days_filtering(monkeypatch):
    old_track = _track("Old Track", "Old Artist", 48)  # 48 hours ago, outside daily window
    new_track = _track("New Track", "New Artist", 1)   # 1 hour ago, inside daily window
    monkeypatch.setattr(history, "read", lambda limit=500: [old_track, new_track] * 5)
    monkeypatch.setattr(history, "read_search", lambda limit=500: [])
    with mock.patch("coding_with_beat.profile.get_source", side_effect=Exception("no AM")):
        prof = profile.build_profile("daily")
    artist_names = [a for a, _ in prof["top_artists"]]
    assert "New Artist" in artist_names
    assert "Old Artist" not in artist_names


def test_build_profile_language_pref_zh(monkeypatch):
    zh_tracks = [_track("夜曲", "周杰伦", i * 2, "华语") for i in range(8)]
    monkeypatch.setattr(history, "read", lambda limit=500: zh_tracks)
    monkeypatch.setattr(history, "read_search", lambda limit=500: [])
    with mock.patch("coding_with_beat.profile.get_source", side_effect=Exception("no AM")):
        prof = profile.build_profile("weekly")
    assert prof["language_pref"].get("zh", 0) > 0.5


def test_build_profile_search_terms_captured(monkeypatch):
    search_recs = [
        {"query": "lofi jazz coding focus instrumental", "ts": datetime.datetime.now() - datetime.timedelta(hours=1)},
        {"query": "lofi hip hop study", "ts": datetime.datetime.now() - datetime.timedelta(hours=2)},
    ]
    monkeypatch.setattr(history, "read", lambda limit=500: _weekly_tracks())
    monkeypatch.setattr(history, "read_search", lambda limit=500: search_recs)
    with mock.patch("coding_with_beat.profile.get_source", side_effect=Exception("no AM")):
        prof = profile.build_profile("weekly")
    term_keys = [t for t, _ in prof["top_search_terms"]]
    assert "lofi" in term_keys


def test_build_profile_returns_required_keys(monkeypatch):
    monkeypatch.setattr(history, "read", lambda limit=500: _weekly_tracks())
    monkeypatch.setattr(history, "read_search", lambda limit=500: [])
    with mock.patch("coding_with_beat.profile.get_source", side_effect=Exception("no AM")):
        prof = profile.build_profile("weekly")
    required = {
        "period", "generated_at", "play_count", "top_artists", "top_genres",
        "top_search_terms", "language_pref", "loved_artists",
        "recent_trend", "stable_pref", "declining_pref", "time_pattern",
    }
    assert required.issubset(prof.keys())
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_profile.py -v
```

Expected: `FAILED` — `ModuleNotFoundError: No module named 'coding_with_beat.profile'`

- [ ] **Step 3: Create `coding_with_beat/profile.py`**

```python
# coding_with_beat/profile.py
"""User music profile: analysis, report generation, and recommendation queries."""
from __future__ import annotations

import datetime
import re
from collections import Counter

from . import history as _history
from .history import _STYLE_KEYWORDS

_PERIOD_DAYS: dict[str, int] = {
    "daily": 1,
    "weekly": 7,
    "monthly": 30,
    "yearly": 365,
}

_INSTRUMENTAL_KEYWORDS = frozenset([
    "instrumental", "无人声", "pure music", "纯音乐", "bgm", "ost",
    "soundtrack", "piano solo", "guitar instrumental",
])

_STOPWORDS = frozenset([
    "a", "the", "and", "or", "of", "for", "in", "to", "with", "no",
    "some", "my", "by", "on", "at", "is", "it", "be", "lo", "fi",
])


def _time_band(hour: int) -> str:
    if 6 <= hour < 12:
        return "morning"
    elif 12 <= hour < 18:
        return "afternoon"
    elif 18 <= hour < 24:
        return "evening"
    else:
        return "night"


def _detect_language(text: str) -> str:
    text_lower = text.lower()
    if any(kw in text_lower for kw in _INSTRUMENTAL_KEYWORDS):
        return "instrumental"
    cjk_count = sum(
        1 for c in text
        if '一' <= c <= '鿿' or '぀' <= c <= 'ヿ'
    )
    return "zh" if cjk_count >= 1 else "en"


def _match_genres(text: str) -> list[str]:
    text_lower = text.lower()
    return [
        tag for tag, keywords in _STYLE_KEYWORDS.items()
        if any(kw in text_lower for kw in keywords)
    ]


def _genre_counter(tracks: list[dict]) -> Counter:
    c: Counter = Counter()
    for t in tracks:
        text = f"{t.get('artist', '')} {t.get('album', '')} {t.get('title', '')}".lower()
        for g in _match_genres(text):
            c[g] += 1
    return c


def build_profile(period: str = "weekly", source: str | None = None) -> dict:
    """Build a UserProfile dict from play and search history.

    Args:
        period: 'daily' | 'weekly' | 'monthly' | 'yearly'
        source: optional override — 'apple_music' | 'local' | None (auto)

    Raises:
        ValueError('insufficient_history') if fewer than 5 records found in period.
    """
    period = period if period in _PERIOD_DAYS else "weekly"
    days = _PERIOD_DAYS[period]
    now = datetime.datetime.now()
    cutoff = now - datetime.timedelta(days=days)

    # ── Fetch tracks ──────────────────────────────────────────────────────────
    raw_tracks: list[dict] = []

    if source != "local":
        try:
            from .sources import get_source
            am = get_source("apple_music")
            fn = getattr(am, "play_history", None)
            if callable(fn):
                raw_tracks.extend(fn(days + 1, 500))
        except Exception:
            pass

    if source != "apple_music":
        raw_tracks.extend(_history.read(limit=500))

    # ── Deduplicate and normalise timestamps ──────────────────────────────────
    seen: set[str] = set()
    tracks: list[dict] = []
    for t in raw_tracks:
        ts = t.get("ts")
        if isinstance(ts, str):
            try:
                ts = datetime.datetime.strptime(ts[:19], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
        if ts is None:
            continue
        key = f"{(t.get('title') or '').lower()}|{(t.get('artist') or '').lower()}"
        if key in seen:
            continue
        seen.add(key)
        t = dict(t)
        t["ts"] = ts
        tracks.append(t)

    period_tracks = [t for t in tracks if t["ts"] >= cutoff]

    if len(period_tracks) < 5:
        raise ValueError("insufficient_history")

    # ── Top artists ───────────────────────────────────────────────────────────
    artist_counter: Counter = Counter()
    for t in period_tracks:
        a = (t.get("artist") or "").strip()
        if a and a != "?":
            artist_counter[a] += t.get("played_count", 1)
    top_artists = artist_counter.most_common(5)

    # ── Top genres ────────────────────────────────────────────────────────────
    top_genres = _genre_counter(period_tracks).most_common(5)

    # ── Language preference ───────────────────────────────────────────────────
    lang_counter: Counter = Counter()
    for t in period_tracks:
        text = f"{t.get('title', '')} {t.get('artist', '')}"
        lang_counter[_detect_language(text)] += 1
    total = sum(lang_counter.values()) or 1
    language_pref = {k: round(v / total, 2) for k, v in lang_counter.most_common()}

    # ── Search terms ──────────────────────────────────────────────────────────
    search_records = _history.read_search(limit=500)
    recent_searches = [s for s in search_records if s["ts"] >= cutoff]
    term_counter: Counter = Counter()
    for rec in recent_searches:
        tokens = re.findall(r'[a-zA-Z一-鿿]+', rec["query"].lower())
        for tok in tokens:
            if tok not in _STOPWORDS and len(tok) > 1:
                term_counter[tok] += 1
    top_search_terms = term_counter.most_common(8)

    # ── Loved artists ─────────────────────────────────────────────────────────
    loved_artists: list[str] = []
    try:
        from .sources import get_source
        am = get_source("apple_music")
        fn = getattr(am, "list_loved", None)
        if callable(fn):
            loved_artists = list({
                t.get("artist", "").strip()
                for t in fn(50)
                if t.get("artist") and t.get("artist") != "?"
            })[:5]
    except Exception:
        pass

    # ── Preference trends (first half vs second half) ─────────────────────────
    mid = cutoff + datetime.timedelta(days=days / 2)
    first_genres = _genre_counter([t for t in period_tracks if t["ts"] < mid])
    second_genres = _genre_counter([t for t in period_tracks if t["ts"] >= mid])
    all_genre_keys = set(first_genres) | set(second_genres)

    recent_trend: list[str] = []
    stable_pref: list[str] = []
    declining_pref: list[str] = []
    for g in all_genre_keys:
        f, s = first_genres.get(g, 0), second_genres.get(g, 0)
        if f == 0 and s > 0:
            recent_trend.append(g)
        elif s == 0 and f > 0:
            declining_pref.append(g)
        else:
            stable_pref.append(g)

    # ── Time pattern ──────────────────────────────────────────────────────────
    band_genres: dict[str, Counter] = {
        "morning": Counter(), "afternoon": Counter(),
        "evening": Counter(), "night": Counter(),
    }
    for t in period_tracks:
        band = _time_band(t["ts"].hour)
        text = f"{t.get('artist', '')} {t.get('album', '')}".lower()
        for g in _match_genres(text):
            band_genres[band][g] += 1
    time_pattern = {
        band: [g for g, _ in ctr.most_common(3)]
        for band, ctr in band_genres.items()
        if ctr
    }

    return {
        "period": period,
        "generated_at": now,
        "play_count": len(period_tracks),
        "top_artists": top_artists,
        "top_genres": top_genres,
        "top_search_terms": top_search_terms,
        "language_pref": language_pref,
        "loved_artists": loved_artists,
        "recent_trend": recent_trend,
        "stable_pref": stable_pref,
        "declining_pref": declining_pref,
        "time_pattern": time_pattern,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_profile.py -v
```

Expected: all `test_build_profile_*` tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add coding_with_beat/profile.py tests/test_profile.py
git commit -m "feat(profile): add profile.py with build_profile()"
```

---

## Task 4: Add `build_report()` to `profile.py`

**Files:**
- Modify: `coding_with_beat/profile.py` (append `build_report`)
- Test: `tests/test_profile.py` (append report tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_profile.py`:

```python
# ── build_report ──────────────────────────────────────────────────────────────

def _make_profile(overrides=None):
    now = datetime.datetime.now()
    base = {
        "period": "weekly",
        "generated_at": now,
        "play_count": 42,
        "top_artists": [("Hans Zimmer", 12), ("周杰伦", 8), ("ODESZA", 5)],
        "top_genres": [("lofi", 9), ("ambient", 6), ("classical", 4)],
        "top_search_terms": [("lofi", 5), ("coding", 4)],
        "language_pref": {"en": 0.6, "zh": 0.3, "instrumental": 0.1},
        "loved_artists": ["Hans Zimmer"],
        "recent_trend": ["synthwave"],
        "stable_pref": ["lofi", "ambient"],
        "declining_pref": ["华语"],
        "time_pattern": {"night": ["lofi", "ambient"], "afternoon": ["classical"]},
    }
    if overrides:
        base.update(overrides)
    return base


def test_build_report_contains_play_count():
    report = profile.build_report(_make_profile())
    assert "42" in report


def test_build_report_contains_top_artist():
    report = profile.build_report(_make_profile())
    assert "Hans Zimmer" in report


def test_build_report_contains_top_genre():
    report = profile.build_report(_make_profile())
    assert "lofi" in report


def test_build_report_contains_preference_changes():
    report = profile.build_report(_make_profile())
    assert "synthwave" in report   # recent_trend
    assert "华语" in report         # declining_pref


def test_build_report_contains_time_pattern():
    report = profile.build_report(_make_profile())
    assert "lofi" in report


def test_build_report_contains_summary_sentence():
    report = profile.build_report(_make_profile())
    assert "💬" in report


def test_build_report_all_periods():
    for period in ("daily", "weekly", "monthly", "yearly"):
        prof = _make_profile({"period": period})
        report = profile.build_report(prof)
        assert "📅" in report


def test_build_report_empty_trend_sections_hidden():
    prof = _make_profile({"recent_trend": [], "stable_pref": [], "declining_pref": []})
    report = profile.build_report(prof)
    # Should not crash and should still contain basic stats
    assert "42" in report
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_profile.py::test_build_report_contains_play_count -v
```

Expected: `FAILED` — `AttributeError: module 'coding_with_beat.profile' has no attribute 'build_report'`

- [ ] **Step 3: Append `build_report` to `coding_with_beat/profile.py`**

```python
_PERIOD_LABELS: dict[str, str] = {
    "daily":   "今日听歌报告",
    "weekly":  "本周听歌报告",
    "monthly": "本月听歌报告",
    "yearly":  "年度听歌报告",
}

_BAND_LABELS: dict[str, str] = {
    "morning":   "早晨",
    "afternoon": "下午",
    "evening":   "傍晚",
    "night":     "深夜",
}

_LANG_LABELS: dict[str, str] = {
    "zh": "中文", "en": "英文", "instrumental": "纯音乐",
}

_PERIOD_ZH: dict[str, str] = {
    "daily": "天", "weekly": "周", "monthly": "月", "yearly": "年",
}


def build_report(profile: dict) -> str:
    """Generate a plain-text listening report from a UserProfile dict."""
    period = profile.get("period", "weekly")
    generated_at = profile.get("generated_at", datetime.datetime.now())
    days = _PERIOD_DAYS.get(period, 7)
    start = (generated_at - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    end = generated_at.strftime("%Y-%m-%d")
    label = _PERIOD_LABELS.get(period, "听歌报告")

    top_artists  = profile.get("top_artists", [])
    top_genres   = profile.get("top_genres", [])
    language_pref = profile.get("language_pref", {})
    recent_trend = profile.get("recent_trend", [])
    stable_pref  = profile.get("stable_pref", [])
    declining_pref = profile.get("declining_pref", [])
    time_pattern = profile.get("time_pattern", {})
    play_count   = profile.get("play_count", 0)

    artists_str = " · ".join(a for a, _ in top_artists[:3]) if top_artists else "—"
    genres_str  = " · ".join(g for g, _ in top_genres[:3]) if top_genres else "—"

    lang_parts = [
        f"{_LANG_LABELS.get(lang, lang)} {int(ratio * 100)}%"
        for lang, ratio in sorted(language_pref.items(), key=lambda x: -x[1])
    ]
    lang_str = " · ".join(lang_parts) if lang_parts else "—"

    lines = [
        f"📅 {label}（{start} ~ {end}）",
        "",
        f"▸ 共播放 {play_count} 次，常听歌手：{artists_str}",
        f"▸ 主要曲风：{genres_str}",
        f"▸ 语言偏好：{lang_str}",
    ]

    if recent_trend or stable_pref or declining_pref:
        lines += ["", "📈 偏好变化"]
        if recent_trend:
            lines.append(f"  新增：{' · '.join(recent_trend[:3])}")
        if stable_pref:
            lines.append(f"  稳定：{' · '.join(stable_pref[:3])}")
        if declining_pref:
            lines.append(f"  下降：{' · '.join(declining_pref[:3])}")

    if time_pattern:
        lines += ["", "🕐 时间规律"]
        for band in ("morning", "afternoon", "evening", "night"):
            genres = time_pattern.get(band, [])
            if genres:
                lines.append(f"  {_BAND_LABELS[band]}：{' · '.join(genres[:3])}")

    # Natural language summary
    lines += ["", "💬 总结"]
    summary_parts: list[str] = []
    if top_genres:
        top2 = " 和 ".join(g for g, _ in top_genres[:2])
        summary_parts.append(f"这{_PERIOD_ZH.get(period, '周')}你的音乐偏好明显偏向 {top2}")
    if declining_pref:
        summary_parts.append(f"{'、'.join(declining_pref[:2])} 播放次数有所下降")
    if recent_trend:
        summary_parts.append(f"{'、'.join(recent_trend[:2])} 开始走高")
    if summary_parts:
        lines.append("，".join(summary_parts) + "。")
    else:
        lines.append(f"本{_PERIOD_ZH.get(period, '周')}共播放 {play_count} 首，继续保持！")

    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_profile.py -v
```

Expected: all `test_build_report_*` tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add coding_with_beat/profile.py tests/test_profile.py
git commit -m "feat(profile): add build_report()"
```

---

## Task 5: Add `build_recommendation_queries()` to `profile.py`

**Files:**
- Modify: `coding_with_beat/profile.py` (append `build_recommendation_queries`)
- Test: `tests/test_profile.py` (append recommendation tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_profile.py`:

```python
# ── build_recommendation_queries ──────────────────────────────────────────────

def test_build_recommendation_queries_returns_list_of_strings():
    queries = profile.build_recommendation_queries(_make_profile())
    assert isinstance(queries, list)
    assert all(isinstance(q, str) for q in queries)
    assert 1 <= len(queries) <= 3


def test_build_recommendation_queries_includes_stable_genre():
    prof = _make_profile({"stable_pref": ["lofi", "jazz"], "recent_trend": []})
    queries = profile.build_recommendation_queries(prof)
    assert any("lofi" in q or "jazz" in q for q in queries)


def test_build_recommendation_queries_includes_context():
    queries = profile.build_recommendation_queries(_make_profile(), context="写代码")
    assert any("写代码" in q for q in queries)


def test_build_recommendation_queries_fallback_when_no_trend():
    prof = _make_profile({"recent_trend": [], "top_genres": [("classical", 5), ("jazz", 3)]})
    queries = profile.build_recommendation_queries(prof)
    # slot 2 falls back to second top_genre
    assert any("jazz" in q or "classical" in q for q in queries)


def test_build_recommendation_queries_includes_top_artist():
    prof = _make_profile({"top_artists": [("Hans Zimmer", 10)]})
    queries = profile.build_recommendation_queries(prof)
    assert any("Hans Zimmer" in q for q in queries)


def test_build_recommendation_queries_not_empty_when_minimal_profile():
    prof = _make_profile({
        "stable_pref": [], "recent_trend": [],
        "top_genres": [("lofi", 3)], "top_artists": [],
    })
    queries = profile.build_recommendation_queries(prof)
    assert len(queries) >= 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_profile.py::test_build_recommendation_queries_returns_list_of_strings -v
```

Expected: `FAILED` — `AttributeError: module has no attribute 'build_recommendation_queries'`

- [ ] **Step 3: Append `build_recommendation_queries` to `coding_with_beat/profile.py`**

```python
def build_recommendation_queries(profile: dict, context: str = "") -> list[str]:
    """Generate 2–3 smart_search query strings based on user profile.

    Slot 1: stable preference genres + context (core recommendation)
    Slot 2: recent trend genre for exploration (falls back to 2nd top genre)
    Slot 3: top artist extension
    """
    top_genres   = profile.get("top_genres", [])
    recent_trend = profile.get("recent_trend", [])
    top_artists  = profile.get("top_artists", [])
    stable_pref  = profile.get("stable_pref", [])

    queries: list[str] = []

    # Slot 1: stable pref (or top genres as fallback) + context
    base = stable_pref[:2] if stable_pref else [g for g, _ in top_genres[:2]]
    if base:
        slot1 = " ".join(base)
        slot1 += f" {context} instrumental focus" if context else " instrumental focus"
        queries.append(slot1.strip())

    # Slot 2: recent trend for exploration; fall back to second top genre
    trend = recent_trend[0] if recent_trend else (
        top_genres[1][0] if len(top_genres) > 1 else None
    )
    if trend:
        queries.append(f"{trend} night coding focus electronic")

    # Slot 3: top artist extension
    if top_artists:
        queries.append(f"{top_artists[0][0]} similar instrumental lo-fi")

    # Guarantee at least 1 query
    if not queries and top_genres:
        queries.append(f"{top_genres[0][0]} instrumental")

    return queries[:3]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_profile.py -v
```

Expected: all profile tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add coding_with_beat/profile.py tests/test_profile.py
git commit -m "feat(profile): add build_recommendation_queries()"
```

---

## Task 6: Add `generate_profile()` MCP tool to `server.py`

**Files:**
- Modify: `coding_with_beat/server.py:17` (add `profile` to imports)
- Modify: `coding_with_beat/server.py` (append new MCP tool near end, before last tool or after `history_search`)

- [ ] **Step 1: Add `profile` to server imports**

In `coding_with_beat/server.py` line 17, change:

```python
from . import dj, focus, history, state
```

to:

```python
from . import dj, focus, history, profile, state
```

- [ ] **Step 2: Append `generate_profile()` MCP tool to `server.py`**

Add after the `history_search` tool (after line ~734):

```python
@mcp.tool()
async def generate_profile(
    period: str = "weekly",
    context: str = "",
) -> str:
    """Generate a personal music listening report with profile analysis and recommendations.

    Analyses play history and search patterns to produce:
    - Listening statistics: top artists, genres, language preference
    - Preference trends: rising, stable, and declining genres
    - Time-of-day listening patterns
    - 2–3 personalised smart_search query strings ready to play

    After displaying the report, offer to call smart_search(queries=[...])
    with the returned recommendation queries.

    Args:
        period: Report time window — daily | weekly | monthly | yearly (default: weekly)
        context: Optional scene or mood hint to tune recommendations
                 e.g. "写代码", "跑步", "放松"
    """
    import asyncio as _asyncio

    if period not in ("daily", "weekly", "monthly", "yearly"):
        period = "weekly"

    try:
        prof = await _asyncio.to_thread(profile.build_profile, period)
    except ValueError:
        return "（听歌记录不足 5 首，多听一会儿再来生成报告吧 🎵）"

    report_text = profile.build_report(prof)
    queries = profile.build_recommendation_queries(prof, context)

    rec_lines = ["", "─" * 40, "🎵 个性化推荐（可用 smart_search 播放）："]
    for i, q in enumerate(queries, 1):
        rec_lines.append(f"  {i}. {q}")
    rec_lines.append("")
    rec_lines.append("想播放推荐吗？说"播放推荐"或"play 1"即可。")

    return report_text + "\n" + "\n".join(rec_lines)
```

- [ ] **Step 3: Run existing tests to verify nothing broke**

```bash
python -m pytest tests/ -v --ignore=tests/test_apple_music.py --ignore=tests/test_qq_music.py -x
```

Expected: all tests `PASSED`

- [ ] **Step 4: Verify the tool is importable**

```bash
python -c "from coding_with_beat.server import generate_profile; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add coding_with_beat/server.py
git commit -m "feat(server): add generate_profile() MCP tool"
```

---

## Task 7: Add `cwb profile` CLI command

**Files:**
- Modify: `coding_with_beat/__main__.py` (add `cmd_profile` function + COMMANDS entry)
- Test: `tests/test_cli.py` (append profile CLI tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_cli.py`:

```python
# ── cwb profile ───────────────────────────────────────────────────────────────

def test_cmd_profile_invalid_period(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["cwb", "profile", "quarterly"])
    from coding_with_beat.__main__ import cmd_profile
    rc = cmd_profile()
    out = capsys.readouterr().out
    assert rc == 2
    assert "error" in out.lower()


def test_cmd_profile_insufficient_history(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["cwb", "profile", "weekly"])
    from coding_with_beat import profile as _profile

    def _raise(period, **kw):
        raise ValueError("insufficient_history")

    monkeypatch.setattr(_profile, "build_profile", _raise)
    from coding_with_beat.__main__ import cmd_profile
    rc = cmd_profile()
    out = capsys.readouterr().out
    assert rc == 0
    assert "不足" in out or "5" in out


def test_cmd_profile_weekly_success(monkeypatch, capsys):
    import sys, datetime
    monkeypatch.setattr(sys, "argv", ["cwb", "profile", "weekly"])

    fake_profile = {
        "period": "weekly",
        "generated_at": datetime.datetime.now(),
        "play_count": 10,
        "top_artists": [("Hans Zimmer", 5)],
        "top_genres": [("lofi", 4)],
        "top_search_terms": [],
        "language_pref": {"en": 1.0},
        "loved_artists": [],
        "recent_trend": [],
        "stable_pref": ["lofi"],
        "declining_pref": [],
        "time_pattern": {},
    }
    from coding_with_beat import profile as _profile
    monkeypatch.setattr(_profile, "build_profile", lambda period, **kw: fake_profile)

    from coding_with_beat.__main__ import cmd_profile
    rc = cmd_profile()
    out = capsys.readouterr().out
    assert rc == 0
    assert "Hans Zimmer" in out
    assert "lofi" in out
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_cli.py::test_cmd_profile_invalid_period -v
```

Expected: `FAILED` — `ImportError: cannot import name 'cmd_profile'`

- [ ] **Step 3: Add `cmd_profile` to `__main__.py`**

Add this function before the `COMMANDS` dict (e.g. after `cmd_history`):

```python
def cmd_profile() -> int:
    from . import profile as _profile

    valid = {"daily", "weekly", "monthly", "yearly"}
    period = sys.argv[2] if len(sys.argv) > 2 else "weekly"
    if period not in valid:
        print(f"error: period must be one of: {', '.join(sorted(valid))}")
        return 2

    try:
        prof = _profile.build_profile(period)
    except ValueError:
        print("（听歌记录不足 5 首，多听一会儿再来生成报告吧 🎵）")
        return 0

    print(_profile.build_report(prof))
    print()
    queries = _profile.build_recommendation_queries(prof)
    if queries:
        print("🎵 个性化推荐 queries：")
        for i, q in enumerate(queries, 1):
            print(f"  {i}. {q}")
    return 0
```

Add to `COMMANDS` dict (after `"history": cmd_history`):

```python
    "profile": cmd_profile,
    "画像": cmd_profile,
    "音乐画像": cmd_profile,
    "听歌报告": cmd_profile,
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_cli.py -v
```

Expected: all CLI tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add coding_with_beat/__main__.py tests/test_cli.py
git commit -m "feat(cli): add cwb profile [daily|weekly|monthly|yearly] command"
```

---

## Task 8: Create `skills/cwb-profile/SKILL.md`

**Files:**
- Create: `skills/cwb-profile/SKILL.md`

- [ ] **Step 1: Create the skill directory and file**

```bash
mkdir -p /Users/jianchengpan/Projects/coding-with-beat/skills/cwb-profile
```

Create `skills/cwb-profile/SKILL.md`:

```markdown
---
name: cwb-profile
description: Music profile analysis and listening reports. Activate when user asks for listening history analysis, music profile, periodic report (daily/weekly/monthly/yearly), or personalized recommendations based on history.
metadata:
  short-description: Personal music profile, listening reports, and history-based recommendations
---

# coding-with-beat — Music Profile & Listening Report

You have access to the `generate_profile` MCP tool. Use it to analyse the user's listening history and generate personalised reports and recommendations.

## When to activate

- 听歌报告 · 音乐画像 · 本周报告 · 本月报告 · 年度报告 · 日报告
- music profile · listening report · music report · my music taste
- 分析我的听歌 · 我最近在听什么 · 推荐基于历史
- history profile · what have I been listening to
- 给我推荐基于历史 · 根据我的喜好推荐

## Dispatch logic

1. **Detect period** from the user's message:
   - 今天 / 日 / today / daily → `"daily"`
   - 本周 / 这周 / week / weekly → `"weekly"` (default)
   - 本月 / 这个月 / month / monthly → `"monthly"`
   - 今年 / 年度 / year / yearly → `"yearly"`
   - No mention → default `"weekly"`

2. **Extract context** (optional scene/mood words the user mentions):
   - 写代码 / coding / 跑步 / 放松 / 通勤 etc. → pass as `context`
   - If no scene mentioned → `context = ""`

3. **Call the tool:**
   ```
   generate_profile(period=<detected>, context=<extracted>)
   ```

4. **Display** the returned report in full.

5. **After the report**, present the recommendation queries and ask:
   > "要播放推荐吗？说"播放推荐1"或直接告诉我你想听哪个方向。"

6. **If user agrees to play:**
   - Extract the query strings from the report's recommendation section
   - Call `smart_search(queries=[<those queries>])`
   - Show results and let user pick by number with `play_number(n)`

## Example exchanges

**User:** 帮我生成本周的听歌报告
→ `generate_profile(period="weekly", context="")`

**User:** 我最近都在听什么，帮我分析一下，适合写代码的
→ `generate_profile(period="weekly", context="写代码")`

**User:** 给我出一份年度音乐画像
→ `generate_profile(period="yearly", context="")`

**User:** 今天听了什么
→ `generate_profile(period="daily", context="")`

## Error handling

If the tool returns "不足 5 首", tell the user:
> "还没有足够的听歌记录来生成画像，先多听几首再来吧 🎵"
Do not retry automatically.
```

- [ ] **Step 2: Verify the skill file is valid YAML front-matter**

```bash
python -c "
import re
content = open('skills/cwb-profile/SKILL.md').read()
assert content.startswith('---'), 'missing frontmatter'
assert 'name: cwb-profile' in content
assert 'generate_profile' in content
print('SKILL.md OK')
"
```

Expected: `SKILL.md OK`

- [ ] **Step 3: Run full test suite to confirm no regressions**

```bash
python -m pytest tests/ -v --ignore=tests/test_apple_music.py --ignore=tests/test_qq_music.py
```

Expected: all tests `PASSED`

- [ ] **Step 4: Commit**

```bash
git add skills/cwb-profile/SKILL.md
git commit -m "feat(skill): add cwb-profile skill for music profile and listening reports"
```

---

## Final verification

- [ ] **Smoke-test CLI (offline)**

```bash
python -m coding_with_beat profile weekly
```

Expected: either a report or the "不足 5 首" message — no Python traceback.

- [ ] **Smoke-test MCP tool import**

```bash
python -c "
import asyncio
from coding_with_beat.server import generate_profile
result = asyncio.run(generate_profile('weekly', ''))
print(result[:120])
"
```

Expected: report text or "不足 5 首" message — no traceback.

- [ ] **Verify search capture is working**

```bash
# Check search_history.log after a smart_search call (requires running MCP server)
cat ~/.coding-with-beat/search_history.log | tail -5
```

Expected: recent search queries in pipe-delimited format.
