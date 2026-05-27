# coding_with_beat/profile.py
"""User music profile: analysis, report generation, and recommendation queries."""
from __future__ import annotations

import datetime
import html
import math
import re
from collections import Counter

from . import history as _history
from .history import _STYLE_KEYWORDS
from .sources import get_source

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
    am_tracks: list[dict] = []
    local_tracks: list[dict] = []

    if source != "local":
        try:
            am = get_source("apple_music")
            fn = getattr(am, "play_history", None)
            if callable(fn):
                am_tracks.extend(fn(days + 1, 500))
        except Exception:
            pass

    if source != "apple_music":
        local_tracks.extend(_history.read(limit=500))

    # ── Normalise timestamps ──────────────────────────────────────────────────
    def _normalise(raw: list[dict]) -> list[dict]:
        result = []
        for t in raw:
            ts = t.get("ts")
            if isinstance(ts, str):
                try:
                    ts = datetime.datetime.strptime(ts[:19], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    continue
            if ts is None:
                continue
            t = dict(t)
            t["ts"] = ts
            result.append(t)
        return result

    am_norm = _normalise(am_tracks)
    local_norm = _normalise(local_tracks)

    # ── Cross-source dedup: prefer AM; drop local records that also appear in AM ─
    if am_norm and local_norm:
        am_keys: set[str] = set()
        for t in am_norm:
            minute_str = t["ts"].strftime("%Y-%m-%dT%H:%M")
            am_keys.add(
                f"{(t.get('title') or '').lower()}|{(t.get('artist') or '').lower()}|{minute_str}"
            )
        filtered_local = []
        for t in local_norm:
            minute_str = t["ts"].strftime("%Y-%m-%dT%H:%M")
            key = f"{(t.get('title') or '').lower()}|{(t.get('artist') or '').lower()}|{minute_str}"
            if key not in am_keys:
                filtered_local.append(t)
        tracks = am_norm + filtered_local
    else:
        tracks = am_norm + local_norm

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
    language_pref = {
        lang: round(lang_counter.get(lang, 0) / total, 2)
        for lang in ("zh", "en", "instrumental")
    }

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
        if ratio > 0
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


def _music_personality(profile: dict) -> tuple[str, str, str]:
    """Derive a fun music personality title. Returns (emoji, title, description)."""
    time_pattern  = profile.get("time_pattern", {})
    language_pref = profile.get("language_pref", {})
    top_genres    = profile.get("top_genres", [])

    time_counts = {band: len(genres) for band, genres in time_pattern.items()}
    dom_time = max(time_counts, key=time_counts.get) if time_counts else "night"

    _BUCKETS = [
        ("lofi",       ["lofi", "lo-fi", "chillhop"]),
        ("electronic", ["electronic", "synthwave", "edm", "techno", "house", "cyberpunk", "赛博"]),
        ("classical",  ["classical", "piano", "orchestra", "古典"]),
        ("jazz",       ["jazz", "bossa"]),
        ("hiphop",     ["hip-hop", "hip hop", "rap", "trap", "嘻哈"]),
        ("ambient",    ["ambient", "drone", "meditation"]),
        ("rnb",        ["rnb", "r&b", "soul"]),
        ("chinese",    ["华语", "国风", "民谣", "古风"]),
        ("pop",        ["pop", "indie"]),
    ]
    bucket_scores: dict[str, int] = {}
    for genre, count in top_genres:
        gl = genre.lower()
        for bucket, keys in _BUCKETS:
            if any(k in gl for k in keys):
                bucket_scores[bucket] = bucket_scores.get(bucket, 0) + count
    top_bucket = max(bucket_scores, key=bucket_scores.get) if bucket_scores else "pop"

    zh = language_pref.get("zh", 0)
    if zh > 0.65 and top_bucket not in ("chinese", "lofi", "classical"):
        top_bucket = "chinese"

    _TABLE: dict[tuple[str, str], tuple[str, str, str]] = {
        ("night",     "lofi"):       ("🌙", "深夜lofi主义者",  "代码与旋律在午夜交融，这是属于你的静谧时光"),
        ("night",     "electronic"): ("⚡", "赛博夜行先锋",    "在霓虹与合成器之间，划破深夜的电波"),
        ("night",     "ambient"):    ("🌌", "深夜氛围冥想者",  "用环境音为思绪构建一片宁静的宇宙"),
        ("night",     "classical"):  ("🎹", "深夜古典守夜人",  "琴键陪伴每个不眠之夜，音符是最好的伴侣"),
        ("night",     "hiphop"):     ("🎤", "深夜嘻哈游侠",    "节拍与黑夜是最忠实的搭档"),
        ("night",     "jazz"):       ("🎷", "午夜爵士幽灵",    "在蓝调的忧郁里，感受那份慵懒的美"),
        ("night",     "chinese"):    ("🏮", "夜色华语诗人",    "在华语旋律里寻找那份独有的共鸣"),
        ("night",     "rnb"):        ("💙", "深夜灵魂歌者",    "R&B的丝滑节奏是深夜最好的慰藉"),
        ("night",     "pop"):        ("🌙", "深夜流行漫游者",  "在旋律里流浪，在深夜里做梦"),
        ("morning",   "pop"):        ("🌅", "清晨活力先行者",  "用音乐点亮每一个崭新的早晨"),
        ("morning",   "classical"):  ("☀️", "清晨古典主义者",  "晨光里，音符比咖啡更能唤醒灵魂"),
        ("morning",   "lofi"):       ("🌤️","晨曦lofi漫步者",  "轻柔的旋律陪伴每一个从容的早晨"),
        ("morning",   "chinese"):    ("🌸", "清晨华语吟游者",  "用熟悉的中文旋律开启每一天"),
        ("afternoon", "jazz"):       ("☕", "午后爵士常客",    "一杯咖啡，一段爵士，完美的下午"),
        ("afternoon", "pop"):        ("✨", "午后流行探索者",  "在阳光下随着旋律自由漂流"),
        ("afternoon", "lofi"):       ("📖", "午后lofi阅读者", "lofi的节拍让午后的专注更持久"),
        ("evening",   "electronic"): ("🌆", "傍晚电子巡游者", "华灯初上，电子音浪开始涌动"),
        ("evening",   "chinese"):    ("🌸", "傍晚华语漫想家", "夕阳西下，用华语旋律填满思绪"),
        ("evening",   "jazz"):       ("🌇", "黄昏爵士追随者", "在落日余晖里享受蓝调的余韵"),
    }
    key = (dom_time, top_bucket)
    if key in _TABLE:
        return _TABLE[key]

    _FALLBACK: dict[str, tuple[str, str, str]] = {
        "lofi":       ("🎧", "lofi冥想主义者",  "在节奏与宁静之间，找到专属的心流状态"),
        "electronic": ("⚡", "电子音浪冲浪者",  "骑着合成器的浪潮，探索声音的边界"),
        "classical":  ("🎼", "古典浪漫主义者",  "在跨越时代的旋律里，寻找灵魂的共鸣"),
        "jazz":       ("☕", "爵士咖啡馆常客",  "蓝调与爵士是你永恒的精神食粮"),
        "hiphop":     ("🎤", "嘻哈文化信徒",    "节拍与韵脚是你表达世界的方式"),
        "ambient":    ("🌌", "氛围音景建筑师",  "用声音构建属于自己的内心宇宙"),
        "rnb":        ("💙", "R&B灵魂共鸣者",   "丝滑的节奏直抵内心最柔软的角落"),
        "chinese":    ("🏮", "华语情怀守护者",  "在中文旋律里找到了最深的情感共鸣"),
        "pop":        ("🎵", "流行音乐探险家",  "广泛探索各种风格，音乐品味包罗万象"),
    }
    return _FALLBACK.get(top_bucket, ("🎵", "音乐探险家", "广泛探索各种风格，音乐品味包罗万象"))


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
    p_emoji, p_title, p_desc = _music_personality(profile)

    summary_parts: list[str] = []
    if top_genres:
        top2 = " 和 ".join(html.escape(g) for g, _ in top_genres[:2])
        summary_parts.append(f"这{_PERIOD_ZH.get(period, '周')}你的音乐偏好明显偏向 {top2}")
    if declining_pref:
        summary_parts.append(f"{'、'.join(html.escape(x) for x in declining_pref[:2])} 播放次数有所下降")
    if recent_trend:
        summary_parts.append(f"{'、'.join(html.escape(x) for x in recent_trend[:2])} 开始走高")
    summary = "，".join(summary_parts) + "。" if summary_parts else f"本{_PERIOD_ZH.get(period, '周')}共播放 {play_count} 首，继续保持！"

    def _bar_svg(items: list, max_items: int = 5) -> str:
        items = items[:max_items]
        if not items:
            return '<p style="color:#68687a;font-size:12px;margin:0">暂无数据</p>'
        max_val = max(c for _, c in items) or 1
        W, BAR_H, GAP, LW = 170, 18, 10, 76
        rows = []
        for i, (name, count) in enumerate(items):
            y = i * (BAR_H + GAP)
            bw = max(4, int((count / max_val) * (W - LW - 24)))
            nm = html.escape((name[:9] + "…") if len(name) > 9 else name)
            rows += [
                f'<text x="0" y="{y+13}" fill="#cec8bc" font-size="12">{nm}</text>',
                f'<rect x="{LW}" y="{y+2}" width="{bw}" height="{BAR_H-4}" rx="3" fill="#8b5cf6" opacity=".8"/>',
                f'<text x="{LW+bw+5}" y="{y+13}" fill="#68687a" font-size="11">{count}</text>',
            ]
        h = len(items) * (BAR_H + GAP)
        return f'<svg width="{W}" height="{h}" style="overflow:hidden;font-family:monospace">{"".join(rows)}</svg>'

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
            f'font-size:12px;font-family:monospace;display:inline-block;margin:2px">{html.escape(item)}</span>'
            for item in items[:4]
        )

    band_labels = {"morning": "🌅 早晨", "afternoon": "☀️ 下午", "evening": "🌆 傍晚", "night": "🌙 深夜"}
    time_rows = "".join(
        f'<div class="time-row">'
        f'<span class="time-label">{band_labels[band]}</span>'
        + "".join(f'<span class="gpill">{html.escape(g)}</span>' for g in genres[:3])
        + "</div>"
        for band in ("morning", "afternoon", "evening", "night")
        if (genres := time_pattern.get(band, []))
    )

    rec_cards = "".join(
        f'<div class="rec-card"><span class="rec-n">{i}</span><span class="rec-q">{html.escape(q)}</span></div>'
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

    _save_js = (
        "function saveAsImage(){"
        "var btn=document.getElementById('save-btn');"
        "var orig=btn.textContent;"
        "btn.textContent='⏳ 生成中…';btn.disabled=true;"
        "var el=document.querySelector('.wrap');"
        "var W=el.offsetWidth,H=el.scrollHeight;"
        "var css=document.querySelector('style').textContent;"
        "var markup='<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"'+W+'\" height=\"'+H+'\">"
        "<foreignObject width=\"100%\" height=\"100%\">"
        "<html xmlns=\"http://www.w3.org/1999/xhtml\"><head>"
        "<style>*{box-sizing:border-box;margin:0;padding:0}"
        "body{background:#080810;color:#cec8bc;font-family:monospace;"
        "padding:24px 16px}'+css+'</style></head>"
        "<body>'+el.outerHTML+'</body></html>"
        "</foreignObject></svg>';"
        "var img=new Image();"
        "img.onload=function(){"
        "var c=document.createElement('canvas');"
        "c.width=W*2;c.height=H*2;"
        "var ctx=c.getContext('2d');"
        "ctx.scale(2,2);"
        "ctx.fillStyle='#080810';ctx.fillRect(0,0,W,H);"
        "ctx.drawImage(img,0,0);"
        "var a=document.createElement('a');"
        "a.download='cwb-report-'+new Date().toISOString().slice(0,10)+'.png';"
        "a.href=c.toDataURL('image/png');a.click();"
        "btn.textContent=orig;btn.disabled=false;"
        "};"
        "img.onerror=function(){"
        "btn.textContent=orig;btn.disabled=false;"
        "window.print();"
        "};"
        "img.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(markup);"
        "}"
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
.card{{background:#0f0f1a;border:1px solid rgba(139,92,246,.25);border-radius:10px;padding:20px;overflow:hidden}}
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
#save-btn{{position:fixed;top:16px;right:16px;background:#8b5cf6;color:#fff;border:none;border-radius:8px;padding:8px 14px;font-size:12px;font-family:'JetBrains Mono',monospace;cursor:pointer;z-index:99;letter-spacing:.05em;box-shadow:0 2px 12px rgba(139,92,246,.4);transition:opacity .15s}}
#save-btn:hover{{opacity:.85}}
#save-btn:disabled{{opacity:.4;cursor:not-allowed}}
.persona{{margin-bottom:24px}}
.persona-emoji{{font-size:44px;line-height:1;margin-bottom:10px}}
.persona-title{{font-size:24px;font-weight:700;color:#f0ece4;letter-spacing:.04em;margin-bottom:6px}}
.persona-desc{{font-size:12px;color:#68687a;letter-spacing:.03em}}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <div class="header-logo">码上律动 · CODING WITH BEAT</div>
    <div class="persona">
      <div class="persona-emoji">{p_emoji}</div>
      <div class="persona-title">{p_title}</div>
      <div class="persona-desc">{p_desc}</div>
    </div>
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

  <div class="footer">Generated by <a href="https://codebeat.top" style="color:#8b5cf6;text-decoration:none">码上律动</a> · {generated_at.strftime("%Y-%m-%d %H:%M")}</div>
</div>
<button id="save-btn" onclick="saveAsImage()">📸 保存图片</button>
<script>{_save_js}</script>
</body>
</html>"""
