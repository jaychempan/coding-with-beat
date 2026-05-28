# coding_with_beat/profile.py
"""User music profile: analysis, report generation, and recommendation queries."""

from __future__ import annotations

import datetime
import html
import json
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

_AVG_TRACK_MIN: float = 3.5  # assumed average track duration in minutes

_INSTRUMENTAL_KEYWORDS = frozenset(
    [
        "instrumental",
        "无人声",
        "pure music",
        "纯音乐",
        "bgm",
        "ost",
        "soundtrack",
        "piano solo",
        "guitar instrumental",
    ]
)

_STOPWORDS = frozenset(
    [
        "a",
        "the",
        "and",
        "or",
        "of",
        "for",
        "in",
        "to",
        "with",
        "no",
        "some",
        "my",
        "by",
        "on",
        "at",
        "is",
        "it",
        "be",
        "lo",
        "fi",
    ]
)


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
    cjk_count = sum(1 for c in text if "一" <= c <= "鿿" or "぀" <= c <= "ヿ")
    return "zh" if cjk_count >= 1 else "en"


def _match_genres(text: str) -> list[str]:
    text_lower = text.lower()
    return [tag for tag, keywords in _STYLE_KEYWORDS.items() if any(kw in text_lower for kw in keywords)]


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
            am_keys.add(f"{(t.get('title') or '').lower()}|{(t.get('artist') or '').lower()}|{minute_str}")
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
    genre_counter_all = _genre_counter(period_tracks)
    top_genres = genre_counter_all.most_common(5)

    # ── Language preference ───────────────────────────────────────────────────
    lang_counter: Counter = Counter()
    for t in period_tracks:
        text = f"{t.get('title', '')} {t.get('artist', '')}"
        lang_counter[_detect_language(text)] += 1
    total = sum(lang_counter.values()) or 1
    language_pref = {lang: round(lang_counter.get(lang, 0) / total, 2) for lang in ("zh", "en", "instrumental")}

    # ── Search terms ──────────────────────────────────────────────────────────
    search_records = _history.read_search(limit=500)
    recent_searches = [s for s in search_records if s["ts"] >= cutoff]
    term_counter: Counter = Counter()
    for rec in recent_searches:
        tokens = re.findall(r"[a-zA-Z一-鿿]+", rec["query"].lower())
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
            loved_artists = list(
                {t.get("artist", "").strip() for t in fn(50) if t.get("artist") and t.get("artist") != "?"}
            )[:5]
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
        "morning": Counter(),
        "afternoon": Counter(),
        "evening": Counter(),
        "night": Counter(),
    }
    for t in period_tracks:
        band = _time_band(t["ts"].hour)
        text = f"{t.get('artist', '')} {t.get('album', '')}".lower()
        for g in _match_genres(text):
            band_genres[band][g] += 1
    time_pattern = {band: [g for g, _ in ctr.most_common(3)] for band, ctr in band_genres.items() if ctr}

    # ── Per-artist track list (for HTML drill-down) ───────────────────────────
    tracks_by_artist: dict[str, list[dict]] = {}
    for artist, _ in top_artists:
        a_tracks = [t for t in period_tracks if (t.get("artist") or "").strip() == artist]
        title_ctr: Counter = Counter()
        for t in a_tracks:
            title = (t.get("title") or "").strip()
            if title:
                title_ctr[title] += t.get("played_count", 1)
        tracks_by_artist[artist] = [{"t": title, "c": cnt} for title, cnt in title_ctr.most_common(8)]

    # ── Per-genre track list (for HTML drill-down) ────────────────────────────
    drill_genres: set[str] = {g for g, _ in top_genres}
    for genres_list in time_pattern.values():
        drill_genres.update(genres_list)

    tracks_by_genre: dict[str, list[dict]] = {}
    for genre in drill_genres:
        seen: set[str] = set()
        g_list: list[dict] = []
        for t in period_tracks:
            text = f"{t.get('artist', '')} {t.get('album', '')} {t.get('title', '')}".lower()
            if genre in _match_genres(text):
                title = (t.get("title") or "").strip()
                a_name = (t.get("artist") or "").strip()
                key = f"{title.lower()}|{a_name.lower()}"
                if key not in seen and title:
                    seen.add(key)
                    g_list.append({"t": title, "a": a_name})
            if len(g_list) >= 10:
                break
        tracks_by_genre[genre] = g_list

    # ── New computed fields ────────────────────────────────────────────────────
    unique_artist_count = len(artist_counter)
    estimated_hours = round(len(period_tracks) * _AVG_TRACK_MIN / 60, 1)

    band_track_counts: Counter = Counter()
    for t_ in period_tracks:
        band_track_counts[_time_band(t_["ts"].hour)] += 1

    peak_band = band_track_counts.most_common(1)[0][0] if band_track_counts else "night"
    night_plays = band_track_counts.get("night", 0)

    personality_scores = _personality_scores(
        language_pref,
        genre_counter_all,
        unique_artist_count,
        len(period_tracks),
        night_plays,
        top_artists,
    )

    if period == "daily":
        plays_ctr: Counter = Counter()
        for t_ in period_tracks:
            plays_ctr[t_["ts"].strftime("%H")] += 1
    elif period == "yearly":
        plays_ctr = Counter()
        for t_ in period_tracks:
            plays_ctr[t_["ts"].strftime("%Y-%m")] += 1
    else:  # weekly / monthly
        plays_ctr = Counter()
        for t_ in period_tracks:
            plays_ctr[t_["ts"].strftime("%Y-%m-%d")] += 1
    daily_plays = dict(sorted(plays_ctr.items()))

    trend_detail: dict[str, tuple[int, int]] = {
        g: (first_genres.get(g, 0), second_genres.get(g, 0)) for g in all_genre_keys
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
        "tracks_by_artist": tracks_by_artist,
        "tracks_by_genre": tracks_by_genre,
        "unique_artist_count": unique_artist_count,
        "estimated_hours": estimated_hours,
        "peak_band": peak_band,
        "band_track_counts": dict(band_track_counts),
        "daily_plays": daily_plays,
        "personality_scores": personality_scores,
        "trend_detail": trend_detail,
    }


