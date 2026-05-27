# tests/test_profile.py
import datetime
from unittest import mock

import pytest

from coding_with_beat import history, profile


# ── helpers ───────────────────────────────────────────────────────────────────

def _track(title, artist, hours_ago, album="", played_count=1):
    ts = datetime.datetime.now() - datetime.timedelta(hours=hours_ago)
    return {
        "title": title, "artist": artist, "album": album,
        "ts": ts, "played_count": played_count,
    }


def _weekly_tracks():
    return [
        _track("Track 1", "Hans Zimmer", 10,  "lofi jazz ambient"),
        _track("Track 2", "Hans Zimmer", 20,  "lofi hip hop"),
        _track("Track 3", "Hans Zimmer", 30,  "lofi"),
        _track("Track 4", "周杰伦",       40,  "华语"),
        _track("Track 5", "周杰伦",       50,  "华语"),
        _track("Track 6", "ODESZA",       60,  "electronic"),
        _track("Track 7", "ODESZA",       80,  "electronic synthwave"),
        _track("Track 8", "Debussy",      100, "classical piano"),
        _track("Track 9", "Debussy",      110, "classical"),
        _track("Track 10", "Tycho",       120, "ambient"),
    ]


# ── build_profile ─────────────────────────────────────────────────────────────

def test_build_profile_raises_on_insufficient_history(monkeypatch):
    monkeypatch.setattr(history, "read", lambda limit=500: [])
    monkeypatch.setattr(history, "read_search", lambda limit=500: [])
    with mock.patch("coding_with_beat.profile.get_source", side_effect=Exception("no AM")):
        with pytest.raises(ValueError, match="insufficient_history"):
            profile.build_profile("weekly")


def test_build_profile_weekly_top_artists(monkeypatch):
    monkeypatch.setattr(history, "read", lambda limit=500: _weekly_tracks())
    monkeypatch.setattr(history, "read_search", lambda limit=500: [])
    with mock.patch("coding_with_beat.profile.get_source", side_effect=Exception("no AM")):
        prof = profile.build_profile("weekly")
    top_artist_names = [a for a, _ in prof["top_artists"]]
    assert "Hans Zimmer" in top_artist_names
    assert prof["play_count"] == 10


def test_build_profile_top_genres_detected(monkeypatch):
    monkeypatch.setattr(history, "read", lambda limit=500: _weekly_tracks())
    monkeypatch.setattr(history, "read_search", lambda limit=500: [])
    with mock.patch("coding_with_beat.profile.get_source", side_effect=Exception("no AM")):
        prof = profile.build_profile("weekly")
    genre_names = [g for g, _ in prof["top_genres"]]
    assert "lofi" in genre_names or "classical" in genre_names


def test_build_profile_period_days_filtering(monkeypatch):
    old_track = _track("Old Track", "Old Artist", 48)  # 48 hours ago, outside daily window
    new_track = _track("New Track", "New Artist", 1)   # 1 hour ago, inside daily window
    monkeypatch.setattr(history, "read", lambda limit=500: [old_track, new_track] * 5)
    monkeypatch.setattr(history, "read_search", lambda limit=500: [])
    with mock.patch("coding_with_beat.profile.get_source", side_effect=Exception("no AM")):
        prof = profile.build_profile("daily")
    artist_names = [a for a, _ in prof["top_artists"]]
    assert "New Artist" in artist_names
    assert "Old Artist" not in artist_names


def test_build_profile_language_pref_zh(monkeypatch):
    zh_tracks = [_track("夜曲", "周杰伦", i * 2, "华语") for i in range(8)]
    monkeypatch.setattr(history, "read", lambda limit=500: zh_tracks)
    monkeypatch.setattr(history, "read_search", lambda limit=500: [])
    with mock.patch("coding_with_beat.profile.get_source", side_effect=Exception("no AM")):
        prof = profile.build_profile("weekly")
    assert prof["language_pref"].get("zh", 0) > 0.5


def test_build_profile_search_terms_captured(monkeypatch):
    search_recs = [
        {"query": "lofi jazz coding focus instrumental", "ts": datetime.datetime.now() - datetime.timedelta(hours=1)},
        {"query": "lofi hip hop study", "ts": datetime.datetime.now() - datetime.timedelta(hours=2)},
    ]
    monkeypatch.setattr(history, "read", lambda limit=500: _weekly_tracks())
    monkeypatch.setattr(history, "read_search", lambda limit=500: search_recs)
    with mock.patch("coding_with_beat.profile.get_source", side_effect=Exception("no AM")):
        prof = profile.build_profile("weekly")
    term_keys = [t for t, _ in prof["top_search_terms"]]
    assert "lofi" in term_keys


