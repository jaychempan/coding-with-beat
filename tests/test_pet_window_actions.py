import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from coding_with_beat.pet.pixel_ui import PixelBubbleLabel
from coding_with_beat.pet.window import PetWindow, _action


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