_PERIOD_LABELS: dict[str, str] = {
    "daily": "今日听歌报告",
    "weekly": "本周听歌报告",
    "monthly": "本月听歌报告",
    "yearly": "年度听歌报告",
}

_BAND_LABELS: dict[str, str] = {
    "morning": "早晨",
    "afternoon": "下午",
    "evening": "傍晚",
    "night": "深夜",
}

_LANG_LABELS: dict[str, str] = {
    "zh": "中文",
    "en": "英文",
    "instrumental": "纯音乐",
}

_PERIOD_ZH: dict[str, str] = {
    "daily": "天",
    "weekly": "周",
    "monthly": "月",
    "yearly": "年",
}


def build_report(profile: dict) -> str:
    """Generate a plain-text listening report from a UserProfile dict."""
    period = profile.get("period", "weekly")
    generated_at = profile.get("generated_at", datetime.datetime.now())
    days = _PERIOD_DAYS.get(period, 7)
    start = (generated_at - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    end = generated_at.strftime("%Y-%m-%d")
    label = _PERIOD_LABELS.get(period, "听歌报告")

    top_artists = profile.get("top_artists", [])
    top_genres = profile.get("top_genres", [])
    language_pref = profile.get("language_pref", {})
    recent_trend = profile.get("recent_trend", [])
    stable_pref = profile.get("stable_pref", [])
    declining_pref = profile.get("declining_pref", [])
    time_pattern = profile.get("time_pattern", {})
    play_count = profile.get("play_count", 0)

    artists_str = " · ".join(a for a, _ in top_artists[:3]) if top_artists else "—"
    genres_str = " · ".join(g for g, _ in top_genres[:3]) if top_genres else "—"

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
    top_genres = profile.get("top_genres", [])
    recent_trend = profile.get("recent_trend", [])
    top_artists = profile.get("top_artists", [])
    stable_pref = profile.get("stable_pref", [])

    queries: list[str] = []

    # Slot 1: stable pref (or top genres as fallback) + context
    base = stable_pref[:2] if stable_pref else [g for g, _ in top_genres[:2]]
    if base:
        slot1 = " ".join(base)
        slot1 += f" {context} instrumental focus" if context else " instrumental focus"
        queries.append(slot1.strip())

    # Slot 2: recent trend for exploration; fall back to second top genre
    trend = recent_trend[0] if recent_trend else (top_genres[1][0] if len(top_genres) > 1 else None)
    if trend:
        queries.append(f"{trend} night coding focus electronic")

    # Slot 3: top artist extension
    if top_artists:
        queries.append(f"{top_artists[0][0]} similar instrumental lo-fi")

    # Guarantee at least 1 query
    if not queries and top_genres:
        queries.append(f"{top_genres[0][0]} instrumental")

    return queries[:3]


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
        "focus": _clamp(instrumental * 60 + genre_conc * 40),
        "explore": _clamp(
            unique_artist_count / max(play_count, 1) * 500
        ),  # 500: hits 100 when ~1 in 5 plays is a new artist
        "mood": _clamp(len(genre_counter) / 5 * 100),
        "night_owl": _clamp(night_plays / max(play_count, 1) * 100),
        "loyalty": _clamp(top3_plays / max(play_count, 1) * 100),
    }


