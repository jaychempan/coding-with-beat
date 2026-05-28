# HTML 听歌报告 v2 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `build_html_report()` 升级为数据仪表盘，新增 8 个模块（每日播放图、时段热力、词云、收藏墙、人格雷达等），配套扩展 `build_profile()` 的返回字段。

**Architecture:** Task 1 扩展 profile 数据层（新增 7 个字段 + `_personality_scores()` helper）；Task 2 全面重写 `build_html_report()`（新增 4 个 HTML helper、新 CSS/JS、完整仪表盘布局）。两个 task 均采用 TDD，先写失败测试再实现。

**Tech Stack:** Python 3.10+, inline SVG, `math` stdlib（雷达图顶点），`Counter`，零外部依赖。

---

## File Map

| 文件 | 变更 |
|------|------|
| `coding_with_beat/profile.py` | `_genre_counter` 调用改为存 Counter；新增 `_personality_scores()`；`build_profile()` 追加 7 个新字段；`build_html_report()` 全面重写 |
| `tests/test_profile.py` | `_make_profile()` 追加新字段默认值；新增 7 个 `test_build_profile_*` 测试；新增 6 个 `test_build_html_report_*` 测试 |

---

## Task 1: Profile 数据层 — 7 个新字段 + `_personality_scores()`

**Files:**
- Modify: `coding_with_beat/profile.py`
- Test: `tests/test_profile.py`

- [ ] **Step 1: 写失败测试**

在 `tests/test_profile.py` 的 `test_build_profile_returns_required_keys` 之后追加：

```python
def test_build_profile_new_fields_present(monkeypatch):
    monkeypatch.setattr(history, "read", lambda limit=500: _weekly_tracks())
    monkeypatch.setattr(history, "read_search", lambda limit=500: [])
    with mock.patch("coding_with_beat.profile.get_source", side_effect=Exception("no AM")):
        prof = profile.build_profile("weekly")
    new_fields = {
        "unique_artist_count", "estimated_hours", "peak_band",
        "band_track_counts", "daily_plays", "personality_scores", "trend_detail",
    }
    assert new_fields.issubset(prof.keys())


def test_build_profile_unique_artist_count(monkeypatch):
    monkeypatch.setattr(history, "read", lambda limit=500: _weekly_tracks())
    monkeypatch.setattr(history, "read_search", lambda limit=500: [])
    with mock.patch("coding_with_beat.profile.get_source", side_effect=Exception("no AM")):
        prof = profile.build_profile("weekly")
    # _weekly_tracks() has 5 distinct artists
    assert prof["unique_artist_count"] == 5


def test_build_profile_estimated_hours(monkeypatch):
    monkeypatch.setattr(history, "read", lambda limit=500: _weekly_tracks())
    monkeypatch.setattr(history, "read_search", lambda limit=500: [])
    with mock.patch("coding_with_beat.profile.get_source", side_effect=Exception("no AM")):
        prof = profile.build_profile("weekly")
    # 10 tracks * 3.5 / 60 = 0.583 → rounds to 0.6
    assert prof["estimated_hours"] == pytest.approx(0.6, abs=0.1)


def test_build_profile_peak_band(monkeypatch):
    monkeypatch.setattr(history, "read", lambda limit=500: _weekly_tracks())
    monkeypatch.setattr(history, "read_search", lambda limit=500: [])
    with mock.patch("coding_with_beat.profile.get_source", side_effect=Exception("no AM")):
        prof = profile.build_profile("weekly")
    assert prof["peak_band"] in {"morning", "afternoon", "evening", "night"}


def test_build_profile_daily_plays_weekly_keys(monkeypatch):
    monkeypatch.setattr(history, "read", lambda limit=500: _weekly_tracks())
    monkeypatch.setattr(history, "read_search", lambda limit=500: [])
    with mock.patch("coding_with_beat.profile.get_source", side_effect=Exception("no AM")):
        prof = profile.build_profile("weekly")
    # weekly → YYYY-MM-DD keys, sorted, totals equal play_count
    assert all(len(k) == 10 for k in prof["daily_plays"])
    assert sum(prof["daily_plays"].values()) == prof["play_count"]


def test_build_profile_daily_plays_daily_period(monkeypatch):
    monkeypatch.setattr(history, "read", lambda limit=500: _weekly_tracks())
    monkeypatch.setattr(history, "read_search", lambda limit=500: [])
    with mock.patch("coding_with_beat.profile.get_source", side_effect=Exception("no AM")):
        prof = profile.build_profile("daily")
    # daily → "HH" keys (2 chars)
    assert all(len(k) == 2 for k in prof["daily_plays"])


def test_build_profile_personality_scores_in_range(monkeypatch):
    monkeypatch.setattr(history, "read", lambda limit=500: _weekly_tracks())
    monkeypatch.setattr(history, "read_search", lambda limit=500: [])
    with mock.patch("coding_with_beat.profile.get_source", side_effect=Exception("no AM")):
        prof = profile.build_profile("weekly")
    scores = prof["personality_scores"]
    for key in ("focus", "explore", "mood", "night_owl", "loyalty"):
        assert key in scores
        assert 0 <= scores[key] <= 100
```

- [ ] **Step 2: 运行，确认失败**

```
pytest tests/test_profile.py -k "test_build_profile_new_fields" -v
```
期望：FAIL — `KeyError` 或 `AssertionError`

- [ ] **Step 3: 在 `profile.py` 中添加 `_personality_scores()` helper**

在 `build_profile()` 函数定义**之前**插入（放在 `_music_personality` 之前）：

