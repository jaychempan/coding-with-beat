# History Feature Design

**Date:** 2026-05-25
**Status:** Approved (revised)

## Overview

Add play history recording and history-based music recommendation to coding-with-beat. History is read from Apple Music's native play database when available (via AppleScript `played count` / `played date`), and falls back to a local `history.log` for other sources. Two new MCP tools are exposed: `list_history` and `history_search`.

## Architecture

```
Apple Music source               Other sources (QQ Music, local)
       │                                      │
AppleScript                           watch.py · track change
played date / played count                    │
       │                               history.py · write()
       │                                      │
       │                               history.log
       │                         (~/.coding-with-beat/history.log)
       └──────────────┬───────────────────────┘
                      │
               history.py · summarize()
                      │
           生成 smart_search queries
                      │
            _multi_angle_search()
                      │
server.py ──list_history()──▶  history.py · read()
           ──history_search()─▶  history.py · summarize()
```

Three layers:
- **Data layer**: Apple Music source queries `played date` / `played count` via AppleScript; other sources fall back to local `history.log`
- **Analysis layer**: `history.py` unifies both data sources, frequency-counts (top artists, style tags, recently-unheard candidates)
- **Tool layer**: `server.py` exposes `list_history` and `history_search` as MCP tools

## Data Sources

### Apple Music (primary)

AppleScript can query the library directly for play history — richer than self-recorded logs:
- `played count` — total play count per track
- `played date` — last played timestamp
- Covers listening done in Music.app directly, on iPhone, etc. (not only via CWB)

Query pattern (used inside `apple_music.py`):
```applescript
tell application "Music"
  set recentTracks to (every track of library playlist 1 whose played date > (current date) - N * days)
  -- returns title, artist, album, played count, played date per track
end tell
```

New method added to `apple_music.py`: `play_history(window_days, limit)` → `list[dict]` with keys `title`, `artist`, `album`, `played_count`, `played_date`.

### Other sources (QQ Music, local) — fallback

Self-recorded `history.log`, written by `watch.py` on track change. Format (unchanged from `state.write_history` skeleton):

```
2026-05-25 23:14:02 | Clair de Lune | Debussy | Classical Piano
2026-05-25 23:31:17 | 夜曲 | 周杰伦 | 十一月的萧邦
```

File location: `~/.coding-with-beat/history.log` (append-only, one entry per line)

## `history.py` Module

New file: `coding_with_beat/history.py`

| Function | Description |
|----------|-------------|
| `write(title, artist, album)` | Append one record to `history.log`. Migrated from `state.write_history` (currently defined but never called). |
| `read(limit)` | Read most recent N entries from `history.log`. Returns `list[dict]` with keys `title`, `artist`, `album`, `ts`. |
| `summarize(source, window_days=14)` | Unified entry point. If `source == "apple_music"`, calls `apple_music.py`'s `play_history()`. Otherwise reads `history.log`. Returns `dict` with `top_artists`, `style_tags`, `unheard_candidates`. |

**`summarize()` output shape:**
```python
{
  "top_artists": [("周杰伦", 9), ("刘德华", 4), ...],
  "style_tags": ["华语", "classical", "lofi"],        # keyword-matched from album/artist
  "unheard_candidates": [{"title": ..., "artist": ...}, ...]  # in history but >window_days ago
}
```

**Style tag inference** (no ML, keyword matching only):
Scans `album` and `artist` fields for keywords (`lofi`, `jazz`, `classical`, `电子`, `民谣`, `ambient`, `synthwave`, `华语`, `古风`, etc.) and tallies frequency. Top 2–3 tags feed into query generation in `history_search`.

## `watch.py` Changes

On track change (non-empty title → different title), if the current source is **not** Apple Music, call `history.write(title, artist, album)`. For Apple Music, the native database is the source of truth — no write needed.

Remove `state.write_history` (currently defined but never called). `history.write` is the single write path for non-AM sources going forward.

## New MCP Tools

### `list_history(limit=20)`

Returns the most recent plays. For Apple Music, queries `play_history(window_days=30, limit=limit)` sorted by `played_date` desc. For other sources, reads `history.log`.

```
最近播放（最近 20 首）：
1. 天空之城 — 催眠音乐盒 · 9次播放
2. 酒狂 — 龚一 · 2次播放
3. 夜曲 — 周杰伦 · 十一月的萧邦
...
```

Play count shown for Apple Music source; omitted for log-based sources.

### `history_search()`

No parameters. Internal flow:

1. Call `history.summarize(source=current_source, window_days=14)`
2. Build 2–3 search query angles:
   - Angle 1 — "most recently heard style": e.g. `"华语 piano ballad 钢琴"`
   - Angle 2 — "similar to top artist": e.g. `"周杰伦 风格 华语流行 情歌"`
   - Angle 3 (if unheard candidates exist) — artists not heard in `window_days`: e.g. `"刘德华 经典 怀旧"`
3. Call `_multi_angle_search(queries, label="History · 为你推荐")`
4. Results written to search queue; return numbered list

**Example output:**
```
🎶 根据你的播放历史推荐：

🎧 最近常听风格
1. Gymnopédie No.1 — Satie · Gymnopédies
2. Experience — Ludovico Einaudi · In a Time Lapse

🕰️ 许久没听
3. 忘情水 — 刘德华
4. 后会无期 — 徐良
```

User picks by number; calls `play_number(N)`.

**Edge case — no history:** Return a friendly message explaining history is empty and suggesting to listen for a while first.

## Files Changed

| File | Change |
|------|--------|
| `coding_with_beat/history.py` | New module: `write`, `read`, `summarize` |
| `coding_with_beat/sources/apple_music.py` | Add `play_history(window_days, limit)` method |
| `coding_with_beat/watch.py` | Call `history.write()` on track change for non-AM sources |
| `coding_with_beat/server.py` | Add `list_history` and `history_search` MCP tools |
| `coding_with_beat/state.py` | Remove `write_history` (dead code, replaced by `history.write`) |
| `tests/test_history.py` | New unit tests for `history.py` functions |

## Out of Scope

- Skip tracking (not recording skips, only completed/started plays)
- SQLite migration (text log is sufficient for non-AM sources)
- Time-of-day or vibe-based history segmentation (future)
- Exposing history to CLAUDE.md for companion check-in (future)
