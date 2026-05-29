from types import SimpleNamespace

from coding_with_beat.pet.dj_brain import DjIntent, PetDjBrain


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


def test_panic_takes_precedence_over_victory_and_playing():
    brain = PetDjBrain(now=lambda: 1000.0)

    intent = brain.intent_from_state(state(companion_failure_streak=3, dj_mood="victory", playing=True))

    assert intent.name == "panic_recover"
    assert intent.pet_action == "panic"


def test_late_idle_maps_to_late_idle_intent():
    brain = PetDjBrain(now=lambda: 4000.0)

    intent = brain.intent_from_state(state(last_tool_at=1000.0))

    assert intent.name == "late_idle"
    assert intent.title == "慢慢回来"
    assert intent.pet_action == "sleep"


def test_victory_takes_precedence_over_playing():
    brain = PetDjBrain(now=lambda: 1000.0)

    intent = brain.intent_from_state(state(dj_mood="victory", playing=True))

    assert intent.name == "victory_boost"
    assert intent.pet_action == "happy"


def test_playing_takes_precedence_over_late_idle():
    brain = PetDjBrain(now=lambda: 4000.0)

    intent = brain.intent_from_state(state(playing=True, last_tool_at=1000.0))

    assert intent.name == "playing_companion"
    assert intent.pet_action == "dance"


def test_review_vibe_maps_to_debug_focus_intent():
    brain = PetDjBrain(now=lambda: 1000.0)

    intent = brain.intent_from_state(state(vibe="review"))

    assert intent.name == "debug_focus"
    assert intent.pet_action == "think"


def test_focus_vibe_maps_to_debug_focus_intent():
    brain = PetDjBrain(now=lambda: 1000.0)

    intent = brain.intent_from_state(state(vibe="focus"))

    assert intent.name == "debug_focus"
    assert intent.pet_action == "think"


def test_unknown_vibe_maps_to_debug_focus_intent():
    brain = PetDjBrain(now=lambda: 1000.0)

    intent = brain.intent_from_state(state(vibe="build"))

    assert intent.name == "debug_focus"
    assert intent.pet_action == "think"


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


def test_whitespace_text_uses_empty_free_text_title():
    brain = PetDjBrain(now=lambda: 1000.0)

    intent = brain.intent_from_text("   \n\t  ")

    assert intent.title == ""
    assert intent.message == "按你的心情找："


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


def test_debug_focus_reroll_wraps_to_first_query_set():
    brain = PetDjBrain(now=lambda: 1000.0)
    intent = brain.intent_from_state(state(vibe="debug"))

    wrapped = brain.queries_for_intent(intent, reroll=2)

    assert wrapped.queries == [
        "deep focus ambient instrumental no vocals",
        "flow state drone minimal electronic",
        "study music concentration piano quiet",
    ]


def test_explicit_intent_queries_are_copied():
    brain = PetDjBrain(now=lambda: 1000.0)
    intent = DjIntent(
        name="custom",
        title="Custom",
        message="Custom message",
        pet_action="think",
        queries=["first query", "second query"],
    )

    query_set = brain.queries_for_intent(intent)
    query_set.queries.append("mutated query")

    assert intent.queries == ["first query", "second query"]
    assert query_set.queries == ["first query", "second query", "mutated query"]
