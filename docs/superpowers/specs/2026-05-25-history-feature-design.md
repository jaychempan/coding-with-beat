# History Feature Design

**Date:** 2026-05-25
**Status:** Approved

## Overview

Add play history recording and history-based music recommendation to coding-with-beat. History is recorded automatically on track change and exposed via two new MCP tools: `list_history` and `history_search`.

## Architecture

```
watch.py  ──track change──▶  history.py · write()
                                  │
                             history.log
                           (~/.coding-with-beat/history.log)
                           (text, append-only)
                                  │
server.py ──list_history()──▶  history.py · read()
           ──history_search()─▶  history.py · summarize()
                                       │
                              生成 smart_search queries
                                       │
                             _multi_angle_search()
```

Three layers:
- **Recording layer**: `watch.py` detects track change → calls `history.write()`, appends to `history.log`
- **Analysis layer**: `history.py` reads, parses, frequency-counts (top artists, style tags, recently-unheard candidates)
- **Tool layer**: `server.py` exposes `list_history` and `history_search` as MCP tools

## Data Format

Reuses the existing format from `state.write_history` (no migration needed):

```
2026-05-25 23:14:02 | Clair de Lune | Debussy | Classical Piano
2026-05-25 23:31:17 | 夜曲 | 周杰伦 | 十一月的萧邦
```

File location: `~/.coding-with-beat/history.log` (append-only, one entry per line)

## `history.py` Module

New file: `coding_with_beat/history.py`

| Function | Description |
|----------|-------------|
| `write(title, artist, album)` | Append one record. Migrated from `state.write_history` (which is currently defined but never called). |
| `read(limit)` | Read most recent N entries. Returns `list[dict]` with keys `title`, `artist`, `album`, `ts`. |
| `top_artists(n, window_days)` | Count plays per artist in the last `window_days` days. Returns top N as `list[(artist, count)]`. |
| `summarize(window_days=14)` | Returns `dict` with `top_artists`, `style_tags` (keyword-matched), `unheard_candidates` (tracks in history but not played in `window_days`). |

**Style tag inference** (no ML, keyword matching only):
`summarize()` scans `album` and `artist` fields for keywords (`lofi`, `jazz`, `classical`, `电子`, `民谣`, `ambient`, `synthwave`, etc.) and tallies frequency. The top 2–3 tags feed into query generation in `history_search`.

## `watch.py` Changes

On track change (non-empty title → different title), call `history.write(title, artist, album)`.

Remove `state.write_history` (currently defined but never called anywhere). `history.write` is the single write path going forward.

## New MCP Tools

### `list_history(limit=20)`

Returns the most recent plays, formatted similarly to `list_loved`:

```
最近播放（最近 20 首）：
1. Clair de Lune — Debussy · Classical Piano
2. 夜曲 — 周杰伦 · 十一月的萧邦
...
```

### `history_search()`

No parameters. Internal flow:

1. Call `history.summarize(window_days=14)`
2. Build 2–3 search query angles from top artists + style tags:
   - One angle: "most recently heard style" (e.g., `"lofi chill instrumental ambient"`)
   - One angle: "similar to top artist" (e.g., `"周杰伦 华语流行 piano ballad"`)
   - One angle (if unheard candidates exist): construct a query from artists not heard in `window_days`
3. Call `_multi_angle_search(queries, label="History · 为你推荐")`
4. Results written to search queue; return numbered list

**Example output:**
```
🎶 根据你的播放历史推荐：

🎧 最近常听风格
1. Gymnopédie No.1 — Satie · Gymnopédies
2. Experience — Ludovico Einaudi · In a Time Lapse

🕰️ 许久没听
3. 夜曲 — 周杰伦 · 十一月的萧邦
4. Retrograde — James Blake · Overgrown
```

User picks by number; calls `play_number(N)`.

**Edge case — no history yet:** Return a friendly message explaining history is empty and suggesting to listen for a while first.

## Files Changed

| File | Change |
|------|--------|
| `coding_with_beat/history.py` | New module |
| `coding_with_beat/watch.py` | Call `history.write()` on track change |
| `coding_with_beat/server.py` | Add `list_history` and `history_search` MCP tools |
| `coding_with_beat/state.py` | Remove `write_history` (dead code, replaced by `history.write`) |
| `tests/test_history.py` | New unit tests for `history.py` functions |

## Out of Scope

- Skip tracking (not recording skips, only completed/started plays)
- SQLite migration (text log is sufficient)
- Time-of-day or vibe-based history segmentation (future)
- Exposing history to CLAUDE.md for companion check-in (future)
