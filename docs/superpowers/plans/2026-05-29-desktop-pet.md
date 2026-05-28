# Desktop Pet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `cwb pet`, a Python-native macOS desktop pet with five built-in pixel skins, mood-based recommendations, and state-aware reactions.

**Architecture:** Keep GUI imports isolated under `coding_with_beat.pet.app` and `coding_with_beat.pet.window` so the base CLI and tests do not require PySide6. Test pure modules first: mood mapping, skin registry, animator, settings, music wrappers, and controller action selection. The GUI window consumes those modules and degrades with a clear install hint when PySide6 is missing.

**Tech Stack:** Python 3.10+, PySide6 optional extra, existing MCP client, dataclasses, pytest.

---

## File Structure

- Create `coding_with_beat/pet/__init__.py`: package marker and public exports.
- Create `coding_with_beat/pet/mood.py`: map user text to 2-3 smart search queries.
- Create `coding_with_beat/pet/sprites.py`: built-in skin/action/frame registry.
- Create `coding_with_beat/pet/animator.py`: skin/action frame cycling.
- Create `coding_with_beat/pet/settings.py`: load/save pet preferences.
- Create `coding_with_beat/pet/music.py`: wrap MCP calls for UI use.
- Create `coding_with_beat/pet/controller.py`: state-to-action selection and recommendation orchestration.
- Create `coding_with_beat/pet/window.py`: PySide6 transparent pet window.
- Create `coding_with_beat/pet/app.py`: PySide6 import boundary and app entrypoint.
- Modify `coding_with_beat/__main__.py`: add `pet` command.
- Modify `pyproject.toml`: add optional `pet` dependency.
- Create `tests/test_pet_mood.py`, `tests/test_pet_sprites.py`, `tests/test_pet_animator.py`, `tests/test_pet_settings.py`, `tests/test_pet_music.py`, `tests/test_pet_controller.py`, `tests/test_pet_cli.py`.

---

### Task 1: Mood Query Mapping

**Files:**
- Create: `coding_with_beat/pet/__init__.py`
- Create: `coding_with_beat/pet/mood.py`
- Test: `tests/test_pet_mood.py`

- [ ] **Step 1: Write failing tests**

```python
from coding_with_beat.pet.mood import queries_for_mood


def test_successful_mood_maps_to_upbeat_queries():
    queries = queries_for_mood("今天很顺利 开心")
    assert len(queries) == 3
    assert any("victory" in q or "feel good" in q for q in queries)


def test_chinese_style_maps_to_chinese_queries():
    queries = queries_for_mood("想听国风古风")
    assert len(queries) == 3
    assert any("中国风" in q or "古风" in q for q in queries)


def test_unknown_text_uses_focus_fallback():
    queries = queries_for_mood("random text")
    assert len(queries) == 3
    assert any("focus" in q or "lofi" in q for q in queries)
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_pet_mood.py -v`
Expected: FAIL because `coding_with_beat.pet.mood` does not exist.

- [ ] **Step 3: Implement mapping**

Create `queries_for_mood(text: str) -> list[str]` with keyword buckets for success, tired, sad, focus, sleep, party, jazz, synthwave, Chinese, and fallback.

- [ ] **Step 4: Verify**

Run: `pytest tests/test_pet_mood.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add coding_with_beat/pet/__init__.py coding_with_beat/pet/mood.py tests/test_pet_mood.py
git commit -m "feat(pet): map moods to recommendation queries"
```

### Task 2: Skin Registry

**Files:**
- Create: `coding_with_beat/pet/sprites.py`
- Test: `tests/test_pet_sprites.py`

- [ ] **Step 1: Write failing tests**

