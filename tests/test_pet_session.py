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
    def __init__(
        self,
        recommend_ok=True,
        recommend_text="1. Night Owl - Luna\n2. Rain Debug - Soft Keys",
        play_ok=True,
        play_text=None,
        now_playing_ok=True,
        now_playing_text="▶ 晴天 - 周杰伦",
        search_text="1. 晴天 — 周杰伦 · 叶惠美 [Library]\n2. 七里香 — 周杰伦 · 七里香 [Apple Music]",
        loved_text="1. 一路向北 — 周杰伦 · Initial J [♥ Loved]",
        library_text="1. 晴天 — 周杰伦 · 叶惠美 [Library]",
        playlists_text="1. Coding Beats [user playlist] — 42 首",
        playlist_text="▶ now playing playlist 'Coding Beats': Intro — DJ  source=apple_music",
        snapshot_text='{"title":"晴天","artist":"周杰伦","source":"apple_music","playing":true}',
    ):
        self.calls = []
        self.recommend_ok = recommend_ok
        self.recommend_text = recommend_text
        self.play_ok = play_ok
        self.play_text = play_text
        self.now_playing_ok = now_playing_ok
        self.now_playing_text = now_playing_text
        self.search_text = search_text
        self.loved_text = loved_text
        self.library_text = library_text
        self.playlists_text = playlists_text
        self.playlist_text = playlist_text
        self.snapshot_text = snapshot_text

    def recommend(self, queries):
        self.calls.append(("recommend", list(queries)))
        return MusicResult(self.recommend_ok, self.recommend_text)

    def play_number(self, number):
        self.calls.append(("play_number", number))
        return MusicResult(self.play_ok, self.play_text or f"playing {number}")

    def now_playing(self):
        self.calls.append(("now_playing",))
        return MusicResult(self.now_playing_ok, self.now_playing_text)

    def now_playing_snapshot(self, known_lyrics_key=""):
        self.calls.append(("now_playing_snapshot", known_lyrics_key))
        return MusicResult(True, self.snapshot_text)

    def search(self, query):
        self.calls.append(("search", query))
        return MusicResult(True, self.search_text)

    def search_loved(self, query):
        self.calls.append(("search_loved", query))
        return MusicResult(True, self.loved_text)

    def list_library(self, limit=40):
        self.calls.append(("list_library", limit))
        return MusicResult(True, self.library_text)

    def list_loved(self, limit=40):
        self.calls.append(("list_loved", limit))
        return MusicResult(True, self.loved_text)

    def list_playlists(self):
        self.calls.append(("list_playlists",))
        return MusicResult(True, self.playlists_text)

    def play_playlist(self, name):
        self.calls.append(("play_playlist", name))
        return MusicResult(True, self.playlist_text)


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


def test_successful_recommendation_sets_current_session_state():
    music = FakeMusic()
    session = PetMusicSession(music=music, load_state=lambda: state(vibe="debug"))

    result = session.recommend_from_context()

    assert session.current_query_set is not None
    assert session.current_query_set.title == "Debug flow"
    assert session.current_query_set.queries == [
        "deep focus ambient instrumental no vocals",
        "flow state drone minimal electronic",
        "study music concentration piano quiet",
    ]
    assert session.current_card == result.card
    assert session.last_result == result


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


def test_play_number_treats_textual_no_match_as_failure_and_preserves_current_card():
    music = FakeMusic(play_text="(no match — #9 out of range, last results had 2 items)")
    session = PetMusicSession(music=music, load_state=lambda: state(vibe="debug"))
    recommendation = session.recommend_from_context()

    result = session.play_number(9)

    assert result.ok is False
    assert result.action == "sad"
    assert result.card.kind == "error"
    assert result.card.text.startswith("播放失败\n")
    assert session.current_card == recommendation.card
    assert session.last_result == result


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


def test_auto_play_textual_playback_failure_returns_error_card():
    music = FakeMusic(play_text="full playback did not start")
    session = PetMusicSession(music=music, load_state=lambda: state(vibe="debug"))

    result = session.auto_play_from_context()

    assert result.ok is False
    assert result.action == "sad"
    assert result.card.kind == "error"
    assert result.card.text == "自动开播失败\nfull playback did not start"
    assert music.calls[-1] == ("play_number", 1)


def test_failed_recommendation_returns_error_card():
    music = FakeMusic(recommend_ok=False, recommend_text="smart search failed")
    session = PetMusicSession(music=music, load_state=lambda: state(vibe="debug"))

    result = session.recommend_from_context()

    assert result.ok is False
    assert result.action == "sad"
    assert result.card.kind == "error"
    assert result.card.text == "推荐失败\nsmart search failed"


def test_empty_recommendation_output_returns_empty_card_and_sets_current_card():
    music = FakeMusic(recommend_text="nothing useful")
    session = PetMusicSession(music=music, load_state=lambda: state(vibe="debug"))

    result = session.recommend_from_context()

    assert result.ok is False
    assert result.action == "sad"
    assert result.card.kind == "empty"
    assert session.current_card == result.card
    assert session.last_result == result


def test_textual_no_matches_recommendation_returns_empty_card_not_error():
    music = FakeMusic(recommend_text="(no matches for queries: debug)")
    session = PetMusicSession(music=music, load_state=lambda: state(vibe="debug"))

    result = session.recommend_from_context()

    assert result.ok is False
    assert result.action == "sad"
    assert result.card.kind == "empty"
    assert not result.card.text.startswith("推荐失败")
    assert session.current_card == result.card


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


