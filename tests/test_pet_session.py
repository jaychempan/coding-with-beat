from types import SimpleNamespace

from coding_with_beat.pet.music import MusicResult
from coding_with_beat.pet.session import PetMusicSession


def state(**kwargs):
    base = {
        "playing": False,
        "dj_mood": "neutral",
        "vibe": "debug",
        "companion_failure_streak": 0,
        "last_tool_at": 0.0,
        "track": None,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


class FakeMusic:
    def __init__(self, recommend_ok=True, recommend_text="1. Night Owl - Luna\n2. Rain Debug - Soft Keys"):
        self.calls = []
        self.recommend_ok = recommend_ok
        self.recommend_text = recommend_text

    def recommend(self, queries):
        self.calls.append(("recommend", list(queries)))
        return MusicResult(self.recommend_ok, self.recommend_text)

    def play_number(self, number):
        self.calls.append(("play_number", number))
        return MusicResult(True, f"playing {number}")

    def now_playing(self):
        self.calls.append(("now_playing",))
        return MusicResult(True, "▶ 晴天 - 周杰伦")


def test_recommend_from_context_searches_without_playing():
    music = FakeMusic()
    session = PetMusicSession(music=music, load_state=lambda: state(vibe="debug"))

    result = session.recommend_from_context()

    assert result.ok is True
    assert result.action == "recommend"
    assert result.card.kind == "recommendations"
    assert music.calls == [
        (
            "recommend",
            [
                "deep focus ambient instrumental no vocals",
                "flow state drone minimal electronic",
                "study music concentration piano quiet",
            ],
        )
    ]


def test_reroll_keeps_current_intent_and_changes_queries():
    music = FakeMusic()
    session = PetMusicSession(music=music, load_state=lambda: state(vibe="debug"))

    session.recommend_from_context()
    result = session.reroll()

    assert result.ok is True
    assert music.calls[1] == (
        "recommend",
        [
            "lofi hip hop late night coding chill",
            "calm electronic coding focus",
            "jazz study background mellow",
        ],
    )


def test_play_number_uses_current_result_list():
    music = FakeMusic()
    session = PetMusicSession(music=music, load_state=lambda: state(vibe="debug"))

    session.recommend_from_context()
    result = session.play_number(2)

    assert result.ok is True
    assert result.action == "dance"
    assert result.card.kind == "confirmation"
    assert result.card.text.startswith("已开播\nplaying 2")
    assert music.calls[-1] == ("play_number", 2)


def test_auto_play_searches_then_plays_first_result():
    music = FakeMusic()
    session = PetMusicSession(music=music, load_state=lambda: state(vibe="debug"))

    result = session.auto_play_from_context()

    assert result.ok is True
    assert result.action == "dance"
    assert result.card.kind == "confirmation"
    assert result.card.text.startswith("已按 Debug flow 开播\nplaying 1")
    assert music.calls == [
        (
            "recommend",
            [
                "deep focus ambient instrumental no vocals",
                "flow state drone minimal electronic",
                "study music concentration piano quiet",
            ],
        ),
        ("play_number", 1),
    ]


def test_failed_recommendation_returns_error_card():
    music = FakeMusic(recommend_ok=False, recommend_text="smart search failed")
    session = PetMusicSession(music=music, load_state=lambda: state(vibe="debug"))

    result = session.recommend_from_context()

    assert result.ok is False
    assert result.action == "sad"
    assert result.card.kind == "error"
    assert result.card.text == "推荐失败\nsmart search failed"


def test_recommend_from_text_uses_user_text_over_state():
    music = FakeMusic()
    session = PetMusicSession(music=music, load_state=lambda: state(dj_mood="victory", vibe="debug"))

    result = session.recommend_from_text("想听国风")

    assert result.ok is True
    assert music.calls == [
        (
            "recommend",
            [
                "中国风 古风 古琴 传统乐器",
                "华语流行 国语歌 indie 民谣",
                "chinese traditional folk guzheng erhu instrumental",
            ],
        )
    ]
