# Companion Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a proactive DJ Buddy companion that checks in at key coding moments (session start/end, debug struggles, victories, idle periods) with caring messages and music suggestions.

**Architecture:** A new `companion.py` module holds all trigger logic, message pools, and query mappings. `JukeboxState` gains 4 companion-tracking fields. The `companion_check()` MCP tool is called by Claude at trigger moments; SessionStart/Stop hooks print lightweight greeting/farewell cards directly. A `cwb-companion` skill tells Claude when and how to call the tool.

**Tech Stack:** Python 3.13, FastMCP, existing `dj`, `state`, `server` modules, `unittest` + `mock` for tests.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `coding_with_beat/companion.py` | Create | Trigger logic, message pools, query mappings |
| `coding_with_beat/state.py` | Modify | Add 4 companion fields to `JukeboxState` |
| `coding_with_beat/vibe.py` | Modify | SessionStart/PostToolUse/Stop hook enhancements |
| `coding_with_beat/server.py` | Modify | `companion_check()` MCP tool + `_companion_card()` helper |
| `skills/cwb-companion/SKILL.md` | Create | Claude trigger rules and presentation guidance |
| `install.sh` | Modify | Inject `cwb-companion` block into `~/.claude/CLAUDE.md` |
| `tests/test_companion.py` | Create | Unit tests for companion.py |
| `tests/test_vibe_companion.py` | Create | Tests for vibe.py companion tracking |
| `tests/test_companion_check.py` | Create | Tests for companion_check MCP tool |

---

## Task 1: `companion.py` — core logic

**Files:**
- Create: `coding_with_beat/companion.py`
- Create: `tests/test_companion.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_companion.py
import time
import unittest
from types import SimpleNamespace
from unittest import mock

from coding_with_beat import companion


def _st(**kwargs):
    defaults = {
        "companion_last_at": 0.0,
        "companion_session_start": 0.0,
        "companion_failure_streak": 0,
        "companion_tool_count": 0,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestCanTrigger(unittest.TestCase):
    def test_cooldown_blocks_when_recent(self):
        st = _st(companion_last_at=time.time() - 100)
        for t in ("session_start", "debug_struggle", "victory", "idle_checkin", "session_end"):
            self.assertFalse(companion.can_trigger(st, t), f"should block {t} during cooldown")

    def test_session_start_passes_when_no_cooldown(self):
        self.assertTrue(companion.can_trigger(_st(), "session_start"))

    def test_victory_passes_when_no_cooldown(self):
        self.assertTrue(companion.can_trigger(_st(), "victory"))

    def test_debug_struggle_needs_failure_streak_of_3(self):
        self.assertFalse(companion.can_trigger(_st(companion_failure_streak=2), "debug_struggle"))
        self.assertTrue(companion.can_trigger(_st(companion_failure_streak=3), "debug_struggle"))

    def test_idle_checkin_needs_20_tool_calls(self):
        self.assertFalse(companion.can_trigger(_st(companion_tool_count=19), "idle_checkin"))
        self.assertTrue(companion.can_trigger(_st(companion_tool_count=20), "idle_checkin"))

    def test_session_end_needs_300s_session(self):
        self.assertFalse(
            companion.can_trigger(_st(companion_session_start=time.time() - 100), "session_end")
        )
        self.assertTrue(
            companion.can_trigger(_st(companion_session_start=time.time() - 301), "session_end")
        )


class TestGetMessageAndQueries(unittest.TestCase):
    def test_get_message_returns_nonempty_string_for_all_triggers(self):
        st = _st()
        for t in ("session_start", "debug_struggle", "victory", "idle_checkin", "session_end"):
            msg = companion.get_message(t, st)
            self.assertIsInstance(msg, str)
            self.assertGreater(len(msg), 0)

    def test_get_queries_returns_list_of_2_plus_strings(self):
        for t in ("session_start", "debug_struggle", "victory", "idle_checkin", "session_end"):
            queries = companion.get_queries(t)
            self.assertIsInstance(queries, list)
            self.assertGreaterEqual(len(queries), 2)
            for q in queries:
                self.assertIsInstance(q, str)
                self.assertGreater(len(q), 0)

    def test_session_start_morning_evening_differ(self):
        st = _st()
        with mock.patch("coding_with_beat.companion._dt") as m:
            m.now.return_value.hour = 9
            q_morning = companion.get_queries("session_start")
            m.now.return_value.hour = 22
            q_evening = companion.get_queries("session_start")
        self.assertNotEqual(q_morning, q_evening)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/jianchengpan/Projects/coding-with-beat
python -m pytest tests/test_companion.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'coding_with_beat.companion'`

