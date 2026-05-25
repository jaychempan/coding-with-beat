# tests/test_history.py
import datetime
from pathlib import Path
from unittest import mock

import pytest

from coding_with_beat import history


# ── write / read ──────────────────────────────────────────────────────────────

def test_read_returns_empty_when_no_log(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "_LOG_FILE", tmp_path / "history.log")
    assert history.read() == []


def test_write_and_read_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "_LOG_FILE", tmp_path / "history.log")
    monkeypatch.setattr(history, "ensure_dirs", lambda: None)
    history.write("Clair de Lune", "Debussy", "Suite bergamasque")
    history.write("夜曲", "周杰伦", "十一月的萧邦")
    entries = history.read()
    assert len(entries) == 2
    # most-recent first
    assert entries[0]["title"] == "夜曲"
    assert entries[0]["artist"] == "周杰伦"
    assert entries[1]["title"] == "Clair de Lune"


def test_write_skips_empty_title(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "_LOG_FILE", tmp_path / "history.log")
    monkeypatch.setattr(history, "ensure_dirs", lambda: None)
    history.write("", "Artist", "Album")
    assert not (tmp_path / "history.log").exists()


def test_read_respects_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "_LOG_FILE", tmp_path / "history.log")
    monkeypatch.setattr(history, "ensure_dirs", lambda: None)
    for i in range(10):
        history.write(f"Track {i}", "Artist", "Album")
    assert len(history.read(limit=3)) == 3


# ── summarize ─────────────────────────────────────────────────────────────────

def _make_track(title, artist, album="Album", days_ago=1):
    ts = datetime.datetime.now() - datetime.timedelta(days=days_ago)
    return {"title": title, "artist": artist, "album": album, "ts": ts}


def test_summarize_top_artists():
    tracks = [
        _make_track("Song A", "周杰伦"),
        _make_track("Song B", "周杰伦"),
        _make_track("Song C", "林俊杰"),
    ]
    result = history.summarize(tracks)
    assert result["top_artists"][0] == ("周杰伦", 2)
    assert result["top_artists"][1] == ("林俊杰", 1)


def test_summarize_style_tags_classical():
    tracks = [_make_track("Nocturne", "Chopin", "Nocturnes")]
    result = history.summarize(tracks)
    assert "classical" in result["style_tags"]


def test_summarize_style_tags_jazz():
    tracks = [_make_track("Blue Note", "Artist", "Jazz Sessions")]
    result = history.summarize(tracks)
    assert "jazz" in result["style_tags"]


def test_summarize_unheard_candidates():
    recent = [_make_track("New Song", "Artist A", days_ago=3)]
    older = [_make_track("Old Song", "Artist B", days_ago=30)]
    result = history.summarize(recent + older, window_days=14)
    titles = [t["title"] for t in result["unheard_candidates"]]
    assert "Old Song" in titles
    assert "New Song" not in titles


def test_summarize_empty_tracks():
    result = history.summarize([])
    assert result["top_artists"] == []
    assert result["style_tags"] == []
    assert result["unheard_candidates"] == []


def test_summarize_discards_corrupt_ts_string():
    """Tracks with unparseable ts strings should be silently discarded."""
    tracks = [
        {"title": "Good", "artist": "A", "album": "X", "ts": datetime.datetime.now()},
        {"title": "Bad", "artist": "B", "album": "Y", "ts": "not-a-date"},
    ]
    result = history.summarize(tracks)
    # "Bad" discarded — only "Good" counted
    assert result["top_artists"] == [("A", 1)]


def test_summarize_question_mark_artist_not_in_recent_artists():
    """'?' placeholder artist should not suppress unheard candidates."""
    recent = [_make_track("Song", "?", days_ago=1)]   # recent entry with no real artist
    older = [_make_track("Old Song", "?", days_ago=30)]  # older entry also with '?'
    result = history.summarize(recent + older, window_days=14)
    # '?' artist should not block unheard_candidates for other '?' entries
    # (since '?' is excluded from recent_artists_lower)
    titles = [t["title"] for t in result["unheard_candidates"]]
    assert "Old Song" in titles


def test_read_malformed_lines_are_skipped(tmp_path, monkeypatch):
    """Lines with fewer than 4 pipe-separated parts are silently skipped."""
    monkeypatch.setattr(history, "_LOG_FILE", tmp_path / "history.log")
    monkeypatch.setattr(history, "ensure_dirs", lambda: None)
    log = tmp_path / "history.log"
    log.write_text(
        "not-a-date | Track | Artist | Album\n"
        "2026-05-25 10:00:00 | Good Track | Artist | Album\n"
        "malformed line with no pipes\n",
        encoding="utf-8",
    )
    entries = history.read()
    assert len(entries) == 1
    assert entries[0]["title"] == "Good Track"
