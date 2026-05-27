# Music Profile Skill — Design Spec

**Date:** 2026-05-27
**Status:** Approved
**Scope:** v1 — Skill + new MCP tool + profile.py module

---

## 1. Overview

Build a `music-profile` feature that generates periodic listening reports, extracts a user music profile, and produces personalized recommendation queries — all based on existing play history and newly captured search history.

**Not in scope for v1:**
- ML models or external APIs
- Persistent profile cache (future v2)
- Skip / dislike capture
- Replacing existing playback logic

---

## 2. Architecture

```
Data Layer
├── history.py          read/write play log + new write_search() / read_search()
│   ├── ~/.coding-with-beat/history.log          (existing)
│   └── ~/.coding-with-beat/search_history.log   (new)
└── sources/apple_music.py  play_history()        (existing)

Analysis Layer (new)
└── coding_with_beat/profile.py
    ├── build_profile(period, source)
    ├── build_report(profile)
    └── build_recommendation_queries(profile, context)

Interface Layer
├── coding_with_beat/server.py   → generate_profile() MCP tool (new)
├── coding_with_beat/cli.py      → cwb profile [period] command (new)
└── skills/cwb-profile/SKILL.md  → trigger words + AI dispatch (new)
```

**Data flow:**
```
User: "生成本周报告" or `cwb profile weekly`
  → generate_profile(period="weekly", context="")
      → merge Apple Music play_history + history.log + search_history.log
      → build_profile()  → UserProfile dict
      → build_report()   → plain-text report string
      → build_recommendation_queries()  → list[str]
  → return formatted text
  → AI optionally calls smart_search(queries=[...]) to play recommendations
```

**Search history capture:** `smart_search()` in `server.py` appends each query string to `search_history.log` as a non-blocking side effect.

---

## 3. Data Layer

### `search_history.log` format

One record per line, pipe-delimited (consistent with `history.log`):
```
2026-05-27 02:14:33 | lofi jazz coding instrumental focus | smart_search
2026-05-27 02:31:07 | synthwave night drive neon retrowave | smart_search
```
Fields: `ts | query | source` — `source` is always `smart_search` in v1, reserved for future expansion.

### `history.py` additions

```python
def write_search(query: str) -> None:
    """Append one search record to search_history.log."""

def read_search(limit: int = 500) -> list[dict]:
    """Read most-recent N search records.
    Returns: [{"query": str, "ts": datetime}]
    """
```

### `UserProfile` dict structure

```python
{
  "period":           str,           # daily | weekly | monthly | yearly
  "generated_at":     datetime,
  "play_count":       int,           # total plays in period
  "top_artists":      list[tuple],   # [(name, count), ...] sorted descending
  "top_genres":       list[tuple],   # [(genre, count), ...] matched via _STYLE_KEYWORDS
  "top_search_terms": list[tuple],   # [(term, count), ...] high-freq tokens from search log
  "language_pref":    dict,          # {"zh": float, "en": float, "instrumental": float}
  "loved_artists":    list[str],     # artists from loved tracks
  "recent_trend":     list[str],     # genres rising in the second half of the period
  "stable_pref":      list[str],     # genres consistently present throughout
  "declining_pref":   list[str],     # genres falling in the second half of the period
  "time_pattern":     dict,          # {"morning": [...], "afternoon": [...], "evening": [...], "night": [...]}
}
```

`time_pattern` time bands:
- `morning`: 06:00–12:00
- `afternoon`: 12:00–18:00
- `evening`: 18:00–24:00
- `night`: 00:00–06:00

Language detection: CJK character ratio in title+artist → `zh`; ASCII-only → `en`; instrumental keywords (`instrumental`, `无人声`, `pure music`, etc.) → `instrumental`.

---

## 4. `profile.py` Module

### `build_profile(period: str, source=None) -> dict`

1. Fetch Apple Music `play_history(window_days=period_days)` + `history.read()`, filter by period, merge and deduplicate by `(title|artist).lower()`
2. Count `top_artists` (by `played_count` for AM, by frequency for local)
3. Match `top_genres` using existing `_STYLE_KEYWORDS` from `history.py`
4. Read `search_history.log`, tokenize queries, count `top_search_terms`
5. Compute `language_pref` from title+artist strings
6. Read `list_loved()` → extract `loved_artists`
7. Split period into first-half / second-half, compare genre distributions → `recent_trend`, `stable_pref`, `declining_pref`
8. Group records by hour band → `time_pattern`