```python
def _personality_scores(
    language_pref: dict,
    genre_counter: Counter,
    unique_artist_count: int,
    play_count: int,
    night_plays: int,
    top_artists: list,
) -> dict[str, int]:
    def _clamp(v: float) -> int:
        return int(min(100, max(0, v)))

    instrumental = language_pref.get("instrumental", 0.0)
    genre_total = sum(genre_counter.values()) or 1
    top2_genre_plays = sum(v for _, v in genre_counter.most_common(2))
    genre_conc = top2_genre_plays / genre_total

    top3_plays = sum(c for _, c in top_artists[:3])

    return {
        "focus":     _clamp(instrumental * 60 + genre_conc * 40),
        "explore":   _clamp(unique_artist_count / max(play_count, 1) * 500),
        "mood":      _clamp(len(genre_counter) / 5 * 100),
        "night_owl": _clamp(night_plays / max(play_count, 1) * 100),
        "loyalty":   _clamp(top3_plays / max(play_count, 1) * 100),
    }
```

- [ ] **Step 4: 在 `build_profile()` 中缓存 genre counter，并计算新字段**

找到现有这一行：
```python
top_genres = _genre_counter(period_tracks).most_common(5)
```
改为：
```python
genre_counter_all = _genre_counter(period_tracks)
top_genres = genre_counter_all.most_common(5)
```

然后在 `tracks_by_genre` 计算完毕、`return` 语句之前，插入：

```python
    # ── New computed fields ────────────────────────────────────────────────────
    unique_artist_count = len(artist_counter)
    estimated_hours = round(len(period_tracks) * 3.5 / 60, 1)

    band_track_counts: Counter = Counter()
    for _t in period_tracks:
        band_track_counts[_time_band(_t["ts"].hour)] += 1

    peak_band = band_track_counts.most_common(1)[0][0] if band_track_counts else "night"
    night_plays = band_track_counts.get("night", 0)

    personality_scores = _personality_scores(
        language_pref, genre_counter_all, unique_artist_count,
        len(period_tracks), night_plays, top_artists,
    )

    if period == "daily":
        _dp: Counter = Counter()
        for _t in period_tracks:
            _dp[_t["ts"].strftime("%H")] += 1
    elif period == "yearly":
        _dp = Counter()
        for _t in period_tracks:
            _dp[_t["ts"].strftime("%Y-%m")] += 1
    else:  # weekly / monthly
        _dp = Counter()
        for _t in period_tracks:
            _dp[_t["ts"].strftime("%Y-%m-%d")] += 1
    daily_plays = dict(sorted(_dp.items()))

    trend_detail: dict[str, tuple[int, int]] = {
        g: (first_genres.get(g, 0), second_genres.get(g, 0))
        for g in all_genre_keys
    }
```

- [ ] **Step 5: 在 `return` 字典中追加新字段**

在现有 `return { ... }` 的 `"tracks_by_genre": tracks_by_genre,` 行之后追加：

```python
        "unique_artist_count": unique_artist_count,
        "estimated_hours": estimated_hours,
        "peak_band": peak_band,
        "band_track_counts": dict(band_track_counts),
        "daily_plays": daily_plays,
        "personality_scores": personality_scores,
        "trend_detail": trend_detail,
```

- [ ] **Step 6: 运行全部 profile 测试，确认通过**

```
pytest tests/test_profile.py -k "test_build_profile" -v
```
期望：所有 `test_build_profile_*` 通过

- [ ] **Step 7: 提交**

```bash
git add coding_with_beat/profile.py tests/test_profile.py
git commit -m "feat(profile): add 7 new computed fields and _personality_scores helper"
```

---

## Task 2: `build_html_report()` 全面重写 — 仪表盘布局

**Files:**
- Modify: `coding_with_beat/profile.py` (仅 `build_html_report` 函数)
- Test: `tests/test_profile.py`

- [ ] **Step 1: 更新 `_make_profile()` 加入新字段默认值**

在 `tests/test_profile.py` 的 `_make_profile()` 函数中，`base` 字典里追加：

```python
        "tracks_by_artist": {"Hans Zimmer": [{"t": "Interstellar", "c": 5}]},
        "tracks_by_genre":  {"lofi": [{"t": "Track 1", "a": "Hans Zimmer"}]},
        "unique_artist_count": 5,
        "estimated_hours": 2.5,
        "peak_band": "night",
        "band_track_counts": {"morning": 3, "afternoon": 8, "evening": 10, "night": 21},
        "daily_plays": {"2026-05-20": 10, "2026-05-21": 15, "2026-05-22": 8,
                        "2026-05-23": 5, "2026-05-24": 12, "2026-05-25": 4, "2026-05-26": 6},
        "personality_scores": {"focus": 70, "explore": 45, "mood": 60, "night_owl": 83, "loyalty": 55},
        "trend_detail": {"synthwave": (0, 4), "lofi": (5, 7), "ambient": (6, 4), "华语": (3, 0)},
```

- [ ] **Step 2: 写新 HTML 测试（先在现有测试区块末尾追加）**

在 `tests/test_profile.py` 最后追加（现有 html 测试已有，这些是新增的）：

```python
def test_build_html_report_contains_daily_chart():
    html_out = profile.build_html_report(_make_profile())
    assert 'id="daily-chart"' in html_out


def test_build_html_report_contains_radar_card():
    html_out = profile.build_html_report(_make_profile())
    assert 'id="radar-card"' in html_out


def test_build_html_report_contains_medals():
    html_out = profile.build_html_report(_make_profile())
    assert "🥇" in html_out


def test_build_html_report_contains_estimated_hours():
    html_out = profile.build_html_report(_make_profile())
    assert "2.5" in html_out


def test_build_html_report_contains_loved_artist():
    html_out = profile.build_html_report(_make_profile())
    # loved_artists has "Hans Zimmer"
    assert "Hans Zimmer" in html_out


def test_build_html_report_contains_search_term():
    html_out = profile.build_html_report(_make_profile())
    # top_search_terms has "lofi"
    assert "lofi" in html_out
```

- [ ] **Step 3: 运行新测试，确认失败**

```
pytest tests/test_profile.py -k "daily_chart or radar_card or medals or estimated_hours" -v
```
期望：FAIL — `AssertionError`（旧 HTML 里没有这些标记）

- [ ] **Step 4: 替换 `build_html_report()` 全函数**

