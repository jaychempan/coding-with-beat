import asyncio
from types import SimpleNamespace
from unittest import mock

from coding_with_beat import server
from coding_with_beat.server import _label_for_query, _sort_by_source, _source_tag


def _hit(title, artist, source):
    return {"title": title, "artist": artist, "album": "Album", "source": source}


def _run(coro):
    return asyncio.run(coro)


def test_source_tag_loved():
    assert _source_tag("loved") == " [♥ 喜欢]"


def test_source_tag_library():
    assert _source_tag("library") == " [资料库]"


def test_source_tag_local():
    assert _source_tag("local") == " [本地]"


def test_source_tag_apple_music():
    assert _source_tag("apple_music") == " [Apple Music]"


def test_source_tag_unknown():
    assert _source_tag("") == ""


def test_sort_by_source_order():
    tracks = [
        {"title": "C", "source": "apple_music"},
        {"title": "A", "source": "loved"},
        {"title": "D", "source": "local"},
        {"title": "B", "source": "library"},
    ]
    result = _sort_by_source(tracks)
    assert [t["title"] for t in result] == ["A", "B", "D", "C"]


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


@mock.patch("coding_with_beat.server._write_active_mode")
@mock.patch("coding_with_beat.server._write_queue_file")
@mock.patch("coding_with_beat.server.get_source")
def test_multi_angle_global_numbering(mock_gs, mock_wqf, mock_wam):
    """Three queries × 2 tracks each → output numbers 1–6 sequentially."""

    def fake_get_source(name):
        src = mock.MagicMock()
        if name == "apple_music":
            src.search.side_effect = lambda q, lim: [
                _hit(f"{q[:4]}-am-1", "Artist", "apple_music"),
                _hit(f"{q[:4]}-am-2", "Artist", "apple_music"),
            ]
        else:
            src.search.return_value = []
        return src

    mock_gs.side_effect = fake_get_source

    from coding_with_beat.server import _multi_angle_search

    result = _run(_multi_angle_search(["lofi hip hop", "jazz cozy rain", "synthwave night"]))

    # All 6 tracks should appear globally numbered
    for n in range(1, 7):
        assert f"{n}." in result


@mock.patch("coding_with_beat.server._write_active_mode")
@mock.patch("coding_with_beat.server._write_queue_file")
@mock.patch("coding_with_beat.server.get_source")
def test_multi_angle_single_queue_write(mock_gs, mock_wqf, mock_wam):
    """Queue is written exactly once regardless of query count."""

    def fake_get_source(name):
        src = mock.MagicMock()
        src.search.return_value = [_hit("Track", "Artist", "apple_music")]
        return src

    mock_gs.side_effect = fake_get_source

    from coding_with_beat.server import _multi_angle_search

    _run(_multi_angle_search(["lofi", "jazz", "synthwave"]))

    mock_wqf.assert_called_once()
    args = mock_wqf.call_args[0]
    assert args[0] == "search"


@mock.patch("coding_with_beat.server._write_active_mode")
@mock.patch("coding_with_beat.server._write_queue_file")
@mock.patch("coding_with_beat.server.get_source")
def test_multi_angle_global_dedup(mock_gs, mock_wqf, mock_wam):
    """Same track returned by two queries appears only once."""
    dup = _hit("Same Song", "Same Artist", "apple_music")

    def fake_get_source(name):
        src = mock.MagicMock()
        if name == "apple_music":
            src.search.return_value = [dup]
        else:
            src.search.return_value = []
        return src

    mock_gs.side_effect = fake_get_source

    from coding_with_beat.server import _multi_angle_search

    result = _run(_multi_angle_search(["lofi", "jazz"]))

    assert result.count("Same Song — Same Artist") == 1


@mock.patch("coding_with_beat.server._write_active_mode")
@mock.patch("coding_with_beat.server._write_queue_file")
@mock.patch("coding_with_beat.server.get_source")
def test_multi_angle_label_in_output(mock_gs, mock_wqf, mock_wam):
    """Each group header appears in the output (distinct tracks so neither group is empty after dedup)."""
    tracks_by_query = {
        "lofi hip hop": [_hit("Lofi Track", "Artist A", "library")],
        "synthwave retrowave": [_hit("Synth Track", "Artist B", "library")],
    }

    def fake_get_source(name):
        src = mock.MagicMock()
        if name == "apple_music":
            src.search.side_effect = lambda q, lim: tracks_by_query.get(q, [])
        else:
            src.search.return_value = []
        return src

    mock_gs.side_effect = fake_get_source

    from coding_with_beat.server import _multi_angle_search

    result = _run(_multi_angle_search(["lofi hip hop", "synthwave retrowave"]))

    assert "🎧" in result  # lofi label
    assert "🌆" in result  # synthwave label


