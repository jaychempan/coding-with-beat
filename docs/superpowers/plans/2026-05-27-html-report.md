# HTML Listening Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `cwb profile --html` that generates a self-contained dark-theme HTML report with SVG charts and opens it in the browser.

**Architecture:** `build_html_report(profile)` appended to `profile.py` generates a complete HTML string (inline SVG bar charts, donut chart, pill tags — zero external deps). `cmd_profile()` in `__main__.py` gains `--html` flag parsing that writes the file to `~/.coding-with-beat/` and calls `open`.

**Tech Stack:** Python 3.10+, inline SVG, `math` stdlib (donut arcs), `subprocess.run(["open", ...])` for browser launch.

---

## File Map

| File | Change |
|------|--------|
| `coding_with_beat/profile.py` | Append `build_html_report()` (uses `math` for arc coords) |
| `coding_with_beat/__main__.py` | Update `cmd_profile()` to parse `--html`, write file, open browser |
| `tests/test_profile.py` | Append HTML report tests |
| `tests/test_cli.py` | Append `--html` CLI test |

---

## Task 1: Add `build_html_report()` to `profile.py`

**Files:**
- Modify: `coding_with_beat/profile.py` (append after `build_recommendation_queries`)
- Test: `tests/test_profile.py` (append 7 tests)

- [ ] **Step 1: Append the failing tests to `tests/test_profile.py`**

```python
# ── build_html_report ─────────────────────────────────────────────────────────

def test_build_html_report_is_valid_html():
    html = profile.build_html_report(_make_profile())
    assert html.startswith("<!DOCTYPE html>")
    assert "</html>" in html


def test_build_html_report_contains_play_count():
    html = profile.build_html_report(_make_profile())
    assert "42" in html


def test_build_html_report_contains_top_artist():
    html = profile.build_html_report(_make_profile())
    assert "Hans Zimmer" in html


def test_build_html_report_contains_top_genre():
    html = profile.build_html_report(_make_profile())
    assert "lofi" in html


def test_build_html_report_contains_language_pct():
    html = profile.build_html_report(_make_profile())
    # language_pref has en:0.6 → 60%
    assert "60" in html


def test_build_html_report_contains_trend_items():
    html = profile.build_html_report(_make_profile())
    assert "synthwave" in html   # recent_trend
    assert "华语" in html         # declining_pref


def test_build_html_report_contains_recommendation_query():
    html = profile.build_html_report(_make_profile())
    # stable_pref=["lofi","ambient"] → slot 1 contains "lofi"
    assert "lofi" in html
```

- [ ] **Step 2: Run one test to verify it fails**

```bash
cd /Users/jianchengpan/Projects/coding-with-beat
python -m pytest tests/test_profile.py::test_build_html_report_is_valid_html -v
```

Expected: `FAILED — AttributeError: module 'coding_with_beat.profile' has no attribute 'build_html_report'`

- [ ] **Step 3: Append `build_html_report` to `coding_with_beat/profile.py`**

Add `import math` at the top of the file (after `import re`), then append the full function at the end of the file:

```python
import math
```

Append at end of file:

```python
def build_html_report(profile: dict) -> str:
    """Generate a self-contained dark-theme HTML listening report with SVG charts."""
    period       = profile.get("period", "weekly")
    generated_at = profile.get("generated_at", datetime.datetime.now())
    days         = _PERIOD_DAYS.get(period, 7)
    start        = (generated_at - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    end          = generated_at.strftime("%Y-%m-%d")
    label        = _PERIOD_LABELS.get(period, "听歌报告")
    play_count   = profile.get("play_count", 0)
    top_artists  = profile.get("top_artists", [])
    top_genres   = profile.get("top_genres", [])
    language_pref = profile.get("language_pref", {})
    recent_trend = profile.get("recent_trend", [])
    stable_pref  = profile.get("stable_pref", [])
    declining_pref = profile.get("declining_pref", [])
    time_pattern = profile.get("time_pattern", {})
    queries      = build_recommendation_queries(profile)

    summary_parts: list[str] = []
    if top_genres:
        top2 = " 和 ".join(g for g, _ in top_genres[:2])
        summary_parts.append(f"这{_PERIOD_ZH.get(period, '周')}你的音乐偏好明显偏向 {top2}")
    if declining_pref:
        summary_parts.append(f"{'、'.join(declining_pref[:2])} 播放次数有所下降")
    if recent_trend:
        summary_parts.append(f"{'、'.join(recent_trend[:2])} 开始走高")
    summary = "，".join(summary_parts) + "。" if summary_parts else f"本{_PERIOD_ZH.get(period, '周')}共播放 {play_count} 首，继续保持！"

    def _bar_svg(items: list, max_items: int = 5) -> str:
        items = items[:max_items]
        if not items:
            return '<p style="color:#68687a;font-size:12px;margin:0">暂无数据</p>'
        max_val = max(c for _, c in items) or 1
        W, BAR_H, GAP, LW = 240, 18, 10, 82
        rows = []
        for i, (name, count) in enumerate(items):
            y = i * (BAR_H + GAP)
            bw = max(4, int((count / max_val) * (W - LW - 36)))
            nm = (name[:9] + "…") if len(name) > 9 else name
            rows += [
                f'<text x="0" y="{y+13}" fill="#cec8bc" font-size="12">{nm}</text>',
                f'<rect x="{LW}" y="{y+2}" width="{bw}" height="{BAR_H-4}" rx="3" fill="#8b5cf6" opacity=".8"/>',
                f'<text x="{LW+bw+5}" y="{y+13}" fill="#68687a" font-size="11">{count}</text>',
            ]
        h = len(items) * (BAR_H + GAP)
        return f'<svg width="{W}" height="{h}" style="overflow:visible;font-family:monospace">{"".join(rows)}</svg>'

    def _donut_svg(lang_pref: dict) -> str:
        COLORS = {"zh": "#8b5cf6", "en": "#a78bfa", "instrumental": "#6d7fd4"}
        LABELS = {"zh": "中文", "en": "英文", "instrumental": "纯音乐"}
        items = [(k, v) for k, v in lang_pref.items() if v > 0]
        if not items:
            return '<p style="color:#68687a;font-size:12px;margin:0">暂无数据</p>'
        total = sum(v for _, v in items)
        cx, cy, R, r = 60, 60, 50, 26
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
                f' L {ix2:.1f} {iy2:.1f} A {r} {r} 0 {lg} 0 {ix1:.1f} {iy1:.1f} Z" fill="{c}"/>'
            )
            angle += sweep
        dom_lang, dom_val = max(items, key=lambda x: x[1])
        dom_pct = int(dom_val * 100)
        legend = []
        for i, (lang, val) in enumerate(items):
            ly = 128 + i * 18
            legend += [
                f'<rect x="0" y="{ly}" width="10" height="10" rx="2" fill="{COLORS.get(lang, "#6b7280")}"/>',
                f'<text x="14" y="{ly+9}" fill="#cec8bc" font-size="11">{LABELS.get(lang, lang)} {int(val*100)}%</text>',
            ]
        total_h = 128 + len(items) * 18
        return (
            f'<svg width="160" height="{total_h}" style="overflow:visible;font-family:monospace">'
            f'{"".join(paths)}'
            f'<text x="{cx}" y="{cy-4}" text-anchor="middle" fill="#a78bfa" font-size="15" font-weight="bold">{dom_pct}%</text>'
            f'<text x="{cx}" y="{cy+12}" text-anchor="middle" fill="#cec8bc" font-size="11">{LABELS.get(dom_lang, dom_lang)}</text>'
            f'{"".join(legend)}</svg>'
        )

    def _pills(items: list, color: str) -> str:
        if not items:
            return '<span style="color:#68687a;font-size:12px">—</span>'
        return "".join(
            f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:10px;'
            f'font-size:12px;font-family:monospace;display:inline-block;margin:2px">{item}</span>'
            for item in items[:4]
        )

    band_labels = {"morning": "🌅 早晨", "afternoon": "☀️ 下午", "evening": "🌆 傍晚", "night": "🌙 深夜"}
    time_rows = "".join(
        f'<div class="time-row">'
        f'<span class="time-label">{band_labels[band]}</span>'
        + "".join(f'<span class="gpill">{g}</span>' for g in genres[:3])
        + "</div>"
        for band in ("morning", "afternoon", "evening", "night")
        if (genres := time_pattern.get(band, []))
    )

    rec_cards = "".join(
        f'<div class="rec-card"><span class="rec-n">{i}</span><span class="rec-q">{q}</span></div>'
        for i, q in enumerate(queries, 1)
    )

    trends_html = ""
    if recent_trend or stable_pref or declining_pref:
        trends_html = (
            "<div class='section'><div class='stitle'>📈 偏好变化</div>"
            "<div class='trends'>"
            f"<div class='tcol'><div class='tcol-h'>↑ 新增</div>{_pills(recent_trend, '#16a34a')}</div>"
            f"<div class='tcol'><div class='tcol-h'>→ 稳定</div>{_pills(stable_pref, '#6d28d9')}</div>"
            f"<div class='tcol'><div class='tcol-h'>↓ 下降</div>{_pills(declining_pref, '#b91c1c')}</div>"
            "</div></div>"
        )

    time_html = (
        f"<div class='section'><div class='stitle'>🕐 时间规律</div>{time_rows}</div>"
        if time_rows else ""
    )

    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{label} · 码上律动</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#080810;color:#cec8bc;font-family:'JetBrains Mono',monospace,sans-serif;padding:24px 16px;min-height:100vh}}
.wrap{{max-width:720px;margin:0 auto}}
.header{{text-align:center;padding:40px 0 32px;border-bottom:1px solid rgba(139,92,246,.25)}}
.header-logo{{font-size:11px;letter-spacing:.15em;color:#68687a;margin-bottom:12px}}
.header h1{{font-size:22px;font-weight:600;color:#f0ece4;letter-spacing:.04em;margin-bottom:6px}}
.header .date{{font-size:12px;color:#68687a;margin-bottom:20px}}
.big-num{{font-size:56px;font-weight:700;color:#a78bfa;line-height:1;margin-bottom:4px}}
.big-label{{font-size:12px;color:#68687a;letter-spacing:.1em}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:16px;margin:24px 0}}
.card{{background:#0f0f1a;border:1px solid rgba(139,92,246,.25);border-radius:10px;padding:20px}}
.ctitle{{font-size:11px;letter-spacing:.1em;color:#68687a;margin-bottom:14px;text-transform:uppercase}}
.section{{margin:0 0 24px}}
.stitle{{font-size:11px;letter-spacing:.1em;color:#68687a;text-transform:uppercase;margin-bottom:12px}}
.trends{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;background:#0f0f1a;border:1px solid rgba(139,92,246,.25);border-radius:10px;padding:20px}}
.tcol-h{{font-size:11px;color:#68687a;margin-bottom:8px;letter-spacing:.08em}}
.time-row{{display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap}}
.time-label{{font-size:12px;color:#68687a;min-width:76px}}
.gpill{{background:rgba(139,92,246,.18);border:1px solid rgba(139,92,246,.3);color:#a78bfa;font-size:11px;padding:2px 8px;border-radius:8px}}
.rec-card{{background:#0f0f1a;border:1px solid rgba(139,92,246,.2);border-radius:8px;padding:12px 16px;display:flex;align-items:flex-start;gap:10px;margin-bottom:8px}}
.rec-n{{color:#8b5cf6;font-size:13px;font-weight:700;min-width:16px;padding-top:1px}}
.rec-q{{color:#cec8bc;font-size:12px;line-height:1.5}}
.summary{{background:rgba(139,92,246,.08);border:1px solid rgba(139,92,246,.2);border-radius:10px;padding:16px 20px;margin:0 0 32px;font-size:13px;line-height:1.7}}
.footer{{text-align:center;padding:24px 0 8px;font-size:11px;color:#68687a;border-top:1px solid rgba(139,92,246,.15)}}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <div class="header-logo">码上律动 · CODING WITH BEAT</div>
    <h1>{label}</h1>
    <div class="date">{start} ~ {end}</div>
    <div class="big-num">{play_count}</div>
    <div class="big-label">首歌曲</div>
  </div>

  <div class="cards" style="margin-top:24px">
    <div class="card"><div class="ctitle">🎤 常听歌手</div>{_bar_svg(top_artists)}</div>
    <div class="card"><div class="ctitle">🎵 主要曲风</div>{_bar_svg(top_genres)}</div>
    <div class="card"><div class="ctitle">🌐 语言偏好</div>{_donut_svg(language_pref)}</div>
  </div>

  {trends_html}
  {time_html}

  <div class="section">
    <div class="stitle">🎵 个性化推荐</div>
    {rec_cards}
  </div>

  <div class="summary">💬 {summary}</div>

  <div class="footer">Generated by coding-with-beat · {generated_at.strftime("%Y-%m-%d %H:%M")}</div>
</div>
</body>
</html>"""
```

