# Loved Tracks Support — Design Spec

**Date:** 2026-05-24  
**Status:** Approved

## Problem

Apple Music distinguishes between "library" (all added tracks) and "loved" (tracks the user has hearted). Currently, coding-with-beat treats all library tracks identically (`source="library"`, tag `[资料库]`). There is no way to browse, search, or prioritise loved tracks.

## Goals

1. **Display**: Loved tracks show `[♥ 喜欢]` instead of `[资料库]` everywhere results are listed.
2. **Ranking**: In `smart_search` and regular `search`, loved tracks sort before ordinary library tracks, which sort before catalog results.
3. **Explicit search**: When the user says "从喜欢里找 / 收藏里搜 / play from liked", route to a loved-only search tool.
4. **Companion priority**: Companion check-in recommendations try the loved list first; fall back to `_multi_angle_search` if empty or unsupported.

## Non-goals

- No changes to QQ Music or Local beyond empty stubs.
- No UI changes to the TUI watch/karaoke views (tag appears in text output only).

---

## Data Model

New `source` value: `"loved"`

Sort order for display: `loved → library → local → apple_music`

Tag map addition:
```
"loved" → "[♥ 喜欢]"
```

---

## Component Breakdown

### 1. `coding_with_beat/sources/apple_music.py`

**`search(query, limit)`** — extend AppleScript to fetch `loved of t` per track (4th field). Python sets `source="loved"` when true, `source="library"` otherwise. One query, no duplicates, no performance regression.

**`list_loved(limit=100)`** — new method. AppleScript: `every track of library playlist 1 whose loved is true`. Returns list of `{title, artist, album, source="loved"}`.

**`search_loved(query, limit=8)`** — new method. AppleScript: `whose loved is true and (name contains … or artist contains … or album contains …)`. Returns loved-only results.

### 2. `coding_with_beat/sources/base.py`

Add to `BaseSource`:
- `def list_loved(self, limit: int = 100) -> List[dict]: return []`
- `def search_loved(self, query: str, limit: int = 8) -> List[dict]: return []`

### 3. `coding_with_beat/server.py`

**Tag display** — add `"loved": "[♥ 喜欢]"` to the tag map in both `smart_search` and `search` formatting blocks.

**Result sorting** — after collecting results, sort by source priority: `loved=0, library=1, local=2, apple_music=3`. Applied in `_multi_angle_search` merge and in the regular `search` MCP tool.

**New MCP tool `list_loved()`** — calls `get_source(st.source).list_loved()`, writes queue, returns formatted numbered list. Used when user asks "列出我的收藏" etc.

**New MCP tool `search_loved(query)`** — calls `get_source(st.source).search_loved(query)`, writes queue, returns numbered list with `[♥ 喜欢]` tags. No catalog fallback.

### 4. `coding_with_beat/companion.py`

In `get_queries()` (or equivalent recommendation entry point): before generating `_multi_angle_search` queries, call `list_loved(limit=20)` on the active source. If results exist, pick up to 3 randomly and surface them as the first suggestion group. If `list_loved()` returns `[]`, proceed with normal query generation unchanged.

### 5. `~/.claude/CLAUDE.md` routing rules (install-time injection)

Append to the music routing block:

```
## Loved / 喜欢列表

When user says: 从喜欢里 / 收藏里找 / 我喜欢的 / loved only / play from liked
→ call search_loved(query) instead of smart_search()

When user says: 列出收藏 / 我的喜欢 / show liked / list loved
→ call list_loved()

Normal smart_search() already includes loved tracks (ranked first, tagged [♥ 喜欢]).
```

---

## Source Priority Sort — reference

| source value | display tag | sort key |
|---|---|---|
| `loved` | `[♥ 喜欢]` | 0 |
| `library` | `[资料库]` | 1 |
| `local` | `[本地]` | 2 |
| `apple_music` | `[Apple Music]` | 3 |

---

## Testing

- Unit test: `search()` returns `source="loved"` for loved tracks, `source="library"` for non-loved.
- Unit test: `search_loved()` returns only loved tracks.
- Unit test: `list_loved()` returns non-empty list (mocked AppleScript).
- Unit test: result sort order in server matches priority table.
- Integration: `companion.py` falls back cleanly when `list_loved()` returns `[]`.
