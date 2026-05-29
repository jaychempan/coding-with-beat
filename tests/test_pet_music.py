from coding_with_beat.pet.music import PetMusicClient


def test_recommend_calls_smart_search_with_queries():
    client = PetMusicClient(call_tool=lambda name, kwargs: f"{name}:{kwargs['queries'][0]}")
    result = client.recommend(["lofi focus", "ambient"])
    assert result.ok is True
    assert result.text.startswith("smart_search:lofi focus")


def test_calls_mcp_with_explicit_timeout():
    calls = []

    def call_tool(name, kwargs, *, timeout):
        calls.append((name, kwargs, timeout))
        return "ok"

    client = PetMusicClient(call_tool=call_tool, timeout=12.5)
    result = client.play_number(1)

    assert result.ok is True
    assert calls == [("play_number", {"number": 1}, 12.5)]


def test_snapshot_uses_short_timeout_and_known_lyrics_key():
    calls = []

    def call_tool(name, kwargs, *, timeout):
        calls.append((name, kwargs, timeout))
        return '{"title":"Song"}'

    client = PetMusicClient(call_tool=call_tool)
    result = client.now_playing_snapshot("source\\0artist\\0album\\0title")

    assert result.ok is True
    assert calls == [
        (
            "now_playing_snapshot",
            {"known_lyrics_key": "source\\0artist\\0album\\0title"},
            1.5,
        )
    ]


def test_control_calls_named_cwb_tool():
    calls = []

    def call_tool(name, kwargs, *, timeout):
        calls.append((name, kwargs, timeout))
        return "liked"

    client = PetMusicClient(call_tool=call_tool, timeout=9.0)
    result = client.control("like_current", {})

    assert result.ok is True
    assert result.text == "liked"
    assert calls == [("like_current", {}, 9.0)]


def test_search_and_library_tools_call_cwb_tools():
    calls = []

    def call_tool(name, kwargs, *, timeout):
        calls.append((name, kwargs, timeout))
        return f"{name}:ok"

    client = PetMusicClient(call_tool=call_tool, timeout=9.0)

    assert client.search("周杰伦").text == "search:ok"
    assert client.list_library().text == "list_library:ok"
    assert client.search_loved("周杰伦").text == "search_loved:ok"
    assert client.list_loved().text == "list_loved:ok"
    assert client.list_playlists().text == "list_playlists:ok"
    assert client.play_playlist("Coding Beats").text == "play_playlist:ok"
    assert calls == [
        ("search", {"query": "周杰伦"}, 9.0),
        ("list_library", {"limit": 40}, 9.0),
        ("search_loved", {"query": "周杰伦"}, 9.0),
        ("list_loved", {"limit": 40}, 9.0),
        ("list_playlists", {}, 9.0),
        ("play_playlist", {"name": "Coding Beats"}, 9.0),
    ]


def test_errors_are_normalized():
    def fail(name, kwargs):
        raise RuntimeError("boom")

    client = PetMusicClient(call_tool=fail)
    result = client.play_number(1)
    assert result.ok is False
    assert "boom" in result.text
