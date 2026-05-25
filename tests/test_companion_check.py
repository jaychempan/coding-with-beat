# tests/test_companion_check.py
import asyncio
import time
import unittest
from types import SimpleNamespace
from unittest import mock

from coding_with_beat import server


def _run(coro):
    return asyncio.run(coro)


def _mock_state(companion_last_at=0.0, companion_failure_streak=0, companion_tool_count=0, companion_session_start=0.0):
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

    @mock.patch("coding_with_beat.server.state")
    @mock.patch("coding_with_beat.server._multi_angle_search")
    @mock.patch("coding_with_beat.server.get_source")
    def test_companion_check_shows_loved_picks_when_available(self, mock_gs, mock_search, mock_state):
        mock_state.load.return_value = _mock_state()
        mock_search.return_value = "1. Song — Artist [资料库]"

        loved_src = mock.MagicMock()
        loved_src.list_loved.return_value = [
            {"title": "My Fave", "artist": "DJ X", "album": "A", "source": "loved"},
            {"title": "Heart Track", "artist": "DJ Y", "album": "B", "source": "loved"},
            {"title": "Love This", "artist": "DJ Z", "album": "C", "source": "loved"},
        ]
        mock_gs.return_value = loved_src

        result = _run(server.companion_check("session_start"))
        assert result != "(not needed right now)"
        assert "[♥ 喜欢]" in result or any(t in result for t in ["My Fave", "Heart Track", "Love This"])

    @mock.patch("coding_with_beat.server.state")
    @mock.patch("coding_with_beat.server._multi_angle_search")
    @mock.patch("coding_with_beat.server.get_source")
    def test_companion_check_falls_back_when_no_loved(self, mock_gs, mock_search, mock_state):
        mock_state.load.return_value = _mock_state()
        mock_search.return_value = "1. Song — Artist [资料库]"

        loved_src = mock.MagicMock()
        loved_src.list_loved.return_value = []
        mock_gs.return_value = loved_src

        result = _run(server.companion_check("session_start"))
        assert result != "(not needed right now)"
        assert "Song" in result
