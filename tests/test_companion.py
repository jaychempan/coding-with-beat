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
        # All triggers with their preconditions satisfied, but cooldown active
        st = _st(
            companion_last_at=time.time() - 100,  # 100s < 900s cooldown
            companion_failure_streak=3,
            companion_tool_count=20,
            companion_session_start=time.time() - 301,
        )
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
            msg = companion.get_message(t)
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