- [ ] **Step 3: Create `coding_with_beat/companion.py`**

```python
"""Companion mode: proactive check-ins and context-aware music suggestions."""
from __future__ import annotations

import random
import time
from datetime import datetime as _dt
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .state import JukeboxState

COOLDOWN_SECS = 900
FAILURE_THRESHOLD = 3
IDLE_TOOLS_THRESHOLD = 20
MIN_SESSION_SECS = 300

MESSAGES: dict[str, list[str]] = {
    "session_start_morning": [
        "早！今天想专注什么？我先挑首暖场的",
        "早安——先把节奏拉起来？",
        "新的一天，来首有劲的开场",
    ],
    "session_start_evening": [
        "又到深夜了——来首 lofi 陪你",
        "晚上好，今天还要鏖战？给你挑首夜间编程的",
        "深夜模式启动——来点节奏感的",
    ],
    "debug_struggle": [
        "调了挺久了，先歇口气——换首轻松的？",
        "bug 有点难缠。先让耳朵放个假？",
        "连续在 debug……先听首舒缓的，思路说不定就来了",
    ],
    "victory": [
        "✓ 成了！该庆祝一下",
        "搞定了！来首应景的庆功曲",
        "测试全绿，今天不错——来点带劲的",
    ],
    "idle_checkin": [
        "你还好吧？忙了一阵了——音乐还合适吗",
        "一直在专注——要不要换个曲风换换脑子？",
        "工作了好一会儿了，我给你找首新的？",
    ],
    "session_end": [
        "收工了，辛苦了——来首舒缓的慢慢降落",
        "今天到这里了，来首放松的结个尾",
        "下班！来首解压的——你赢得了它",
    ],
}

QUERIES: dict[str, list[str]] = {
    "session_start_morning": [
        "morning fresh indie pop upbeat",
        "coffee acoustic gentle start of day",
        "morning motivation energy focus",
    ],
    "session_start_evening": [
        "lofi late night coding chill",
        "night session ambient focus instrumental",
        "synthwave night drive electronic",
    ],
    "debug_struggle": [
        "calm piano breathe relax stress relief",
        "lofi chill gentle decompress",
        "acoustic soft peaceful unwind",
    ],
    "victory": [
        "celebration feel good indie pop",
        "victory upbeat dance energetic",
        "achievement summer bright positive",
    ],
    "idle_checkin": [
        "background lofi focus no distraction",
        "ambient flow state instrumental",
        "study chill rain cafe cozy",
    ],
    "session_end": [
        "wind down gentle piano evening",
        "soft acoustic relax unwind peaceful",
        "end of day calm slow",
    ],
}


def _trigger_key(trigger: str) -> str:
    if trigger == "session_start":
        return "session_start_morning" if 6 <= _dt.now().hour < 18 else "session_start_evening"
    return trigger


def can_trigger(st: "JukeboxState", trigger: str) -> bool:
    now = time.time()
    if now - st.companion_last_at < COOLDOWN_SECS:
        return False
    if trigger == "debug_struggle":
        return st.companion_failure_streak >= FAILURE_THRESHOLD
    if trigger == "idle_checkin":
        return st.companion_tool_count >= IDLE_TOOLS_THRESHOLD
    if trigger == "session_end":
        return (now - st.companion_session_start) >= MIN_SESSION_SECS
    return True


def get_message(trigger: str, st: "JukeboxState") -> str:
    key = _trigger_key(trigger)
    pool = MESSAGES.get(key, MESSAGES["idle_checkin"])
    return random.choice(pool)


def get_queries(trigger: str) -> list[str]:
    key = _trigger_key(trigger)
    return QUERIES.get(key, QUERIES["idle_checkin"])
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_companion.py -v
```