- [ ] **Step 4: Run all profile tests to verify they pass**

```bash
python -m pytest tests/test_profile.py -v
```

Expected: all tests `PASSED` (21 existing + 7 new = 28 total)

- [ ] **Step 5: Commit**

```bash
git add coding_with_beat/profile.py tests/test_profile.py
git commit -m "feat(profile): add build_html_report() with SVG charts"
```

---

## Task 2: Add `--html` flag to `cwb profile` CLI

**Files:**
- Modify: `coding_with_beat/__main__.py` — replace `cmd_profile()` function body
- Test: `tests/test_cli.py` (append 2 tests)

- [ ] **Step 1: Append the failing tests to `tests/test_cli.py`**

```python
def test_cmd_profile_html_flag_writes_file(monkeypatch, tmp_path):
    import sys, datetime
    monkeypatch.setattr(sys, "argv", ["cwb", "profile", "weekly", "--html"])

    fake_profile = {
        "period": "weekly",
        "generated_at": datetime.datetime.now(),
        "play_count": 10,
        "top_artists": [("Hans Zimmer", 5)],
        "top_genres": [("lofi", 4)],
        "top_search_terms": [],
        "language_pref": {"en": 1.0, "zh": 0.0, "instrumental": 0.0},
        "loved_artists": [],
        "recent_trend": [],
        "stable_pref": ["lofi"],
        "declining_pref": [],
        "time_pattern": {},
    }
    from coding_with_beat import profile as _profile
    monkeypatch.setattr(_profile, "build_profile", lambda period, **kw: fake_profile)

    import subprocess
    opened = []
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: opened.append(cmd))

    import coding_with_beat.config as _cfg
    real_data_dir = _cfg.DATA_DIR
    _cfg.DATA_DIR = tmp_path
    try:
        from coding_with_beat.__main__ import cmd_profile
        rc = cmd_profile()
    finally:
        _cfg.DATA_DIR = real_data_dir

    assert rc == 0
    html_files = list(tmp_path.glob("report_weekly_*.html"))
    assert len(html_files) == 1
    assert html_files[0].read_text(encoding="utf-8").startswith("<!DOCTYPE html>")


def test_cmd_profile_html_flag_insufficient_history(monkeypatch, capsys):
    import sys
    monkeypatch.setattr(sys, "argv", ["cwb", "profile", "weekly", "--html"])
    from coding_with_beat import profile as _profile

    def _raise(period, **kw):
        raise ValueError("insufficient_history")

    monkeypatch.setattr(_profile, "build_profile", _raise)
    from coding_with_beat.__main__ import cmd_profile
    rc = cmd_profile()
    out = capsys.readouterr().out
    assert rc == 0
    assert "不足" in out or "5" in out
```