def _music_personality(profile: dict) -> tuple[str, str, str]:
    """Derive a fun music personality title. Returns (emoji, title, description)."""
    time_pattern = profile.get("time_pattern", {})
    language_pref = profile.get("language_pref", {})
    top_genres = profile.get("top_genres", [])

    time_counts = {band: len(genres) for band, genres in time_pattern.items()}
    dom_time = max(time_counts, key=time_counts.get) if time_counts else "night"

    _BUCKETS = [
        ("lofi", ["lofi", "lo-fi", "chillhop"]),
        ("electronic", ["electronic", "synthwave", "edm", "techno", "house", "cyberpunk", "赛博"]),
        ("classical", ["classical", "piano", "orchestra", "古典"]),
        ("jazz", ["jazz", "bossa"]),
        ("hiphop", ["hip-hop", "hip hop", "rap", "trap", "嘻哈"]),
        ("ambient", ["ambient", "drone", "meditation"]),
        ("rnb", ["rnb", "r&b", "soul"]),
        ("chinese", ["华语", "国风", "民谣", "古风"]),
        ("pop", ["pop", "indie"]),
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
        ("night", "lofi"): ("🌙", "深夜lofi主义者", "代码与旋律在午夜交融，这是属于你的静谧时光"),
        ("night", "electronic"): ("⚡", "赛博夜行先锋", "在霓虹与合成器之间，划破深夜的电波"),
        ("night", "ambient"): ("🌌", "深夜氛围冥想者", "用环境音为思绪构建一片宁静的宇宙"),
        ("night", "classical"): ("🎹", "深夜古典守夜人", "琴键陪伴每个不眠之夜，音符是最好的伴侣"),
        ("night", "hiphop"): ("🎤", "深夜嘻哈游侠", "节拍与黑夜是最忠实的搭档"),
        ("night", "jazz"): ("🎷", "午夜爵士幽灵", "在蓝调的忧郁里，感受那份慵懒的美"),
        ("night", "chinese"): ("🏮", "夜色华语诗人", "在华语旋律里寻找那份独有的共鸣"),
        ("night", "rnb"): ("💙", "深夜灵魂歌者", "R&B的丝滑节奏是深夜最好的慰藉"),
        ("night", "pop"): ("🌙", "深夜流行漫游者", "在旋律里流浪，在深夜里做梦"),
        ("morning", "pop"): ("🌅", "清晨活力先行者", "用音乐点亮每一个崭新的早晨"),
        ("morning", "classical"): ("☀️", "清晨古典主义者", "晨光里，音符比咖啡更能唤醒灵魂"),
        ("morning", "lofi"): ("🌤️", "晨曦lofi漫步者", "轻柔的旋律陪伴每一个从容的早晨"),
        ("morning", "chinese"): ("🌸", "清晨华语吟游者", "用熟悉的中文旋律开启每一天"),
        ("afternoon", "jazz"): ("☕", "午后爵士常客", "一杯咖啡，一段爵士，完美的下午"),
        ("afternoon", "pop"): ("✨", "午后流行探索者", "在阳光下随着旋律自由漂流"),
        ("afternoon", "lofi"): ("📖", "午后lofi阅读者", "lofi的节拍让午后的专注更持久"),
        ("evening", "electronic"): ("🌆", "傍晚电子巡游者", "华灯初上，电子音浪开始涌动"),
        ("evening", "chinese"): ("🌸", "傍晚华语漫想家", "夕阳西下，用华语旋律填满思绪"),
        ("evening", "jazz"): ("🌇", "黄昏爵士追随者", "在落日余晖里享受蓝调的余韵"),
    }
    key = (dom_time, top_bucket)
    if key in _TABLE:
        return _TABLE[key]

    _FALLBACK: dict[str, tuple[str, str, str]] = {
        "lofi": ("🎧", "lofi冥想主义者", "在节奏与宁静之间，找到专属的心流状态"),
        "electronic": ("⚡", "电子音浪冲浪者", "骑着合成器的浪潮，探索声音的边界"),
        "classical": ("🎼", "古典浪漫主义者", "在跨越时代的旋律里，寻找灵魂的共鸣"),
        "jazz": ("☕", "爵士咖啡馆常客", "蓝调与爵士是你永恒的精神食粮"),
        "hiphop": ("🎤", "嘻哈文化信徒", "节拍与韵脚是你表达世界的方式"),
        "ambient": ("🌌", "氛围音景建筑师", "用声音构建属于自己的内心宇宙"),
        "rnb": ("💙", "R&B灵魂共鸣者", "丝滑的节奏直抵内心最柔软的角落"),
        "chinese": ("🏮", "华语情怀守护者", "在中文旋律里找到了最深的情感共鸣"),
        "pop": ("🎵", "流行音乐探险家", "广泛探索各种风格，音乐品味包罗万象"),
    }
    return _FALLBACK.get(top_bucket, ("🎵", "音乐探险家", "广泛探索各种风格，音乐品味包罗万象"))