Expected: all 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add coding_with_beat/companion.py tests/test_companion.py
git commit -m "feat(companion): add companion.py — trigger logic, message pools, queries"
```

---

## Task 2: `state.py` — add companion fields to `JukeboxState`

**Files:**
- Modify: `coding_with_beat/state.py`

- [ ] **Step 1: Write failing test**

```python
# Add to tests/test_companion.py (append at end of file)

class TestJukeboxStateCompanionFields(unittest.TestCase):
    def test_defaults_are_zero(self):
        from coding_with_beat.state import JukeboxState
        st = JukeboxState()
        self.assertEqual(st.companion_last_at, 0.0)
        self.assertEqual(st.companion_session_start, 0.0)
        self.assertEqual(st.companion_failure_streak, 0)
        self.assertEqual(st.companion_tool_count, 0)

    def test_load_without_fields_returns_defaults(self):
        import json
        import tempfile
        from pathlib import Path
        from unittest import mock
        from coding_with_beat import state as st_mod

        old_state = {"playing": False, "source": "apple_music", "volume": 60,
                     "track": {}, "vibe": "focus", "dj_mood": "neutral"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(old_state, f)
            path = Path(f.name)
        with mock.patch.object(st_mod, "STATE_FILE", path):
            loaded = st_mod.load()
        self.assertEqual(loaded.companion_last_at, 0.0)
        self.assertEqual(loaded.companion_failure_streak, 0)
        path.unlink(missing_ok=True)
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
python -m pytest tests/test_companion.py::TestJukeboxStateCompanionFields -v
```

Expected: `AttributeError: 'JukeboxState' object has no attribute 'companion_last_at'`

- [ ] **Step 3: Add fields to `JukeboxState` in `coding_with_beat/state.py`**

After `last_tool_at: float = 0.0` (line 43), add:

```python
    companion_last_at: float = 0.0
    companion_session_start: float = 0.0
    companion_failure_streak: int = 0
    companion_tool_count: int = 0
```

The full `JukeboxState` class should now end with:
```python
    last_tool_at: float = 0.0
    statusline_mode: str = "show"  # show | hide | auto
    companion_last_at: float = 0.0
    companion_session_start: float = 0.0
    companion_failure_streak: int = 0
    companion_tool_count: int = 0
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_companion.py -v
```

Expected: all 11 tests PASS

- [ ] **Step 5: Run full test suite to check no regressions**

```bash
python -m pytest --tb=short -q
```

Expected: all tests pass (companion fields have defaults so existing state files load fine)

- [ ] **Step 6: Commit**

```bash
git add coding_with_beat/state.py tests/test_companion.py
git commit -m "feat(companion): add companion tracking fields to JukeboxState"
```

---

## Task 3: `vibe.py` — hook enhancements

**Files:**
- Modify: `coding_with_beat/vibe.py`
- Create: `tests/test_vibe_companion.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_vibe_companion.py
import time
import unittest
from types import SimpleNamespace
from unittest import mock

from coding_with_beat import vibe


class TestIsTestCommand(unittest.TestCase):
    def test_recognises_pytest(self):
        self.assertTrue(vibe._is_test_command("pytest tests/"))

    def test_recognises_npm_test(self):
        self.assertTrue(vibe._is_test_command("npm test"))

    def test_recognises_jest(self):
        self.assertTrue(vibe._is_test_command("jest --watch"))

    def test_ignores_regular_bash(self):
        self.assertFalse(vibe._is_test_command("git commit -m 'fix'"))
        self.assertFalse(vibe._is_test_command("ls -la"))


class TestUpdateCompanionTracking(unittest.TestCase):
    def _make_state(self):
        return SimpleNamespace(
            companion_failure_streak=0,
            companion_tool_count=0,
        )

    def test_increments_tool_count_always(self):
        st = self._make_state()
        event = {"tool_name": "Read", "tool_input": {}, "tool_response": {}}
        vibe._update_companion_tracking(st, event)
        self.assertEqual(st.companion_tool_count, 1)

    def test_increments_failure_streak_on_failed_test(self):
        st = self._make_state()
        event = {
            "tool_name": "Bash",
            "tool_input": {"command": "pytest tests/"},
            "tool_response": {"success": False, "stderr": "FAILED test_foo.py::test_bar"},
        }
        vibe._update_companion_tracking(st, event)
        self.assertEqual(st.companion_failure_streak, 1)

    def test_resets_failure_streak_on_passing_test(self):
        st = self._make_state()
        st.companion_failure_streak = 5
        event = {
            "tool_name": "Bash",
            "tool_input": {"command": "pytest tests/"},
            "tool_response": {"success": True, "stderr": ""},
        }
        vibe._update_companion_tracking(st, event)
        self.assertEqual(st.companion_failure_streak, 0)

    def test_does_not_change_streak_for_non_test_bash(self):
        st = self._make_state()
        st.companion_failure_streak = 2
        event = {
            "tool_name": "Bash",
            "tool_input": {"command": "git status"},
            "tool_response": {"success": False, "stderr": "error"},
        }
        vibe._update_companion_tracking(st, event)
        self.assertEqual(st.companion_failure_streak, 2)


class TestBuildSessionCards(unittest.TestCase):
    def test_greeting_contains_nonempty_string(self):
        st = SimpleNamespace(companion_session_start=time.time())
        card = vibe._build_session_greeting(st)
        self.assertIsInstance(card, str)
        self.assertGreater(len(card), 10)

    def test_farewell_contains_nonempty_string(self):
        st = SimpleNamespace(companion_session_start=time.time() - 600)
        card = vibe._build_session_farewell(st)
        self.assertIsInstance(card, str)
        self.assertGreater(len(card), 10)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_vibe_companion.py -v 2>&1 | head -20
```

Expected: `AttributeError` — `_is_test_command`, `_update_companion_tracking`, `_build_session_greeting`, `_build_session_farewell` not yet defined.

- [ ] **Step 3: Add helpers to `coding_with_beat/vibe.py`**

Add these imports at the top of vibe.py (after existing imports):
```python
import datetime as _dt
```

Add these functions after the existing `_is_test_file()` function (around line 44):

```python
_TEST_KEYWORDS = ("pytest", "npm test", "jest", "go test", "cargo test", " test", "vitest")


def _is_test_command(cmd: str) -> bool:
    lc = cmd.lower()
    return any(k in lc for k in _TEST_KEYWORDS)


def _update_companion_tracking(st, event: dict) -> None:
    tool = (event.get("tool_name") or "").lower()
    tool_input = event.get("tool_input") or {}
    tool_response = event.get("tool_response") or {}
    cmd = tool_input.get("command") or ""
    if tool == "bash" and _is_test_command(cmd):
        ok = bool(tool_response.get("success", True))
        stderr = (tool_response.get("stderr") or "").lower()
        failed = ("fail" in stderr or "error" in stderr) and "0 failures" not in stderr
        if failed or not ok:
            st.companion_failure_streak += 1
        else:
            st.companion_failure_streak = 0
    st.companion_tool_count += 1


def _build_session_greeting(st) -> str:
    hour = _dt.datetime.now().hour
    if 6 <= hour < 12:
        greeting = "早安！新的一天开始了"
    elif 12 <= hour < 18:
        greeting = "下午好！继续保持"
    else:
        greeting = "晚上好——深夜写代码辛苦了"
    sprite = dj.pixel_person_frame("happy", 0, colored=False)
    return f"\n♪ · · · DJ Buddy · · · ♪\n{sprite}\n  {greeting}\n  说想听什么风格，我来找\n"


def _build_session_farewell(st) -> str:
    sprite = dj.sprite("sleep")  # SPRITES["sleep"] exists; PIXEL_FRAMES["sleep"] does not
    quip = dj.quip("sleep")
    return f"\n♪ · · · DJ Buddy · · · ♪\n{sprite}\n  {quip}\n  下次见 ♩\n"
```

- [ ] **Step 4: Update `handle_hook()` in `coding_with_beat/vibe.py`**

Replace the existing `handle_hook` function (lines 91–111) with:

```python
def handle_hook(event: dict) -> dict:
    mood, vibe = classify(event)
    st = state.load()
    prev_mood = st.dj_mood
    st.dj_mood = mood
    st.vibe = vibe

    hook = (event.get("hook_event_name") or "").lower()
    if hook in ("pretooluse", "posttooluse"):
        st.last_tool_at = time.time()
    if mood != prev_mood and mood in ("victory", "sad", "panic", "happy", "groove"):
        st.dj_quip = dj.quip(mood)
        st.dj_quip_at = time.time()
    elif hook == "stop":
        st.dj_quip = dj.quip("sleep")
        st.dj_quip_at = time.time()

    if hook == "sessionstart":
        st.companion_session_start = time.time()
        st.companion_failure_streak = 0
        st.companion_tool_count = 0
        st.companion_last_at = 0.0
    elif hook == "posttooluse":
        _update_companion_tracking(st, event)

    state.save(st)
    _log(f"hook {event.get('hook_event_name')} tool={event.get('tool_name')} → mood={mood} vibe={vibe}")

    if hook == "sessionstart":
        print(_build_session_greeting(st), flush=True)
    elif hook == "stop":
        from .companion import MIN_SESSION_SECS
        if (time.time() - st.companion_session_start) >= MIN_SESSION_SECS:
            print(_build_session_farewell(st), flush=True)

    return {"mood": mood, "vibe": vibe}
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/test_vibe_companion.py -v
```

Expected: all 11 tests PASS

- [ ] **Step 6: Run full test suite**

```bash
python -m pytest --tb=short -q
```

Expected: all tests pass

- [ ] **Step 7: Commit**

```bash
git add coding_with_beat/vibe.py tests/test_vibe_companion.py
git commit -m "feat(companion): enhance vibe.py hooks — session greeting/farewell + failure tracking"
```

---

## Task 4: `server.py` — `companion_check()` MCP tool

**Files:**
- Modify: `coding_with_beat/server.py`
- Create: `tests/test_companion_check.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_companion_check.py
import asyncio
import time
import unittest
from types import SimpleNamespace
from unittest import mock

from coding_with_beat import server


def _run(coro):
    return asyncio.run(coro)


def _mock_state(companion_last_at=0.0, companion_failure_streak=0,
                companion_tool_count=0, companion_session_start=0.0):
    return SimpleNamespace(
        source="apple_music",
        companion_last_at=companion_last_at,
        companion_failure_streak=companion_failure_streak,
        companion_tool_count=companion_tool_count,
        companion_session_start=companion_session_start,
    )


class TestCompanionCard(unittest.TestCase):
    def test_companion_card_contains_message_and_music(self):
        card = server._companion_card("调了挺久了——换首轻松的？", "1. 雨天 — 某某\n2. Quiet — FM")
        self.assertIn("调了挺久了", card)
        self.assertIn("雨天", card)


class TestCompanionCheck(unittest.TestCase):
    @mock.patch("coding_with_beat.server.state")
    @mock.patch("coding_with_beat.server._multi_angle_search")
    def test_returns_not_needed_when_cooldown_active(self, mock_search, mock_state):
        mock_state.load.return_value = _mock_state(companion_last_at=time.time() - 100)
        result = _run(server.companion_check("session_start"))
        self.assertEqual(result, "(not needed right now)")
        mock_search.assert_not_called()

    @mock.patch("coding_with_beat.server.state")
    @mock.patch("coding_with_beat.server._multi_angle_search")
    def test_returns_card_when_conditions_met(self, mock_search, mock_state):
        mock_state.load.return_value = _mock_state()
        mock_search.return_value = "1. Test Song — Artist [资料库]"
        result = _run(server.companion_check("session_start"))
        self.assertNotEqual(result, "(not needed right now)")
        self.assertIn("Test Song", result)
        mock_state.save.assert_called_once()

    @mock.patch("coding_with_beat.server.state")
    @mock.patch("coding_with_beat.server._multi_angle_search")
    def test_debug_struggle_blocked_without_streak(self, mock_search, mock_state):
        mock_state.load.return_value = _mock_state(companion_failure_streak=2)
        result = _run(server.companion_check("debug_struggle"))
        self.assertEqual(result, "(not needed right now)")

    @mock.patch("coding_with_beat.server.state")
    @mock.patch("coding_with_beat.server._multi_angle_search")
    def test_updates_companion_last_at_on_success(self, mock_search, mock_state):
        st = _mock_state()
        mock_state.load.return_value = st
        mock_search.return_value = "1. Song — Artist"
        _run(server.companion_check("victory"))
        self.assertGreater(st.companion_last_at, 0)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_companion_check.py -v 2>&1 | head -20
```

Expected: `AttributeError` — `_companion_card` and `companion_check` not yet defined in server.

- [ ] **Step 3: Add `_companion_card()` to `coding_with_beat/server.py`**

Add after the existing `_needs_library_add()` function (around line 218), before `_wait_and_play_from_library`:

```python
def _companion_card(message: str, music_results: str) -> str:
    frame_idx = int(time.time() * 2) % 3
    sprite = dj.pixel_person_frame("groove", frame_idx)  # colored=True, shown in CC terminal
    sprite_lines = sprite.splitlines()
    sprite_w = 10
    pad = "  "
    music_lines = music_results.splitlines()[:12]
    right_lines = [message, ""] + music_lines
    offset = max(0, (len(sprite_lines) - len(right_lines)) // 2)
    rows = []
    total = max(len(sprite_lines), len(right_lines) + offset)
    for i in range(total):
        sl = sprite_lines[i] if i < len(sprite_lines) else " " * sprite_w
        ri = i - offset
        rl = right_lines[ri] if 0 <= ri < len(right_lines) else ""
        rows.append(f"{sl}{pad}{rl}" if rl else sl)
    return "\n".join(rows)
```

- [ ] **Step 4: Add `companion_check()` MCP tool to `coding_with_beat/server.py`**

Add after the `dj_say()` tool function (around line 1037), before `vibe_set()`:

```python
@mcp.tool()
async def companion_check(trigger: str) -> str:
    """DJ Buddy companion check-in.

    trigger must be one of: session_start, debug_struggle, victory,
    idle_checkin, session_end.

    Call this proactively at key moments:
    - session_start: in your first reply of a new session
    - debug_struggle: after observing 3+ consecutive test/command failures
    - victory: right after a successful git commit or all tests passing
    - idle_checkin: after 20+ tool calls with no music suggestion in 25+ min
    - session_end: when the user signals they are done (bye, 收工, 下班, etc.)

    Returns a companion card with a caring message and music suggestions,
    or '(not needed right now)' if cooldown is active or conditions unmet.
    When '(not needed right now)' is returned, do NOT mention it to the user.
    """
    from . import companion as _companion
    st = state.load()
    if not _companion.can_trigger(st, trigger):
        return "(not needed right now)"
    queries = _companion.get_queries(trigger)
    try:
        music_results = await _multi_angle_search(queries, limit_per_query=4)
    except Exception:
        music_results = "(music search unavailable — say what you'd like to hear)"
    st.companion_last_at = time.time()
    state.save(st)
    message = _companion.get_message(trigger, st)
    return _companion_card(message, music_results)
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/test_companion_check.py -v
```

Expected: all 5 tests PASS

- [ ] **Step 6: Run full test suite**

```bash
python -m pytest --tb=short -q
```

Expected: all tests pass

- [ ] **Step 7: Commit**

```bash
git add coding_with_beat/server.py tests/test_companion_check.py
git commit -m "feat(companion): add companion_check() MCP tool and _companion_card() helper"
```

---

## Task 5: `cwb-companion` skill

**Files:**
- Create: `skills/cwb-companion/SKILL.md`

- [ ] **Step 1: Create directory and skill file**

```bash
mkdir -p /Users/jianchengpan/Projects/coding-with-beat/skills/cwb-companion
```

- [ ] **Step 2: Write `skills/cwb-companion/SKILL.md`**

```markdown
# cwb-companion — DJ Buddy Companion Mode

DJ Buddy is your coding companion. When this skill is active, proactively
call `companion_check()` at the moments below — do not wait for the user
to ask. The tool handles cooldown and conditions internally.

## Trigger rules

| Moment | Call |
|--------|------|
| Your first reply in a new session | `companion_check("session_start")` |
| You observe ≥ 3 consecutive test/command failures | `companion_check("debug_struggle")` |
| A `git commit` succeeds, or all tests pass green | `companion_check("victory")` |
| You've made ≥ 20 tool calls and haven't suggested music in 25+ minutes | `companion_check("idle_checkin")` |
| User says "收工", "下班", "bye", "晚安", "done for today", or similar | `companion_check("session_end")` |

## Presenting the result

**If the tool returns `(not needed right now)`:** stay silent. Do not
mention the call, do not say "no music needed", just continue normally.

**If the tool returns a companion card:** output it in full. You may add
one short transition phrase *before* the card (e.g. "对了——" or
"顺便——"). Do NOT add explanation or commentary after the card.

After showing the card, wait for the user to pick a number from the list.
When they do, call `play_number(N)` to play it.

## Tone

DJ Buddy speaks in short, warm, no-nonsense sentences.
"调了挺久了" beats "I noticed you've been debugging for quite some time."
Match DJ Buddy's energy, not a customer service bot's.
```

- [ ] **Step 3: Verify file created correctly**

```bash
cat /Users/jianchengpan/Projects/coding-with-beat/skills/cwb-companion/SKILL.md | head -5
```

Expected: shows the `# cwb-companion — DJ Buddy Companion Mode` header line.

- [ ] **Step 4: Commit**

```bash
git add skills/cwb-companion/SKILL.md
git commit -m "feat(companion): add cwb-companion skill — trigger rules and presentation guidance"
```

---

## Task 6: `install.sh` — inject companion block into `~/.claude/CLAUDE.md`

**Files:**
- Modify: `install.sh`

- [ ] **Step 1: Read the existing injection block in `install.sh`**

The existing block (around line 244) injects the `coding-with-beat` music routing rules.
It uses the pattern:
```bash
CWB_CLAUDE_BEGIN="# >>> coding-with-beat >>>"
CWB_CLAUDE_END="# <<< coding-with-beat <<<"
```
and writes a heredoc with `cat >> "$GLOBAL_CLAUDE_MD" <<'CLAUDEMD'`.

We add a **second idempotent block** for the companion rules, right after step 7 ends.

- [ ] **Step 2: Find the end of step 7 in `install.sh`**

```bash
grep -n "coding-with-beat\|CLAUDEMD\|companion" /Users/jianchengpan/Projects/coding-with-beat/install.sh | tail -20
```

Locate the line after the `CLAUDEMD` heredoc close that ends step 7.

- [ ] **Step 3: Add companion injection after the existing CLAUDEMD block**

Find the closing `CLAUDEMD` heredoc marker in step 7 (the line that says just `CLAUDEMD`). After it, and before the next section, add:

```bash

# 8. inject cwb-companion routing rules into ~/.claude/CLAUDE.md (idempotent)
COMPANION_BEGIN="# >>> cwb-companion >>>"
COMPANION_END="# <<< cwb-companion <<<"
inject_companion_claude_md() {
  if [ -f "$GLOBAL_CLAUDE_MD" ] && grep -q "$COMPANION_BEGIN" "$GLOBAL_CLAUDE_MD"; then
    awk "/$COMPANION_BEGIN/{found=1} !found{print} /$COMPANION_END/{found=0}" \
      "$GLOBAL_CLAUDE_MD" > "$GLOBAL_CLAUDE_MD.tmp" && mv "$GLOBAL_CLAUDE_MD.tmp" "$GLOBAL_CLAUDE_MD"
  fi
  cat >> "$GLOBAL_CLAUDE_MD" <<'COMPANIONMD'

# >>> cwb-companion >>>
# DJ Buddy companion mode — added by coding-with-beat install.sh

## Companion mode

When the `cwb-companion` skill is loaded, call `companion_check(trigger)`
proactively at these moments (the tool handles cooldown internally):

| Moment | trigger |
|--------|---------|
| First reply of a new session | `session_start` |
| 3+ consecutive test failures observed | `debug_struggle` |
| git commit success / tests all green | `victory` |
| 20+ tools used, no music in 25+ min | `idle_checkin` |
| User signals end of session | `session_end` |

If `companion_check` returns `(not needed right now)`, stay silent.
If it returns a card, output it in full (one short lead-in phrase is fine).
Wait for the user to pick a number, then call `play_number(N)`.
# <<< cwb-companion <<<
COMPANIONMD
}
inject_companion_claude_md
echo "  ✓ cwb-companion rules injected into $GLOBAL_CLAUDE_MD"
```

- [ ] **Step 4: Run install.sh on a test copy to verify injection works**

```bash
# Create a temp CLAUDE.md to test against
cp ~/.claude/CLAUDE.md /tmp/CLAUDE.md.bak
bash -c 'GLOBAL_CLAUDE_MD=/tmp/test_claude.md; touch "$GLOBAL_CLAUDE_MD"; source /Users/jianchengpan/Projects/coding-with-beat/install.sh 2>/dev/null; grep -c "cwb-companion" /tmp/test_claude.md'
```

Expected: output is `2` (begin + end markers both present). If that's awkward to run in isolation, instead:

```bash
grep -c "cwb-companion" ~/.claude/CLAUDE.md || echo "0"
```

Then run the actual `install.sh` and check the count increases to 2.

- [ ] **Step 5: Verify idempotency — run injection twice**

```bash
# Simulate running twice: call inject_companion_claude_md from a shell snippet
bash -c '
  GLOBAL_CLAUDE_MD=/tmp/test_idempotent.md
  touch "$GLOBAL_CLAUDE_MD"
  COMPANION_BEGIN="# >>> cwb-companion >>>"
  COMPANION_END="# <<< cwb-companion <<<"
  for i in 1 2; do
    if grep -q "$COMPANION_BEGIN" "$GLOBAL_CLAUDE_MD" 2>/dev/null; then
      awk "/$COMPANION_BEGIN/{found=1} !found{print} /$COMPANION_END/{found=0}" \
        "$GLOBAL_CLAUDE_MD" > "$GLOBAL_CLAUDE_MD.tmp" && mv "$GLOBAL_CLAUDE_MD.tmp" "$GLOBAL_CLAUDE_MD"
    fi
    printf "\n# >>> cwb-companion >>>\ntest content\n# <<< cwb-companion <<<\n" >> "$GLOBAL_CLAUDE_MD"
  done
  grep -c "cwb-companion" "$GLOBAL_CLAUDE_MD"
'
```

Expected: `2` (begin + end markers appear exactly once, not duplicated).

- [ ] **Step 6: Commit**

```bash
git add install.sh
git commit -m "feat(companion): inject cwb-companion rules into ~/.claude/CLAUDE.md via install.sh"
```

---

## Task 7: Integration smoke test

**Files:** None modified

- [ ] **Step 1: Run the full test suite one final time**

```bash
python -m pytest --tb=short -q
```

Expected: all tests pass, 0 failures.

- [ ] **Step 2: Verify companion_check appears in MCP tool list**

```bash
python -m coding_with_beat server &
sleep 2
python -m coding_with_beat.mcp_client list_tools 2>/dev/null | grep companion || echo "check server output manually"
kill %1 2>/dev/null
```

If `mcp_client` doesn't support `list_tools`, verify via:

```bash
python -c "from coding_with_beat.server import mcp; print([t.name for t in mcp._tool_manager.list_tools()])" 2>/dev/null | grep companion
```

Expected: `companion_check` appears in the output.

- [ ] **Step 3: Verify companion.py exports are importable**

```bash
python -c "
from coding_with_beat.companion import can_trigger, get_message, get_queries, COOLDOWN_SECS
from coding_with_beat.state import JukeboxState
st = JukeboxState()
print('can_trigger session_start:', can_trigger(st, 'session_start'))
print('get_message:', get_message('victory', st))
print('queries:', get_queries('debug_struggle'))
"
```

Expected: `can_trigger session_start: True`, a non-empty message string, a list of query strings.

- [ ] **Step 4: Final commit if any fixups were needed**

```bash
git add -p  # only if there were fixups
git commit -m "fix(companion): integration smoke test fixups"
```

---

## Self-Review Checklist

### Spec coverage

| Spec requirement | Covered by |
|---|---|
| `companion.py` module with `can_trigger`, `get_message`, `get_queries` | Task 1 |
| COOLDOWN_SECS=900, FAILURE_THRESHOLD=3, IDLE_TOOLS_THRESHOLD=20, MIN_SESSION_SECS=300 | Task 1 |
| 4 new fields on `JukeboxState` | Task 2 |
| SessionStart hook: init fields + print greeting | Task 3 |
| PostToolUse hook: update failure_streak + tool_count | Task 3 |
| Stop hook: print farewell if session ≥ 5 min | Task 3 |
| `companion_check()` MCP tool with cooldown gate | Task 4 |
| `_companion_card()` helper reusing dj sprites | Task 4 |
| `(not needed right now)` returned when blocked | Task 4 |
| `cwb-companion` skill with trigger table + tone guidance | Task 5 |
| `install.sh` injection of companion CLAUDE.md block | Task 6 |
| Idempotent injection | Task 6 step 5 |
