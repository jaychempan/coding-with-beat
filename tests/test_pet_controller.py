from types import SimpleNamespace

from coding_with_beat.pet.controller import action_for_state


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
