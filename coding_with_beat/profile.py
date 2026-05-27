# coding_with_beat/profile.py
"""User music profile: analysis, report generation, and recommendation queries."""
from __future__ import annotations

import datetime
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
    language_pref = {k: round(v / total, 2) for k, v in lang_counter.most_common()}

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