@mock.patch("coding_with_beat.server._write_active_mode")
@mock.patch("coding_with_beat.server._write_queue_file")
@mock.patch("coding_with_beat.server.get_source")
def test_multi_angle_queue_track_order_matches_output(mock_gs, mock_wqf, mock_wam):
    """Tracks in the queue are in the same order as the global numbering."""
    a = _hit("Alpha", "Artist", "library")
    b = _hit("Beta", "Artist", "library")
    c = _hit("Gamma", "Artist", "library")

    tracks_by_query = {"q1": [a], "q2": [b], "q3": [c]}

    def fake_get_source(name):
        src = mock.MagicMock()
        if name == "apple_music":
            src.search.side_effect = lambda q, lim: tracks_by_query.get(q, [])
        else:
            src.search.return_value = []
        return src

    mock_gs.side_effect = fake_get_source

    from coding_with_beat.server import _multi_angle_search

    _run(_multi_angle_search(["q1", "q2", "q3"]))

    written_tracks = mock_wqf.call_args[0][1]["tracks"]
    titles = [t["title"] for t in written_tracks]
    assert titles == ["Alpha", "Beta", "Gamma"]


@mock.patch("coding_with_beat.server._multi_angle_search")
def test_smart_search_delegates_to_multi_angle_when_queries_given(mock_multi):
    """When queries= is passed, smart_search delegates to _multi_angle_search."""
    import asyncio

    async def fake_multi(queries, limit_per_query=6, label=None):
        return "mocked result"

    mock_multi.side_effect = fake_multi

    result = asyncio.run(server.smart_search(queries=["lofi hip hop", "jazz cozy", "synthwave"]))
    mock_multi.assert_called_once_with(
        ["lofi hip hop", "jazz cozy", "synthwave"], limit_per_query=6, label="Search · lofi hip hop"
    )
    assert result == "mocked result"


@mock.patch("coding_with_beat.server._write_active_mode")
@mock.patch("coding_with_beat.server._write_queue_file")
@mock.patch("coding_with_beat.server.state")
@mock.patch("coding_with_beat.server.get_source")
def test_smart_search_loved_ranked_first_and_tagged(mock_gs, mock_state, mock_wqf, mock_wam):
    mock_state.load.return_value = SimpleNamespace(source="apple_music")

    am_hits = [
        _hit("Normal Song", "Artist B", "library"),
        _hit("Loved Song", "Artist A", "loved"),
        _hit("Catalog Song", "Artist C", "apple_music"),
    ]

    def fake_get_source(name):
        src = mock.MagicMock()
        src.search.return_value = am_hits if name == "apple_music" else []
        return src

    mock_gs.side_effect = fake_get_source

    result = _run(server.smart_search("late night chill"))

    lines = [line for line in result.splitlines() if line.startswith(("1.", "2.", "3."))]
    assert lines[0].startswith("1.") and "Loved Song" in lines[0]
    assert "[♥ 喜欢]" in lines[0]
    assert "[资料库]" in lines[1]
    assert "[Apple Music]" in lines[2]


@mock.patch("coding_with_beat.server._write_active_mode")
@mock.patch("coding_with_beat.server._write_queue_file")
@mock.patch("coding_with_beat.server.state")
@mock.patch("coding_with_beat.server.get_source")
def test_list_loved_returns_numbered_loved_tracks(mock_gs, mock_state, mock_wqf, mock_wam):
    mock_state.load.return_value = SimpleNamespace(source="apple_music")
    src = mock.MagicMock()
    src.list_loved.return_value = [
        {"title": "Heart Song", "artist": "DJ A", "album": "Vol 1", "source": "loved"},
        {"title": "Fave Track", "artist": "DJ B", "album": "Vol 2", "source": "loved"},
    ]
    mock_gs.return_value = src

    result = _run(server.list_loved())

    assert "1. Heart Song" in result
    assert "[♥ 喜欢]" in result
    assert "2. Fave Track" in result


@mock.patch("coding_with_beat.server._write_active_mode")
@mock.patch("coding_with_beat.server._write_queue_file")
@mock.patch("coding_with_beat.server.state")
@mock.patch("coding_with_beat.server.get_source")
def test_search_loved_returns_numbered_results(mock_gs, mock_state, mock_wqf, mock_wam):
    mock_state.load.return_value = SimpleNamespace(source="apple_music")
    src = mock.MagicMock()
    src.search_loved.return_value = [
        {"title": "Rain Song", "artist": "Piano", "album": "Calm", "source": "loved"},
    ]
    mock_gs.return_value = src

    result = _run(server.search_loved("rain"))

    assert "1. Rain Song" in result
    assert "[♥ 喜欢]" in result
    src.search_loved.assert_called_once_with("rain", 8)


@mock.patch("coding_with_beat.server._write_active_mode")
@mock.patch("coding_with_beat.server._write_queue_file")
@mock.patch("coding_with_beat.server.state")
@mock.patch("coding_with_beat.server.get_source")
def test_search_loved_no_results(mock_gs, mock_state, mock_wqf, mock_wam):
    mock_state.load.return_value = SimpleNamespace(source="apple_music")
    src = mock.MagicMock()
    src.search_loved.return_value = []
    mock_gs.return_value = src

    result = _run(server.search_loved("zzz"))
    assert "no loved tracks" in result
