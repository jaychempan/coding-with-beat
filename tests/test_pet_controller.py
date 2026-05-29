from types import SimpleNamespace

from coding_with_beat.pet.controller import PetController, action_for_state


def state(**kwargs):
    base = {
        "playing": False,
        "dj_mood": "neutral",
        "vibe": "focus",
        "companion_failure_streak": 0,
        "last_tool_at": 0.0,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_playing_state_dances():
    assert action_for_state(state(playing=True)) == "dance"


def test_failure_streak_panics():
    assert action_for_state(state(companion_failure_streak=3)) == "panic"


def test_victory_is_happy():
    assert action_for_state(state(dj_mood="victory")) == "happy"


def test_ambient_actions_cycle_when_idle():
    controller = PetController()
    assert [controller.next_ambient_action() for _ in range(5)] == ["idle", "walk", "think", "happy", "idle"]


def test_current_track_label_uses_state_track():
    st = state(playing=True)
    st.track = SimpleNamespace(title="晴天", artist="周杰伦")
    controller = PetController(load_state=lambda: st)
    assert controller.current_track_label() == "▶ 晴天 — 周杰伦"


def test_current_track_label_handles_empty_track():
    st = state(playing=False)
    st.track = SimpleNamespace(title="", artist="")
    controller = PetController(load_state=lambda: st)
    assert controller.current_track_label() == "未播放"


def test_cycle_skin_switches_to_next_builtin_skin():
    controller = PetController()
    assert controller.animator.skin.id == "dj"
    assert controller.cycle_skin() == "programmer"
    assert controller.animator.skin.id == "programmer"
