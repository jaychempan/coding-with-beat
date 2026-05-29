"""Scrollable DJ interaction panel for the desktop pet."""

from __future__ import annotations

import json
import math
import shlex

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..lyrics_snapshot import line_from_text
from .bubble import PetBubbleCard, PetResultItem
from .macos import keep_window_above_apps
from .session import PetSessionResult

PANEL_STYLE = """
QWidget#CodeBeatDjPanel {
  color: #f8fafc;
  background: transparent;
  font-family: Menlo;
}
QLabel {
  background: transparent;
}
QLabel#DjTitle {
  color: #f8fafc;
  font-size: 25px;
  font-weight: 800;
  padding: 0;
}
QLabel#DjSubtitle {
  color: #5eead4;
  font-size: 11px;
  font-weight: 600;
}
QLabel#IntroLine {
  color: rgba(203, 213, 225, 175);
  font-size: 11px;
}
QFrame#NowPlayingBand {
  background: rgba(2, 6, 23, 96);
  border: 1px solid rgba(94, 234, 212, 78);
  border-radius: 12px;
}
QLabel#SectionKicker {
  color: rgba(94, 234, 212, 205);
  font-size: 9px;
  font-weight: 900;
  letter-spacing: 1px;
}
QLabel#NowTitle {
  color: #f8fafc;
  font-size: 14px;
  font-weight: 800;
}
QLabel#NowMeta {
  color: rgba(203, 213, 225, 178);
  font-size: 10px;
}
QLabel#NowLyric {
  color: #5eead4;
  font-size: 12px;
  font-weight: 700;
}
QLabel#LivePillLabel {
  color: #5eead4;
  font-size: 10px;
  font-weight: 800;
}
QFrame#IdentityBadge {
  background: rgba(15, 23, 42, 150);
  border: 1px solid rgba(94, 234, 212, 88);
  border-radius: 12px;
  color: #5eead4;
  font-size: 20px;
}
QFrame#IdentityBadge QLabel {
  color: #5eead4;
  font-size: 20px;
  font-weight: 900;
}
QFrame#LivePill {
  background: rgba(20, 184, 166, 22);
  border: 1px solid rgba(94, 234, 212, 78);
  border-radius: 10px;
}
QFrame#StatsBand {
  background: rgba(2, 6, 23, 58);
  border-top: 1px solid rgba(148, 163, 184, 42);
  border-bottom: 1px solid rgba(148, 163, 184, 42);
}
QLabel#StatLabel {
  color: rgba(148, 163, 184, 176);
  font-size: 9px;
  font-weight: 700;
}
QLabel#StatOnAirValue,
QLabel#StatMoodValue,
QLabel#StatQueueValue {
  color: #f8fafc;
  font-size: 15px;
  font-weight: 800;
}
QLabel#TasteChip {
  color: rgba(226, 232, 240, 205);
  background: rgba(15, 23, 42, 86);
  border: 1px solid rgba(148, 163, 184, 48);
  border-radius: 10px;
  padding: 4px 9px;
  font-size: 10px;
  font-weight: 800;
}
QLineEdit#DjPromptInput {
  color: #f8fafc;
  background: rgba(2, 6, 23, 132);
  border: 1px solid rgba(94, 234, 212, 70);
  border-radius: 12px;
  padding: 8px 12px;
}
QPushButton#ActionChip {
  color: #f8fafc;
  background: rgba(15, 23, 42, 108);
  border: 1px solid rgba(148, 163, 184, 54);
  border-radius: 10px;
  padding: 6px 10px;
  font-size: 11px;
  font-weight: 700;
}
QPushButton#ActionChip:hover {
  color: #67e8f9;
  border-color: rgba(103, 232, 249, 220);
}
QFrame#QueueRow {
  background: rgba(15, 23, 42, 82);
  border: 1px solid rgba(94, 234, 212, 54);
  border-radius: 10px;
}
QLabel#QueueLabel {
  color: rgba(226, 232, 240, 220);
  font-size: 12px;
  font-weight: 650;
}
QLabel#TranscriptBlock {
  color: rgba(203, 213, 225, 205);
  background: rgba(2, 6, 23, 66);
  border: 1px solid rgba(148, 163, 184, 34);
  border-radius: 10px;
  padding: 7px;
  font-size: 11px;
}
QPushButton#QueuePlayButton {
  color: #04131b;
  background: rgba(94, 234, 212, 230);
  border: 1px solid rgba(236, 254, 255, 130);
  border-radius: 13px;
  min-width: 26px;
  max-width: 26px;
  min-height: 26px;
  max-height: 26px;
  padding: 0;
  font-size: 11px;
  font-weight: 900;
}
QPushButton#QueuePlayButton:hover {
  background: #67e8f9;
}
QScrollArea {
  background: transparent;
}
QScrollArea > QWidget > QWidget {
  background: transparent;
}
QScrollBar:vertical {
  background: transparent;
  width: 6px;
}
QScrollBar::handle:vertical {
  background: rgba(94, 234, 212, 90);
  border-radius: 3px;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
  height: 0;
}
"""


