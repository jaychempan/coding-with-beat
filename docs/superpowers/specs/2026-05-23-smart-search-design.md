# smart_search — Design Spec

**Date:** 2026-05-23  
**Status:** Approved

---

## Problem

The existing `search()` and `play_song()` MCP tools pass the raw query string directly to the music backend. This works for exact queries like `"青花瓷 周杰伦"` but fails for natural language like `"来首适合深夜写代码的"` — Apple Music / QQ Music return nothing useful.

Terminal users type precise queries and don't need LLM mediation. AI callers (Claude Code, Codex CLI) receive natural language from the end user and need a smarter path.

---

## Design

### Principle

**The intelligence is the calling LLM itself.** `smart_search` does not make an extra Claude API call inside the server. Instead, its docstring contains a rich query-translation guide that instructs the calling LLM (Claude Code / Codex) to expand natural language into music-specific keywords *before* passing the argument. Zero extra latency, zero extra cost.

### Entry Points

| Caller | Tool to use | Query processing |
|--------|-------------|-----------------|
| Terminal (`cwb search`) | `search()` | None — raw query, unchanged |
| Claude Code / Codex CLI | `smart_search()` | LLM translates intent → keywords |

### New Tool: `smart_search(description, limit=8)`

**File:** `coding_with_beat/server.py`

**Docstring contract (instruction to calling LLM):**

```
Natural-language music search for AI callers (Claude Code / Codex).

IMPORTANT — translate `description` into music keywords BEFORE calling:

Mood / emotion
  "安静"        → "ambient instrumental chill"
  "想兴奋起来"  → "energetic upbeat electronic"
  "放松"        → "relaxing calm downtempo"

Scene / time
  "深夜写代码"  → "lofi hip hop late night study"
  "早晨跑步"    → "running motivation pop upbeat"
  "专注模式"    → "focus deep work instrumental"

Style reference
  "像 Daft Punk 那种"  → "electronic synth funk dance"
  "带点爵士"           → "jazz fusion smooth"
  "复古感"             → "vintage retro soul funk"

No lyrics
  Append "instrumental" to any of the above.

After translating, pass the expanded keyword string as `description`.
```

**Internal implementation:**

1. Call Apple Music library search (local AppleScript, same as `search()`)
2. Call Apple Music catalog search (iTunes Search API)
3. Call local files search
4. Merge, deduplicate, annotate each result with source tag
5. Return numbered list

**Result format:**

```
1. 雨的印记 — 李闰珉            [资料库]
2. Quiet Library — FM STAR      [Apple Music]
3. lofi study beats.mp3         [本地]
```

Use `play_number(n)` to play a result.

### CLAUDE.md Addition

One line added to the project `CLAUDE.md`:

```
When the user asks for music by mood, scene, or style description,
use smart_search() instead of search().
```

---

## What Is Not Changing

- `search(query)` — untouched, used by terminal
- `play_song(query)` — untouched
- `play_number(n)` — untouched
- All music backends (Apple Music, QQ Music, Local) — untouched
- No new API keys, no new dependencies

---

## Files to Touch

| File | Change |
|------|--------|
| `coding_with_beat/server.py` | Add `smart_search()` tool (~40 lines) |
| `CLAUDE.md` | Add one routing line |

---

## Success Criteria

- `smart_search("来首深夜写代码的")` called from Claude Code returns results annotated with source
- Terminal `cwb search "青花瓷"` behaviour is unchanged
- Results from library are marked `[资料库]`, catalog `[Apple Music]`, local `[本地]`
