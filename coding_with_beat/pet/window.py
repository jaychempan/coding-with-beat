"""PySide6 desktop pet window."""

from __future__ import annotations

import re

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QPainter, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QInputDialog, QLabel, QMenu, QPushButton, QTextEdit, QVBoxLayout, QWidget

from .animator import PetAnimator
from .controller import PetController
from .petdex import PetdexAnimator, PetdexPet, ensure_petdex_pet, resolve_spritesheet_path
from .settings import load_settings, save_settings
from .sprites import BUILTIN_SKINS, Frame


class PetWindow(QWidget):
    @classmethod
    def from_petdex(cls, slug: str):
        return PetdexWindow(ensure_petdex_pet(slug))

    def __init__(self, controller: PetController | None = None) -> None:
        super().__init__()
        self.settings = load_settings()
        self.controller = controller or PetController(PetAnimator(self.settings.skin_id))
        self._drag_origin: QPoint | None = None
        self._bubble = QTextEdit(self)
        self._bubble.setReadOnly(True)
        self._bubble.setVisible(False)
        self._bubble.setMaximumHeight(120)
        self._track_label = QLabel("未播放", self)
        self._track_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._track_label.setStyleSheet(
            "QLabel { color: #f8fafc; background: rgba(15, 23, 42, 190);"
            " border-radius: 5px; padding: 3px 6px; font-size: 12px; }"
        )
        self._label = QLabel(self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._recommend_button = _button("推荐")
        self._recommend_button.clicked.connect(self.ask_mood)
        self._now_button = _button("在播")
        self._now_button.clicked.connect(self.show_now_playing)
        self._skin_button = _button("皮肤")
        self._skin_button.clicked.connect(self.cycle_skin)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(4)
        controls.addWidget(self._recommend_button)
        controls.addWidget(self._now_button)
        controls.addWidget(self._skin_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self._bubble)
        layout.addWidget(self._track_label)
        layout.addWidget(self._label)
        layout.addLayout(controls)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.move(self.settings.x, self.settings.y)
        self._render()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(240)

        self.state_timer = QTimer(self)
        self.state_timer.timeout.connect(self._refresh_state)
        self.state_timer.start(1500)

        self.ambient_timer = QTimer(self)
        self.ambient_timer.timeout.connect(self._ambient_motion)
        self.ambient_timer.start(3200)

    def _tick(self) -> None:
        self.controller.animator.tick()
        self._render()

    def _refresh_state(self) -> None:
        self.controller.refresh_action()
        self._track_label.setText(self.controller.current_track_label())

    def _ambient_motion(self) -> None:
        if self.controller.animator.action in {"idle", "walk", "think", "happy"}:
            self.controller.animator.set_action(self.controller.next_ambient_action())

    def _render(self) -> None:
        frame = self.controller.animator.current_frame()
        pixmap = _frame_pixmap(frame, self.controller.animator.skin.palette, self.settings.scale)
        self._label.setPixmap(pixmap)
        extra = 82 + (130 if self._bubble.isVisible() else 0)
        self.resize(max(172, pixmap.width() + 12), pixmap.height() + extra)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.controller.animator.set_action("dance")
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_origin is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_origin)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = None
            self.settings.x = self.x()
            self.settings.y = self.y()
            save_settings(self.settings)
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.ask_mood()
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        menu.addAction(_action("推荐歌曲", self.ask_mood, self))
        menu.addAction(_action("播放编号", self.play_number_dialog, self))
        menu.addAction(_action("当前播放", self.show_now_playing, self))
        menu.addAction(_action("暂停/继续", self.toggle_playback, self))
        menu.addAction(_action("下一首", self.next_track, self))
        skin_menu = menu.addMenu("切换皮肤")
        for skin_id, skin in BUILTIN_SKINS.items():
            skin_menu.addAction(_action(skin.name, lambda sid=skin_id: self.set_skin(sid), self))
        menu.addSeparator()
        menu.addAction(_action("退出", self.close, self))
        menu.exec(event.globalPos())

    def ask_mood(self) -> None:
        text, ok = QInputDialog.getText(self, "DJ Buddy", "想听什么心情？")
        if not ok or not text.strip():
            return
        result = self.controller.handle_mood_text(text.strip())
        self._show_bubble(result.text)

    def show_now_playing(self) -> None:
        self._show_bubble(self.controller.music.now_playing().text)

    def play_number_dialog(self) -> None:
        number, ok = QInputDialog.getInt(self, "DJ Buddy", "播放第几首？", 1, 1, 999, 1)
        if not ok:
            return
        self._show_bubble(self.controller.play_number(number).text)

    def toggle_playback(self) -> None:
        self._show_bubble(self.controller.music.toggle().text)

    def next_track(self) -> None:
        self._show_bubble(self.controller.music.next_track().text)

    def set_skin(self, skin_id: str) -> None:
        self.controller.animator.set_skin(skin_id)
        self.settings.skin_id = self.controller.animator.skin.id
        save_settings(self.settings)
        self._render()

    def cycle_skin(self) -> None:
        self.settings.skin_id = self.controller.cycle_skin()
        save_settings(self.settings)
        self._show_bubble(f"皮肤：{self.controller.animator.skin.name}")

    def _show_bubble(self, text: str) -> None:
        self._bubble.setPlainText(_trim_output(text))
        self._bubble.setVisible(True)
        self._render()


