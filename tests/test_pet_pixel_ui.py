import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from coding_with_beat.pet.pixel_ui import PixelBubbleLabel, trim_pixel_text


def test_trim_pixel_text_caps_lines_and_width():
    text = "\n".join(
        [
            "Debug flow",
            "1. " + "A" * 80,
            "2. Track",
            "3. Track",
            "4. Track",
            "5. Track",
            "6. Track",
        ]
    )

    trimmed = trim_pixel_text(text, max_lines=5, max_chars=24)

    lines = trimmed.splitlines()
    assert len(lines) == 5
    assert lines[1].endswith("...")
    assert "6. Track" not in trimmed


def test_trim_pixel_text_removes_blank_runs():
    trimmed = trim_pixel_text("Title\n\n\n1. Track\n\n", max_lines=5, max_chars=40)

    assert trimmed == "Title\n\n1. Track"


def test_pixel_bubble_label_is_display_only_and_has_no_scrollbar():
    app = QApplication.instance() or QApplication([])

    label = PixelBubbleLabel()
    label.set_pixel_text("Debug flow\n1. Track")

    assert app is not None
    assert label.text() == "Debug flow\n1. Track"
    assert label.wordWrap() is True
    assert label.textFormat() == Qt.TextFormat.PlainText
    assert label.textInteractionFlags() == Qt.TextInteractionFlag.NoTextInteraction
    assert "background" in label.styleSheet()
