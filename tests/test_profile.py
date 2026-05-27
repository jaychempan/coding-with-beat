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
