import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from coding_with_beat.pet.window import _action


def test_action_does_not_pass_qt_checked_arg_to_callback():
    app = QApplication.instance() or QApplication([])
    seen = []

    action = _action("Skin", lambda skin_id="cyber": seen.append(skin_id), app)
    action.trigger()

    assert seen == ["cyber"]
