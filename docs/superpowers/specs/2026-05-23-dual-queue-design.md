# Dual Queue Design

**Date:** 2026-05-23  
**Status:** Approved

## Problem

`last_results.json` is a single file shared by both `cwb list` (library) and `cwb search` (search results). Each command overwrites the other. There is also no auto-advance mechanism for queue playback — when a track ends naturally, cwb gets stuck and does not play the next item.

## Goals

- Library queue and search queue are completely independent and do not overwrite each other.
- Search queue auto-advances track by track; when exhausted, playback falls back to the library queue.
- External song switches (user clicks in Music.app) do not trigger cwb auto-advance; cwb only resumes control when the user issues a cwb command.
- `play_song` one-off interruptions continue to work as before.

---

## State Model

### New files

| File | Schema | Written by |
|------|--------|------------|
| `library_queue.json` | `{"tracks": [...], "index": 0, "expected_title": ""}` | `cwb list` only |
| `search_queue.json` | `{"tracks": [...], "index": 0, "expected_title": ""}` | `cwb search` only |
| `active_mode.json` | `{"mode": "library\|search", "context": "library\|search"}` | see below |
| `one_off_queue.json` | `{"one_off_title": "", "resume_mode": "library\|search", "resume_index": 0}` | `play_song` |

**`mode`** — which queue is currently playing (drives auto-advance).  
**`context`** — which queue was most recently listed/searched (drives `play_number` indexing).

**Default state** (file absent or first run): `mode = "library"`, `context = "library"`.

### Deprecated files

`last_results.json` and `queue_index.json` are no longer written. Existing files on disk are ignored harmlessly.

---

## Command Behavior

### `cwb list`
- Writes results to `library_queue.json` (`index=0`, `expected_title=""`)
- Sets `active_mode.context = "library"`
- Does not play anything, does not change `mode`

### `cwb search <q>`
- Writes results to `search_queue.json` (`index=0`, `expected_title=""`)
- Sets `active_mode.context = "search"`
- Does not play anything, does not change `mode` (currently playing track is unaffected)

### `cwb play <n>` / `play_number`
- Reads the queue identified by `active_mode.context`
- Plays the track, writes `expected_title` into that queue file
- Sets `active_mode.mode = context` (playback mode follows the context that was just used)

### `cwb next` / `cwb prev` (and `n`/`p` in watch mode)
- Uses `active_mode.mode` to determine which queue to advance within
- If the search queue index goes past the last track → switch `mode` to `"library"` and continue from `library_queue.index`
- If the library queue index goes past the last track → stop (Apple Music decides)

### `play_song <query>` (one-off)
- Behavior unchanged: plays the requested song, writes `one_off_queue.json`
- `one_off_queue.json` now additionally stores `resume_mode` (the current `mode`) so the correct queue is resumed after the one-off ends

### watch mode — right panel
- Displays the queue identified by `active_mode.mode` (the one that is playing)
- Number input plays from that same queue

---

## Auto-Advance Detection

`now_playing_snapshot` is polled every 2 seconds by `cwb watch` and the statusline.

### Trigger condition

```
current_title  ≠  expected_title  (stored in the active queue file)
AND
last_known_position  ≥  last_known_duration − 5s
```

The position threshold distinguishes a natural end from an external switch:

| Scenario | Position at title change | Action |
|----------|--------------------------|--------|
| Track played to end | ≥ duration − 5s | Auto-advance cwb queue |
| User clicked different song in Music.app | < duration − 5s | Sync display only (lyrics, cover), no queue advance |
| User paused | title unchanged | No action |
| User pressed `n`/`p` | next/prev already updated `expected_title` | No false trigger |

### Advance logic (when triggered)

```
mode = "search"
  search_queue has next track  →  play search_queue[index + 1]
  search_queue exhausted       →  set mode = "library", play library_queue[index]

mode = "library"
  library_queue has next track →  play library_queue[index + 1]
  library_queue exhausted      →  stop (Apple Music controls further)
```

### One-off interaction

`_maybe_resume_queue` is checked first (before the general auto-advance). If `one_off_queue.json` exists and the title changed → resume the saved queue. The general auto-advance only runs when no one-off file is present.

---

## Implementation Scope

### `server.py`
- `list_library`: write `library_queue.json` instead of `last_results.json`; set context
- `search`: write `search_queue.json` instead of `last_results.json`; set context
- `play_number`: read from context queue; set mode; write `expected_title`
- `_play_queue_at`: update to accept a queue target (`library` | `search`); write `expected_title`
- `next_track` / `prev_track`: use mode queue; handle search exhaustion → library fallback
- `_maybe_resume_queue`: extend `one_off_queue.json` schema with `resume_mode`; call correct queue on resume
- Add `_load_queue_file(name)` / `_write_queue_file(name, data)` helpers
- Add `_read_active_mode()` / `_write_active_mode(mode, context)` helpers
- Add `_auto_advance_if_needed(np)` — the new detection function, called from `now_playing_snapshot`

### `watch.py`
- `_load_queue()`: read from `active_mode.mode` queue instead of `last_results.json`

### No schema changes to `state.py` or `Track`/`JukeboxState`
