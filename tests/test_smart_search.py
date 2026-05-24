import asyncio
from types import SimpleNamespace
from unittest import mock

from coding_with_beat import server


def _hit(title, artist, source):
    return {"title": title, "artist": artist, "album": "Album", "source": source}


def _run(coro):
    return asyncio.run(coro)


@mock.patch("coding_with_beat.server._write_active_mode")
@mock.patch("coding_with_beat.server._write_queue_file")
@mock.patch("coding_with_beat.server.state")
@mock.patch("coding_with_beat.server.get_source")
def test_smart_search_annotates_sources(mock_gs, mock_state, mock_wqf, mock_wam):
    mock_state.load.return_value = SimpleNamespace(source="apple_music")

    am_hits = [
        _hit("雨的印记", "李闰珉", "library"),
        _hit("Quiet Library", "FM STAR", "apple_music"),
    ]
    local_hits = [
        _hit("lofi study", "unknown", "local"),
    ]

    def fake_get_source(name):
        src = mock.MagicMock()
        if name == "apple_music":
            src.search.return_value = am_hits
        elif name == "local":
            src.search.return_value = local_hits
        return src

    mock_gs.side_effect = fake_get_source

    result = _run(server.smart_search("something chill for late night coding"))

    assert "雨的印记" in result
    assert "[资料库]" in result
    assert "Quiet Library" in result
    assert "[Apple Music]" in result
    assert "lofi study" in result
    assert "[本地]" in result


@mock.patch("coding_with_beat.server._write_active_mode")
@mock.patch("coding_with_beat.server._write_queue_file")
@mock.patch("coding_with_beat.server.state")
@mock.patch("coding_with_beat.server.get_source")
def test_smart_search_no_results(mock_gs, mock_state, mock_wqf, mock_wam):
    mock_state.load.return_value = SimpleNamespace(source="apple_music")

    def fake_get_source(name):
        src = mock.MagicMock()
        src.search.return_value = []
        return src

    mock_gs.side_effect = fake_get_source

    result = _run(server.smart_search("xyzzy nothing matches"))
    assert "no matches" in result


@mock.patch("coding_with_beat.server._write_active_mode")
@mock.patch("coding_with_beat.server._write_queue_file")
@mock.patch("coding_with_beat.server.state")
@mock.patch("coding_with_beat.server.get_source")
def test_smart_search_deduplicates(mock_gs, mock_state, mock_wqf, mock_wam):
    mock_state.load.return_value = SimpleNamespace(source="apple_music")

    dup = _hit("Song", "Artist", "library")

    def fake_get_source(name):
        src = mock.MagicMock()
        src.search.return_value = [dup]
        return src

    mock_gs.side_effect = fake_get_source

    result = _run(server.smart_search("song"))
    assert result.count("Song — Artist") == 1


@mock.patch("coding_with_beat.server._write_active_mode")
@mock.patch("coding_with_beat.server._write_queue_file")
@mock.patch("coding_with_beat.server.state")
@mock.patch("coding_with_beat.server.get_source")
def test_smart_search_writes_search_queue(mock_gs, mock_state, mock_wqf, mock_wam):
    mock_state.load.return_value = SimpleNamespace(source="apple_music")

    hits = [_hit("Track", "Artist", "library")]

    def fake_get_source(name):
        src = mock.MagicMock()
        src.search.return_value = hits if name == "apple_music" else []
        return src

    mock_gs.side_effect = fake_get_source

    _run(server.smart_search("something"))

    mock_wqf.assert_called_once()
    args = mock_wqf.call_args[0]
    assert args[0] == "search"
    assert len(args[1]["tracks"]) == 1


from coding_with_beat.server import _label_for_query


def test_label_lofi():
    assert _label_for_query("lofi hip hop late night coding") == "🎧 Lofi"


def test_label_jazz():
    assert _label_for_query("lofi jazz rain study") == "🎷 Jazz"


def test_label_synthwave():
    assert _label_for_query("synthwave retrowave night drive neon") == "🌆 Synthwave"


def test_label_fallback():
    # No keyword match → first three words title-cased
    assert _label_for_query("choral gospel choir ambient") == "Choral Gospel Choir"


def test_label_fallback_short():
    assert _label_for_query("ambient") == "Ambient"