将 `profile.py` 中从 `def build_html_report(profile: dict) -> str:` 到函数结束（即 `return f"""..."""` 末尾）的全部内容，替换为以下实现：

```python
def build_html_report(profile: dict) -> str:
    """Generate a self-contained dark-theme HTML dashboard listening report."""
    period            = profile.get("period", "weekly")
    generated_at      = profile.get("generated_at", datetime.datetime.now())
    days              = _PERIOD_DAYS.get(period, 7)
    start             = (generated_at - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    end               = generated_at.strftime("%Y-%m-%d")
    label             = _PERIOD_LABELS.get(period, "听歌报告")
    play_count        = profile.get("play_count", 0)
    top_artists       = profile.get("top_artists", [])
    top_genres        = profile.get("top_genres", [])
    language_pref     = profile.get("language_pref", {})
    recent_trend      = profile.get("recent_trend", [])
    stable_pref       = profile.get("stable_pref", [])
    declining_pref    = profile.get("declining_pref", [])
    time_pattern      = profile.get("time_pattern", {})
    top_search_terms  = profile.get("top_search_terms", [])
    loved_artists     = profile.get("loved_artists", [])
    tracks_by_artist  = profile.get("tracks_by_artist", {})
    tracks_by_genre   = profile.get("tracks_by_genre", {})
    unique_artist_count = profile.get("unique_artist_count", 0)
    estimated_hours   = profile.get("estimated_hours", 0.0)
    peak_band         = profile.get("peak_band", "night")
    band_track_counts = profile.get("band_track_counts", {})
    daily_plays       = profile.get("daily_plays", {})
    personality_scores = profile.get("personality_scores", {})
    trend_detail      = profile.get("trend_detail", {})
    queries           = build_recommendation_queries(profile)
    p_emoji, p_title, p_desc = _music_personality(profile)

    _PEAK_LABELS = {
        "morning": "🌅 早晨", "afternoon": "☀️ 下午",
        "evening": "🌆 傍晚", "night": "🌙 深夜",
    }
    peak_label = _PEAK_LABELS.get(peak_band, "🌙 深夜")

    # ── Summary sentence ──────────────────────────────────────────────────────
    summary_parts: list[str] = []
    if top_genres:
        top2 = " 和 ".join(html.escape(g) for g, _ in top_genres[:2])
        summary_parts.append(f"这{_PERIOD_ZH.get(period, '周')}你的音乐偏好明显偏向 {top2}")
    if declining_pref:
        summary_parts.append(f"{'、'.join(html.escape(x) for x in declining_pref[:2])} 播放次数有所下降")
    if recent_trend:
        summary_parts.append(f"{'、'.join(html.escape(x) for x in recent_trend[:2])} 开始走高")
    summary = "，".join(summary_parts) + "。" if summary_parts else (
        f"本{_PERIOD_ZH.get(period, '周')}共播放 {play_count} 首，继续保持！"
    )

    # ── JSON for modal drill-down ─────────────────────────────────────────────
    _raw = json.dumps(
        {"artists": tracks_by_artist, "genres": tracks_by_genre},
        ensure_ascii=False,
    ).replace("</script>", "<\\/script>").replace("<!--", "<\\!--")
    track_data_json = _raw

    # ── Helper: bar chart with medals ─────────────────────────────────────────
    def _bar_html(items: list, data_type: str, max_items: int = 5) -> str:
        items = items[:max_items]
        if not items:
            return '<p style="color:#68687a;font-size:12px;margin:0">暂无数据</p>'
        medals = ["🥇", "🥈", "🥉"]
        max_val = max(c for _, c in items) or 1
        rows = []
        for idx, (name, count) in enumerate(items):
            pct = max(4, int((count / max_val) * 100))
            nm = html.escape((name[:9] + "…") if len(name) > 9 else name)
            key = html.escape(name, quote=True)
            prefix = medals[idx] + " " if idx < 3 else "  "
            rows.append(
                f'<div class="bar-item" data-type="{data_type}" data-key="{key}"'
                f' onclick="handleBarClick(this)">'
                f'<div class="bar-label">{prefix}{nm}</div>'
                f'<div class="bar-track">'
                f'<div class="bar-bg"><div class="bar-fill" style="width:{pct}%"></div></div>'
                f'<span class="bar-count">{count}</span>'
                f'</div></div>'
            )
        return "".join(rows)

    # ── Helper: donut SVG (language) ──────────────────────────────────────────
    def _donut_svg(lang_pref: dict) -> str:
        COLORS = {"zh": "#8b5cf6", "en": "#a78bfa", "instrumental": "#6d7fd4"}
        LABELS = {"zh": "中文", "en": "英文", "instrumental": "纯音乐"}
        items = [(k, v) for k, v in lang_pref.items() if v > 0]
        if not items:
            return '<p style="color:#68687a;font-size:12px;margin:0">暂无数据</p>'
        total = sum(v for _, v in items)
        cx, cy, R, r = 80, 64, 52, 26
        angle = -math.pi / 2
        paths = []
        for lang, val in items:
            sweep = (val / total) * 2 * math.pi
            x1, y1 = cx + R * math.cos(angle), cy + R * math.sin(angle)
            x2, y2 = cx + R * math.cos(angle + sweep), cy + R * math.sin(angle + sweep)
            ix1, iy1 = cx + r * math.cos(angle), cy + r * math.sin(angle)
            ix2, iy2 = cx + r * math.cos(angle + sweep), cy + r * math.sin(angle + sweep)
            lg = 1 if sweep > math.pi else 0
            c = COLORS.get(lang, "#6b7280")
            paths.append(
                f'<path d="M {x1:.1f} {y1:.1f} A {R} {R} 0 {lg} 1 {x2:.1f} {y2:.1f}'
                f' L {ix2:.1f} {iy2:.1f} A {r} {r} 0 {lg} 0 {ix1:.1f} {iy1:.1f} Z"'
                f' fill="{c}"/>'
            )
            angle += sweep
        dom_lang, dom_val = max(items, key=lambda x: x[1])
        dom_pct = int(dom_val * 100)
        legend_top = cy + R + 28
        legend = []
        for i, (lang, val) in enumerate(items):
            ly = legend_top + i * 20
            c = COLORS.get(lang, "#6b7280")
            legend.append(
                f'<g transform="translate({cx},{ly})">'
                f'<rect x="-33" y="0" width="10" height="10" rx="2" fill="{c}"/>'
                f'<text x="-19" y="9" fill="#cec8bc" font-size="11">'
                f'{LABELS.get(lang, lang)} {int(val * 100)}%</text>'
                f'</g>'
            )
        total_h = legend_top + len(items) * 20 + 4
        return (
            f'<svg width="160" height="{total_h}"'
            f' style="overflow:visible;font-family:monospace">'
            f'{"".join(paths)}'
            f'<text x="{cx}" y="{cy - 5}" text-anchor="middle" fill="#a78bfa"'
            f' font-size="15" font-weight="bold">{dom_pct}%</text>'
            f'<text x="{cx}" y="{cy + 12}" text-anchor="middle" fill="#cec8bc"'
            f' font-size="11">{LABELS.get(dom_lang, dom_lang)}</text>'
            f'{"".join(legend)}</svg>'
        )

    # ── Helper: daily plays bar chart ─────────────────────────────────────────
    def _daily_chart_html(plays: dict, p: str) -> str:
        if not plays:
            return '<p style="color:#68687a;font-size:12px;margin:0">暂无数据</p>'
        _DAY_CN = {
            "Mon": "周一", "Tue": "周二", "Wed": "周三", "Thu": "周四",
            "Fri": "周五", "Sat": "周六", "Sun": "周日",
        }
        items = sorted(plays.items())
        max_val = max(v for _, v in items) or 1

        def _label(k: str) -> str:
            if p == "daily":
                return f"{k}:00"
            if p == "yearly":
                return k[5:]  # "MM"
            try:
                d = datetime.datetime.strptime(k, "%Y-%m-%d")
                return _DAY_CN.get(d.strftime("%a"), d.strftime("%m/%d"))
            except ValueError:
                return k

        bars = []
        for k, v in items:
            bar_h = max(4, int(v / max_val * 60))
            lbl = html.escape(_label(k)[:4])
            bars.append(
                f'<div style="display:flex;flex-direction:column;align-items:center;flex:1;gap:2px">'
                f'<div style="width:100%;height:60px;display:flex;align-items:flex-end">'
                f'<div style="width:100%;height:{bar_h}px;background:#8b5cf6;opacity:.8;'
                f'border-radius:2px 2px 0 0" title="{lbl}: {v}首"></div>'
                f'</div>'
                f'<span style="font-size:9px;color:#68687a;white-space:nowrap;'
                f'overflow:hidden;text-overflow:ellipsis;max-width:28px">{lbl}</span>'
                f'</div>'
            )
        return f'<div style="display:flex;gap:2px;align-items:flex-end">{"".join(bars)}</div>'

    # ── Helper: search term word cloud ────────────────────────────────────────
    def _word_cloud_html(terms: list) -> str:
        if not terms:
            return '<p style="color:#68687a;font-size:12px;margin:0">暂无搜索记录</p>'
        terms = terms[:8]
        max_count = max(c for _, c in terms) or 1
        tags = []
        for term, count in terms:
            ratio = count / max_count
            size = int(11 + ratio * 7)
            opacity = round(0.3 + ratio * 0.7, 2)
            tags.append(
                f'<span style="font-size:{size}px;color:rgba(139,92,246,{opacity});'
                f'font-family:monospace;margin:2px 4px;display:inline-block">'
                f'{html.escape(term)}</span>'
            )
        return f'<div style="line-height:2">{"".join(tags)}</div>'

    # ── Helper: time band heatmap ─────────────────────────────────────────────
    def _time_heatmap_html(tp: dict, btc: dict) -> str:
        bands = [
            ("morning",   "🌅", "早晨"),
            ("afternoon", "☀️", "下午"),
            ("evening",   "🌆", "傍晚"),
            ("night",     "🌙", "深夜"),
        ]
        max_count = max(btc.values()) if btc else 1
        cols = []
        for band, emoji, short in bands:
            count = btc.get(band, 0)
            opacity = round(max(0.12, count / max(max_count, 1)), 2)
            genres = tp.get(band, [])
            genre_tags = "".join(
                f'<span class="gpill" data-type="genre"'
                f' data-key="{html.escape(g, quote=True)}"'
                f' onclick="handlePillClick(this)">{html.escape(g)}</span>'
                for g in genres[:2]
            )
            cols.append(
                f'<div style="display:flex;flex-direction:column;align-items:center;gap:6px;flex:1">'
                f'<div style="width:100%;height:44px;background:rgba(139,92,246,{opacity});'
                f'border-radius:8px;display:flex;align-items:center;'
                f'justify-content:center;font-size:18px">{emoji}</div>'
                f'<span style="font-size:10px;color:#68687a">{short}</span>'
                f'<div style="display:flex;flex-wrap:wrap;gap:2px;justify-content:center">'
                f'{genre_tags}</div>'
                f'</div>'
            )
        return f'<div style="display:flex;gap:8px">{"".join(cols)}</div>'

    # ── Helper: loved artists wall ────────────────────────────────────────────
    def _loved_html(loved: list, artists: list) -> str:
        if not loved:
            return '<p style="color:#68687a;font-size:12px;margin:0">暂无收藏</p>'
        artist_map = {a: c for a, c in artists}
        rows = []
        for artist in loved[:5]:
            count = artist_map.get(artist, 0)
            color = "#a78bfa" if count > 0 else "#68687a"
            rows.append(
                f'<div style="display:flex;justify-content:space-between;'
                f'align-items:center;padding:5px 0;'
                f'border-bottom:1px solid rgba(139,92,246,.1)">'
                f'<span style="font-size:12px;color:{color};font-family:monospace">'
                f'{html.escape(artist)}</span>'
                f'<span style="font-size:11px;color:#68687a">{count} 次</span>'
                f'</div>'
            )
        return "".join(rows)

    # ── Helper: trend pills with % change ────────────────────────────────────
    def _trend_pill(genre: str, direction: str) -> str:
        first, second = trend_detail.get(genre, (0, 0))
        if direction == "new":
            badge = '<span style="background:#16a34a;color:#fff;font-size:9px;padding:1px 5px;border-radius:4px;margin-left:4px">NEW</span>'
            color = "#16a34a"
        elif direction == "gone":
            badge = '<span style="background:#b91c1c;color:#fff;font-size:9px;padding:1px 5px;border-radius:4px;margin-left:4px">-100%</span>'
            color = "#b91c1c"
        else:
            if first > 0:
                pct = int(abs(second - first) / first * 100)
                sign = "+" if second >= first else "-"
                clr = "#16a34a" if second >= first else "#b91c1c"
                badge = (
                    f'<span style="background:{clr};color:#fff;font-size:9px;'
                    f'padding:1px 5px;border-radius:4px;margin-left:4px">'
                    f'{sign}{pct}%</span>'
                )
            else:
                badge = ""
            color = "#a78bfa"
        return (
            f'<div style="display:flex;align-items:center;margin-bottom:4px">'
            f'<span style="font-size:12px;color:{color};font-family:monospace">'
            f'{html.escape(genre)}</span>{badge}'
            f'</div>'
        )

    def _trends_col(title: str, items: list, direction: str, header_color: str) -> str:
        if not items:
            return (
                f'<div>'
                f'<div style="font-size:10px;color:{header_color};'
                f'letter-spacing:.08em;margin-bottom:8px">{title}</div>'
                f'<span style="font-size:11px;color:#68687a">—</span>'
                f'</div>'
            )
        pills = "".join(_trend_pill(g, direction) for g in items[:3])
        return (
            f'<div>'
            f'<div style="font-size:10px;color:{header_color};'
            f'letter-spacing:.08em;margin-bottom:8px">{title}</div>'
            f'{pills}'
            f'</div>'
        )

    trends_section = (
        f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">'
        f'{_trends_col("↑ 新增", recent_trend,  "new",  "#16a34a")}'
        f'{_trends_col("→ 稳定", stable_pref,   "stable","#a78bfa")}'
        f'{_trends_col("↓ 下降", declining_pref,"gone",  "#b91c1c")}'
        f'</div>'
    )

    # ── Helper: pentagon radar SVG ────────────────────────────────────────────
    def _radar_svg(scores: dict) -> str:
        dims = [
            ("focus",     "专注力"),
            ("explore",   "探索欲"),
            ("mood",      "情绪"),
            ("night_owl", "夜猫"),
            ("loyalty",   "忠诚"),
        ]
        N = len(dims)
        cx, cy, R = 85, 80, 60
        label_R = R + 22

        def pt(i: int, ratio: float) -> tuple[float, float]:
            angle = -math.pi / 2 + i * 2 * math.pi / N
            return cx + ratio * R * math.cos(angle), cy + ratio * R * math.sin(angle)

        def lpt(i: int) -> tuple[float, float]:
            angle = -math.pi / 2 + i * 2 * math.pi / N
            return cx + label_R * math.cos(angle), cy + label_R * math.sin(angle)

        # Grid rings at 33%, 67%, 100%
        grid_paths = []
        for level in (0.33, 0.67, 1.0):
            pts_str = " ".join(f"{pt(i, level)[0]:.1f},{pt(i, level)[1]:.1f}" for i in range(N))
            op = "0.12" if level < 1.0 else "0.25"
            grid_paths.append(
                f'<polygon points="{pts_str}" fill="none" stroke="#8b5cf6"'
                f' stroke-width="1" opacity="{op}"/>'
            )

        # Spokes
        spokes = []
        for i in range(N):
            x, y = pt(i, 1.0)
            spokes.append(
                f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}"'
                f' stroke="#8b5cf6" stroke-width="1" opacity="0.15"/>'
            )

        # Data polygon
        data_pts = " ".join(
            f"{pt(i, scores.get(k, 0) / 100)[0]:.1f},"
            f"{pt(i, scores.get(k, 0) / 100)[1]:.1f}"
            for i, (k, _) in enumerate(dims)
        )
        data_poly = (
            f'<polygon points="{data_pts}"'
            f' fill="rgba(139,92,246,0.3)" stroke="#8b5cf6" stroke-width="2"/>'
        )

        # Corner dots
        dots = []
        for i, (k, _) in enumerate(dims):
            dx, dy = pt(i, scores.get(k, 0) / 100)
            dots.append(f'<circle cx="{dx:.1f}" cy="{dy:.1f}" r="3" fill="#8b5cf6"/>')

        # Labels
        labels = []
        for i, (_, lbl) in enumerate(dims):
            lx, ly = lpt(i)
            labels.append(
                f'<text x="{lx:.0f}" y="{ly:.0f}" text-anchor="middle"'
                f' fill="#cec8bc" font-size="10" font-family="monospace">{lbl}</text>'
            )

        total_h = int(cy + R + label_R - R + 20)
        return (
            f'<svg width="170" height="{total_h}"'
            f' style="overflow:visible;font-family:monospace">'
            + "".join(grid_paths) + "".join(spokes) + data_poly
            + "".join(dots) + "".join(labels)
            + "</svg>"
        )

    # ── Radar score bars (right side of radar card) ───────────────────────────
    _DIM_LABELS = {
        "focus":     "专注力",
        "explore":   "探索欲",
        "mood":      "情绪起伏",
        "night_owl": "夜猫指数",
        "loyalty":   "忠诚度",
    }
    radar_scores_html = "".join(
        f'<div style="margin-bottom:8px">'
        f'<div style="display:flex;justify-content:space-between;'
        f'font-size:11px;margin-bottom:3px">'
        f'<span style="color:#cec8bc">{_DIM_LABELS[k]}</span>'
        f'<span style="color:#a78bfa">{personality_scores.get(k, 0)}</span>'
        f'</div>'
        f'<div style="height:5px;background:rgba(139,92,246,.15);border-radius:3px;overflow:hidden">'
        f'<div style="width:{personality_scores.get(k, 0)}%;height:100%;'
        f'background:#8b5cf6;border-radius:3px"></div>'
        f'</div>'
        f'</div>'
        for k in ("focus", "explore", "mood", "night_owl", "loyalty")
    )

    # ── Recommendation cards ──────────────────────────────────────────────────
    rec_cards = "".join(
        f'<div class="rec-card"><span class="rec-n">{i}</span>'
        f'<span class="rec-q">{html.escape(q)}</span></div>'
        for i, q in enumerate(queries, 1)
    )

    # ── JavaScript ────────────────────────────────────────────────────────────
    _save_js = (
        "function saveAsImage(){"
        "var btn=document.getElementById('save-btn');"
        "var orig=btn.textContent;"
        "if(typeof html2canvas==='undefined'){"
        "btn.textContent='❌ 需要联网';setTimeout(function(){btn.textContent=orig;},2000);return;}"
        "btn.textContent='⏳ 生成中…';btn.disabled=true;"
        "html2canvas(document.querySelector('.wrap'),{"
        "backgroundColor:'#080810',scale:2,logging:false,useCORS:true,"
        "ignoreElements:function(el){return el.id==='save-btn'||el.id==='modal';}"
        "}).then(function(c){"
        "var PAD=80;"
        "var out=document.createElement('canvas');"
        "out.width=c.width+PAD*2;out.height=c.height+PAD*2;"
        "var ctx=out.getContext('2d');"
        "ctx.fillStyle='#080810';ctx.fillRect(0,0,out.width,out.height);"
        "ctx.drawImage(c,PAD,PAD);"
        "var a=document.createElement('a');"
        "a.download='cwb-report-'+new Date().toISOString().slice(0,10)+'.png';"
        "a.href=out.toDataURL('image/png');a.click();"
        "btn.textContent=orig;btn.disabled=false;"
        "}).catch(function(){btn.textContent=orig;btn.disabled=false;});}"
    )

    _modal_js = (
        "function handleBarClick(el){showModal(el.dataset.type,el.dataset.key);}"
        "function handlePillClick(el){showModal('genre',el.dataset.key);}"
        "function showModal(type,key){"
        "var data=type==='artist'?TRACK_DATA.artists[key]:TRACK_DATA.genres[key];"
        "var emoji=type==='artist'?'🎤':'🎵';"
        "document.getElementById('modal-title').textContent=emoji+' '+key;"
        "var rows='';"
        "if(data&&data.length){"
        "for(var i=0;i<data.length;i++){"
        "var d=data[i];"
        "if(type==='artist'){"
        "rows+='<div class=\"modal-row\"><span class=\"modal-track\">'+d.t+'</span>"
        "<span class=\"modal-sub\">'+d.c+'次</span></div>';}"
        "else{"
        "rows+='<div class=\"modal-row\"><span class=\"modal-track\">'+d.t+'</span>"
        "<span class=\"modal-sub\">'+d.a+'</span></div>';}}"
        "}else{"
        "rows='<div style=\"color:#68687a;font-size:12px;padding:8px 0\">暂无详细记录</div>';}"
        "document.getElementById('modal-body').innerHTML=rows;"
        "document.getElementById('modal').classList.add('open');}"
        "function closeModal(){document.getElementById('modal').classList.remove('open');}"
        "document.addEventListener('keydown',function(e){if(e.key==='Escape')closeModal();});"
    )

    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{label} · 码上律动</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 40'><rect x='0' y='14' width='6' height='12' rx='3' fill='%238b5cf6' opacity='.5'/><rect x='9' y='8' width='6' height='24' rx='3' fill='%238b5cf6' opacity='.75'/><rect x='18' y='0' width='8' height='40' rx='4' fill='%238b5cf6'/><rect x='29' y='6' width='6' height='28' rx='3' fill='%238b5cf6' opacity='.75'/><rect x='38' y='14' width='10' height='12' rx='3' fill='%238b5cf6' opacity='.5'/></svg>">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#080810;color:#cec8bc;font-family:'JetBrains Mono',monospace,sans-serif;padding:24px 16px;min-height:100vh}}
.wrap{{max-width:860px;margin:0 auto}}
.header{{text-align:center;padding:40px 0 28px;border-bottom:1px solid rgba(139,92,246,.25)}}
.header-logo{{display:flex;align-items:center;justify-content:center;gap:8px;margin-bottom:20px;text-decoration:none}}
.header-logo .logo-text{{font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:700;letter-spacing:.12em;color:#f0ece4}}
.header-logo .logo-name{{color:#a78bfa}}
.header h1{{font-size:20px;font-weight:600;color:#f0ece4;letter-spacing:.04em;margin-bottom:4px}}
.header .date{{font-size:12px;color:#68687a;margin-bottom:0}}
.persona{{margin-bottom:20px}}
.persona-emoji{{font-size:40px;line-height:1;margin-bottom:8px}}
.persona-title{{font-size:22px;font-weight:700;color:#f0ece4;letter-spacing:.04em;margin-bottom:4px}}
.persona-desc{{font-size:12px;color:#68687a;letter-spacing:.03em}}
.stats-bar{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:20px 0}}
.stat-card{{background:#0f0f1a;border:1px solid rgba(139,92,246,.25);border-radius:10px;padding:16px;text-align:center}}
.stat-num{{font-size:28px;font-weight:700;color:#a78bfa;line-height:1;margin-bottom:4px}}
.stat-label{{font-size:11px;color:#68687a;letter-spacing:.08em}}
.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}}
.three-col{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-bottom:16px}}
.card{{background:#0f0f1a;border:1px solid rgba(139,92,246,.25);border-radius:10px;padding:20px;margin-bottom:16px;overflow:hidden}}
.ctitle{{font-size:11px;letter-spacing:.1em;color:#68687a;margin-bottom:14px;text-transform:uppercase}}
.bar-item{{cursor:pointer;margin-bottom:8px;padding:4px 6px;border-radius:6px;transition:background .15s}}
.bar-item:hover{{background:rgba(139,92,246,.1)}}
.bar-label{{font-size:12px;color:#cec8bc;margin-bottom:3px;font-family:monospace}}
.bar-track{{display:flex;align-items:center;gap:8px}}
.bar-bg{{flex:1;height:8px;background:rgba(139,92,246,.15);border-radius:4px;overflow:hidden;min-width:60px}}
.bar-fill{{height:100%;background:#8b5cf6;border-radius:4px;opacity:.8}}
.bar-count{{font-size:11px;color:#68687a;min-width:24px;text-align:right;flex-shrink:0}}
.gpill{{background:rgba(139,92,246,.18);border:1px solid rgba(139,92,246,.3);color:#a78bfa;font-size:10px;padding:2px 6px;border-radius:6px;cursor:pointer;transition:background .15s;display:inline-block;margin:2px}}
.gpill:hover{{background:rgba(139,92,246,.35)}}
.radar-wrap{{display:flex;align-items:flex-start;gap:24px}}
.radar-scores{{flex:1;padding-top:8px}}
.rec-card{{background:#0f0f1a;border:1px solid rgba(139,92,246,.2);border-radius:8px;padding:12px 16px;display:flex;align-items:flex-start;gap:10px;margin-bottom:8px}}
.rec-n{{color:#8b5cf6;font-size:13px;font-weight:700;min-width:16px;padding-top:1px}}
.rec-q{{color:#cec8bc;font-size:12px;line-height:1.5}}
.summary{{background:rgba(139,92,246,.08);border:1px solid rgba(139,92,246,.2);border-radius:10px;padding:16px 20px;margin:0 0 24px;font-size:13px;line-height:1.7}}
.footer{{text-align:center;padding:20px 0 8px;font-size:11px;color:#68687a;border-top:1px solid rgba(139,92,246,.15)}}
#modal{{display:none;position:fixed;inset:0;z-index:200;align-items:center;justify-content:center}}
#modal.open{{display:flex}}
#modal-backdrop{{position:absolute;inset:0;background:rgba(0,0,0,.72)}}
#modal-box{{position:relative;background:#0f0f1a;border:1px solid rgba(139,92,246,.4);border-radius:12px;padding:24px;max-width:400px;width:90%;max-height:70vh;overflow-y:auto;z-index:1}}
#modal-head{{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}}
#modal-title{{font-size:14px;font-weight:700;color:#f0ece4;letter-spacing:.02em}}
#modal-close{{background:none;border:none;color:#68687a;font-size:20px;cursor:pointer;padding:0 4px;line-height:1}}
#modal-close:hover{{color:#cec8bc}}
.modal-row{{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid rgba(139,92,246,.1);font-size:12px;gap:8px}}
.modal-row:last-child{{border-bottom:none}}
.modal-track{{color:#cec8bc;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.modal-sub{{color:#68687a;font-size:11px;flex-shrink:0}}
#save-btn{{position:fixed;top:16px;right:16px;background:#8b5cf6;color:#fff;border:none;border-radius:8px;padding:8px 14px;font-size:12px;font-family:'JetBrains Mono',monospace;cursor:pointer;z-index:99;letter-spacing:.05em;box-shadow:0 2px 12px rgba(139,92,246,.4);transition:opacity .15s}}
#save-btn:hover{{opacity:.85}}
#save-btn:disabled{{opacity:.4;cursor:not-allowed}}
@media(max-width:600px){{.two-col,.three-col{{grid-template-columns:1fr}}.stats-bar{{grid-template-columns:repeat(2,1fr)}}}}
@media print{{#save-btn{{display:none!important}}body{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}@page{{margin:0}}}}
</style>
</head>
<body>
<div class="wrap">

  <div class="header">
    <a href="https://codebeat.top" class="header-logo" target="_blank" rel="noopener">
      <svg width="20" height="20" viewBox="0 0 48 40" fill="none">
        <rect x="0" y="14" width="6" height="12" rx="3" fill="#8b5cf6" opacity=".5"/>
        <rect x="9" y="8" width="6" height="24" rx="3" fill="#8b5cf6" opacity=".75"/>
        <rect x="18" y="0" width="8" height="40" rx="4" fill="#8b5cf6"/>
        <rect x="29" y="6" width="6" height="28" rx="3" fill="#8b5cf6" opacity=".75"/>
        <rect x="38" y="14" width="10" height="12" rx="3" fill="#8b5cf6" opacity=".5"/>
      </svg>
      <span class="logo-text"><span class="logo-name">Coding</span>&nbsp;with Beat</span>
    </a>
    <div class="persona">
      <div class="persona-emoji">{p_emoji}</div>
      <div class="persona-title">{p_title}</div>
      <div class="persona-desc">{p_desc}</div>
    </div>
    <h1>{label}</h1>
    <div class="date">{start} ~ {end}</div>
  </div>

  <div class="stats-bar">
    <div class="stat-card">
      <div class="stat-num">{play_count}</div>
      <div class="stat-label">总播放</div>
    </div>
    <div class="stat-card">
      <div class="stat-num">{unique_artist_count}</div>
      <div class="stat-label">独立艺手</div>
    </div>
    <div class="stat-card">
      <div class="stat-num">{estimated_hours}h</div>
      <div class="stat-label">估算时长</div>
    </div>
    <div class="stat-card">
      <div class="stat-num" style="font-size:24px">{peak_label}</div>
      <div class="stat-label">峰值时段</div>
    </div>
  </div>

  <div class="card" id="daily-chart">
    <div class="ctitle">📅 每日播放</div>
    {_daily_chart_html(daily_plays, period)}
  </div>

  <div class="two-col">
    <div class="card"><div class="ctitle">🎤 常听歌手</div>{_bar_html(top_artists, 'artist')}</div>
    <div class="card"><div class="ctitle">🎵 主要曲风</div>{_bar_html(top_genres, 'genre')}</div>
  </div>

  <div class="two-col">
    <div class="card"><div class="ctitle">🕐 时段热力</div>{_time_heatmap_html(time_pattern, band_track_counts)}</div>
    <div class="card"><div class="ctitle">🔍 热搜词云</div>{_word_cloud_html(top_search_terms)}</div>
  </div>

  <div class="three-col">
    <div class="card" style="text-align:center">
      <div class="ctitle">🌐 语言偏好</div>
      {_donut_svg(language_pref)}
    </div>
    <div class="card">
      <div class="ctitle">♥ 收藏艺手</div>
      {_loved_html(loved_artists, top_artists)}
    </div>
    <div class="card">
      <div class="ctitle">📈 偏好变化</div>
      {trends_section}
    </div>
  </div>

  <div class="card" id="radar-card">
    <div class="ctitle">🎧 音乐人格</div>
    <div class="radar-wrap">
      {_radar_svg(personality_scores)}
      <div class="radar-scores">
        <div style="margin-bottom:16px">
          <div style="font-size:18px;font-weight:700;color:#f0ece4">{p_emoji} {p_title}</div>
          <div style="font-size:11px;color:#68687a;margin-top:4px">{p_desc}</div>
        </div>
        {radar_scores_html}
      </div>
    </div>
  </div>

  <div style="margin-bottom:16px">
    <div class="ctitle" style="margin-bottom:12px">🎵 个性化推荐</div>
    {rec_cards}
  </div>

  <div class="summary">💬 {summary}</div>

  <div class="footer">
    Generated by <a href="https://codebeat.top" style="color:#8b5cf6;text-decoration:none">码上律动</a>
    · {generated_at.strftime("%Y-%m-%d %H:%M")}
  </div>
</div>

<div id="modal" onclick="closeModal()">
  <div id="modal-backdrop"></div>
  <div id="modal-box" onclick="event.stopPropagation()">
    <div id="modal-head">
      <span id="modal-title"></span>
      <button id="modal-close" onclick="closeModal()">×</button>
    </div>
    <div id="modal-body"></div>
  </div>
</div>

<button id="save-btn" onclick="saveAsImage()">📸 保存图片</button>
<script>var TRACK_DATA={track_data_json};</script>
<script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>
<script>{_save_js}</script>
<script>{_modal_js}</script>
</body>
</html>"""
```