```python
from coding_with_beat.pet.sprites import ACTIONS, BUILTIN_SKINS, get_skin


def test_all_five_skins_exist():
    assert set(BUILTIN_SKINS) == {"dj", "programmer", "sleepwear", "cyber", "chinese"}


def test_every_skin_has_every_action_with_frames():
    for skin in BUILTIN_SKINS.values():
        assert set(skin.actions) == set(ACTIONS)
        for action, frames in skin.actions.items():
            assert frames, f"{skin.id} missing frames for {action}"
            assert all(frame.pixels for frame in frames)


def test_get_skin_falls_back_to_dj():
    assert get_skin("missing").id == "dj"
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_pet_sprites.py -v`
Expected: FAIL because `sprites.py` does not exist.

- [ ] **Step 3: Implement registry**

Add `Frame` and `Skin` dataclasses, action constants, base 12x12 pixel templates, and five generated skins with palette metadata.

- [ ] **Step 4: Verify**

Run: `pytest tests/test_pet_sprites.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add coding_with_beat/pet/sprites.py tests/test_pet_sprites.py
git commit -m "feat(pet): add built-in pixel skins"
```

### Task 3: Animator

**Files:**
- Create: `coding_with_beat/pet/animator.py`
- Test: `tests/test_pet_animator.py`

- [ ] **Step 1: Write failing tests**

```python
from coding_with_beat.pet.animator import PetAnimator


def test_animator_starts_on_default_skin_idle():
    animator = PetAnimator()
    assert animator.skin.id == "dj"
    assert animator.action == "idle"
    assert animator.current_frame().action == "idle"


def test_set_action_resets_frame_index():
    animator = PetAnimator()
    animator.tick()
    animator.set_action("dance")
    assert animator.action == "dance"
    assert animator.frame_index == 0


def test_invalid_skin_and_action_fall_back():
    animator = PetAnimator(skin_id="missing")
    assert animator.skin.id == "dj"
    animator.set_action("unknown")
    assert animator.action == "idle"
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_pet_animator.py -v`
Expected: FAIL because `animator.py` does not exist.

- [ ] **Step 3: Implement animator**

Add `PetAnimator` with `set_skin`, `set_action`, `tick`, and `current_frame`.

- [ ] **Step 4: Verify**

Run: `pytest tests/test_pet_animator.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add coding_with_beat/pet/animator.py tests/test_pet_animator.py
git commit -m "feat(pet): add sprite animator"
```

### Task 4: Settings

**Files:**
- Create: `coding_with_beat/pet/settings.py`
- Test: `tests/test_pet_settings.py`

- [ ] **Step 1: Write failing tests**

```python
from coding_with_beat.pet.settings import PetSettings, load_settings, save_settings


def test_missing_settings_returns_defaults(tmp_path):
    settings = load_settings(tmp_path / "pet.json")
    assert settings.skin_id == "dj"
    assert settings.scale == 5


def test_save_and_load_round_trip(tmp_path):
    path = tmp_path / "pet.json"
    save_settings(PetSettings(x=12, y=34, skin_id="cyber", scale=4), path)
    loaded = load_settings(path)
    assert loaded.x == 12
    assert loaded.y == 34
    assert loaded.skin_id == "cyber"
    assert loaded.scale == 4
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_pet_settings.py -v`
Expected: FAIL because `settings.py` does not exist.

- [ ] **Step 3: Implement settings**

Add `PetSettings`, `load_settings`, and `save_settings` using JSON and an atomic replace.

- [ ] **Step 4: Verify**

Run: `pytest tests/test_pet_settings.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add coding_with_beat/pet/settings.py tests/test_pet_settings.py
git commit -m "feat(pet): persist desktop pet settings"
```

### Task 5: Music Wrapper

**Files:**
- Create: `coding_with_beat/pet/music.py`
- Test: `tests/test_pet_music.py`

- [ ] **Step 1: Write failing tests**

```python
from unittest import mock

from coding_with_beat.pet.music import PetMusicClient


def test_recommend_calls_smart_search_with_queries():
    client = PetMusicClient(call_tool=lambda name, kwargs: f"{name}:{kwargs['queries'][0]}")
    result = client.recommend(["lofi focus", "ambient"])
    assert result.ok is True
    assert result.text.startswith("smart_search:lofi focus")


def test_errors_are_normalized():
    def fail(name, kwargs):
        raise RuntimeError("boom")

    client = PetMusicClient(call_tool=fail)
    result = client.play_number(1)
    assert result.ok is False
    assert "boom" in result.text
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_pet_music.py -v`
Expected: FAIL because `music.py` does not exist.