- [ ] **Step 2: Run one test to verify it fails**

```bash
cd /Users/jianchengpan/Projects/coding-with-beat
python -m pytest tests/test_cli.py::test_cmd_profile_html_flag_writes_file -v
```

Expected: `FAILED` — `--html` not parsed, no HTML file written

- [ ] **Step 3: Replace `cmd_profile()` in `coding_with_beat/__main__.py`**

Replace the entire `cmd_profile` function with:

```python
def cmd_profile() -> int:
    from . import profile as _profile

    args = sys.argv[2:]
    html_mode = "--html" in args
    period_args = [a for a in args if not a.startswith("-")]

    valid = {"daily", "weekly", "monthly", "yearly"}
    period = period_args[0] if period_args else "weekly"
    if period not in valid:
        print(f"error: period must be one of: {', '.join(sorted(valid))}")
        return 2

    try:
        prof = _profile.build_profile(period)
    except ValueError:
        print("（听歌记录不足 5 首，多听一会儿再来生成报告吧 🎵）")
        return 0

    if html_mode:
        import subprocess
        from .config import DATA_DIR
        html = _profile.build_html_report(prof)
        out_path = DATA_DIR / f"report_{period}_{prof['generated_at'].strftime('%Y%m%d')}.html"
        out_path.write_text(html, encoding="utf-8")
        print(f"报告已生成：{out_path}")
        subprocess.run(["open", str(out_path)], check=False)
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

- [ ] **Step 4: Run all CLI tests to verify they pass**

```bash
python -m pytest tests/test_cli.py -v
```

Expected: all tests `PASSED`

- [ ] **Step 5: Smoke-test the HTML output**

```bash
python -m coding_with_beat profile weekly --html
```

Expected: either a browser opens with the report, or prints "不足 5 首" — no Python traceback.

- [ ] **Step 6: Commit**

```bash
git add coding_with_beat/__main__.py tests/test_cli.py
git commit -m "feat(cli): add cwb profile --html flag to generate and open HTML report"
```