Returns `UserProfile` dict. Raises `ValueError("insufficient_history")` if fewer than 5 records found.

### `build_report(profile: dict) -> str`

Generates a plain-text report using template strings (no AI dependency):

```
📅 {period_label}（{start} ~ {end}）

▸ 共播放 {play_count} 次，常听歌手：{top_artists}
▸ 主要曲风：{top_genres}
▸ 语言偏好：{language_pref}

📈 偏好变化
  新增：{recent_trend}
  稳定：{stable_pref}
  下降：{declining_pref}

🕐 时间规律
  {time_pattern per band, only non-empty bands shown}

💬 总结
{template-assembled natural language summary sentence}
```

Summary sentence assembled from profile fields (e.g. "这周你的音乐偏好明显偏向 {top2 genres}，{declining_pref} 播放次数下降。"). AI may rephrase in conversation.

### `build_recommendation_queries(profile: dict, context: str = "") -> list[str]`

Returns 2–3 `smart_search` query strings. Logic:

| Slot | Strategy | Example |
|------|----------|---------|
| 1 | Stable pref + context | `"lofi jazz {context} instrumental focus"` |
| 2 | Recent trend (exploration) | `"{recent_trend[0]} night coding focus electronic"` |
| 3 | Top artist extension | `"{top_artist} similar instrumental lo-fi"` |

If `context` is empty, slot 1 uses top genre only. If `recent_trend` is empty, slot 2 falls back to second `top_genre`.

---

## 5. MCP Tool

```python
@mcp.tool()
def generate_profile(
    period: str = "weekly",   # daily | weekly | monthly | yearly
    context: str = "",        # current scene/mood hint for recommendation tuning
) -> str:
```

**Returns:** Formatted text combining `build_report()` output + recommendation queries section.

**Error handling:**
- `< 5` records → returns friendly message in Chinese prompting user to listen more first
- Invalid `period` value → defaults to `weekly`

AI workflow after receiving the response:
1. Display report to user
2. Show recommendation queries
3. Ask user if they want to play recommendations
4. If yes → call `smart_search(queries=[...])` with the returned queries

---

## 6. CLI Command

```bash
cwb profile              # defaults to weekly
cwb profile daily
cwb profile weekly
cwb profile monthly
cwb profile yearly
```

Calls `profile.build_profile()` + `build_report()` + `build_recommendation_queries()` directly (no MCP server dependency — works offline). Prints report then recommendation queries.

---

## 7. Skill File

**Path:** `skills/cwb-profile/SKILL.md`

**Trigger words:**
- 听歌报告 · 音乐画像 · 本周报告 · 本月报告 · 年度报告 · 日报告
- music profile · listening report · music report · my music taste
- 分析我的听歌 · 我最近在听什么 · 推荐基于历史
- history profile · what have I been listening to

**AI dispatch logic (in SKILL.md):**
1. Detect `period` from user message (日→daily, 周→weekly, 月→monthly, 年→yearly; default weekly)
2. Extract `context` from user message (scene/mood words, may be empty)
3. Call `generate_profile(period, context)`
4. Display the returned report
5. Present recommendation queries, ask user if they want to play
6. If yes → call `smart_search(queries=[recommendation queries from report])`

---

## 8. File Checklist

| File | Change |
|------|--------|
| `coding_with_beat/history.py` | Add `write_search()`, `read_search()` |
| `coding_with_beat/server.py` | Capture search queries in `smart_search()`; add `generate_profile()` MCP tool |
| `coding_with_beat/profile.py` | New file — `build_profile()`, `build_report()`, `build_recommendation_queries()` |
| `coding_with_beat/cli.py` | Add `cwb profile [period]` subcommand |
| `skills/cwb-profile/SKILL.md` | New skill file |
| `tests/test_profile.py` | New test file — unit tests for all three profile functions |

---

## 9. Acceptance Criteria

- [ ] `generate_profile()` returns a structured report from play history
- [ ] Report includes top artists, genres, language pref, time pattern, preference changes
- [ ] Recommendation queries reflect long-term stable pref + recent trend
- [ ] `cwb profile weekly` works offline (no MCP server)
- [ ] `< 5` records returns a graceful error message
- [ ] Search queries are captured to `search_history.log` on every `smart_search()` call
- [ ] `daily` / `weekly` / `monthly` / `yearly` all produce period-correct data windows
- [ ] Unit tests cover `build_profile()`, `build_report()`, `build_recommendation_queries()`
