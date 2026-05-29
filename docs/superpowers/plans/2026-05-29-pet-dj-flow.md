# Pet DJ Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the context-aware DJ Buddy interaction flow for the desktop pet: quiet ambient state, double-click recommendations, long-press auto-play, reroll, compact cards, and right-click fallback controls.

**Architecture:** Keep Qt windowing thin and move CWB-specific decisions into small testable modules. `PetDjBrain` maps state/text to DJ intents and query sets, `PetMusicSession` owns active recommendation/playback state, `PetBubbleView` formats compact cards, and `PetInteractionController` maps UI gestures to session commands.

**Tech Stack:** Python 3.13, PySide6, pytest, existing `PetMusicClient`, existing `JukeboxState` shape, existing MCP tools `smart_search`, `play_number`, `now_playing`, `toggle`, and `next_track`.

---

## File Structure

- Create `coding_with_beat/pet/dj_brain.py`
  - Defines `DjIntent`, `DjQuerySet`, and `PetDjBrain`.
  - Converts CWB state or user text into intent names, display titles, search query angles, and reroll query sets.
- Create `coding_with_beat/pet/bubble.py`
  - Defines `PetBubbleCard`, `PetResultItem`, and `PetBubbleView`.
  - Parses numbered search output into compact recommendation cards and short status/error cards.
- Create `coding_with_beat/pet/session.py`
  - Defines `PetSessionResult` and `PetMusicSession`.
  - Owns the active intent, query set, result text, reroll count, and play-number/auto-play flow.
- Create `coding_with_beat/pet/interactions.py`
  - Defines `PetInteractionController`.
  - Converts single click, double click, long press, and quick actions into session calls.
- Modify `coding_with_beat/pet/controller.py`
  - Keep state-to-animation helpers and current-track label.
  - Stop owning recommendation flow once the session is wired.
- Modify `coding_with_beat/pet/window.py`
  - Replace persistent text buttons with a compact action strip.
  - Wire single click, double click, long press, reroll, compact bubble cards, and right-click fallback.
- Modify `README.md`
  - Update desktop pet usage from button-panel flow to DJ Buddy flow.
- Add/modify tests:
  - `tests/test_pet_dj_brain.py`
  - `tests/test_pet_bubble.py`
  - `tests/test_pet_session.py`
  - `tests/test_pet_interactions.py`
  - Existing pet tests as needed.

---

### Task 1: Add `PetDjBrain` Intent Mapping

**Files:**
- Create: `coding_with_beat/pet/dj_brain.py`
- Test: `tests/test_pet_dj_brain.py`

- [ ] **Step 1: Write failing tests for state-to-intent and query generation**

Create `tests/test_pet_dj_brain.py`:

```python
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
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
pytest tests/test_pet_dj_brain.py -q
```

Expected: FAIL during import with `ModuleNotFoundError: No module named 'coding_with_beat.pet.dj_brain'`.

- [ ] **Step 3: Implement `PetDjBrain`**

Create `coding_with_beat/pet/dj_brain.py`:

```python
"""Context-aware DJ intent selection for the desktop pet."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from .mood import queries_for_mood


@dataclass(frozen=True)
class DjIntent:
    name: str
    title: str
    message: str
    pet_action: str
    queries: list[str] | None = None


@dataclass(frozen=True)
class DjQuerySet:
    intent: DjIntent
    title: str
    message: str
    queries: list[str]


class PetDjBrain:
    def __init__(self, now: Callable[[], float] | None = None) -> None:
        self._now = now or time.time

    def intent_from_text(self, text: str, st: object | None = None) -> DjIntent:
        clean = (text or "").strip()
        title = clean[:18] or "想听点什么"
        return DjIntent(
            name="free_text",
            title=title,
            message=f"按你的心情找：{title}",
            pet_action="think",
            queries=queries_for_mood(clean),
        )

    def intent_from_state(self, st: object) -> DjIntent:
        if getattr(st, "companion_failure_streak", 0) >= 3 or getattr(st, "dj_mood", "") == "panic":
            return DjIntent("panic_recover", "缓一下", "刚才有点乱，先找点稳住节奏的。", "panic")
        if getattr(st, "dj_mood", "") == "victory":
            return DjIntent("victory_boost", "庆祝一下", "这波很顺，来点亮一点的。", "happy")
        if getattr(st, "playing", False):
            return DjIntent("playing_companion", "继续这个感觉", "基于当前播放，找相近或下一段氛围。", "dance")
        last_tool_at = float(getattr(st, "last_tool_at", 0.0) or 0.0)
        if last_tool_at and self._now() - last_tool_at > 1800:
            return DjIntent("late_idle", "慢慢回来", "空了一会儿，来点轻松回到状态。", "sleep")
        vibe = getattr(st, "vibe", "") or ""
        if vibe in {"debug", "review", "focus"}:
            return DjIntent("debug_focus", "Debug flow", "给你找低干扰的专注音乐。", "think")
        return DjIntent("debug_focus", "Debug flow", "给你找低干扰的专注音乐。", "think")

    def queries_for_intent(self, intent: DjIntent, reroll: int = 0) -> DjQuerySet:
        if intent.queries is not None:
            return DjQuerySet(intent, intent.title, intent.message, list(intent.queries))
        sets = _QUERY_SETS[intent.name]
        queries = sets[reroll % len(sets)]
        return DjQuerySet(intent, intent.title, intent.message, list(queries))


_QUERY_SETS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "debug_focus": (
        (
            "deep focus ambient instrumental no vocals",
            "flow state drone minimal electronic",
            "study music concentration piano quiet",
        ),
        (
            "lofi hip hop late night coding chill",
            "calm electronic coding focus",
            "jazz study background mellow",
        ),
    ),
    "victory_boost": (
        (
            "victory feel good indie pop",
            "celebration upbeat bright positive",
            "happy dance pop fresh energy",
        ),
        (
            "morning energy upbeat pop indie fresh",
            "funky groove celebration coding win",
            "upbeat electronic bright success",
        ),
    ),
    "panic_recover": (
        (
            "calming ambient reset no vocals",
            "soft piano breathe stress relief",
            "relaxing downtempo chill evening unwind",
        ),
        (
            "minimal electronic calm focus recovery",
            "warm acoustic gentle calm soft",
            "rainy lofi decompress coding",
        ),
    ),
    "late_idle": (
        (
            "relaxing downtempo chill evening unwind",
            "nature ambient breeze afternoon easy listening",
            "soft acoustic gentle calm",
        ),
        (
            "lofi rain cafe cozy return to work",
            "quiet piano focus gentle",
            "ambient study music soft restart",
        ),
    ),
    "playing_companion": (
        (
            "similar vibe current track coding",
            "fresh adjacent music flow state",
            "next song same mood energetic enough",
        ),
        (
            "discover similar artist coding background",
            "related indie electronic focus",
            "same mood playlist smooth transition",
        ),
    ),
}
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```bash
pytest tests/test_pet_dj_brain.py -q
```

Expected: `7 passed`.

- [ ] **Step 5: Commit**

Run:

```bash
git add coding_with_beat/pet/dj_brain.py tests/test_pet_dj_brain.py
git commit -m "feat(pet): add dj intent brain"
```

---

### Task 2: Add Compact Bubble Formatting

**Files:**
- Create: `coding_with_beat/pet/bubble.py`
- Test: `tests/test_pet_bubble.py`

- [ ] **Step 1: Write failing tests for compact cards**

Create `tests/test_pet_bubble.py`:

```python
from coding_with_beat.pet.bubble import PetBubbleView


def test_recommendation_card_extracts_numbered_results():
    raw = """
1. Night Owl - Luna
2. Rain Debug - Soft Keys
3. Calm Compile - Build Room
"""
    view = PetBubbleView()

    card = view.recommendations("Debug flow", "给你找低干扰的专注音乐。", raw)

    assert card.kind == "recommendations"
    assert card.action == "recommend"
    assert card.items[0].number == 1
    assert card.items[0].label == "Night Owl - Luna"
    assert card.text == "Debug flow\n给你找低干扰的专注音乐。\n\n1. Night Owl - Luna\n2. Rain Debug - Soft Keys\n3. Calm Compile - Build Room\n\n点编号播放 · 🎲 换一组"


def test_recommendation_card_caps_at_five_results():
    raw = "\n".join(f"{n}. Track {n}" for n in range(1, 8))
    view = PetBubbleView()

    card = view.recommendations("Flow", "挑一首", raw)

    assert [item.number for item in card.items] == [1, 2, 3, 4, 5]
    assert "6. Track 6" not in card.text


def test_recommendation_card_handles_no_results():
    view = PetBubbleView()

    card = view.recommendations("Flow", "挑一首", "没有找到")

    assert card.kind == "empty"
    assert card.action == "sad"
    assert card.text == "Flow\n没有找到合适结果。可以换一组，或者说一个更具体的心情。"


def test_status_card_is_short():
    view = PetBubbleView()

    card = view.status("当前播放", "▶ 晴天 - 周杰伦")

    assert card.kind == "status"
    assert card.action == "idle"
    assert card.text == "当前播放\n▶ 晴天 - 周杰伦"