- [ ] **Step 3: Implement wrapper**

Add `MusicResult` and `PetMusicClient` with `recommend`, `play_number`, `now_playing`, `toggle`, and `next_track`.

- [ ] **Step 4: Verify**

Run: `pytest tests/test_pet_music.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add coding_with_beat/pet/music.py tests/test_pet_music.py
git commit -m "feat(pet): wrap music controls for desktop pet"
```

### Task 6: Controller

**Files:**
- Create: `coding_with_beat/pet/controller.py`
- Test: `tests/test_pet_controller.py`

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_pet_controller.py -v`
Expected: FAIL because `controller.py` does not exist.

- [ ] **Step 3: Implement controller core**

Add `action_for_state(st, now=None)`, `PetController`, `handle_mood_text`, and `play_number`.

- [ ] **Step 4: Verify**

Run: `pytest tests/test_pet_controller.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add coding_with_beat/pet/controller.py tests/test_pet_controller.py
git commit -m "feat(pet): connect state and recommendations"
```

### Task 7: CLI And Optional Dependency

**Files:**
- Modify: `pyproject.toml`
- Modify: `coding_with_beat/__main__.py`
- Create: `coding_with_beat/pet/app.py`
- Create: `coding_with_beat/pet/window.py`
- Test: `tests/test_pet_cli.py`

- [ ] **Step 1: Write failing tests**

```python
from unittest import mock

from coding_with_beat.__main__ import COMMANDS, cmd_pet


def test_pet_command_registered():
    assert COMMANDS["pet"] is cmd_pet


def test_cmd_pet_prints_install_hint_when_pyside_missing(capsys):
    with mock.patch("coding_with_beat.pet.app.run", side_effect=RuntimeError("PySide6 is required")):
        rc = cmd_pet()
    assert rc == 1
    assert "pip install" in capsys.readouterr().err
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_pet_cli.py -v`
Expected: FAIL because `cmd_pet` does not exist.

- [ ] **Step 3: Implement CLI boundary**

Add `cmd_pet`, register `pet`, and add optional dependency group. `app.py` imports PySide6 inside `run()`.

- [ ] **Step 4: Add GUI window**

Implement `PetWindow` with frameless translucent flags, sprite rendering, drag, double-click input, menu actions, skin switching, and timer-driven frame updates.

- [ ] **Step 5: Verify**

Run: `pytest tests/test_pet_cli.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml coding_with_beat/__main__.py coding_with_beat/pet/app.py coding_with_beat/pet/window.py tests/test_pet_cli.py
git commit -m "feat(pet): add desktop pet command"
```

### Task 8: Full Verification

**Files:**
- All pet files

- [ ] **Step 1: Run pet tests**

Run: `pytest tests/test_pet_*.py -v`
Expected: PASS.

- [ ] **Step 2: Run focused existing tests**

Run: `pytest tests/test_cli.py tests/test_companion.py tests/test_smart_search.py -v`
Expected: PASS.

- [ ] **Step 3: Run lint**

Run: `ruff check coding_with_beat tests`
Expected: PASS.

- [ ] **Step 4: Manual command check**

Run: `python -m coding_with_beat pet`
Expected without PySide6 installed: a clear install hint and exit code 1.
Expected with PySide6 installed: pet window opens.

---

## Self-Review

- Spec coverage: product scope, five skins, action system, optional PySide6, state reactions, recommendations, settings, and CLI entry are covered by tasks 1-7.
- Placeholder scan: no unresolved markers or open-ended testing tasks remain.
- Type consistency: plan consistently uses `Frame`, `Skin`, `PetAnimator`, `PetSettings`, `PetMusicClient`, `MusicResult`, `action_for_state`, and `cmd_pet`.
