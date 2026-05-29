import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from coding_with_beat.pet.macos import (
    APP_NAME,
    CodeBeatControlWindow,
    PetMenuBarController,
    _collection_behavior_with_pet_flags,
    app_icon_path,
    hide_dock_icon,
    menu_bar_icon,
    pet_icon_path,
    set_dock_icon_visible,
)
from coding_with_beat.pet.settings import PetSettings


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


def test_pet_icon_path_matches_app_icon():
    path = pet_icon_path()

    assert path is not None
    assert path == app_icon_path()
    assert path.name == "waveform_app_icon.svg"
    assert path.exists()


def test_app_icon_path_uses_padded_waveform_logo():
    path = app_icon_path()

    assert path is not None
    assert path.name == "waveform_app_icon.svg"
    assert path.exists()


def test_menu_bar_icon_is_not_null():
    app = QApplication.instance() or QApplication([])
    icon = menu_bar_icon()

    assert app is not None
    assert not icon.isNull()


def test_hide_dock_icon_returns_false_on_non_macos(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")

    assert hide_dock_icon() is False


def test_set_dock_icon_visible_returns_false_on_non_macos(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")

    assert set_dock_icon_visible(True) is False
    assert set_dock_icon_visible(False) is False


def test_pet_window_collection_behavior_joins_spaces_and_full_screen():
    current_behavior = (1 << 1) | (1 << 6)

    behavior = _collection_behavior_with_pet_flags(current_behavior)

    assert behavior & (1 << 0)
    assert behavior & (1 << 4)
    assert behavior & (1 << 8)
    assert behavior & (1 << 6)
    assert not behavior & (1 << 1)


def test_menu_bar_controller_builds_expected_menu_actions():
    app = QApplication.instance() or QApplication([])
    window = DummyWindow()

    controller = PetMenuBarController(app, window)

    labels = [action.text() for action in controller.menu.actions() if action.text()]
    assert APP_NAME == "CodeBeat"
    assert labels == ["显示/隐藏宠物", "当前播放", "推荐歌曲", "下一首", "显示设置", "退出"]


def test_menu_bar_controller_persists_display_settings():
    app = QApplication.instance() or QApplication([])
    window = DummyWindow()
    saved = []
    dock_calls = []
    settings = PetSettings(show_menu_bar_icon=True, show_dock_icon=True)

    controller = PetMenuBarController(
        app,
        window,
        settings=settings,
        save_settings_func=saved.append,
        dock_visibility_func=dock_calls.append,
    )

    controller.set_menu_bar_visible(False)
    assert settings.show_menu_bar_icon is False
    assert saved[-1].show_menu_bar_icon is False
    assert controller.tray.isVisible() is False

    controller.set_dock_icon_visible(False)
    assert settings.show_dock_icon is False
    assert saved[-1].show_dock_icon is False
    assert dock_calls[-1] is False


def test_menu_bar_controller_toggles_window_visibility():
    app = QApplication.instance() or QApplication([])
    window = DummyWindow()
    controller = PetMenuBarController(app, window)

    controller.toggle_window()
    assert window.visible is False

    controller.toggle_window()
    assert window.visible is True


def test_control_window_exposes_fallback_actions():
    app = QApplication.instance() or QApplication([])
    window = DummyWindow()
    control = CodeBeatControlWindow(app, window)

    labels = [button.text() for button in control.findChildren(type(control.show_hide_button))]

    assert "显示/隐藏" in labels
    assert "当前播放" in labels
    assert "推荐" in labels
    assert "下一首" in labels