def test_error_card_trims_long_output():
    view = PetBubbleView()

    card = view.error("播放失败", "boom\n" + "x" * 500)

    assert card.kind == "error"
    assert card.action == "sad"
    assert len(card.text) <= 170
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
pytest tests/test_pet_bubble.py -q
```

Expected: FAIL during import with `ModuleNotFoundError: No module named 'coding_with_beat.pet.bubble'`.

- [ ] **Step 3: Implement `PetBubbleView`**

Create `coding_with_beat/pet/bubble.py`:

```python
"""Compact bubble cards for desktop pet interactions."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PetResultItem:
    number: int
    label: str


@dataclass(frozen=True)
class PetBubbleCard:
    kind: str
    text: str
    action: str = "idle"
    items: list[PetResultItem] = field(default_factory=list)


class PetBubbleView:
    def recommendations(self, title: str, message: str, raw_results: str) -> PetBubbleCard:
        items = _parse_numbered_items(raw_results)[:5]
        if not items:
            return PetBubbleCard(
                kind="empty",
                text=f"{title}\n没有找到合适结果。可以换一组，或者说一个更具体的心情。",
                action="sad",
            )
        lines = [title, message, ""]
        lines.extend(f"{item.number}. {item.label}" for item in items)
        lines.extend(["", "点编号播放 · 🎲 换一组"])
        return PetBubbleCard(kind="recommendations", text="\n".join(lines), action="recommend", items=items)

    def status(self, title: str, detail: str, action: str = "idle") -> PetBubbleCard:
        clean = _one_line(detail, limit=140)
        return PetBubbleCard(kind="status", text=f"{title}\n{clean}", action=action)

    def confirmation(self, title: str, detail: str, action: str = "dance") -> PetBubbleCard:
        clean = _one_line(detail, limit=140)
        return PetBubbleCard(kind="confirmation", text=f"{title}\n{clean}\n\n下一首 · 🎲 换一组", action=action)

    def error(self, title: str, detail: str) -> PetBubbleCard:
        clean = _one_line(detail, limit=130)
        return PetBubbleCard(kind="error", text=f"{title}\n{clean}", action="sad")


def _parse_numbered_items(text: str) -> list[PetResultItem]:
    items: list[PetResultItem] = []
    for line in (text or "").splitlines():
        match = re.match(r"^\s*(\d+)[.)、]\s+(.+?)\s*$", line)
        if not match:
            continue
        items.append(PetResultItem(number=int(match.group(1)), label=match.group(2)))
    return items


def _one_line(text: str, limit: int) -> str:
    clean = re.sub(r"\s+", " ", (text or "").strip()) or "没有返回内容"
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```bash
pytest tests/test_pet_bubble.py -q
```

Expected: `5 passed`.

- [ ] **Step 5: Commit**

Run:

```bash
git add coding_with_beat/pet/bubble.py tests/test_pet_bubble.py
git commit -m "feat(pet): add compact bubble cards"
```

---

### Task 3: Add `PetMusicSession`

**Files:**
- Create: `coding_with_beat/pet/session.py`
- Test: `tests/test_pet_session.py`

- [ ] **Step 1: Write failing tests for recommendation, reroll, play, and auto-play**

Create `tests/test_pet_session.py`:

```python
from types import SimpleNamespace

from coding_with_beat.pet.dj_brain import PetDjBrain
from coding_with_beat.pet.music import MusicResult
from coding_with_beat.pet.session import PetMusicSession


class FakeMusic:
    def __init__(self):
        self.calls = []

    def recommend(self, queries):
        self.calls.append(("recommend", list(queries)))
        return MusicResult(True, "1. Night Owl - Luna\n2. Rain Debug - Soft Keys")

    def play_number(self, number):
        self.calls.append(("play_number", number))
        return MusicResult(True, f"playing {number}")

    def now_playing(self):
        self.calls.append(("now_playing", {}))
        return MusicResult(True, "▶ 晴天 - 周杰伦")


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


def test_recommend_from_context_searches_without_playing():
    music = FakeMusic()
    session = PetMusicSession(music=music, brain=PetDjBrain(now=lambda: 1000.0), load_state=lambda: state())

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
    session = PetMusicSession(music=music, brain=PetDjBrain(now=lambda: 1000.0), load_state=lambda: state())

    session.recommend_from_context()
    session.reroll()

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
    session = PetMusicSession(music=music, brain=PetDjBrain(now=lambda: 1000.0), load_state=lambda: state())

    session.recommend_from_context()
    result = session.play_number(2)

    assert result.ok is True
    assert result.action == "dance"
    assert result.card.kind == "confirmation"
    assert music.calls[-1] == ("play_number", 2)


def test_auto_play_searches_then_plays_first_result():
    music = FakeMusic()
    session = PetMusicSession(music=music, brain=PetDjBrain(now=lambda: 1000.0), load_state=lambda: state())

    result = session.auto_play_from_context()

    assert result.ok is True
    assert result.action == "dance"
    assert music.calls[-2][0] == "recommend"
    assert music.calls[-1] == ("play_number", 1)


def test_failed_recommendation_returns_error_card():
    class FailingMusic(FakeMusic):
        def recommend(self, queries):
            self.calls.append(("recommend", list(queries)))
            return MusicResult(False, "network down")

    session = PetMusicSession(
        music=FailingMusic(),
        brain=PetDjBrain(now=lambda: 1000.0),
        load_state=lambda: state(),
    )

    result = session.recommend_from_context()

    assert result.ok is False
    assert result.action == "sad"
    assert result.card.kind == "error"
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
pytest tests/test_pet_session.py -q
```

Expected: FAIL during import with `ModuleNotFoundError: No module named 'coding_with_beat.pet.session'`.

- [ ] **Step 3: Implement `PetMusicSession`**

Create `coding_with_beat/pet/session.py`:

```python
"""Recommendation session state for the desktop pet DJ flow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from coding_with_beat import state as state_mod

