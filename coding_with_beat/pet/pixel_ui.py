"""Pixel-styled Qt helpers for the desktop pet."""

from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QPushButton

PIXEL_FONT = "Menlo"
ELLIPSIS = "..."
STATUS_STYLE = (
    "QLabel { color: #67e8f9; background: transparent; border: none;"
    " padding: 0 2px; font-size: 12px; font-weight: 700; }"
)
BUBBLE_STYLE = (
    "QLabel { color: #f8fafc; background: rgba(2, 6, 23, 188);"
    " border: 1px solid rgba(103, 232, 249, 160); border-radius: 0px;"
    " padding: 6px 7px; font-size: 11px; }"
)
ICON_BUTTON_STYLE = (
    "QPushButton { color: #f8fafc; background: rgba(2, 6, 23, 92);"
    " border: 1px solid rgba(103, 232, 249, 115); border-radius: 0px; padding: 0;"
    " font-size: 13px; }"
    "QPushButton:hover { color: #22d3ee; background: rgba(2, 6, 23, 150);"
    " border-color: rgba(34, 211, 238, 210); }"
    "QPushButton:pressed { color: #facc15; background: rgba(15, 23, 42, 210); }"
)


class PixelBubbleLabel(QLabel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setVisible(False)
        self.setWordWrap(True)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.setMaximumWidth(230)
        self.setMaximumHeight(120)
        self.setFont(_pixel_font(11))
        self.setStyleSheet(BUBBLE_STYLE)

    def set_pixel_text(self, text: str) -> None:
        self.setText(trim_pixel_text(text, max_lines=5, max_chars=42))
        self.setVisible(True)


def trim_pixel_text(text: str, max_lines: int = 5, max_chars: int = 42) -> str:
    clean = re.sub(r"\n{3,}", "\n\n", (text or "").strip()) or "没有返回内容"
    lines = clean.splitlines()[:max_lines]
    return "\n".join(_trim_line(line, max_chars) for line in lines).rstrip()


def style_status_label(label: QLabel) -> None:
    label.setFont(_pixel_font(12, bold=True))
    label.setStyleSheet(STATUS_STYLE)
    label.setTextFormat(Qt.TextFormat.PlainText)


def style_icon_button(button: QPushButton) -> None:
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setFixedSize(26, 26)
    button.setFont(_pixel_font(13, bold=True))
    button.setStyleSheet(ICON_BUTTON_STYLE)


def _trim_line(line: str, max_chars: int) -> str:
    if len(line) <= max_chars:
        return line
    return line[: max_chars - len(ELLIPSIS)].rstrip() + ELLIPSIS


def _pixel_font(size: int, *, bold: bool = False) -> QFont:
    font = QFont(PIXEL_FONT, size)
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setBold(bold)
    return font