class CockpitSignalRail(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.phase = 0
        self.setObjectName("SignalRail")
        self.setFixedHeight(28)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def set_phase(self, phase: int) -> None:
        self.phase = int(phase)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
            center_y = self.height() // 2
            painter.setPen(QPen(QColor(94, 234, 212, 42), 1))
            painter.drawLine(0, center_y, self.width(), center_y)

            scan_x = (self.phase * 4) % max(1, self.width() + 80) - 40
            gradient = QLinearGradient(scan_x - 38, 0, scan_x + 38, 0)
            gradient.setColorAt(0.0, QColor(94, 234, 212, 0))
            gradient.setColorAt(0.5, QColor(94, 234, 212, 115))
            gradient.setColorAt(1.0, QColor(94, 234, 212, 0))
            painter.fillRect(QRectF(scan_x - 38, center_y - 1, 76, 3), gradient)

            for index, x in enumerate(range(4, self.width(), 12)):
                pulse = 0.5 + 0.5 * math.sin((self.phase + index * 3) / 5)
                color = QColor("#5eead4" if index % 4 else "#c4b5fd")
                color.setAlpha(45 + int(72 * pulse))
                painter.fillRect(x, center_y - 5, 2, 10, color)
        finally:
            painter.end()
        super().paintEvent(event)


class LiquidNowPlayingBand(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.phase = 0
        self.live_playing = False
        self.setObjectName("NowPlayingBand")
        self.setAutoFillBackground(False)

    def set_phase(self, phase: int) -> None:
        self.phase = int(phase)
        self.update()

    def set_live_playing(self, playing: bool) -> None:
        self.live_playing = bool(playing)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
            pulse = 0.5 + 0.5 * math.sin(self.phase / 8)
            base = QColor(2, 6, 23, 118)
            painter.fillRect(self.rect(), base)

            glow = QLinearGradient(0, 0, self.width(), self.height())
            glow.setColorAt(0.0, QColor(94, 234, 212, 8 + int(10 * pulse)))
            glow.setColorAt(0.48, QColor(167, 139, 250, 18 + int(12 * pulse)))
            glow.setColorAt(1.0, QColor(94, 234, 212, 4))
            painter.fillRect(self.rect(), glow)

            painter.setPen(QPen(QColor(94, 234, 212, 38), 1))
            for y in range(7 + (self.phase % 9), self.height(), 9):
                painter.drawLine(8, y, self.width() - 8, y)

            if self.live_playing:
                color = QColor("#5eead4")
                color.setAlpha(138)
                painter.setPen(QPen(color, 2))
                baseline = self.height() - 17
                for index in range(18):
                    height = 4 + int(12 * (0.5 + 0.5 * math.sin((self.phase + index * 2) / 4)))
                    x = self.width() - 136 + index * 7
                    painter.drawLine(x, baseline, x, baseline - height)
        finally:
            painter.end()
        super().paintEvent(event)


class QueueTrackRow(QFrame):
    def __init__(self, track_number: int, parent=None) -> None:
        super().__init__(parent)
        self.track_number = int(track_number)
        self.setObjectName("QueueRow")
        self.setAutoFillBackground(False)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
            painter.fillRect(self.rect(), QColor(15, 23, 42, 76))
            if self.underMouse():
                painter.fillRect(self.rect(), QColor(94, 234, 212, 18))
            painter.setPen(QPen(QColor(94, 234, 212, 44), 1))
            painter.drawLine(0, 0, self.width(), 0)
            painter.setPen(QPen(QColor(167, 139, 250, 55), 1))
            painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)
        finally:
            painter.end()
        super().paintEvent(event)


class CodeBeatDjPanel(QWidget):
    def __init__(self, host) -> None:
        super().__init__()
        self.host = host
        self._transcript: list[str] = []
        self._chip_labels: list[QLabel] = []
        self._lyrics_key = ""
        self._lyrics_text = ""
        self._live_playing = False
        self._motion_phase = 0
        self.signal_rail = CockpitSignalRail()
        self.setObjectName("CodeBeatDjPanel")
        self.setWindowTitle("CodeBeat DJ")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumSize(410, 580)
        self.setAutoFillBackground(False)
        self.setStyleSheet(PANEL_STYLE)

        self.title_label = QLabel("CodeBeat DJ")
        self.title_label.setObjectName("DjTitle")
        self.subtitle_label = QLabel("coding state mixer")
        self.subtitle_label.setObjectName("DjSubtitle")
        self.on_air_value = QLabel("LIVE")
        self.on_air_value.setObjectName("StatOnAirValue")
        self.mood_value = QLabel("IDLE")
        self.mood_value.setObjectName("StatMoodValue")
        self.queue_value = QLabel("0")
        self.queue_value.setObjectName("StatQueueValue")
        self.now_title = QLabel("No track")
        self.now_title.setObjectName("NowTitle")
        self.now_meta = QLabel("等待播放状态")
        self.now_meta.setObjectName("NowMeta")
        self.now_lyric = QLabel("lyrics will appear here")
        self.now_lyric.setObjectName("NowLyric")

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_content = QWidget()
        self.results_layout = QVBoxLayout(self.scroll_content)
        self.results_layout.setContentsMargins(8, 8, 8, 8)
        self.results_layout.setSpacing(7)
        self.results_layout.addStretch(1)
        self.scroll_area.setWidget(self.scroll_content)

        self.prompt_input = QLineEdit()
        self.prompt_input.setObjectName("DjPromptInput")
        self.prompt_input.setPlaceholderText("搜歌手、歌名、歌单，或输入：来点爵士")
        self.prompt_input.returnPressed.connect(self.submit_prompt)
        send_button = QPushButton("搜索")
        send_button.setObjectName("ActionChip")
        send_button.clicked.connect(self.submit_prompt)

        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.setSpacing(6)
        input_row.addWidget(self.prompt_input, 1)
        input_row.addWidget(send_button)

        recommend_button = QPushButton("推荐")
        recommend_button.setObjectName("ActionChip")
        recommend_button.clicked.connect(self.recommend_from_context)
        reroll_button = QPushButton("换组")
        reroll_button.setObjectName("ActionChip")
        reroll_button.clicked.connect(self.reroll)
        now_button = QPushButton("当前")
        now_button.setObjectName("ActionChip")
        now_button.clicked.connect(self.now_playing)
        library_button = QPushButton("资料库")
        library_button.setObjectName("ActionChip")
        library_button.clicked.connect(self.list_library)
        liked_button = QPushButton("喜欢")
        liked_button.setObjectName("ActionChip")
        liked_button.clicked.connect(self.list_loved)
        playlist_button = QPushButton("歌单")
        playlist_button.setObjectName("ActionChip")
        playlist_button.clicked.connect(self.list_playlists)

        action_grid = QGridLayout()
        action_grid.setContentsMargins(0, 0, 0, 0)
        action_grid.setHorizontalSpacing(6)
        action_grid.setVerticalSpacing(6)
        for index, button in enumerate(
            (recommend_button, library_button, liked_button, playlist_button, now_button, reroll_button)
        ):
            action_grid.addWidget(button, index // 3, index % 3)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        layout.addWidget(self._build_identity_header())
        layout.addWidget(self._build_now_playing_band())
        layout.addWidget(self._build_stats_band())
        layout.addWidget(self._build_chips_row())
        layout.addWidget(self.signal_rail)
        layout.addWidget(self.scroll_area, 1)
        layout.addLayout(input_row)
        layout.addLayout(action_grid)

        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._tick_motion)
        self._animation_timer.setInterval(120)
        self._snapshot_timer = QTimer(self)
        self._snapshot_timer.timeout.connect(self.refresh_live_snapshot)
        self._snapshot_timer.setInterval(1500)

    def transcript_text(self) -> str:
        return "\n".join(self._transcript)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
            painter.fillRect(self.rect(), QColor(5, 9, 18, 246))

            pulse = 0.5 + 0.5 * math.sin(self._motion_phase / 7)
            gradient = QRadialGradient(
                self.width() * (0.62 + 0.03 * pulse),
                self.height() * 0.22,
                self.width() * (0.40 + 0.04 * pulse),
            )
            gradient.setColorAt(0.0, QColor(45, 212, 191, 22 + int(12 * pulse)))
            gradient.setColorAt(0.45, QColor(45, 212, 191, 9))
            gradient.setColorAt(1.0, QColor(45, 212, 191, 0))
            painter.fillRect(self.rect(), gradient)

            painter.setPen(QPen(QColor(94, 234, 212, 30), 1))
            offset = self._motion_phase % 22
            for y in range(16 - offset, self.height(), 22):
                for x in range(14 + (offset // 2), self.width(), 22):
                    painter.drawPoint(x, y)

            if self._live_playing:
                painter.setPen(QPen(QColor(94, 234, 212, 120), 2))
                base_x = self.width() - 74
                base_y = 76
                for i in range(5):
                    h = 7 + int(12 * (0.5 + 0.5 * math.sin((self._motion_phase + i * 2) / 3)))
                    painter.drawLine(base_x + i * 8, base_y, base_x + i * 8, base_y - h)

            painter.setPen(QPen(QColor(148, 163, 184, 24), 1))
            painter.drawLine(18, 194, self.width() - 18, 194)
        finally:
            painter.end()
        super().paintEvent(event)

    def chip_text(self) -> str:
        return " ".join(label.text() for label in self._chip_labels)

    def show_result(self, result: PetSessionResult) -> None:
        self._append_card(result.card)
        self.show()
        keep_window_above_apps(self)
        self.raise_()
        self.activateWindow()

    def set_pending(self, text: str) -> None:
        self._append_text(text)
        self.show()
        keep_window_above_apps(self)

    def recommend_from_context(self) -> None:
        self._run(self.host.music_session.recommend_from_context, "正在按当前状态找歌...")

    def recommend_from_text(self, text: str) -> None:
        query = text.strip()
        if not query:
            return
        self._run(lambda: self.host.music_session.handle_prompt(query), "正在处理音乐请求...")

    def list_library(self) -> None:
        self._run(self.host.music_session.list_library, "正在打开资料库...")

    def list_loved(self) -> None:
        self._run(self.host.music_session.list_loved, "正在打开喜欢列表...")

    def list_playlists(self) -> None:
        self._run(self.host.music_session.list_playlists, "正在读取歌单...")

    def reroll(self) -> None:
        self._run(self.host.music_session.reroll, "正在换一组...")

    def now_playing(self) -> None:
        self._run(self.host.music_session.now_playing, "读取当前播放...")

    def submit_prompt(self) -> None:
        text = self.prompt_input.text().strip()
        if not text:
            return
        self.prompt_input.clear()
        if text.startswith("/"):
            self._submit_command_text(text[1:].strip())
            return
        self.recommend_from_text(text)

    def refresh_live_snapshot(self) -> None:
        music = getattr(self.host.music_session, "music", None)
        if music is None or not hasattr(music, "now_playing_snapshot"):
            return
        result = music.now_playing_snapshot(self._lyrics_key)
        if not result.ok:
            self.now_meta.setText(result.text)
            return
        try:
            data = json.loads(result.text or "{}")
        except json.JSONDecodeError:
            self.now_meta.setText(result.text)
            return
        self._apply_snapshot(data)

    def _run(self, command, pending_text: str) -> None:
        self.set_pending(pending_text)
        self.host._run_pet_command(command, pending_text)

    def _run_cwb_command(self, tool: str, kwargs: dict) -> None:
        music = getattr(self.host.music_session, "music", None)
        if music is None or not hasattr(music, "control"):
            self._append_text("当前音乐客户端不支持这个命令")
            return
        result = music.control(tool, kwargs)
        self._append_text(result.text)
        self.refresh_live_snapshot()

    def _submit_command_text(self, text: str) -> None:
        parsed = _parse_cwb_command(text)
        if parsed is None:
            self._append_text(f"未知 CWB 命令：/{text}")
            return
        tool, kwargs = parsed
        self._run_cwb_command(tool, kwargs)

    def _append_card(self, card: PetBubbleCard) -> None:
        self._update_stats(card)
        self._append_text(card.text)
        if card.items:
            for item in card.items:
                self._append_result_item(item)

    def _append_text(self, text: str) -> None:
        label = QLabel((text or "").strip() or "没有返回内容")
        label.setObjectName("TranscriptBlock")
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.PlainText)
        self._insert_widget(label)
        self._transcript.append(label.text())

    def _append_result_item(self, item: PetResultItem) -> None:
        row = QueueTrackRow(item.number)
        text = f"{item.number}. {item.label}"
        label = QLabel(text)
        label.setObjectName("QueueLabel")
        label.setWordWrap(True)
        play_button = QPushButton("▶")
        play_button.setObjectName("QueuePlayButton")
        play_button.clicked.connect(lambda _checked=False, number=item.number: self._play_number(number))
        layout = QHBoxLayout(row)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)
        layout.addWidget(label, 1)
        layout.addWidget(play_button)
        self._insert_widget(row)
        self._transcript.append(text)

    def _play_number(self, number: int) -> None:
        self._run(lambda: self.host.music_session.play_number(number), f"正在播放第 {number} 首...")

    def _insert_widget(self, widget: QWidget) -> None:
        self.results_layout.insertWidget(max(0, self.results_layout.count() - 1), widget)
        self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())

    def _build_identity_header(self) -> QWidget:
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        badge = QFrame()
        badge.setObjectName("IdentityBadge")
        badge.setFixedSize(48, 48)
        badge_label = QLabel("♪", badge)
        badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_label.setGeometry(0, 0, 48, 48)

        title_column = QVBoxLayout()
        title_column.setContentsMargins(0, 0, 0, 0)
        title_column.setSpacing(5)
        title_column.addWidget(self.title_label)
        title_column.addWidget(self.subtitle_label)

        live_pill = QFrame()
        live_pill.setObjectName("LivePill")
        live_layout = QHBoxLayout(live_pill)
        live_layout.setContentsMargins(9, 5, 9, 5)
        live_layout.setSpacing(5)
        live_label = QLabel("ON AIR")
        live_label.setObjectName("LivePillLabel")
        live_layout.addWidget(live_label)

        layout.addWidget(badge)
        layout.addLayout(title_column, 1)
        layout.addWidget(live_pill, alignment=Qt.AlignmentFlag.AlignTop)
        return header

    def _build_intro(self) -> QWidget:
        intro = QWidget()
        layout = QVBoxLayout(intro)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        for text in ("为当前 coding 状态打碟", "I hate algorithm. I have taste."):
            label = QLabel(text)
            label.setObjectName("IntroLine")
            layout.addWidget(label)
        return intro

    def _build_now_playing_band(self) -> QWidget:
        band = LiquidNowPlayingBand()
        self.now_band = band
        layout = QVBoxLayout(band)
        layout.setContentsMargins(11, 9, 11, 9)
        layout.setSpacing(4)
        kicker = QLabel("NOW PLAYING")
        kicker.setObjectName("SectionKicker")
        layout.addWidget(kicker)
        layout.addWidget(self.now_title)
        layout.addWidget(self.now_meta)
        layout.addWidget(self.now_lyric)
        return band

    def _build_stats_band(self) -> QWidget:
        band = QFrame()
        band.setObjectName("StatsBand")
        layout = QGridLayout(band)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(3)
        for column, (label, value) in enumerate(
            (
                ("ON AIR", self.on_air_value),
                ("MOOD", self.mood_value),
                ("QUEUE", self.queue_value),
            )
        ):
            label_widget = QLabel(label)
            label_widget.setObjectName("StatLabel")
            value.setObjectName(value.objectName())
            layout.addWidget(label_widget, 0, column)
            layout.addWidget(value, 1, column)
        return band

    def _build_chips_row(self) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)
        for text in ("LOFI", "FOCUS", "JAZZ", "NO VOCAL"):
            chip = QLabel(text)
            chip.setObjectName("TasteChip")
            chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._chip_labels.append(chip)
            layout.addWidget(chip)
        layout.addStretch(1)
        return row

    def _update_stats(self, card: PetBubbleCard) -> None:
        self.queue_value.setText(str(len(card.items)))
        if card.kind == "recommendations":
            self.mood_value.setText("FOCUS")
        elif card.kind == "confirmation":
            self.mood_value.setText("PLAY")
        elif card.kind == "error":
            self.mood_value.setText("ERROR")
        else:
            self.mood_value.setText("IDLE")

    def _apply_snapshot(self, data: dict) -> None:
        title = str(data.get("title") or "No track")
        artist = str(data.get("artist") or "—")
        source = str(data.get("source") or "source")
        position = float(data.get("position") or 0.0)
        duration = float(data.get("duration") or 0.0)
        self._live_playing = bool(data.get("playing"))
        self.now_band.set_live_playing(self._live_playing)
        self.now_title.setText(title)
        self.now_meta.setText(f"{artist} · {source} · {_mmss(position)} / {_mmss(duration)}")
        lyrics_key = str(data.get("lyrics_key") or "")
        if lyrics_key and lyrics_key != self._lyrics_key:
            self._lyrics_text = ""
        self._lyrics_key = lyrics_key
        lyrics_text = data.get("lyrics_text")
        if isinstance(lyrics_text, str) and lyrics_text:
            self._lyrics_text = lyrics_text
        if self._lyrics_text:
            self.now_lyric.setText(line_from_text(self._lyrics_text, position, duration).strip() or "lyrics...")
        elif data.get("lyrics_pending"):
            self.now_lyric.setText("lyrics loading...")
        else:
            self.now_lyric.setText("no lyrics yet")
        self.update()

    def _tick_motion(self) -> None:
        self._motion_phase = (self._motion_phase + 1) % 3600
        self.signal_rail.set_phase(self._motion_phase)
        self.now_band.set_phase(self._motion_phase)
        self.update()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        keep_window_above_apps(self)
        self._animation_timer.start()
        self._snapshot_timer.start()

    def hideEvent(self, event) -> None:
        self._animation_timer.stop()
        self._snapshot_timer.stop()
        super().hideEvent(event)


def _mmss(seconds: float) -> str:
    seconds = max(0, int(seconds or 0))
    return f"{seconds // 60}:{seconds % 60:02d}"


def _parse_cwb_command(text: str) -> tuple[str, dict] | None:
    parts = shlex.split(text)
    if not parts:
        return None
    command = parts[0].lower()
    if command in {"like", "喜欢"}:
        return "like_current", {}
    if command in {"next", "下一首"}:
        return "next_track", {}
    if command in {"pause", "toggle", "暂停"}:
        return "toggle", {}
    if command in {"lyrics", "歌词"}:
        return "now_playing_snapshot", {"known_lyrics_key": ""}
    if command in {"volume", "音量"} and len(parts) == 2:
        return "set_volume", {"percent": int(parts[1])}
    if command in {"seek", "跳转"} and len(parts) == 2:
        return "seek", {"seconds": _parse_seconds(parts[1])}
    if command in {"mode", "模式"} and len(parts) == 2:
        return "set_play_mode", {"mode": parts[1]}
    return None


def _parse_seconds(value: str) -> float:
    if ":" not in value:
        return float(value)
    minutes, seconds = value.split(":", 1)
    return int(minutes) * 60 + int(seconds)