from .bubble import PetBubbleCard, PetBubbleView
from .dj_brain import DjIntent, PetDjBrain
from .music import PetMusicClient


@dataclass(frozen=True)
class PetSessionResult:
    ok: bool
    action: str
    card: PetBubbleCard


class PetMusicSession:
    def __init__(
        self,
        music: PetMusicClient | None = None,
        brain: PetDjBrain | None = None,
        bubble: PetBubbleView | None = None,
        load_state: Callable[[], object] = state_mod.load,
    ) -> None:
        self.music = music or PetMusicClient()
        self.brain = brain or PetDjBrain()
        self.bubble = bubble or PetBubbleView()
        self.load_state = load_state
        self.current_intent: DjIntent | None = None
        self.reroll_count = 0

    def recommend_from_context(self) -> PetSessionResult:
        self.current_intent = self.brain.intent_from_state(self.load_state())
        self.reroll_count = 0
        return self._recommend_current()

    def recommend_from_text(self, text: str) -> PetSessionResult:
        self.current_intent = self.brain.intent_from_text(text, self.load_state())
        self.reroll_count = 0
        return self._recommend_current()

    def reroll(self) -> PetSessionResult:
        if self.current_intent is None:
            self.current_intent = self.brain.intent_from_state(self.load_state())
            self.reroll_count = 0
        else:
            self.reroll_count += 1
        return self._recommend_current()

    def play_number(self, number: int) -> PetSessionResult:
        result = self.music.play_number(number)
        if not result.ok:
            return PetSessionResult(False, "sad", self.bubble.error("播放失败", result.text))
        return PetSessionResult(True, "dance", self.bubble.confirmation("已开播", result.text, action="dance"))

    def auto_play_from_context(self) -> PetSessionResult:
        recommendation = self.recommend_from_context()
        if not recommendation.ok:
            return recommendation
        result = self.music.play_number(1)
        if not result.ok:
            return PetSessionResult(False, "sad", self.bubble.error("自动开播失败", result.text))
        title = self.current_intent.title if self.current_intent else "自动开播"
        return PetSessionResult(True, "dance", self.bubble.confirmation(f"已按 {title} 开播", result.text))

    def now_playing(self) -> PetSessionResult:
        result = self.music.now_playing()
        if not result.ok:
            return PetSessionResult(False, "sad", self.bubble.error("当前播放读取失败", result.text))
        return PetSessionResult(True, "idle", self.bubble.status("当前播放", result.text))

    def _recommend_current(self) -> PetSessionResult:
        assert self.current_intent is not None
        query_set = self.brain.queries_for_intent(self.current_intent, self.reroll_count)
        result = self.music.recommend(query_set.queries)
        if not result.ok:
            return PetSessionResult(False, "sad", self.bubble.error("推荐失败", result.text))
        card = self.bubble.recommendations(query_set.title, query_set.message, result.text)
        return PetSessionResult(card.kind != "empty", card.action, card)
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```bash
pytest tests/test_pet_session.py -q
```

Expected: `5 passed`.

- [ ] **Step 5: Commit**

Run:

```bash
git add coding_with_beat/pet/session.py tests/test_pet_session.py
git commit -m "feat(pet): add music recommendation session"
```

---

### Task 4: Add Interaction Controller

**Files:**
- Create: `coding_with_beat/pet/interactions.py`
- Test: `tests/test_pet_interactions.py`