def test_build_profile_returns_required_keys(monkeypatch):
    monkeypatch.setattr(history, "read", lambda limit=500: _weekly_tracks())
    monkeypatch.setattr(history, "read_search", lambda limit=500: [])
    with mock.patch("coding_with_beat.profile.get_source", side_effect=Exception("no AM")):
        prof = profile.build_profile("weekly")
    required = {
        "period", "generated_at", "play_count", "top_artists", "top_genres",
        "top_search_terms", "language_pref", "loved_artists",
        "recent_trend", "stable_pref", "declining_pref", "time_pattern",
    }
    assert required.issubset(prof.keys())


# ── build_report ──────────────────────────────────────────────────────────────

def _make_profile(overrides=None):
    now = datetime.datetime.now()
    base = {
        "period": "weekly",
        "generated_at": now,
        "play_count": 42,
        "top_artists": [("Hans Zimmer", 12), ("周杰伦", 8), ("ODESZA", 5)],
        "top_genres": [("lofi", 9), ("ambient", 6), ("classical", 4)],
        "top_search_terms": [("lofi", 5), ("coding", 4)],
        "language_pref": {"en": 0.6, "zh": 0.3, "instrumental": 0.1},
        "loved_artists": ["Hans Zimmer"],
        "recent_trend": ["synthwave"],
        "stable_pref": ["lofi", "ambient"],
        "declining_pref": ["华语"],
        "time_pattern": {"night": ["lofi", "ambient"], "afternoon": ["classical"]},
    }
    if overrides:
        base.update(overrides)
    return base


def test_build_report_contains_play_count():
    report = profile.build_report(_make_profile())
    assert "42" in report


def test_build_report_contains_top_artist():
    report = profile.build_report(_make_profile())
    assert "Hans Zimmer" in report


def test_build_report_contains_top_genre():
    report = profile.build_report(_make_profile())
    assert "lofi" in report


def test_build_report_contains_preference_changes():
    report = profile.build_report(_make_profile())
    assert "synthwave" in report   # recent_trend
    assert "华语" in report         # declining_pref


def test_build_report_contains_time_pattern():
    report = profile.build_report(_make_profile())
    assert "lofi" in report


def test_build_report_contains_summary_sentence():
    report = profile.build_report(_make_profile())
    assert "💬" in report


def test_build_report_all_periods():
    for period in ("daily", "weekly", "monthly", "yearly"):
        prof = _make_profile({"period": period})
        report = profile.build_report(prof)
        assert "📅" in report


def test_build_report_empty_trend_sections_hidden():
    prof = _make_profile({"recent_trend": [], "stable_pref": [], "declining_pref": []})
    report = profile.build_report(prof)
    # Should not crash and should still contain basic stats
    assert "42" in report


# ── build_recommendation_queries ──────────────────────────────────────────────

def test_build_recommendation_queries_returns_list_of_strings():
    queries = profile.build_recommendation_queries(_make_profile())
    assert isinstance(queries, list)
    assert all(isinstance(q, str) for q in queries)
    assert 1 <= len(queries) <= 3


def test_build_recommendation_queries_includes_stable_genre():
    prof = _make_profile({"stable_pref": ["lofi", "jazz"], "recent_trend": []})
    queries = profile.build_recommendation_queries(prof)
    assert any("lofi" in q or "jazz" in q for q in queries)


def test_build_recommendation_queries_includes_context():
    queries = profile.build_recommendation_queries(_make_profile(), context="写代码")
    assert any("写代码" in q for q in queries)


def test_build_recommendation_queries_fallback_when_no_trend():
    prof = _make_profile({"recent_trend": [], "top_genres": [("classical", 5), ("jazz", 3)]})
    queries = profile.build_recommendation_queries(prof)
    # slot 2 falls back to second top_genre
    assert any("jazz" in q or "classical" in q for q in queries)


def test_build_recommendation_queries_includes_top_artist():
    prof = _make_profile({"top_artists": [("Hans Zimmer", 10)]})
    queries = profile.build_recommendation_queries(prof)
    assert any("Hans Zimmer" in q for q in queries)


def test_build_recommendation_queries_not_empty_when_minimal_profile():
    prof = _make_profile({
        "stable_pref": [], "recent_trend": [],
        "top_genres": [("lofi", 3)], "top_artists": [],
    })
    queries = profile.build_recommendation_queries(prof)
    assert len(queries) >= 1


# ── build_html_report ─────────────────────────────────────────────────────────

def test_build_html_report_is_valid_html():
    html = profile.build_html_report(_make_profile())
    assert html.startswith("<!DOCTYPE html>")
    assert "</html>" in html


def test_build_html_report_contains_play_count():
    html = profile.build_html_report(_make_profile())
    assert "42" in html


def test_build_html_report_contains_top_artist():
    html_out = profile.build_html_report(_make_profile())
    assert "Hans Zimm" in html_out  # truncated in bar SVG or present in rec query


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
