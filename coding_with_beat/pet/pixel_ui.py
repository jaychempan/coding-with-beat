"""Pixel-styled Qt helpers for the desktop pet."""

from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QPushButton

PIXEL_FONT = "Menlo"
ELLIPSIS = "..."
STATUS_STYLE = (
    "QLabel { color: #5eead4; background: transparent; border: none;"
    " padding: 0 2px; font-size: 12px; font-weight: 700; }"
)
BUBBLE_STYLE = (
    "QLabel { color: #f8fafc; background: rgba(5, 9, 18, 176);"
    " border: 1px solid rgba(94, 234, 212, 128); border-radius: 9px;"
    " padding: 7px 9px; font-size: 11px; }"
)
ICON_BUTTON_STYLE = (
    "QPushButton { color: #ecfeff; background: rgba(5, 9, 18, 92);"
    " border: 1px solid rgba(94, 234, 212, 92); border-radius: 6px; padding: 0;"
    " font-size: 12px; }"
    "QPushButton:hover { color: #5eead4; background: rgba(8, 18, 28, 172);"
    " border-color: rgba(94, 234, 212, 210); }"
    "QPushButton:pressed { color: #020617; background: #5eead4; border-color: #99f6e4; }"
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
    label.setWordWrap(False)
    label.setMaximumWidth(150)


def style_icon_button(button: QPushButton) -> None:
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setFixedSize(22, 22)
    button.setFont(_pixel_font(12, bold=True))
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
