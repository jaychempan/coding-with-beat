"""Scrollable DJ interaction panel for the desktop pet."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
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
QWidget {
  color: #f8fafc;
  background: rgba(8, 13, 31, 235);
  font-family: Menlo;
}
QLabel {
  background: transparent;
}
QLineEdit {
  color: #f8fafc;
  background: rgba(15, 23, 42, 190);
  border: 1px solid rgba(167, 139, 250, 145);
  border-radius: 6px;
  padding: 7px 9px;
}
QPushButton {
  color: #f8fafc;
  background: rgba(15, 23, 42, 160);
  border: 1px solid rgba(103, 232, 249, 120);
  border-radius: 6px;
  padding: 6px 9px;
}
QPushButton:hover {
  color: #67e8f9;
  border-color: rgba(103, 232, 249, 220);
}
QFrame#ResultRow {
  background: rgba(15, 23, 42, 118);
  border: 1px solid rgba(167, 139, 250, 72);
  border-radius: 7px;
}
"""


class CodeBeatDjPanel(QWidget):
    def __init__(self, host) -> None:
        super().__init__()
        self.host = host
        self._transcript: list[str] = []
        self.setWindowTitle("CodeBeat DJ")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setMinimumSize(360, 420)
        self.setStyleSheet(PANEL_STYLE)

        title = QLabel("CodeBeat DJ")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 14px; font-weight: 700; color: #a78bfa; padding: 4px;")

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
        self.prompt_input.setPlaceholderText("想听什么？比如：来点爵士 / 不要人声 / 换轻松一点")
        self.prompt_input.returnPressed.connect(self.submit_prompt)
        send_button = QPushButton("发送")
        send_button.clicked.connect(self.submit_prompt)

        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.setSpacing(6)
        input_row.addWidget(self.prompt_input, 1)
        input_row.addWidget(send_button)

        recommend_button = QPushButton("按当前状态推荐")
        recommend_button.clicked.connect(self.recommend_from_context)
        reroll_button = QPushButton("换一组")
        reroll_button.clicked.connect(self.reroll)
        now_button = QPushButton("当前播放")
        now_button.clicked.connect(self.now_playing)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(6)
        action_row.addWidget(recommend_button)
        action_row.addWidget(reroll_button)
        action_row.addWidget(now_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        layout.addWidget(title)
        layout.addWidget(self.scroll_area, 1)
        layout.addLayout(input_row)
        layout.addLayout(action_row)

    def transcript_text(self) -> str:
        return "\n".join(self._transcript)

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
        self._append_text(card.text)
        if card.items:
            for item in card.items:
                self._append_result_item(item)

    def _append_text(self, text: str) -> None:
        label = QLabel((text or "").strip() or "没有返回内容")
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setStyleSheet("color: #cbd5e1; padding: 4px 2px;")
        self._insert_widget(label)
        self._transcript.append(label.text())

    def _append_result_item(self, item: PetResultItem) -> None:
        row = QFrame()
        row.setObjectName("ResultRow")
        text = f"{item.number}. {item.label}"
        label = QLabel(text)
        label.setWordWrap(True)
        play_button = QPushButton("播放")
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