- [ ] **Step 1: Write failing tests for gesture mapping**

Create `tests/test_pet_interactions.py`:

```python
from coding_with_beat.pet.bubble import PetBubbleCard
from coding_with_beat.pet.interactions import PetInteractionController
from coding_with_beat.pet.session import PetSessionResult


class FakeSession:
    def __init__(self):
        self.calls = []

    def now_playing(self):
        self.calls.append("now_playing")
        return PetSessionResult(True, "idle", PetBubbleCard("status", "当前播放\nNothing"))

    def recommend_from_context(self):
        self.calls.append("recommend_from_context")
        return PetSessionResult(True, "recommend", PetBubbleCard("recommendations", "Debug flow"))

    def auto_play_from_context(self):
        self.calls.append("auto_play_from_context")
        return PetSessionResult(True, "dance", PetBubbleCard("confirmation", "已开播"))

    def reroll(self):
        self.calls.append("reroll")
        return PetSessionResult(True, "recommend", PetBubbleCard("recommendations", "换一组"))


def test_single_click_shows_status_bubble():
    session = FakeSession()
    controller = PetInteractionController(session=session)

    result = controller.single_click()

    assert result.card.kind == "status"
    assert session.calls == ["now_playing"]


def test_double_click_recommends_from_context():
    session = FakeSession()
    controller = PetInteractionController(session=session)

    controller.double_click()

    assert session.calls == ["recommend_from_context"]


def test_long_press_auto_plays_from_context():
    session = FakeSession()
    controller = PetInteractionController(session=session)

    controller.long_press()

    assert session.calls == ["auto_play_from_context"]


def test_quick_action_reroll():
    session = FakeSession()
    controller = PetInteractionController(session=session)

    controller.quick_action("reroll")

    assert session.calls == ["reroll"]


def test_unknown_quick_action_returns_error_card():
    session = FakeSession()
    controller = PetInteractionController(session=session)

    result = controller.quick_action("missing")

    assert result.ok is False
    assert result.action == "sad"
    assert result.card.kind == "error"
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
pytest tests/test_pet_interactions.py -q
```

Expected: FAIL during import with `ModuleNotFoundError: No module named 'coding_with_beat.pet.interactions'`.

- [ ] **Step 3: Implement `PetInteractionController`**

Create `coding_with_beat/pet/interactions.py`:

```python
"""UI gesture routing for the desktop pet."""

from __future__ import annotations

from .bubble import PetBubbleView
from .session import PetMusicSession, PetSessionResult


class PetInteractionController:
    def __init__(self, session: PetMusicSession | None = None, bubble: PetBubbleView | None = None) -> None:
        self.session = session or PetMusicSession()
        self.bubble = bubble or PetBubbleView()

    def single_click(self) -> PetSessionResult:
        return self.session.now_playing()

    def double_click(self) -> PetSessionResult:
        return self.session.recommend_from_context()

    def long_press(self) -> PetSessionResult:
        return self.session.auto_play_from_context()

    def quick_action(self, action: str) -> PetSessionResult:
        if action == "now":
            return self.session.now_playing()
        if action == "recommend":
            return self.session.recommend_from_context()
        if action == "reroll":
            return self.session.reroll()
        return PetSessionResult(False, "sad", self.bubble.error("未知动作", action))
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```bash
pytest tests/test_pet_interactions.py -q
```

Expected: `5 passed`.

- [ ] **Step 5: Commit**

Run:

```bash
git add coding_with_beat/pet/interactions.py tests/test_pet_interactions.py
git commit -m "feat(pet): add interaction routing"
```

---

### Task 5: Wire Petdex Window to the DJ Session

**Files:**
- Modify: `coding_with_beat/pet/window.py`
- Test: `tests/test_pet_session.py`, `tests/test_pet_interactions.py`, existing pet tests

- [ ] **Step 1: Add a focused test for text-based recommendation through the session**

Append to `tests/test_pet_session.py`:

```python
def test_recommend_from_text_uses_user_text_over_state():
    music = FakeMusic()
    session = PetMusicSession(music=music, brain=PetDjBrain(now=lambda: 1000.0), load_state=lambda: state(vibe="debug"))

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
```

- [ ] **Step 2: Run the focused test**

Run:

```bash
pytest tests/test_pet_session.py::test_recommend_from_text_uses_user_text_over_state -q
```

Expected: PASS if Task 3 implementation already supports `recommend_from_text`.

- [ ] **Step 3: Modify `PetdexWindow` constructor to create an interaction controller**

In `coding_with_beat/pet/window.py`, add imports:

```python
from .interactions import PetInteractionController
from .session import PetMusicSession, PetSessionResult
```

Inside `PetdexWindow.__init__`, after `self.controller = ...`, add:

```python
        self.music_session = PetMusicSession(music=self.controller.music, load_state=self.controller.load_state)
        self.interactions = PetInteractionController(session=self.music_session)
        self._long_press_fired = False
        self._long_press_timer = QTimer(self)
        self._long_press_timer.setSingleShot(True)
        self._long_press_timer.timeout.connect(self._handle_long_press)
