import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QPushButton

from coding_with_beat.pet.bubble import PetBubbleCard, PetResultItem
from coding_with_beat.pet.dj_panel import CodeBeatDjPanel
from coding_with_beat.pet.session import PetSessionResult


class FakeSession:
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
    buttons = [button.text() for button in panel.findChildren(QPushButton)]

    assert app is not None
    assert panel.scroll_area.widgetResizable() is True
    assert "1" in panel.transcript_text()
    assert "Night Owl - Luna" in panel.transcript_text()
    assert buttons.count("播放") == 2


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
    play_button = next(button for button in panel.findChildren(QPushButton) if button.text() == "播放")
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