def test_handle_prompt_searches_plain_artist_instead_of_mood_recommendation():
    music = FakeMusic()
    session = PetMusicSession(music=music, load_state=lambda: state(vibe="debug"))

    result = session.handle_prompt("周杰伦")

    assert result.ok is True
    assert result.action == "recommend"
    assert result.card.kind == "recommendations"
    assert result.card.text.startswith("搜索：周杰伦")
    assert [item.number for item in result.card.items] == [1, 2]
    assert music.calls == [("search", "周杰伦")]


def test_handle_prompt_keeps_mood_requests_on_smart_search():
    music = FakeMusic()
    session = PetMusicSession(music=music, load_state=lambda: state(vibe="debug"))

    result = session.handle_prompt("来点爵士")

    assert result.ok is True
    assert music.calls == [
        (
            "recommend",
            [
                "smooth jazz cafe background mellow",
                "jazz trio acoustic bossa nova guitar",
                "late night jazz piano bar cool relaxed",
            ],
        )
    ]


def test_handle_prompt_filters_library_only_search_results():
    music = FakeMusic(
        search_text=(
            "1. 稻香 — 周杰伦 · 魔杰座 [Apple Music]\n"
            "2. 晴天 — 周杰伦 · 叶惠美 [Library]\n"
            "3. 七里香 — 周杰伦 · 七里香 [Apple Music]"
        )
    )
    session = PetMusicSession(music=music, load_state=lambda: state(vibe="debug"))

    result = session.handle_prompt("从资料库找 周杰伦")

    assert result.ok is True
    assert result.card.text.startswith("资料库：周杰伦")
    assert "晴天" in result.card.text
    assert "稻香" not in result.card.text
    assert [item.number for item in result.card.items] == [2]
    assert music.calls == [("search", "周杰伦")]


def test_list_library_keeps_more_than_five_playable_results():
    library_text = "\n".join(f"{number}. Track {number} — Artist · Album [Library]" for number in range(1, 13))
    music = FakeMusic(library_text=library_text)
    session = PetMusicSession(music=music, load_state=lambda: state(vibe="debug"))

    result = session.list_library()

    assert result.ok is True
    assert result.card.text.startswith("资料库")
    assert [item.number for item in result.card.items] == list(range(1, 13))
    assert "12. Track 12" in result.card.text
    assert music.calls == [("list_library", 40)]


def test_handle_prompt_searches_loved_tracks():
    music = FakeMusic()
    session = PetMusicSession(music=music, load_state=lambda: state(vibe="debug"))

    result = session.handle_prompt("从喜欢里找 周杰伦")

    assert result.ok is True
    assert result.card.text.startswith("喜欢：周杰伦")
    assert "一路向北" in result.card.text
    assert music.calls == [("search_loved", "周杰伦")]


def test_handle_prompt_lists_playlists():
    music = FakeMusic()
    session = PetMusicSession(music=music, load_state=lambda: state(vibe="debug"))

    result = session.handle_prompt("我的歌单")

    assert result.ok is True
    assert result.card.text.startswith("歌单")
    assert "Coding Beats" in result.card.text
    assert music.calls == [("list_playlists",)]


def test_handle_prompt_plays_named_playlist():
    music = FakeMusic()
    session = PetMusicSession(music=music, load_state=lambda: state(vibe="debug"))

    result = session.handle_prompt("播放歌单 Coding Beats")

    assert result.ok is True
    assert result.action == "dance"
    assert result.card.kind == "confirmation"
    assert result.card.text.startswith("播放歌单\n")
    assert music.calls == [("play_playlist", "Coding Beats")]


def test_now_playing_success_returns_status_card():
    music = FakeMusic()
    session = PetMusicSession(music=music, load_state=lambda: state(vibe="debug"))

    result = session.now_playing()

    assert result.ok is True
    assert result.action == "idle"
    assert result.card.kind == "status"
    assert result.card.text == "当前播放\n▶ 晴天 - 周杰伦"
    assert session.last_result == result


def test_live_now_playing_reports_terminal_started_track():
    music = FakeMusic(snapshot_text='{"title":"晴天","artist":"周杰伦","source":"apple_music","playing":true}')
    session = PetMusicSession(music=music, load_state=lambda: state(vibe="debug"))

    result = session.live_now_playing()

    assert result.ok is True
    assert result.action == "dance"
    assert result.card.kind == "live"
    assert result.card.text == "当前播放\n▶ 晴天 — 周杰伦"
    assert music.calls == [("now_playing_snapshot", "")]


def test_live_now_playing_reports_paused_track_without_dance():
    music = FakeMusic(snapshot_text='{"title":"晴天","artist":"周杰伦","source":"apple_music","playing":false}')
    session = PetMusicSession(music=music, load_state=lambda: state(vibe="debug"))

    result = session.live_now_playing()

    assert result.ok is True
    assert result.action == "idle"
    assert result.card.text == "当前播放\n▷ 晴天 — 周杰伦"


def test_live_now_playing_ignores_empty_snapshot():
    music = FakeMusic(snapshot_text='{"title":"","artist":"","playing":false}')
    session = PetMusicSession(music=music, load_state=lambda: state(vibe="debug"))

    result = session.live_now_playing()

    assert result.ok is False
    assert result.action == "idle"
    assert result.card.kind == "live"
    assert result.card.text == "当前播放\n未播放"


def test_now_playing_failure_returns_error_card():
    music = FakeMusic(now_playing_ok=False, now_playing_text="source unavailable")
    session = PetMusicSession(music=music, load_state=lambda: state(vibe="debug"))

    result = session.now_playing()

    assert result.ok is False
    assert result.action == "sad"
    assert result.card.kind == "error"
    assert result.card.text == "当前播放读取失败\nsource unavailable"
    assert session.last_result == result
