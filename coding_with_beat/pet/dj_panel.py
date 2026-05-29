"""Scrollable DJ interaction panel for the desktop pet."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen, QRadialGradient
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

from .bubble import PetBubbleCard, PetResultItem
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
  font-size: 34px;
  font-weight: 800;
  padding: 0;
}
QLabel#DjSubtitle {
  color: #5eead4;
  font-size: 12px;
  font-weight: 600;
}
QLabel#IntroLine {
  color: rgba(203, 213, 225, 175);
  font-size: 12px;
}
QLabel#LivePillLabel {
  color: #5eead4;
  font-size: 10px;
  font-weight: 800;
}
QFrame#IdentityBadge {
  background: rgba(15, 23, 42, 170);
  border: 1px solid rgba(94, 234, 212, 105);
  border-radius: 29px;
  color: #5eead4;
  font-size: 24px;
}
QFrame#IdentityBadge QLabel {
  color: #5eead4;
  font-size: 24px;
  font-weight: 900;
}
QFrame#LivePill {
  background: rgba(20, 184, 166, 28);
  border: 1px solid rgba(94, 234, 212, 95);
  border-radius: 11px;
}
QFrame#StatsBand {
  background: rgba(2, 6, 23, 92);
  border-top: 1px solid rgba(148, 163, 184, 48);
  border-bottom: 1px solid rgba(148, 163, 184, 48);
}
QLabel#StatLabel {
  color: rgba(148, 163, 184, 188);
  font-size: 10px;
  font-weight: 700;
}
QLabel#StatOnAirValue,
QLabel#StatMoodValue,
QLabel#StatQueueValue {
  color: #f8fafc;
  font-size: 24px;
  font-weight: 800;
}
QLabel#TasteChip {
  color: rgba(226, 232, 240, 205);
  background: rgba(15, 23, 42, 118);
  border: 1px solid rgba(148, 163, 184, 62);
  border-radius: 12px;
  padding: 5px 10px;
  font-size: 10px;
  font-weight: 800;
}
QLineEdit#DjPromptInput {
  color: #f8fafc;
  background: rgba(2, 6, 23, 118);
  border: 1px solid rgba(94, 234, 212, 78);
  border-radius: 15px;
  padding: 8px 12px;
}
QPushButton#ActionChip {
  color: #f8fafc;
  background: rgba(15, 23, 42, 118);
  border: 1px solid rgba(148, 163, 184, 58);
  border-radius: 13px;
  padding: 6px 10px;
  font-size: 11px;
  font-weight: 700;
}
QPushButton#ActionChip:hover {
  color: #67e8f9;
  border-color: rgba(103, 232, 249, 220);
}
QFrame#QueueRow {
  background: rgba(15, 23, 42, 126);
  border: 1px solid rgba(94, 234, 212, 55);
  border-radius: 9px;
}
QLabel#QueueLabel {
  color: rgba(226, 232, 240, 220);
  font-size: 12px;
  font-weight: 650;
}
QLabel#TranscriptBlock {
  color: rgba(203, 213, 225, 205);
  background: rgba(2, 6, 23, 74);
  border: 1px solid rgba(148, 163, 184, 34);
  border-radius: 8px;
  padding: 7px;
  font-size: 11px;
}
QPushButton#QueuePlayButton {
  color: #03151b;
  background: #5eead4;
  border: 1px solid rgba(255, 255, 255, 90);
  border-radius: 15px;
  min-width: 30px;
  max-width: 30px;
  min-height: 30px;
  max-height: 30px;
  padding: 0;
  font-size: 12px;
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


class CodeBeatDjPanel(QWidget):
    def __init__(self, host) -> None:
        super().__init__()
        self.host = host
        self._transcript: list[str] = []
        self._chip_labels: list[QLabel] = []
        self.setObjectName("CodeBeatDjPanel")
        self.setWindowTitle("CodeBeat DJ")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setMinimumSize(390, 560)
        self.setAutoFillBackground(False)
        self.setStyleSheet(PANEL_STYLE)

        self.title_label = QLabel("CodeBeat DJ")
        self.title_label.setObjectName("DjTitle")
        self.subtitle_label = QLabel("Your mood is my prompt.")
        self.subtitle_label.setObjectName("DjSubtitle")
        self.on_air_value = QLabel("LIVE")
        self.on_air_value.setObjectName("StatOnAirValue")
        self.mood_value = QLabel("IDLE")
        self.mood_value.setObjectName("StatMoodValue")
        self.queue_value = QLabel("0")
        self.queue_value.setObjectName("StatQueueValue")

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
        self.prompt_input.setPlaceholderText("想听什么？比如：来点爵士 / 不要人声 / 换轻松一点")
        self.prompt_input.returnPressed.connect(self.submit_prompt)
        send_button = QPushButton("发送")
        send_button.setObjectName("ActionChip")
        send_button.clicked.connect(self.submit_prompt)

        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.setSpacing(6)
        input_row.addWidget(self.prompt_input, 1)
        input_row.addWidget(send_button)

        recommend_button = QPushButton("按当前状态推荐")
        recommend_button.setObjectName("ActionChip")
        recommend_button.clicked.connect(self.recommend_from_context)
        reroll_button = QPushButton("换一组")
        reroll_button.setObjectName("ActionChip")
        reroll_button.clicked.connect(self.reroll)
        now_button = QPushButton("当前播放")
        now_button.setObjectName("ActionChip")
        now_button.clicked.connect(self.now_playing)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(6)
        action_row.addWidget(recommend_button)
        action_row.addWidget(reroll_button)
        action_row.addWidget(now_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 16)
        layout.setSpacing(12)
        layout.addWidget(self._build_identity_header())
        layout.addWidget(self._build_intro())
        layout.addWidget(self._build_stats_band())
        layout.addWidget(self._build_chips_row())
        layout.addWidget(self.scroll_area, 1)
        layout.addLayout(input_row)
        layout.addLayout(action_row)

    def transcript_text(self) -> str:
        return "\n".join(self._transcript)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
            painter.fillRect(self.rect(), QColor(5, 9, 18, 246))

            gradient = QRadialGradient(self.width() * 0.66, self.height() * 0.22, self.width() * 0.45)
            gradient.setColorAt(0.0, QColor(45, 212, 191, 42))
            gradient.setColorAt(0.45, QColor(45, 212, 191, 14))
            gradient.setColorAt(1.0, QColor(45, 212, 191, 0))
            painter.fillRect(self.rect(), gradient)

            painter.setPen(QPen(QColor(94, 234, 212, 48), 1))
            for y in range(14, self.height(), 18):
                for x in range(12, self.width(), 18):
                    painter.drawPoint(x, y)

            painter.setPen(QPen(QColor(148, 163, 184, 30), 1))
            painter.drawLine(18, 176, self.width() - 18, 176)
        finally:
            painter.end()
        super().paintEvent(event)

    def chip_text(self) -> str:
        return " ".join(label.text() for label in self._chip_labels)

    def show_result(self, result: PetSessionResult) -> None:
        self._append_card(result.card)
        self.show()
        self.raise_()
        self.activateWindow()

    def set_pending(self, text: str) -> None:
        self._append_text(text)
        self.show()

    def recommend_from_context(self) -> None:
        self._run(self.host.music_session.recommend_from_context, "正在按当前状态找歌...")

    def recommend_from_text(self, text: str) -> None:
        query = text.strip()
        if not query:
            return
        self._run(lambda: self.host.music_session.recommend_from_text(query), "正在按你的描述找歌...")

    def reroll(self) -> None:
        self._run(self.host.music_session.reroll, "正在换一组...")

    def now_playing(self) -> None:
        self._run(self.host.music_session.now_playing, "读取当前播放...")

    def submit_prompt(self) -> None:
        text = self.prompt_input.text().strip()
        if not text:
            return
        self.prompt_input.clear()
        self.recommend_from_text(text)

    def _run(self, command, pending_text: str) -> None:
        self.set_pending(pending_text)
        self.host._run_pet_command(command, pending_text)

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
        row = QFrame()
        row.setObjectName("QueueRow")
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
        badge.setFixedSize(58, 58)
        badge_label = QLabel("♪", badge)
        badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_label.setGeometry(0, 0, 58, 58)

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

    def _build_stats_band(self) -> QWidget:
        band = QFrame()
        band.setObjectName("StatsBand")
        layout = QGridLayout(band)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(18)
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