```

- [ ] **Step 4: Replace text buttons with compact action strip**

In `PetdexWindow.__init__`, replace the three text buttons:

```python
        self._recommend_button = _icon_button("✨", "按当前状态推荐")
        self._recommend_button.clicked.connect(lambda: self._apply_session_result(self.interactions.quick_action("recommend")))
        self._now_button = _icon_button("♪", "当前播放")
        self._now_button.clicked.connect(lambda: self._apply_session_result(self.interactions.quick_action("now")))
        self._reroll_button = _icon_button("🎲", "换一组")
        self._reroll_button.clicked.connect(lambda: self._apply_session_result(self.interactions.quick_action("reroll")))
        self._more_button = _icon_button("⋯", "更多")
        self._more_button.clicked.connect(self._show_more_menu)
```

Update controls:

```python
        controls.addWidget(self._now_button)
        controls.addWidget(self._recommend_button)
        controls.addWidget(self._reroll_button)
        controls.addWidget(self._more_button)
```

Add helper near `_button`:

```python
def _icon_button(text: str, tooltip: str) -> QPushButton:
    button = QPushButton(text)
    button.setToolTip(tooltip)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setFixedSize(26, 26)
    button.setStyleSheet(
        "QPushButton { color: #f8fafc; background: rgba(15, 23, 42, 150);"
        " border: 1px solid rgba(148, 163, 184, 130); border-radius: 13px; padding: 0;"
        " font-size: 13px; }"
        "QPushButton:hover { background: rgba(30, 41, 59, 230); }"
        "QPushButton:pressed { background: rgba(15, 23, 42, 240); }"
    )
    return button
```

- [ ] **Step 5: Add session result application**

Inside `PetdexWindow`, add:

```python
    def _apply_session_result(self, result: PetSessionResult) -> None:
        self.petdex_animator.set_action(result.action)
        self._show_bubble(result.card.text)
        self._track_label.setText(self.controller.current_track_label())
```

- [ ] **Step 6: Update mouse handling for single click and long press**

In `mousePressEvent`, start long-press timing:

```python
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._long_press_fired = False
            self._long_press_timer.start(650)
            self.petdex_animator.set_action("dance")
```

In `mouseReleaseEvent`, stop timer and show status on simple click:

```python
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = None
            was_long_press = self._long_press_fired
            self._long_press_timer.stop()
            self.settings.x = self.x()
            self.settings.y = self.y()
            save_settings(self.settings)
            if not was_long_press:
                self._apply_session_result(self.interactions.single_click())
```

Add long-press handler:

```python
    def _handle_long_press(self) -> None:
        self._long_press_fired = True
        self._apply_session_result(self.interactions.long_press())
```

- [ ] **Step 7: Update double click and mood input to use the session**

Replace `mouseDoubleClickEvent` body for left button:

```python
        if event.button() == Qt.MouseButton.LeftButton:
            self._long_press_timer.stop()
            self._long_press_fired = True
            self._apply_session_result(self.interactions.double_click())
```

Update `ask_mood`:

```python
        self.petdex_animator.set_action("think")
        result = self.music_session.recommend_from_text(text.strip())
        self._apply_session_result(result)
```

Update `play_number_dialog`:

```python
        result = self.music_session.play_number(number)
        self._apply_session_result(result)
```

- [ ] **Step 8: Add compact more menu**

Inside `PetdexWindow`, add:

```python
    def _show_more_menu(self) -> None:
        menu = self._build_context_menu()
        menu.exec(self.mapToGlobal(self._more_button.geometry().bottomLeft()))

    def _build_context_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.addAction(_action("推荐歌曲", lambda: self._apply_session_result(self.interactions.double_click()), self))
        menu.addAction(_action("自动开播", lambda: self._apply_session_result(self.interactions.long_press()), self))
        menu.addAction(_action("播放编号", self.play_number_dialog, self))
        menu.addAction(_action("当前播放", lambda: self._apply_session_result(self.interactions.quick_action("now")), self))
        menu.addAction(_action("暂停/继续", self.toggle_playback, self))
        menu.addAction(_action("下一首", self.next_track, self))
        pet_menu = menu.addMenu("切换宠物")
        for pet in self._installed_pets:
            pet_menu.addAction(_action(pet.name, lambda next_pet=pet: self.set_petdex_pet(next_pet), self))
        if not self._installed_pets:
            pet_menu.addAction(_action("未发现本地宠物", lambda: self._show_bubble("未发现本地 Petdex 宠物"), self))
        menu.addSeparator()
        menu.addAction(_action("退出", self.close, self))
        return menu
