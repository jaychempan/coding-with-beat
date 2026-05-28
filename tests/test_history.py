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


# ── apple_music.play_history ───────────────────────────────────────────────────

def test_play_history_parses_applescript_output():
    import datetime
    from unittest.mock import patch
    from coding_with_beat.sources.apple_music import AppleMusic as AppleMusicSource

    fake_osa_output = (
        "Clair de Lune|||Debussy|||Suite bergamasque|||5|||3\n"
        "夜曲|||周杰伦|||十一月的萧邦|||12|||0\n"
    )

    with patch("coding_with_beat.sources.apple_music._osa", return_value=fake_osa_output):
        src = AppleMusicSource()
        result = src.play_history(window_days=14, limit=50)

    assert len(result) == 2
    assert result[0]["title"] == "Clair de Lune"
    assert result[0]["artist"] == "Debussy"
    assert result[0]["played_count"] == 5
    assert isinstance(result[0]["ts"], datetime.datetime)
    assert result[1]["title"] == "夜曲"
    assert result[1]["played_count"] == 12


def test_play_history_returns_empty_on_applescript_error():
    from unittest.mock import patch
    from coding_with_beat.sources.apple_music import AppleMusic as AppleMusicSource

    with patch("coding_with_beat.sources.apple_music._osa", side_effect=RuntimeError("fail")):
        src = AppleMusicSource()
        result = src.play_history()

    assert result == []


# ── server._refresh_now_playing writes history for non-AM ─────────────────────

