import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from coding_with_beat.pet.bubble import PetBubbleCard
from coding_with_beat.pet.petdex import ensure_petdex_pet
from coding_with_beat.pet.pixel_ui import PixelBubbleLabel
from coding_with_beat.pet.session import PetSessionResult
from coding_with_beat.pet.window import PetdexWindow, PetWindow, _action


def test_action_does_not_pass_qt_checked_arg_to_callback():
    app = QApplication.instance() or QApplication([])
    seen = []

    action = _action("Skin", lambda skin_id="cyber": seen.append(skin_id), app)
    action.trigger()

    assert seen == ["cyber"]


def test_builtin_pet_window_uses_pixel_bubble_label():
    app = QApplication.instance() or QApplication([])
    window = PetWindow()
    try:
        assert app is not None
        assert isinstance(window._bubble, PixelBubbleLabel)
    finally:
        window.close()


def test_builtin_pet_window_applies_pending_result():
    app = QApplication.instance() or QApplication([])
    window = PetWindow()
    try:
        assert app is not None
        window._apply_session_result(PetSessionResult(True, "think", PetBubbleCard("status", "思考中...")))
        assert "思考中" in window._bubble.text()
    finally:
        window.close()


def test_builtin_pet_window_hides_constant_now_playing_label():
    app = QApplication.instance() or QApplication([])
    window = PetWindow()
    try:
        assert app is not None
        assert window._track_label.isVisible() is False
    finally:
        window.close()


def test_builtin_pet_window_centers_pet_sprite_widget():
    app = QApplication.instance() or QApplication([])
    window = PetWindow()
    try:
        assert app is not None
        label_item = window.layout().itemAt(2)

        assert label_item.widget() is window._label
        assert label_item.alignment() & Qt.AlignmentFlag.AlignHCenter
    finally:
        window.close()


def test_builtin_pet_window_keeps_controls_cluster_compact_and_centered():
    app = QApplication.instance() or QApplication([])
    window = PetWindow()
    try:
        assert app is not None
        controls_item = window.layout().itemAt(3)

        assert controls_item.widget() is window._controls_widget
        assert controls_item.alignment() & Qt.AlignmentFlag.AlignHCenter
        assert window._controls_widget.maximumWidth() == 116
    finally:
        window.close()


def test_builtin_pet_sprite_has_transparent_label_background():
    app = QApplication.instance() or QApplication([])
    window = PetWindow()
    try:
        assert app is not None
        assert "background: transparent" in window._label.styleSheet()
        assert window._label.autoFillBackground() is False
    finally:
        window.close()


def test_builtin_pet_window_disables_system_backdrop_and_shadow():
    app = QApplication.instance() or QApplication([])
    window = PetWindow()
    try:
        assert app is not None
        assert window.windowFlags() & Qt.WindowType.NoDropShadowWindowHint
        assert window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        assert window.testAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
    finally:
        window.close()


def test_petdex_window_centers_pet_sprite_widget():
    app = QApplication.instance() or QApplication([])
    window = PetdexWindow(ensure_petdex_pet("codebeat-buddy"))
    try:
        assert app is not None
        label_item = window.layout().itemAt(2)

        assert label_item.widget() is window._label
        assert label_item.alignment() & Qt.AlignmentFlag.AlignHCenter
    finally:
        window.close()


def test_petdex_window_disables_system_backdrop_and_shadow():
    app = QApplication.instance() or QApplication([])
    window = PetdexWindow(ensure_petdex_pet("codebeat-buddy"))
    try:
        assert app is not None
        assert window.windowFlags() & Qt.WindowType.NoDropShadowWindowHint
        assert window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        assert window.testAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
    finally:
        window.close()


def test_petdex_window_hides_constant_now_playing_label():
    app = QApplication.instance() or QApplication([])
    window = PetdexWindow(ensure_petdex_pet("codebeat-buddy"))
    try:
        assert app is not None
        assert window._track_label.isVisible() is False
    finally:
        window.close()


def test_petdex_sprite_has_transparent_label_background():
    app = QApplication.instance() or QApplication([])
    window = PetdexWindow(ensure_petdex_pet("codebeat-buddy"))
    try:
        assert app is not None
        assert "background: transparent" in window._label.styleSheet()
        assert window._label.autoFillBackground() is False
    finally:
        window.close()


def test_petdex_window_keeps_controls_cluster_compact_and_centered():
    app = QApplication.instance() or QApplication([])
    window = PetdexWindow(ensure_petdex_pet("codebeat-buddy"))
    try:
        assert app is not None
        controls_item = window.layout().itemAt(3)

        assert controls_item.widget() is window._controls_widget
        assert controls_item.alignment() & Qt.AlignmentFlag.AlignHCenter
        assert window._controls_widget.maximumWidth() == 116
    finally:
        window.close()


def test_builtin_pet_window_context_menu_keeps_music_and_skin_actions():
    app = QApplication.instance() or QApplication([])
    window = PetWindow()
    try:
        assert app is not None
        menu = window._build_context_menu()
        labels = [action.text() for action in menu.actions() if action.text()]

        assert labels == [
            "按心情推荐",
            "按当前状态推荐",
            "自动开播",
            "播放编号",
            "当前播放",
            "暂停/继续",
            "下一首",
            "切换皮肤",
            "退出",
        ]
    finally:
        window.close()