def _action(text: str, callback, parent) -> QAction:
    action = QAction(text, parent)
    action.triggered.connect(callback)
    return action


def _button(text: str) -> QPushButton:
    button = QPushButton(text)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setFixedHeight(26)
    button.setStyleSheet(
        "QPushButton { color: #f8fafc; background: rgba(30, 41, 59, 210);"
        " border: 1px solid rgba(148, 163, 184, 180); border-radius: 5px; padding: 2px 7px;"
        " font-size: 12px; }"
        "QPushButton:hover { background: rgba(51, 65, 85, 230); }"
        "QPushButton:pressed { background: rgba(15, 23, 42, 235); }"
    )
    return button


def _trim_output(text: str) -> str:
    clean = text.strip() or "没有返回内容"
    return re.sub(r"\n{3,}", "\n\n", clean)[:1200]


def _frame_pixmap(frame: Frame, palette: dict[str, str], scale: int) -> QPixmap:
    rows = frame.pixels
    width = max(len(row) for row in rows)
    height = len(rows)
    pixmap = QPixmap(width * scale, height * scale)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    try:
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch == ".":
                    continue
                painter.fillRect(x * scale, y * scale, scale, scale, QColor(palette.get(ch, "#ffffff")))
    finally:
        painter.end()
    return pixmap