```

Replace `contextMenuEvent` with:

```python
    def contextMenuEvent(self, event) -> None:
        self._build_context_menu().exec(event.globalPos())
```

- [ ] **Step 9: Run pet-related tests**

Run:

```bash
pytest tests/test_pet_*.py -q
```

Expected: all pet tests pass.

- [ ] **Step 10: Commit**

Run:

```bash
git add coding_with_beat/pet/window.py tests/test_pet_session.py
git commit -m "feat(pet): wire dj interactions into window"
```

---

### Task 6: Wire Built-In Pet Window to the Same Session

**Files:**
- Modify: `coding_with_beat/pet/window.py`
- Test: `tests/test_pet_session.py`, `tests/test_pet_interactions.py`, existing pet tests

- [ ] **Step 1: Ensure pure interaction tests cover both window modes indirectly**

Run:

```bash
pytest tests/test_pet_session.py tests/test_pet_interactions.py -q
```

Expected: all tests pass before touching the built-in window.

- [ ] **Step 2: Add session and interaction fields to `PetWindow.__init__`**

Inside `PetWindow.__init__`, after `self.controller = ...`, add:

```python
        self.music_session = PetMusicSession(music=self.controller.music, load_state=self.controller.load_state)
        self.interactions = PetInteractionController(session=self.music_session)
        self._long_press_fired = False
        self._long_press_timer = QTimer(self)
        self._long_press_timer.setSingleShot(True)
        self._long_press_timer.timeout.connect(self._handle_long_press)
```

- [ ] **Step 3: Replace built-in window buttons with icon action strip**

Use the same `_icon_button` setup as `PetdexWindow`:

```python
        self._recommend_button = _icon_button("✨", "按当前状态推荐")
        self._recommend_button.clicked.connect(lambda: self._apply_session_result(self.interactions.quick_action("recommend")))
        self._now_button = _icon_button("♪", "当前播放")
        self._now_button.clicked.connect(lambda: self._apply_session_result(self.interactions.quick_action("now")))
        self._reroll_button = _icon_button("🎲", "换一组")
        self._reroll_button.clicked.connect(lambda: self._apply_session_result(self.interactions.quick_action("reroll")))
        self._skin_button = _icon_button("⋯", "更多")
        self._skin_button.clicked.connect(self._show_more_menu)
```

- [ ] **Step 4: Add built-in window result application and long press**

Inside `PetWindow`, add:

```python
    def _apply_session_result(self, result: PetSessionResult) -> None:
        self.controller.animator.set_action(result.action)
        self._show_bubble(result.card.text)
        self._track_label.setText(self.controller.current_track_label())

    def _handle_long_press(self) -> None:
        self._long_press_fired = True
        self._apply_session_result(self.interactions.long_press())
```

Update built-in `mousePressEvent`, `mouseReleaseEvent`, and `mouseDoubleClickEvent` with the same timer pattern from Task 5, replacing `self.petdex_animator.set_action(...)` with `self.controller.animator.set_action(...)`.

- [ ] **Step 5: Add built-in more menu**

Inside `PetWindow`, add:

```python
    def _show_more_menu(self) -> None:
        menu = self._build_context_menu()
        menu.exec(self.mapToGlobal(self._skin_button.geometry().bottomLeft()))

    def _build_context_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.addAction(_action("推荐歌曲", lambda: self._apply_session_result(self.interactions.double_click()), self))
        menu.addAction(_action("自动开播", lambda: self._apply_session_result(self.interactions.long_press()), self))
        menu.addAction(_action("播放编号", self.play_number_dialog, self))
        menu.addAction(_action("当前播放", lambda: self._apply_session_result(self.interactions.quick_action("now")), self))
        menu.addAction(_action("暂停/继续", self.toggle_playback, self))
        menu.addAction(_action("下一首", self.next_track, self))
        skin_menu = menu.addMenu("切换内置皮肤")
        for skin_id, skin in BUILTIN_SKINS.items():
            skin_menu.addAction(_action(skin.name, lambda sid=skin_id: self.set_skin(sid), self))
        menu.addSeparator()
        menu.addAction(_action("退出", self.close, self))
        return menu
```

Replace built-in `contextMenuEvent` with:

```python
    def contextMenuEvent(self, event) -> None:
        self._build_context_menu().exec(event.globalPos())
