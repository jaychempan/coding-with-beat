# Multi-Angle Smart Search — Design Spec

**Date:** 2026-05-24  
**Status:** Approved

## Problem

When Claude Code handles a mood/vibe music request, it calls `smart_search()` three times in parallel (one per keyword angle). Each call overwrites the same `search_queue.json` file. The last call to complete "wins," so the cached queue only contains that call's results (≤8 tracks). Claude then displays a merged, globally-renumbered list (1–N across all groups), but `play_number(N)` reads from the single-winner cache — producing the wrong track.

## Solution

Extend `smart_search` in `server.py` to accept an optional `queries: list[str]` parameter. When provided, all queries run in parallel inside a single call, results are merged and deduplicated globally, and a single queue write occurs. The return value uses global numbering that exactly matches the cache.

## Interface

```python
# Existing single-angle call — unchanged behavior
smart_search(description="lofi hip hop late night coding")

# New multi-angle call
smart_search(queries=[
    "lofi hip hop late night coding instrumental",
    "lofi jazz late night rain cozy",
    "synthwave retrowave night drive electronic",
])
```

- `description` and `queries` are mutually exclusive. If both are passed, `queries` takes precedence.
- `queries` accepts 1–5 strings. Each string is searched independently against Apple Music + local.
- `limit` applies per query (default 6 when multi-angle, 8 when single).

## Label Auto-Generation

The server derives a short display label from each query string using a keyword→label mapping table. Matching is case-insensitive, first-match wins:

| Keywords | Label |
|---|---|
| lofi, lo-fi, chillhop | 🎧 Lofi |
| jazz, bossa nova, smooth jazz | 🎷 Jazz |
| synthwave, retrowave, outrun | 🌆 Synthwave |
| ambient, drone, meditation | 🌫️ Ambient |
| classical, piano, nocturne, string | 🎹 Classical |
| hype, workout, energetic, dance, edm | 🔥 Hype |
| sleep, lullaby, white noise | 🌙 Sleep |
| sad, melancholy, heartbreak | 💙 Sad |
| party, celebrat | 🎉 Party |
| chinese, 中国, 古风, 国风 | 🏮 Chinese |
| focus, study, concentration | 🧠 Focus |
| relax, unwind, calm | 🌅 Relax |

Fallback: join the first three words of the query, title-cased (e.g. `"choral gospel choir"` → `Choral Gospel Choir`).

## Output Format

```
🎧 Lofi Hip Hop
1. Late Night Drive — FM STAR · Deep Work Lofi [Apple Music]
2. Gently — Yakubu · Gently - Single [Apple Music]

🎷 Jazz
3. Soul Cozy Window — Lofi Jazz Terrace [Apple Music]
4. Late Night Jazz — Gramatik [Apple Music]

🌆 Synthwave
5. Retrowave — Ambient Essence [Apple Music]
6. Timeless — Relax Vibes [Apple Music]

喜欢哪首？说编号我来播。
```

- Numbers are globally sequential across all groups.
- The queue written to disk maps these same numbers: track at position 1 in the output is index 0 in the queue, track at position 5 is index 4, etc.
- The `💡 [Apple Music]` catalog hint appears once at the end if any catalog track is present.

## Files Changed

| File | Change |
|---|---|
| `coding_with_beat/server.py` | Extend `smart_search`: accept `queries: list[str] \| None`, run parallel searches, merge globally, auto-generate labels, write queue once |
| `coding_with_beat/__main__.py` | Extend `cmd_smart_search`: when multiple quoted args are passed (`cwb smart_search "q1" "q2" "q3"`), treat each as a separate query angle; single arg preserves old behavior |
| `codex_skills/cwb/SKILL.md` | Update scene dispatch table: replace three `smart_search(query)` calls with one `smart_search(queries=[a1, a2, a3])` |
| `CLAUDE.md` | Update multi-angle search instructions to reflect `queries` parameter |
| `tests/test_smart_search.py` | Add tests: multi-query merges globally, labels correct, single queue write, label fallback |

## Backwards Compatibility

- Existing `smart_search(description="...")` calls continue to work unchanged.
- `limit` defaults to 8 in single-query mode, 6 per query in multi-query mode (caps total at ~18, dedup reduces further).
- No change to `play_number`, `_write_queue_file`, or queue file format.

## Testing Plan

1. `test_multi_smart_search_global_numbering` — 3 queries × 2 results each → queue has 6 tracks, output numbers 1–6 sequentially.
2. `test_multi_smart_search_deduplication` — same track returned by two queries → appears once in output.
3. `test_multi_smart_search_label_keyword_match` — `"lofi hip hop"` → label contains `🎧`.
4. `test_multi_smart_search_label_fallback` — unknown query → label is first-three-words title-cased.
5. `test_multi_smart_search_single_queue_write` — `_write_queue_file` called exactly once regardless of query count.
6. `test_smart_search_single_description_unchanged` — existing single-description behavior unaffected.