class PetdexWindow(QWidget):
    def __init__(self, pet: PetdexPet, controller: PetController | None = None) -> None:
        super().__init__()
        self.pet = pet
        self.settings = load_settings()
        self.controller = controller or PetController(PetAnimator(self.settings.skin_id))
        self.petdex_animator = PetdexAnimator()
        self._spritesheet = QPixmap(str(resolve_spritesheet_path(pet)))
        if self._spritesheet.isNull():
            raise RuntimeError(f"Could not load Petdex spritesheet: {pet.spritesheet_path}")
        self._drag_origin: QPoint | None = None

        self._bubble = QTextEdit(self)
        self._bubble.setReadOnly(True)
        self._bubble.setVisible(False)
        self._bubble.setMaximumHeight(120)
        self._track_label = QLabel("未播放", self)
        self._track_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._track_label.setStyleSheet(
            "QLabel { color: #f8fafc; background: rgba(15, 23, 42, 190);"
            " border-radius: 5px; padding: 3px 6px; font-size: 12px; }"
        )
        self._label = QLabel(self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._recommend_button = _button("推荐")
        self._recommend_button.clicked.connect(self.ask_mood)
        self._now_button = _button("在播")
        self._now_button.clicked.connect(self.show_now_playing)
        self._pet_button = _button("宠物")
        self._pet_button.clicked.connect(lambda: self._show_bubble(f"Petdex: {self.pet.name}"))

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(4)
        controls.addWidget(self._recommend_button)
        controls.addWidget(self._now_button)
        controls.addWidget(self._pet_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self._bubble)
        layout.addWidget(self._track_label)
        layout.addWidget(self._label)
        layout.addLayout(controls)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.move(self.settings.x, self.settings.y)
        self._render()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(110)

        self.state_timer = QTimer(self)
        self.state_timer.timeout.connect(self._refresh_state)
        self.state_timer.start(1500)

    def _tick(self) -> None:
        self.petdex_animator.tick()
        self._render()

    def _refresh_state(self) -> None:
        action = self.controller.refresh_action()
        self.petdex_animator.set_action(action)
        self._track_label.setText(self.controller.current_track_label())

    def _render(self) -> None:
        pixmap = _petdex_frame_pixmap(self._spritesheet, self.petdex_animator, max(1, self.settings.scale // 2))
        self._label.setPixmap(pixmap)
        extra = 82 + (130 if self._bubble.isVisible() else 0)
        self.resize(max(220, pixmap.width() + 12), pixmap.height() + extra)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.petdex_animator.set_action("dance")
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_origin is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_origin)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = None
            self.settings.x = self.x()
            self.settings.y = self.y()
            save_settings(self.settings)
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.ask_mood()
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        menu.addAction(_action("推荐歌曲", self.ask_mood, self))
        menu.addAction(_action("播放编号", self.play_number_dialog, self))
        menu.addAction(_action("当前播放", self.show_now_playing, self))
        menu.addAction(_action("暂停/继续", self.toggle_playback, self))
        menu.addAction(_action("下一首", self.next_track, self))
        menu.addAction(_action(f"Petdex: {self.pet.name}", lambda: self._show_bubble(str(self.pet.folder)), self))
        menu.addSeparator()
        menu.addAction(_action("退出", self.close, self))
        menu.exec(event.globalPos())

    def ask_mood(self) -> None:
        text, ok = QInputDialog.getText(self, "DJ Buddy", "想听什么心情？")
        if not ok or not text.strip():
            return
        self.petdex_animator.set_action("think")
        result = self.controller.handle_mood_text(text.strip())
        self.petdex_animator.set_action("recommend" if result.ok else "sad")
        self._show_bubble(result.text)

    def show_now_playing(self) -> None:
        self._show_bubble(self.controller.music.now_playing().text)

    def play_number_dialog(self) -> None:
        number, ok = QInputDialog.getInt(self, "DJ Buddy", "播放第几首？", 1, 1, 999, 1)
        if not ok:
            return
        result = self.controller.play_number(number)
        self.petdex_animator.set_action("dance" if result.ok else "sad")
        self._show_bubble(result.text)

    def toggle_playback(self) -> None:
        self._show_bubble(self.controller.music.toggle().text)

    def next_track(self) -> None:
        self._show_bubble(self.controller.music.next_track().text)

    def _show_bubble(self, text: str) -> None:
        self._bubble.setPlainText(_trim_output(text))
        self._bubble.setVisible(True)
        self._render()


def _petdex_frame_pixmap(spritesheet: QPixmap, animator: PetdexAnimator, scale: int) -> QPixmap:
    row, col = animator.current_cell()
    from .petdex import frame_size

    frame_w, frame_h = frame_size(spritesheet.width(), spritesheet.height())
    source = QRect(col * frame_w, row * frame_h, frame_w, frame_h)
    frame = spritesheet.copy(source)
    return frame.scaled(
        frame_w * scale, frame_h * scale, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation
    )
