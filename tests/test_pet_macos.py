import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from coding_with_beat.pet.macos import (
    APP_NAME,
    PetMenuBarController,
    app_icon_path,
    hide_dock_icon,
    pet_icon_path,
)


class DummyWindow:
    def __init__(self) -> None:
        self.visible = True
        self.show_now_playing_called = False
        self.recommend_called = False
        self.next_track_called = False
        self.closed = False

    def isVisible(self) -> bool:
        return self.visible

    def hide(self) -> None:
        self.visible = False

    def show(self) -> None:
        self.visible = True

    def raise_(self) -> None:
        pass

    def activateWindow(self) -> None:
        pass

    def show_now_playing(self) -> None:
        self.show_now_playing_called = True

    def _run_pet_command(self, command, pending_text: str = "思考中...") -> None:
        self.recommend_called = True

    def next_track(self) -> None:
        self.next_track_called = True


def test_pet_icon_path_uses_repo_logo():
    path = pet_icon_path()

    assert path is not None
    assert path.name == "waveform_menu_bar.svg"
    assert path.exists()


def test_app_icon_path_uses_padded_waveform_logo():
    path = app_icon_path()

    assert path is not None
    assert path.name == "waveform_app_icon.svg"
    assert path.exists()


def test_hide_dock_icon_returns_false_on_non_macos(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")

    assert hide_dock_icon() is False


def test_menu_bar_controller_builds_expected_menu_actions():
    app = QApplication.instance() or QApplication([])
    window = DummyWindow()

    controller = PetMenuBarController(app, window)

    labels = [action.text() for action in controller.menu.actions() if action.text()]
    assert APP_NAME == "Coding With Beat Pet"
    assert labels == ["显示/隐藏宠物", "当前播放", "推荐歌曲", "下一首", "退出"]


def test_menu_bar_controller_toggles_window_visibility():
    app = QApplication.instance() or QApplication([])
    window = DummyWindow()
    controller = PetMenuBarController(app, window)

    controller.toggle_window()
    assert window.visible is False

    controller.toggle_window()
    assert window.visible is True
