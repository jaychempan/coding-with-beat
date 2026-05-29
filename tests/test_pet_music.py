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


def test_errors_are_normalized():
    def fail(name, kwargs):
        raise RuntimeError("boom")

    client = PetMusicClient(call_tool=fail)
    result = client.play_number(1)
    assert result.ok is False
    assert "boom" in result.text