def test_refresh_now_playing_writes_history_for_non_am_source(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import MagicMock, patch

    monkeypatch.setattr(history, "_LOG_FILE", tmp_path / "history.log")
    monkeypatch.setattr(history, "ensure_dirs", lambda: None)

    fake_np = SimpleNamespace(
        title="New Song", artist="Artist", album="Album",
        duration=180.0, position=0.0, playing=True,
        artwork_path=None, source="qq_music", unsupported_reason=None,
    )
    fake_state = SimpleNamespace(
        source="qq_music",
        track=SimpleNamespace(
            title="Old Song", artist="Old Artist", album="Old Album",
            duration=200.0, position=0.0, artwork_path=None,
            source="qq_music", lyrics_key="", lyrics_text="",
            lyrics_pending=False, position_sampled_at=0.0,
        ),
        playing=False,
    )

    with (
        patch("coding_with_beat.server.state.load", return_value=fake_state),
        patch("coding_with_beat.server.state.save"),
        patch("coding_with_beat.server.get_source") as mock_gs,
    ):
        src = MagicMock()
        src.now_playing.return_value = fake_np
        mock_gs.return_value = src
        from coding_with_beat.server import _refresh_now_playing
        _refresh_now_playing()

    entries = history.read()
    assert len(entries) == 1
    assert entries[0]["title"] == "New Song"


def test_refresh_now_playing_skips_history_for_apple_music(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import MagicMock, patch

    monkeypatch.setattr(history, "_LOG_FILE", tmp_path / "history.log")
    monkeypatch.setattr(history, "ensure_dirs", lambda: None)

    fake_np = SimpleNamespace(
        title="New Song", artist="Artist", album="Album",
        duration=180.0, position=0.0, playing=True,
        artwork_path=None, source="apple_music", unsupported_reason=None,
    )
    fake_state = SimpleNamespace(
        source="apple_music",
        track=SimpleNamespace(
            title="Old Song", artist="Old Artist", album="Old Album",
            duration=200.0, position=0.0, artwork_path=None,
            source="apple_music", lyrics_key="", lyrics_text="",
            lyrics_pending=False, position_sampled_at=0.0,
        ),
        playing=False,
    )

    with (
        patch("coding_with_beat.server.state.load", return_value=fake_state),
        patch("coding_with_beat.server.state.save"),
        patch("coding_with_beat.server.get_source") as mock_gs,
    ):
        src = MagicMock()
        src.now_playing.return_value = fake_np
        mock_gs.return_value = src
        from coding_with_beat.server import _refresh_now_playing
        _refresh_now_playing()

    assert not (tmp_path / "history.log").exists()


# ── list_history MCP tool ─────────────────────────────────────────────────────

def test_list_history_apple_music_source():
    import asyncio
    import datetime
    from types import SimpleNamespace
    from unittest.mock import MagicMock, patch

    fake_tracks = [
        {"title": "天空之城", "artist": "久石譲", "album": "OST", "played_count": 9, "ts": datetime.datetime.now()},
        {"title": "夜曲", "artist": "周杰伦", "album": "十一月的萧邦", "played_count": 3, "ts": datetime.datetime.now()},
    ]

    with (
        patch("coding_with_beat.server.state.load",
              return_value=SimpleNamespace(source="apple_music")),
        patch("coding_with_beat.server.get_source") as mock_gs,
    ):
        src = MagicMock()
        src.play_history.return_value = fake_tracks
        mock_gs.return_value = src
        from coding_with_beat.server import list_history
        result = asyncio.run(list_history())

    assert "天空之城" in result
    assert "9次播放" in result
    assert "夜曲" in result
    assert "3次播放" in result


def test_list_history_empty_returns_friendly_message():
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import MagicMock, patch

    with (
        patch("coding_with_beat.server.state.load",
              return_value=SimpleNamespace(source="apple_music")),
        patch("coding_with_beat.server.get_source") as mock_gs,
    ):
        src = MagicMock()
        src.play_history.return_value = []
        mock_gs.return_value = src
        from coding_with_beat.server import list_history
        result = asyncio.run(list_history())

    assert "还没有" in result


def test_list_history_non_am_reads_log(tmp_path, monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import patch

    monkeypatch.setattr(history, "_LOG_FILE", tmp_path / "history.log")
    monkeypatch.setattr(history, "ensure_dirs", lambda: None)
    history.write("Log Track", "Log Artist", "Log Album")

    with patch("coding_with_beat.server.state.load",
               return_value=SimpleNamespace(source="local")):
        from coding_with_beat.server import list_history
        result = asyncio.run(list_history())

    assert "Log Track" in result


# ── history_search MCP tool ───────────────────────────────────────────────────

def test_history_search_builds_queries_from_history():
    import asyncio
    import datetime
    from types import SimpleNamespace
    from unittest.mock import MagicMock, patch

    recent_tracks = [
        {"title": "Nocturne Op.9", "artist": "Chopin", "album": "Nocturnes", "ts": datetime.datetime.now()},
        {"title": "Gymnopédie", "artist": "Satie", "album": "Classical Piano", "ts": datetime.datetime.now()},
    ]

    captured_queries: list = []

    async def _fake_multi_angle(queries, **kwargs):
        captured_queries.extend(queries)
        return "1. Result Track — Artist"

    with (
        patch("coding_with_beat.server.state.load",
              return_value=SimpleNamespace(source="apple_music")),
        patch("coding_with_beat.server.get_source") as mock_gs,
        patch("coding_with_beat.server._multi_angle_search", side_effect=_fake_multi_angle),
    ):
        src = MagicMock()
        src.play_history.return_value = recent_tracks
        mock_gs.return_value = src
        from coding_with_beat.server import history_search
        asyncio.run(history_search())

    assert len(captured_queries) >= 1
    assert any("classical" in q.lower() or "piano" in q.lower() for q in captured_queries)


def test_history_search_empty_history_returns_message():
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import MagicMock, patch

    with (
        patch("coding_with_beat.server.state.load",
              return_value=SimpleNamespace(source="apple_music")),
        patch("coding_with_beat.server.get_source") as mock_gs,
    ):
        src = MagicMock()
        src.play_history.return_value = []
        mock_gs.return_value = src
        from coding_with_beat.server import history_search
        result = asyncio.run(history_search())

    assert "还没有" in result


# ── write_search / read_search ────────────────────────────────────────────────

def test_read_search_returns_empty_when_no_log(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "_SEARCH_LOG_FILE", tmp_path / "search_history.log")
    assert history.read_search() == []


def test_write_search_and_read_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "_SEARCH_LOG_FILE", tmp_path / "search_history.log")
    monkeypatch.setattr(history, "ensure_dirs", lambda: None)
    history.write_search("lofi jazz coding instrumental focus")
    history.write_search("synthwave night drive neon")
    records = history.read_search()
    assert len(records) == 2
    # most-recent first
    assert records[0]["query"] == "synthwave night drive neon"
    assert records[1]["query"] == "lofi jazz coding instrumental focus"
    assert isinstance(records[0]["ts"], datetime.datetime)


def test_write_search_skips_empty_query(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "_SEARCH_LOG_FILE", tmp_path / "search_history.log")
    monkeypatch.setattr(history, "ensure_dirs", lambda: None)
    history.write_search("")
    assert not (tmp_path / "search_history.log").exists()


def test_read_search_respects_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "_SEARCH_LOG_FILE", tmp_path / "search_history.log")
    monkeypatch.setattr(history, "ensure_dirs", lambda: None)
    for i in range(10):
        history.write_search(f"query {i}")
    assert len(history.read_search(limit=3)) == 3