```

- [ ] **Step 6: Run pet tests**

Run:

```bash
pytest tests/test_pet_*.py -q
```

Expected: all pet tests pass.

- [ ] **Step 7: Commit**

Run:

```bash
git add coding_with_beat/pet/window.py
git commit -m "feat(pet): share dj flow with built-in pet"
```

---

### Task 7: Update Documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update desktop pet usage text**

In `README.md`, replace the current Petdex mode bullets with:

```markdown
Petdex mode:

- The pet stays compact by default: sprite animation plus a short current-status line.
- Single-click shows the current playback/status bubble.
- Double-click asks DJ Buddy to recommend from the current coding vibe.
- Long-press auto-starts music from the current coding vibe.
- The compact action strip uses `♪`, `✨`, `🎲`, and `⋯` for now playing, recommend, reroll, and more.
- Right-click remains available for play/pause, next track, play by number, pet switching, and quit.
- The `⋯` menu cycles local Petdex pets discovered in `~/.coding-with-beat/petdex/`, `~/.petdex/pets/`, and `~/.codex/pets/`.
- The last selected Petdex pet is saved and used by the next `cwb pet` launch.
```

- [ ] **Step 2: Check README for stale button wording**

Run:

```bash
rg -n "推荐`, `在播`, and `皮肤`|Double-click it to ask|button row|按钮" README.md
```

Expected: no stale text claiming the old permanent `推荐/在播/皮肤` button row is the main flow.

- [ ] **Step 3: Commit**

Run:

```bash
git add README.md
git commit -m "docs: update desktop pet dj flow usage"
```

---

### Task 8: Full Verification and Local Launch

**Files:**
- No source files unless verification exposes a bug.

- [ ] **Step 1: Run linter**

Run:

```bash
ruff check coding_with_beat tests
```

Expected: `All checks passed!`

- [ ] **Step 2: Run full test suite**

Run:

```bash
pytest -q
```

Expected: all tests pass.

- [ ] **Step 3: Restart the local desktop pet**

Run:

```bash
launchctl remove cwb-petdex-boba 2>/dev/null || true
launchctl submit -l cwb-petdex-boba -- /bin/zsh -lc 'cd /Users/jianchengpan/Projects/coding-with-beat && /Users/jianchengpan/miniconda3/bin/python -m coding_with_beat pet >/tmp/cwb-petdex-launchctl.log 2>&1'
sleep 2
launchctl list | rg 'cwb-petdex-boba' || true
tail -80 /tmp/cwb-petdex-launchctl.log 2>/dev/null || true
```

Expected: launchctl lists `cwb-petdex-boba` and the log has no traceback.

- [ ] **Step 4: Manual smoke test**

Perform these checks on the running desktop pet:

```text
1. Single-click pet -> compact current status bubble appears.
2. Double-click pet -> recommendation card appears; no song auto-plays.
3. Click or choose play number -> selected result plays and pet dances.
4. Click 🎲 -> a new recommendation set appears.
5. Long-press pet -> recommendation runs and number 1 auto-plays.
6. Right-click -> fallback menu includes play/pause, next, play by number, pet switching, quit.
```

Expected: the pet remains compact and does not expand into a large raw-output panel.

- [ ] **Step 5: Commit any verification fixes**

If Step 1-4 required fixes, commit them:

```bash
git add coding_with_beat tests README.md
git commit -m "fix(pet): polish dj flow verification"
```

If no fixes were required, do not create an empty commit.

---

## Self-Review

Spec coverage:

- Ambient status is covered by Tasks 5 and 6 through compact window wiring and state animation reuse.
- DJ Buddy interaction is covered by Tasks 3, 4, 5, and 6.
- Long-press auto-play is covered by Tasks 3, 4, 5, 6, and Task 8 manual verification.
- Reroll is covered by Tasks 1, 3, 4, 5, and 8.
- Compact cards are covered by Task 2.
- Component boundaries are covered by Tasks 1-4.
- Error handling is covered by Tasks 2 and 3.
- Documentation is covered by Task 7.
- Verification and local launch are covered by Task 8.

Placeholder scan:

- The plan contains no unresolved markers, empty implementation steps, or unspecified tests.
- Every new module has concrete code snippets and focused tests.

Type consistency:

- `DjIntent`, `DjQuerySet`, `PetBubbleCard`, `PetSessionResult`, `PetMusicSession`, and `PetInteractionController` are introduced before use in later tasks.
- Later window steps use the same method names defined in earlier tasks: `recommend_from_context`, `recommend_from_text`, `auto_play_from_context`, `reroll`, `play_number`, and `quick_action`.