- [ ] **Step 5: 运行所有测试，确认通过**

```
pytest tests/test_profile.py -v
```
期望：所有测试绿灯，尤其检查：
- `test_build_html_report_contains_daily_chart` — PASS
- `test_build_html_report_contains_radar_card` — PASS
- `test_build_html_report_contains_medals` — PASS
- `test_build_html_report_contains_estimated_hours` — PASS
- `test_build_html_report_contains_loved_artist` — PASS
- `test_build_html_report_contains_search_term` — PASS

若有 import 报错，检查 `pytest.approx` 是否已在 Task 1 测试里 import（`import pytest` 在文件顶部已有）。

- [ ] **Step 6: 手动验证报告渲染**

```bash
python -c "
from coding_with_beat import profile
import datetime, json

p = {
    'period': 'weekly',
    'generated_at': datetime.datetime.now(),
    'play_count': 42,
    'top_artists': [('Hans Zimmer', 12), ('周杰伦', 8), ('ODESZA', 5)],
    'top_genres': [('lofi', 9), ('ambient', 6), ('classical', 4)],
    'top_search_terms': [('lofi coding', 5), ('jazz night', 4), ('focus', 3)],
    'language_pref': {'en': 0.6, 'zh': 0.3, 'instrumental': 0.1},
    'loved_artists': ['Hans Zimmer', 'Nujabes'],
    'recent_trend': ['synthwave'],
    'stable_pref': ['lofi', 'ambient'],
    'declining_pref': ['华语'],
    'time_pattern': {'night': ['lofi', 'ambient'], 'afternoon': ['classical']},
    'tracks_by_artist': {'Hans Zimmer': [{'t': 'Interstellar', 'c': 5}]},
    'tracks_by_genre': {'lofi': [{'t': 'Track 1', 'a': 'Hans Zimmer'}]},
    'unique_artist_count': 8,
    'estimated_hours': 2.5,
    'peak_band': 'night',
    'band_track_counts': {'morning': 3, 'afternoon': 8, 'evening': 10, 'night': 21},
    'daily_plays': {'2026-05-20': 10, '2026-05-21': 15, '2026-05-22': 8,
                    '2026-05-23': 5, '2026-05-24': 12, '2026-05-25': 4, '2026-05-26': 6},
    'personality_scores': {'focus': 70, 'explore': 45, 'mood': 60, 'night_owl': 83, 'loyalty': 55},
    'trend_detail': {'synthwave': (0, 4), 'lofi': (5, 7), 'ambient': (6, 4), '华语': (3, 0)},
}
html = profile.build_html_report(p)
path = '/tmp/cwb-report-v2-test.html'
open(path, 'w').write(html)
print('Written to', path)
"
open /tmp/cwb-report-v2-test.html
```

在浏览器里检查：
- 顶部人格 emoji + 4 个统计卡
- 每日播放柱状图（7 根柱）
- 两列：艺手/曲风 各有 🥇🥈🥉
- 两列：时段热力块 + 搜索词云
- 三列：语言 donut / 收藏艺手（含播放次数）/ 偏好趋势（含 % 变化）
- 雷达图（五边形 SVG）+ 右侧 5 维度进度条
- 推荐卡片 + 总结

- [ ] **Step 7: 提交**

```bash
git add coding_with_beat/profile.py tests/test_profile.py
git commit -m "feat(html-report): v2 dashboard — daily chart, heatmap, word cloud, radar, loved wall"
```
