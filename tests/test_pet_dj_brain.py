from types import SimpleNamespace

from coding_with_beat.pet.dj_brain import PetDjBrain


def state(**kwargs):
    base = {
        "playing": False,
        "dj_mood": "neutral",
        "vibe": "focus",
        "companion_failure_streak": 0,
        "last_tool_at": 0.0,
        "track": None,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_debug_vibe_maps_to_debug_focus_intent():
    brain = PetDjBrain(now=lambda: 1000.0)

    intent = brain.intent_from_state(state(vibe="debug", last_tool_at=990.0))

    assert intent.name == "debug_focus"
    assert intent.title == "Debug flow"
    assert intent.pet_action == "think"


def test_victory_mood_maps_to_boost_intent():
    brain = PetDjBrain(now=lambda: 1000.0)

    intent = brain.intent_from_state(state(dj_mood="victory"))

    assert intent.name == "victory_boost"
    assert intent.title == "庆祝一下"
    assert intent.pet_action == "happy"


def test_panic_state_maps_to_recovery_intent():
    brain = PetDjBrain(now=lambda: 1000.0)

    intent = brain.intent_from_state(state(companion_failure_streak=3))

    assert intent.name == "panic_recover"
    assert intent.title == "缓一下"
    assert intent.pet_action == "panic"


def test_late_idle_maps_to_late_idle_intent():
    brain = PetDjBrain(now=lambda: 4000.0)

    intent = brain.intent_from_state(state(last_tool_at=1000.0))

    assert intent.name == "late_idle"
    assert intent.title == "慢慢回来"
    assert intent.pet_action == "sleep"


def test_user_text_overrides_state():
    brain = PetDjBrain(now=lambda: 1000.0)

    intent = brain.intent_from_text("想听国风", state(dj_mood="victory", vibe="debug"))

    assert intent.name == "free_text"
    assert intent.title == "想听国风"
    assert intent.queries == [
        "中国风 古风 古琴 传统乐器",
        "华语流行 国语歌 indie 民谣",
        "chinese traditional folk guzheng erhu instrumental",
    ]


def test_queries_for_debug_focus_have_reroll_sets():
    brain = PetDjBrain(now=lambda: 1000.0)
    intent = brain.intent_from_state(state(vibe="debug"))

    first = brain.queries_for_intent(intent, reroll=0)
    second = brain.queries_for_intent(intent, reroll=1)

    assert first.title == "Debug flow"
    assert first.queries == [
        "deep focus ambient instrumental no vocals",
        "flow state drone minimal electronic",
        "study music concentration piano quiet",
    ]
    assert second.queries == [
        "lofi hip hop late night coding chill",
        "calm electronic coding focus",
        "jazz study background mellow",
    ]
