# tests/test_vibe_companion.py
import time
import unittest
from types import SimpleNamespace

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
