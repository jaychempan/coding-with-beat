"""Transparent music aura for the desktop pet."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class MusicAuraWidget(QWidget):
    def __init__(self, *, sprite_size: tuple[int, int], parent=None) -> None:
        super().__init__(parent)
        self.is_playing = False
        self.rotation = 0.0
        self.burst_phase = 0.0
        self._sprite_size = sprite_size
        self._particle_count = 18
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self.set_sprite_size(sprite_size)

    def set_sprite_size(self, sprite_size: tuple[int, int]) -> None:
        self._sprite_size = sprite_size
        width = max(112, sprite_size[0] + 48)
        height = max(118, sprite_size[1] + 48)
        self.setMinimumSize(width, height)
        self.setFixedSize(width, height)
        self.update()

    def set_playing(self, playing: bool) -> None:
        self.is_playing = bool(playing)
        self.update()

    def burst(self) -> None:
        self.burst_phase = 1.0
        self.update()

    def advance(self) -> None:
        self.rotation = (self.rotation + (8.0 if self.is_playing else 2.0)) % 360.0
        if self.burst_phase > 0.0:
            self.burst_phase = max(0.0, self.burst_phase - 0.08)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
            center = QPointF(self.width() / 2, self.height() / 2)
            radius = min(self.width(), self.height()) / 2 - 18
            self._paint_particles(painter, center, radius)
            self._paint_orbit(painter, center, radius)
            self._paint_wave_ticks(painter, center, radius)
            self._paint_burst(painter, center, radius)
        finally:
            painter.end()
        super().paintEvent(event)

    def _paint_particles(self, painter: QPainter, center: QPointF, radius: float) -> None:
        base_alpha = 135 if self.is_playing else 44
        for index in range(self._particle_count):
            angle = math.radians((360 / self._particle_count) * index + self.rotation)
            wobble = 5 * math.sin(math.radians(self.rotation * 2 + index * 23))
            distance = radius * 0.68 + wobble
            x = center.x() + math.cos(angle) * distance
            y = center.y() + math.sin(angle) * distance
            color = QColor("#5eead4" if index % 3 else "#a78bfa")
            color.setAlpha(base_alpha if index % 2 else max(28, base_alpha - 36))
            painter.fillRect(round(x), round(y), 2, 2, color)

    def _paint_orbit(self, painter: QPainter, center: QPointF, radius: float) -> None:
        if not self.is_playing and self.burst_phase <= 0.0:
            return
        color = QColor("#5eead4")
        color.setAlpha(150 if self.is_playing else 80)
        painter.setPen(QPen(color, 2))
        for offset in (0, 120, 240):
            start = int((self.rotation + offset) * 16)
            painter.drawArc(
                round(center.x() - radius),
                round(center.y() - radius),
                round(radius * 2),
                round(radius * 2),
                start,
                34 * 16,
            )

    def _paint_wave_ticks(self, painter: QPainter, center: QPointF, radius: float) -> None:
        if not self.is_playing:
            return
        color = QColor("#c4b5fd")
        color.setAlpha(130)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        baseline = center.y() + radius * 0.76
        for index in range(9):
            height = 3 + int(5 * (0.5 + 0.5 * math.sin(math.radians(self.rotation * 3 + index * 40))))
            x = center.x() - 24 + index * 6
            painter.drawRect(round(x), round(baseline - height), 3, height)

    def _paint_burst(self, painter: QPainter, center: QPointF, radius: float) -> None:
        if self.burst_phase <= 0.0:
            return
        alpha = int(180 * self.burst_phase)
        color = QColor("#5eead4")
        color.setAlpha(alpha)
        painter.setPen(QPen(color, 2))
        burst_radius = radius * (1.0 + (1.0 - self.burst_phase) * 0.55)
        painter.drawEllipse(center, burst_radius, burst_radius)
