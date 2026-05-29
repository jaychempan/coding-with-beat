import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QFrame, QLabel, QPushButton

from coding_with_beat.pet.bubble import PetBubbleCard, PetResultItem
from coding_with_beat.pet.dj_panel import CodeBeatDjPanel
from coding_with_beat.pet.session import PetSessionResult


class FakeSession:
    def __init__(self):
        self.music = FakePanelMusic()

    def recommend_from_context(self):
        return PetSessionResult(True, "recommend", PetBubbleCard("status", "context"))

    def reroll(self):
        return PetSessionResult(True, "recommend", PetBubbleCard("status", "reroll"))

    def now_playing(self):
        return PetSessionResult(True, "idle", PetBubbleCard("status", "now"))

    def recommend_from_text(self, text):
        return PetSessionResult(True, "recommend", PetBubbleCard("status", text))

    def play_number(self, number):
        return PetSessionResult(True, "dance", PetBubbleCard("confirmation", f"play {number}"))


class FakeHost:
    def __init__(self):
        self.music_session = FakeSession()
        self.calls = []
        self.pending = []

    def _run_pet_command(self, command, pending_text="思考中..."):
        self.pending.append(pending_text)
        self.calls.append(command())


class FakePanelMusic:
    def __init__(self):
        self.controls = []
        self.snapshots = []

    def now_playing_snapshot(self, known_lyrics_key=""):
        self.snapshots.append(known_lyrics_key)
        return type(
            "Result",
            (),
            {
                "ok": True,
                "text": json.dumps(
                    {
                        "title": "Night Owl",
                        "artist": "Luna",
                        "source": "apple_music",
                        "position": 10.0,
                        "duration": 20.0,
                        "playing": True,
                        "lyrics_key": "apple_music\\0Luna\\0Album\\0Night Owl",
                        "lyrics_text": "first\nsecond\nthird\n",
                        "lyrics_pending": False,
                    }
                ),
            },
        )()

    def control(self, tool, kwargs):
        self.controls.append((tool, kwargs))
        return type("Result", (), {"ok": True, "text": f"{tool}:{kwargs}"})()


def test_dj_panel_renders_recommendations_with_direct_play_buttons():
    app = QApplication.instance() or QApplication([])
    host = FakeHost()
    panel = CodeBeatDjPanel(host)
    result = PetSessionResult(
        True,
        "recommend",
        PetBubbleCard(
            "recommendations",
            "Debug flow\n找到这些",
            items=[
                PetResultItem(1, "Night Owl - Luna"),
                PetResultItem(2, "Rain Debug - Soft Keys"),
            ],
        ),
    )

    panel.show_result(result)
    queue_buttons = [button for button in panel.findChildren(QPushButton) if button.objectName() == "QueuePlayButton"]

    assert app is not None
    assert panel.scroll_area.widgetResizable() is True
    assert "1" in panel.transcript_text()
    assert "Night Owl - Luna" in panel.transcript_text()
    assert [button.text() for button in queue_buttons] == ["▶", "▶"]


def test_dj_panel_play_button_runs_play_number_without_manual_number_dialog():
    app = QApplication.instance() or QApplication([])
    host = FakeHost()
    panel = CodeBeatDjPanel(host)
    result = PetSessionResult(
        True,
        "recommend",
        PetBubbleCard(
            "recommendations",
            "Debug flow",
            items=[PetResultItem(2, "Rain Debug - Soft Keys")],
        ),
    )

    panel.show_result(result)
    play_button = next(button for button in panel.findChildren(QPushButton) if button.objectName() == "QueuePlayButton")
    play_button.click()

    assert app is not None
    assert host.pending[-1] == "正在播放第 2 首..."
    assert host.calls[-1].card.text == "play 2"


def test_dj_panel_text_prompt_runs_text_recommendation():
    app = QApplication.instance() or QApplication([])
    host = FakeHost()
    panel = CodeBeatDjPanel(host)

    panel.prompt_input.setText("来点爵士")
    panel.submit_prompt()

    assert app is not None
    assert host.pending[-1] == "正在按你的描述找歌..."
    assert host.calls[-1].card.text == "来点爵士"


def test_dj_panel_has_profile_identity_stats_and_chips():
    app = QApplication.instance() or QApplication([])
    panel = CodeBeatDjPanel(FakeHost())

    assert app is not None
    assert panel.findChild(QLabel, "DjTitle").text() == "CodeBeat DJ"
    assert "mood" in panel.findChild(QLabel, "DjSubtitle").text().lower()
    assert panel.findChild(QLabel, "StatOnAirValue").text() == "LIVE"
    assert panel.findChild(QLabel, "StatMoodValue").text() == "IDLE"
    assert panel.findChild(QLabel, "StatQueueValue").text() == "0"
    assert "LOFI" in panel.chip_text()
    assert "NO VOCAL" in panel.chip_text()


def test_dj_panel_updates_queue_stat_when_recommendations_render():
    app = QApplication.instance() or QApplication([])
    panel = CodeBeatDjPanel(FakeHost())
    result = PetSessionResult(
        True,
        "recommend",
        PetBubbleCard(
            "recommendations",
            "Debug flow",
            items=[
                PetResultItem(1, "Night Owl - Luna"),
                PetResultItem(2, "Rain Debug - Soft Keys"),
                PetResultItem(3, "Green Terminal - Byte"),
            ],
        ),
    )

    panel.show_result(result)

    assert app is not None
    assert panel.findChild(QLabel, "StatMoodValue").text() == "FOCUS"
    assert panel.findChild(QLabel, "StatQueueValue").text() == "3"


def test_dj_panel_queue_rows_use_profile_objects_and_play_controls():
    app = QApplication.instance() or QApplication([])
    panel = CodeBeatDjPanel(FakeHost())
    result = PetSessionResult(
        True,
        "recommend",
        PetBubbleCard(
            "recommendations",
            "Debug flow",
            items=[PetResultItem(1, "Night Owl - Luna")],
        ),
    )

    panel.show_result(result)
    row = panel.findChild(QFrame, "QueueRow")
    play_button = next(button for button in panel.findChildren(QPushButton) if button.objectName() == "QueuePlayButton")

    assert app is not None
    assert row is not None
    assert play_button.text() == "▶"
    assert panel.prompt_input.objectName() == "DjPromptInput"


def test_dj_panel_renders_live_snapshot_and_current_lyric():
    app = QApplication.instance() or QApplication([])
    host = FakeHost()
    panel = CodeBeatDjPanel(host)

    panel.refresh_live_snapshot()

    assert app is not None
    assert panel.findChild(QLabel, "NowTitle").text() == "Night Owl"
    assert "Luna" in panel.findChild(QLabel, "NowMeta").text()
    assert panel.findChild(QLabel, "NowLyric").text() == "second"
    assert panel._live_playing is True


def test_dj_panel_prompt_slash_command_routes_to_cwb_control():
    app = QApplication.instance() or QApplication([])
    host = FakeHost()
    panel = CodeBeatDjPanel(host)

    panel.prompt_input.setText("/volume 70")
    panel.submit_prompt()

    assert app is not None
    assert host.music_session.music.controls == [("set_volume", {"percent": 70})]
    assert "set_volume" in panel.transcript_text()


def test_dj_panel_motion_timer_runs_only_while_visible():
    app = QApplication.instance() or QApplication([])
    panel = CodeBeatDjPanel(FakeHost())

    panel.show()
    app.processEvents()
    assert panel._animation_timer.isActive() is True
    panel.hide()
    app.processEvents()
    assert panel._animation_timer.isActive() is False