def build_html_report(profile: dict) -> str:
    """Generate a self-contained dark-theme HTML dashboard listening report."""
    period = profile.get("period", "weekly")
    generated_at = profile.get("generated_at", datetime.datetime.now())
    days = _PERIOD_DAYS.get(period, 7)
    start = (generated_at - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    end = generated_at.strftime("%Y-%m-%d")
    label = _PERIOD_LABELS.get(period, "听歌报告")
    play_count = profile.get("play_count", 0)
    top_artists = profile.get("top_artists", [])
    top_genres = profile.get("top_genres", [])
    language_pref = profile.get("language_pref", {})
    recent_trend = profile.get("recent_trend", [])
    stable_pref = profile.get("stable_pref", [])
    declining_pref = profile.get("declining_pref", [])
    time_pattern = profile.get("time_pattern", {})
    top_search_terms = profile.get("top_search_terms", [])
    loved_artists = profile.get("loved_artists", [])
    tracks_by_artist = profile.get("tracks_by_artist", {})
    tracks_by_genre = profile.get("tracks_by_genre", {})
    unique_artist_count = profile.get("unique_artist_count", 0)
    estimated_hours = profile.get("estimated_hours", 0.0)
    peak_band = profile.get("peak_band", "night")
    band_track_counts = profile.get("band_track_counts", {})
    daily_plays = profile.get("daily_plays", {})
    personality_scores = profile.get("personality_scores", {})
    trend_detail = profile.get("trend_detail", {})
    queries = build_recommendation_queries(profile)
    p_emoji, p_title, p_desc = _music_personality(profile)

    _PEAK_LABELS = {
        "morning": "🌅 早晨",
        "afternoon": "☀️ 下午",
        "evening": "🌆 傍晚",
        "night": "🌙 深夜",
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
    summary = (
        "，".join(summary_parts) + "。"
        if summary_parts
        else (f"本{_PERIOD_ZH.get(period, '周')}共播放 {play_count} 首，继续保持！")
    )

    # ── JSON for modal drill-down ─────────────────────────────────────────────
    track_data_json = (
        json.dumps(
            {"artists": tracks_by_artist, "genres": tracks_by_genre},
            ensure_ascii=False,
        )
        .replace("</script>", "<\\/script>")
        .replace("<!--", "<\\!--")
    )

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
                f"</div></div>"
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
                f"{LABELS.get(lang, lang)} {int(val * 100)}%</text>"
                f"</g>"
            )
        total_h = legend_top + len(items) * 20 + 4
        return (
            f'<svg width="160" height="{total_h}"'
            f' style="overflow:visible;font-family:monospace">'
            f"{''.join(paths)}"
            f'<text x="{cx}" y="{cy - 5}" text-anchor="middle" fill="#a78bfa"'
            f' font-size="15" font-weight="bold">{dom_pct}%</text>'
            f'<text x="{cx}" y="{cy + 12}" text-anchor="middle" fill="#cec8bc"'
            f' font-size="11">{LABELS.get(dom_lang, dom_lang)}</text>'
            f"{''.join(legend)}</svg>"
        )

    # ── Helper: daily plays bar chart ─────────────────────────────────────────
    def _daily_chart_html(plays: dict, p: str) -> str:
        if not plays:
            return '<p style="color:#68687a;font-size:12px;margin:0">暂无数据</p>'
        _DAY_CN = {
            "Mon": "周一",
            "Tue": "周二",
            "Wed": "周三",
            "Thu": "周四",
            "Fri": "周五",
            "Sat": "周六",
            "Sun": "周日",
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
            lbl = html.escape(_label(k)[:5])
            bars.append(
                f'<div style="display:flex;flex-direction:column;align-items:center;flex:1;gap:2px">'
                f'<div style="width:100%;height:60px;display:flex;align-items:flex-end">'
                f'<div style="width:100%;height:{bar_h}px;background:#8b5cf6;opacity:.8;'
                f'border-radius:2px 2px 0 0" title="{lbl}: {v}首"></div>'
                f"</div>"
                f'<span style="font-size:9px;color:#68687a;white-space:nowrap;'
                f'overflow:hidden;text-overflow:ellipsis;max-width:28px">{lbl}</span>'
                f"</div>"
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
                f"{html.escape(term)}</span>"
            )
        return f'<div style="line-height:2">{"".join(tags)}</div>'

    # ── Helper: time band heatmap ─────────────────────────────────────────────
    def _time_heatmap_html(tp: dict, btc: dict) -> str:
        bands = [
            ("morning", "🌅", "早晨"),
            ("afternoon", "☀️", "下午"),
            ("evening", "🌆", "傍晚"),
            ("night", "🌙", "深夜"),
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
                f"border-radius:8px;display:flex;align-items:center;"
                f'justify-content:center;font-size:18px">{emoji}</div>'
                f'<span style="font-size:10px;color:#68687a">{short}</span>'
                f'<div style="display:flex;flex-wrap:wrap;gap:2px;justify-content:center">'
                f"{genre_tags}</div>"
                f"</div>"
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
                f"align-items:center;padding:5px 0;"
                f'border-bottom:1px solid rgba(139,92,246,.1)">'
                f'<span style="font-size:12px;color:{color};font-family:monospace">'
                f"{html.escape(artist)}</span>"
                f'<span style="font-size:11px;color:#68687a">{count} 次</span>'
                f"</div>"
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
                    f"{sign}{pct}%</span>"
                )
            else:
                badge = ""
            color = "#a78bfa"
        return (
            f'<div style="display:flex;align-items:center;margin-bottom:4px">'
            f'<span style="font-size:12px;color:{color};font-family:monospace">'
            f"{html.escape(genre)}</span>{badge}"
            f"</div>"
        )

    def _trends_col(title: str, items: list, direction: str, header_color: str) -> str:
        if not items:
            return (
                f"<div>"
                f'<div style="font-size:10px;color:{header_color};'
                f'letter-spacing:.08em;margin-bottom:8px">{title}</div>'
                f'<span style="font-size:11px;color:#68687a">—</span>'
                f"</div>"
            )
        pills = "".join(_trend_pill(g, direction) for g in items[:3])
        return (
            f"<div>"
            f'<div style="font-size:10px;color:{header_color};'
            f'letter-spacing:.08em;margin-bottom:8px">{title}</div>'
            f"{pills}"
            f"</div>"
        )

    trends_section = (
        f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">'
        f"{_trends_col('↑ 新增', recent_trend, 'new', '#16a34a')}"
        f"{_trends_col('→ 稳定', stable_pref, 'stable', '#a78bfa')}"
        f"{_trends_col('↓ 下降', declining_pref, 'gone', '#b91c1c')}"
        f"</div>"
    )

    # ── Helper: pentagon radar SVG ────────────────────────────────────────────
    def _radar_svg(scores: dict) -> str:
        dims = [
            ("focus", "专注力"),
            ("explore", "探索欲"),
            ("mood", "情绪"),
            ("night_owl", "夜猫"),
            ("loyalty", "忠诚"),
        ]
        N = len(dims)
        cx, cy, R = 100, 105, 60
        label_R = R + 22

        def pt(i: int, ratio: float) -> tuple[float, float]:
            angle = -math.pi / 2 + i * 2 * math.pi / N
            return cx + ratio * R * math.cos(angle), cy + ratio * R * math.sin(angle)

        def lpt(i: int) -> tuple[float, float]:
            angle = -math.pi / 2 + i * 2 * math.pi / N
            return cx + label_R * math.cos(angle), cy + label_R * math.sin(angle)

        grid_paths = []
        for level in (0.33, 0.67, 1.0):
            pts_str = " ".join(f"{pt(i, level)[0]:.1f},{pt(i, level)[1]:.1f}" for i in range(N))
            op = "0.12" if level < 1.0 else "0.25"
            grid_paths.append(
                f'<polygon points="{pts_str}" fill="none" stroke="#8b5cf6" stroke-width="1" opacity="{op}"/>'
            )

        spokes = []
        for i in range(N):
            x, y = pt(i, 1.0)
            spokes.append(
                f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}"'
                f' stroke="#8b5cf6" stroke-width="1" opacity="0.15"/>'
            )

        data_pts = " ".join(
            f"{pt(i, scores.get(k, 0) / 100)[0]:.1f},{pt(i, scores.get(k, 0) / 100)[1]:.1f}"
            for i, (k, _) in enumerate(dims)
        )
        data_poly = f'<polygon points="{data_pts}" fill="rgba(139,92,246,0.3)" stroke="#8b5cf6" stroke-width="2"/>'

        dots = []
        for i, (k, _) in enumerate(dims):
            dx, dy = pt(i, scores.get(k, 0) / 100)
            dots.append(f'<circle cx="{dx:.1f}" cy="{dy:.1f}" r="3" fill="#8b5cf6"/>')

        labels = []
        for i, (_, lbl) in enumerate(dims):
            lx, ly = lpt(i)
            labels.append(
                f'<text x="{lx:.0f}" y="{ly:.0f}" text-anchor="middle"'
                f' fill="#cec8bc" font-size="10" font-family="monospace">{lbl}</text>'
            )

        total_h = int(cy + R + label_R - R + 20)
        return (
            f'<svg width="200" height="{total_h}"'
            f' style="overflow:visible;font-family:monospace">'
            + "".join(grid_paths)
            + "".join(spokes)
            + data_poly
            + "".join(dots)
            + "".join(labels)
            + "</svg>"
        )

    # ── Radar score bars (right side of radar card) ───────────────────────────
    _DIM_LABELS = {
        "focus": "专注力",
        "explore": "探索欲",
        "mood": "情绪起伏",
        "night_owl": "夜猫指数",
        "loyalty": "忠诚度",
    }
    radar_scores_html = "".join(
        f'<div style="margin-bottom:8px">'
        f'<div style="display:flex;justify-content:space-between;'
        f'font-size:11px;margin-bottom:3px">'
        f'<span style="color:#cec8bc">{_DIM_LABELS[k]}</span>'
        f'<span style="color:#a78bfa">{personality_scores.get(k, 0)}</span>'
        f"</div>"
        f'<div style="height:5px;background:rgba(139,92,246,.15);border-radius:3px;overflow:hidden">'
        f'<div style="width:{personality_scores.get(k, 0)}%;height:100%;'
        f'background:#8b5cf6;border-radius:3px"></div>'
        f"</div>"
        f"</div>"
        for k in ("focus", "explore", "mood", "night_owl", "loyalty")
    )

    # ── Recommendation cards ──────────────────────────────────────────────────
    rec_cards = "".join(
        f'<div class="rec-card"><span class="rec-n">{i}</span><span class="rec-q">{html.escape(q)}</span></div>'
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
        "function esc(s){var d=document.createElement('div');d.textContent=String(s);return d.innerHTML;}"
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
        'rows+=\'<div class="modal-row"><span class="modal-track">\'+esc(d.t)+\'</span>'
        "<span class=\"modal-sub\">'+esc(d.c)+'次</span></div>';}"
        "else{"
        'rows+=\'<div class="modal-row"><span class="modal-track">\'+esc(d.t)+\'</span>'
        "<span class=\"modal-sub\">'+esc(d.a)+'</span></div>';}}"
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
    <div class="card"><div class="ctitle">🎤 常听歌手</div>{_bar_html(top_artists, "artist")}</div>
    <div class="card"><div class="ctitle">🎵 主要曲风</div>{_bar_html(top_genres, "genre")}</div>
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
