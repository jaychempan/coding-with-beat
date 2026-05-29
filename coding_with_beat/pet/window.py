"""PySide6 desktop pet window."""

from __future__ import annotations

import re

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .animator import PetAnimator
from .async_runner import PetCommandRunner
from .bubble import PetBubbleCard
from .controller import PetController
from .dj_panel import CodeBeatDjPanel
from .interactions import PetInteractionController
from .macos import keep_window_above_apps, set_dock_icon_visible
from .petdex import (
    PetdexAnimator,
    PetdexPet,
    display_size,
    ensure_petdex_pet,
    frame_size,
    installed_petdex_pets,
    resolve_spritesheet_path,
)
from .pixel_ui import PixelBubbleLabel, style_icon_button, style_status_label
from .session import PetMusicSession, PetSessionResult
from .settings import load_settings, save_settings
from .sprites import BUILTIN_SKINS, Frame


def _quit_application() -> None:
    app = QApplication.instance()
    if app is not None:
        app.quit()


class PetWindow(QWidget):
    @classmethod
    def from_petdex(cls, slug: str):
        return PetdexWindow(ensure_petdex_pet(slug))

    def __init__(self, controller: PetController | None = None) -> None:
        super().__init__()
        self.settings = load_settings()
        self.controller = controller or PetController(PetAnimator(self.settings.skin_id))
        self.music_session = PetMusicSession(music=self.controller.music, load_state=self.controller.load_state)
        self.interactions = PetInteractionController(session=self.music_session)
        self.command_runner = PetCommandRunner(self)
        self.command_runner.finished.connect(self._apply_session_result)
        self.live_runner = PetCommandRunner(self, timeout_ms=4_000)
        self.live_runner.finished.connect(self._apply_live_result)
        self._dj_panel = CodeBeatDjPanel(self)
        self._last_live_label = ""
        self._last_live_playing = False
        self._long_press_fired = False
        self._drag_started = False
        self._press_global_pos: QPoint | None = None
        self._long_press_timer = QTimer(self)
        self._long_press_timer.setSingleShot(True)
        self._long_press_timer.timeout.connect(self._handle_long_press)
        self._single_click_timer = QTimer(self)
        self._single_click_timer.setSingleShot(True)
        self._single_click_timer.timeout.connect(self._handle_single_click)
        self._drag_origin: QPoint | None = None
        self._bubble = PixelBubbleLabel(self)
        self._track_label = QLabel("未播放", self)
        self._track_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        style_status_label(self._track_label)
        self._track_label.setVisible(False)
        self._label = QLabel(self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _style_sprite_label(self._label)
        self._now_button = _icon_button("♪", "当前播放")
        self._now_button.clicked.connect(self._dj_panel.now_playing)
        self._recommend_button = _icon_button("+", "按当前状态推荐")
        self._recommend_button.clicked.connect(self._dj_panel.recommend_from_context)
        self._reroll_button = _icon_button("↻", "换一组")
        self._reroll_button.clicked.connect(self._dj_panel.reroll)
        self._more_button = _icon_button("...", "更多")
        self._more_button.clicked.connect(self._show_more_menu)

        self._controls_widget = _controls_widget(
            self._now_button,
            self._recommend_button,
            self._reroll_button,
            self._more_button,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self._bubble)
        layout.addWidget(self._track_label)
        layout.addWidget(self._label, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._controls_widget, alignment=Qt.AlignmentFlag.AlignHCenter)

        _style_pet_window(self)
        self.move(self.settings.x, self.settings.y)
        self._render()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(240)

        self.state_timer = QTimer(self)
        self.state_timer.timeout.connect(self._refresh_state)
        self.state_timer.start(1500)

        self.live_timer = QTimer(self)
        self.live_timer.timeout.connect(self._poll_live_music)
        self.live_timer.start(3500)

        self.ambient_timer = QTimer(self)
        self.ambient_timer.timeout.connect(self._ambient_motion)
        self.ambient_timer.start(3200)

    def _tick(self) -> None:
        self.controller.animator.tick()
        self._render()

    def _refresh_state(self) -> None:
        self.controller.refresh_action()
        if self._last_live_playing:
            self.controller.animator.set_action("dance")
        self._track_label.setText(self.controller.current_track_label())

    def _poll_live_music(self) -> None:
        if not self.live_runner.busy:
            self.live_runner.run(self.music_session.live_now_playing)

    def _ambient_motion(self) -> None:
        if self.controller.animator.action in {"idle", "walk", "think", "happy"}:
            self.controller.animator.set_action(self.controller.next_ambient_action())

    def _render(self) -> None:
        frame = self.controller.animator.current_frame()
        pixmap = _frame_pixmap(frame, self.controller.animator.skin.palette, self.settings.scale)
        self._label.setPixmap(pixmap)
        extra = 66 + (self._bubble.sizeHint().height() + 8 if self._bubble.isVisible() else 0)
        self.resize(max(172, pixmap.width() + 12), pixmap.height() + extra)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._long_press_fired = False
            self._drag_started = False
            self._press_global_pos = event.globalPosition().toPoint()
            self._single_click_timer.stop()
            self._long_press_timer.start(650)
            self._drag_origin = self._press_global_pos - self.frameGeometry().topLeft()
            self.controller.animator.set_action("dance")
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_origin is not None and event.buttons() & Qt.MouseButton.LeftButton:
            if self._press_global_pos is not None:
                distance = (event.globalPosition().toPoint() - self._press_global_pos).manhattanLength()
                if distance >= QApplication.startDragDistance():
                    self._drag_started = True
                    self._long_press_timer.stop()
                    self._single_click_timer.stop()
            self.move(event.globalPosition().toPoint() - self._drag_origin)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._long_press_timer.stop()
            self._drag_origin = None
            self._press_global_pos = None
            self.settings.x = self.x()
            self.settings.y = self.y()
            save_settings(self.settings)
            if not self._long_press_fired and not self._drag_started:
                self._single_click_timer.start(QApplication.doubleClickInterval())
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._long_press_timer.stop()
            self._single_click_timer.stop()
            self._long_press_fired = True
            self._drag_started = False
            self._dj_panel.recommend_from_context()
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event) -> None:
        self._build_context_menu().exec(event.globalPos())

    def showEvent(self, event) -> None:
        super().showEvent(event)
        keep_window_above_apps(self)

    def _build_context_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.addAction(_action("按心情推荐", self.ask_mood, self))
        menu.addAction(
            _action(
                "按当前状态推荐",
                self._dj_panel.recommend_from_context,
                self,
            )
        )
        menu.addAction(
            _action("自动开播", lambda: self._run_pet_command(self.interactions.long_press, "正在自动开播..."), self)
        )
        menu.addAction(_action("播放编号", self.play_number_dialog, self))
        menu.addAction(
            _action(
                "当前播放",
                self._dj_panel.now_playing,
                self,
            )
        )
        menu.addAction(_action("打开 DJ 面板", self._dj_panel.show, self))
        menu.addAction(_action("暂停/继续", self.toggle_playback, self))
        menu.addAction(_action("下一首", self.next_track, self))
        skin_menu = menu.addMenu("切换皮肤")
        for skin_id, skin in BUILTIN_SKINS.items():
            skin_menu.addAction(_action(skin.name, lambda sid=skin_id: self.set_skin(sid), self))
        menu.addSeparator()
        _add_display_settings_menu(menu, self)
        menu.addSeparator()
        menu.addAction(_action("退出", _quit_application, self))
        return menu

    def _show_more_menu(self) -> None:
        self._build_context_menu().exec(self._more_button.mapToGlobal(QPoint(0, self._more_button.height())))

    def _handle_long_press(self) -> None:
        self._long_press_fired = True
        self._run_pet_command(self.interactions.long_press, "正在自动开播...")

    def _handle_single_click(self) -> None:
        self._run_pet_command(self.interactions.single_click, "读取当前播放...")

    def ask_mood(self) -> None:
        text, ok = QInputDialog.getText(self, "DJ Buddy", "想听什么心情？")
        if not ok or not text.strip():
            return
        self._dj_panel.recommend_from_text(text)

    def show_now_playing(self) -> None:
        self._dj_panel.now_playing()

    def play_number_dialog(self) -> None:
        number, ok = QInputDialog.getInt(self, "DJ Buddy", "播放第几首？", 1, 1, 999, 1)
        if not ok:
            return
        self._run_pet_command(lambda: self.music_session.play_number(number), "正在播放选择...")

    def toggle_playback(self) -> None:
        self._run_pet_command(
            lambda: self._music_command_card("暂停/继续", self.controller.music.toggle), "切换播放中..."
        )

    def next_track(self) -> None:
        self._run_pet_command(
            lambda: self._music_command_card("下一首", self.controller.music.next_track), "切到下一首..."
        )

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
        self._bubble.set_pixel_text(_trim_output(text))
        self._render()

    def _run_pet_command(self, command, pending_text: str = "思考中...") -> None:
        pending = PetSessionResult(True, "think", PetBubbleCard("status", pending_text, action="think"))
        self._apply_session_result(pending)
        accepted = self.command_runner.run(command)
        if not accepted:
            self._show_bubble("上一条命令还在进行中...")

    def _music_command_card(self, title: str, fn) -> PetSessionResult:
        result = fn()
        if not result.ok:
            return PetSessionResult(False, "sad", self.music_session.bubble.error(title, result.text))
        return PetSessionResult(True, "dance", self.music_session.bubble.confirmation(title, result.text))

    def _apply_session_result(self, result: PetSessionResult) -> None:
        self.controller.animator.set_action(result.action)
        if self._dj_panel.isVisible() and _should_record_in_dj_panel(result):
            self._dj_panel.show_result(result)
        self._show_bubble(_pet_bubble_text(result))
        self._track_label.setText(self.controller.current_track_label())

    def _apply_live_result(self, result: PetSessionResult) -> None:
        if result.card.kind != "live":
            return
        self._last_live_playing = result.action == "dance"
        if self._last_live_playing:
            self.controller.animator.set_action("dance")
        elif self.controller.animator.action == "dance":
            self.controller.refresh_action()
        if self._dj_panel.isVisible():
            self._dj_panel.refresh_live_snapshot()
        if not result.ok:
            self._last_live_label = result.card.text
            return
        if result.card.text == self._last_live_label:
            return
        self._last_live_label = result.card.text
        self._show_bubble(result.card.text)
        self._track_label.setText(_live_track_label(result.card.text))


def _action(text: str, callback, parent) -> QAction:
    action = QAction(text, parent)
    action.triggered.connect(lambda _checked=False: callback())
    return action


def _add_display_settings_menu(menu: QMenu, owner) -> None:
    settings_menu = menu.addMenu("显示设置")
    menu_bar_action = QAction("显示菜单栏图标", owner)
    menu_bar_action.setCheckable(True)
    menu_bar_action.setChecked(owner.settings.show_menu_bar_icon)
    menu_bar_action.toggled.connect(lambda checked: _set_menu_bar_from_pet(owner, checked))
    settings_menu.addAction(menu_bar_action)

    dock_action = QAction("显示程序坞图标", owner)
    dock_action.setCheckable(True)
    dock_action.setChecked(owner.settings.show_dock_icon)
    dock_action.toggled.connect(lambda checked: _set_dock_from_pet(owner, checked))
    settings_menu.addAction(dock_action)


def _set_menu_bar_from_pet(owner, visible: bool) -> None:
    owner.settings.show_menu_bar_icon = bool(visible)
    controller = _pet_menu_bar_controller()
    if controller is not None:
        controller.set_menu_bar_visible(owner.settings.show_menu_bar_icon)
    else:
        save_settings(owner.settings)
    state = "显示" if owner.settings.show_menu_bar_icon else "隐藏"
    owner._show_bubble(f"菜单栏图标：{state}")


def _set_dock_from_pet(owner, visible: bool) -> None:
    owner.settings.show_dock_icon = bool(visible)
    controller = _pet_menu_bar_controller()
    if controller is not None:
        applied = controller.set_dock_icon_visible(owner.settings.show_dock_icon)
    else:
        applied = set_dock_icon_visible(owner.settings.show_dock_icon)
        save_settings(owner.settings)
    if applied:
        state = "显示" if owner.settings.show_dock_icon else "隐藏"
        owner._show_bubble(f"程序坞图标：{state}")
        return
    owner._show_bubble("显示设置已保存，重启 App 后生效")


def _pet_menu_bar_controller():
    app = QApplication.instance()
    if app is None:
        return None
    return getattr(app, "_cwb_pet_menu_bar", None)


def _icon_button(text: str, tooltip: str) -> QPushButton:
    button = QPushButton(text)
    button.setToolTip(tooltip)
    style_icon_button(button)
    return button


def _controls_widget(*buttons: QPushButton) -> QWidget:
    widget = QWidget()
    width = 26 * len(buttons) + 4 * max(0, len(buttons) - 1)
    widget.setFixedWidth(width)
    widget.setMaximumWidth(width)
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    for button in buttons:
        layout.addWidget(button)
    return widget


def _style_sprite_label(label: QLabel) -> None:
    label.setAutoFillBackground(False)
    label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    label.setStyleSheet("QLabel { background: transparent; border: none; }")


def _style_pet_window(window: QWidget) -> None:
    window.setWindowFlags(
        Qt.WindowType.Window
        | Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.WindowStaysOnTopHint
        | Qt.WindowType.NoDropShadowWindowHint
    )
    window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    window.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
    window.setAutoFillBackground(False)


def _trim_output(text: str) -> str:
    clean = text.strip() or "没有返回内容"
    return re.sub(r"\n{3,}", "\n\n", clean)[:1200]


def _pet_bubble_text(result: PetSessionResult) -> str:
    if result.card.kind == "recommendations":
        count = len(result.card.items)
        title = result.card.text.splitlines()[0] if result.card.text else ""
        if title.startswith(("搜索", "资料库", "喜欢", "歌单")):
            if count:
                return f"找到 {count} 个结果，已放到 DJ 面板"
            return "找到结果，已放到 DJ 面板"
        if count:
            return f"找到 {count} 首推荐，已放到 DJ 面板"
        return "找到推荐结果，已放到 DJ 面板"
    return result.card.text


def _should_record_in_dj_panel(result: PetSessionResult) -> bool:
    return not (result.action == "think" and result.card.kind == "status")


def _live_track_label(text: str) -> str:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if len(lines) >= 2:
        return lines[1]
    return "未播放"


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
        self.music_session = PetMusicSession(music=self.controller.music, load_state=self.controller.load_state)
        self.interactions = PetInteractionController(session=self.music_session)
        self.command_runner = PetCommandRunner(self)
        self.command_runner.finished.connect(self._apply_session_result)
        self.live_runner = PetCommandRunner(self, timeout_ms=4_000)
        self.live_runner.finished.connect(self._apply_live_result)
        self._dj_panel = CodeBeatDjPanel(self)
        self._last_live_label = ""
        self._last_live_playing = False
        self._long_press_fired = False
        self._long_press_timer = QTimer(self)
        self._long_press_timer.setSingleShot(True)
        self._long_press_timer.timeout.connect(self._handle_long_press)
        self._single_click_timer = QTimer(self)
        self._single_click_timer.setSingleShot(True)
        self._single_click_timer.timeout.connect(self._handle_single_click)
        self.petdex_animator = PetdexAnimator()
        self._installed_pets = installed_petdex_pets()
        self._spritesheet = QPixmap()
        self._petdex_display_size = (72, 78)
        self._load_petdex_pet(pet)
        if self.settings.petdex_slug != self.pet.slug:
            self.settings.petdex_slug = self.pet.slug
            save_settings(self.settings)
        self._drag_origin: QPoint | None = None
        self._press_global_pos: QPoint | None = None
        self._drag_started = False

        self._bubble = PixelBubbleLabel(self)
        self._track_label = QLabel("未播放", self)
        self._track_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        style_status_label(self._track_label)
        self._track_label.setVisible(False)
        self._label = QLabel(self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _style_sprite_label(self._label)
        self._label.setFixedSize(*self._petdex_display_size)
        self._now_button = _icon_button("♪", "当前播放")
        self._now_button.clicked.connect(self._dj_panel.now_playing)
        self._recommend_button = _icon_button("+", "按当前状态推荐")
        self._recommend_button.clicked.connect(self._dj_panel.recommend_from_context)
        self._reroll_button = _icon_button("↻", "换一组")
        self._reroll_button.clicked.connect(self._dj_panel.reroll)
        self._more_button = _icon_button("...", "更多")
        self._more_button.clicked.connect(self._show_more_menu)

        self._controls_widget = _controls_widget(
            self._now_button,
            self._recommend_button,
            self._reroll_button,
            self._more_button,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self._bubble)
        layout.addWidget(self._track_label)
        layout.addWidget(self._label, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._controls_widget, alignment=Qt.AlignmentFlag.AlignHCenter)

        _style_pet_window(self)
        self.move(self.settings.x, self.settings.y)
        self._render()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(180)

        self.state_timer = QTimer(self)
        self.state_timer.timeout.connect(self._refresh_state)
        self.state_timer.start(1500)

        self.live_timer = QTimer(self)
        self.live_timer.timeout.connect(self._poll_live_music)
        self.live_timer.start(3500)

    def _tick(self) -> None:
        self.petdex_animator.tick()
        self._render()

    def _refresh_state(self) -> None:
        action = self.controller.refresh_action()
        if self._last_live_playing:
            action = "dance"
        self.petdex_animator.set_action(action)
        self._track_label.setText(self.controller.current_track_label())

    def _poll_live_music(self) -> None:
        if not self.live_runner.busy:
            self.live_runner.run(self.music_session.live_now_playing)

    def _render(self) -> None:
        pixmap = _petdex_frame_pixmap(self._spritesheet, self.petdex_animator, self._petdex_display_size)
        self._label.setPixmap(pixmap)
        self._resize_shell()

    def _resize_shell(self) -> None:
        extra = 62 + (self._bubble.sizeHint().height() + 8 if self._bubble.isVisible() else 0)
        width = max(150, self._petdex_display_size[0] + 12)
        height = self._petdex_display_size[1] + extra
        if self.width() != width or self.height() != height:
            self.resize(width, height)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._long_press_fired = False
            self._drag_started = False
            self._press_global_pos = event.globalPosition().toPoint()
            self._single_click_timer.stop()
            self._long_press_timer.start(650)
            self._drag_origin = self._press_global_pos - self.frameGeometry().topLeft()
            self.petdex_animator.set_action("dance")
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_origin is not None and event.buttons() & Qt.MouseButton.LeftButton:
            if self._press_global_pos is not None:
                distance = (event.globalPosition().toPoint() - self._press_global_pos).manhattanLength()
                if distance >= QApplication.startDragDistance():
                    self._drag_started = True
                    self._long_press_timer.stop()
                    self._single_click_timer.stop()
            self.move(event.globalPosition().toPoint() - self._drag_origin)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._long_press_timer.stop()
            self._drag_origin = None
            self._press_global_pos = None
            self.settings.x = self.x()
            self.settings.y = self.y()
            save_settings(self.settings)
            if not self._long_press_fired and not self._drag_started:
                self._single_click_timer.start(QApplication.doubleClickInterval())
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._long_press_timer.stop()
            self._single_click_timer.stop()
            self._long_press_fired = True
            self._drag_started = False
            self._dj_panel.recommend_from_context()
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event) -> None:
        self._build_context_menu().exec(event.globalPos())

    def showEvent(self, event) -> None:
        super().showEvent(event)
        keep_window_above_apps(self)

    def _build_context_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.addAction(_action("按心情推荐", self.ask_mood, self))
        menu.addAction(
            _action(
                "按当前状态推荐",
                self._dj_panel.recommend_from_context,
                self,
            )
        )
        menu.addAction(
            _action("自动开播", lambda: self._run_pet_command(self.interactions.long_press, "正在自动开播..."), self)
        )
        menu.addAction(_action("播放编号", self.play_number_dialog, self))
        menu.addAction(
            _action(
                "当前播放",
                self._dj_panel.now_playing,
                self,
            )
        )
        menu.addAction(_action("打开 DJ 面板", self._dj_panel.show, self))
        menu.addAction(_action("暂停/继续", self.toggle_playback, self))
        menu.addAction(_action("下一首", self.next_track, self))
        pet_menu = menu.addMenu("切换宠物")
        for pet in self._installed_pets:
            pet_menu.addAction(_action(pet.name, lambda next_pet=pet: self.set_petdex_pet(next_pet), self))
        if not self._installed_pets:
            pet_menu.addAction(_action("未发现本地宠物", lambda: self._show_bubble("未发现本地 Petdex 宠物"), self))
        menu.addSeparator()
        _add_display_settings_menu(menu, self)
        menu.addSeparator()
        menu.addAction(_action("退出", _quit_application, self))
        return menu

    def _show_more_menu(self) -> None:
        self._build_context_menu().exec(self._more_button.mapToGlobal(QPoint(0, self._more_button.height())))

    def _handle_long_press(self) -> None:
        self._long_press_fired = True
        self._run_pet_command(self.interactions.long_press, "正在自动开播...")

    def _handle_single_click(self) -> None:
        self._run_pet_command(self.interactions.single_click, "读取当前播放...")

    def ask_mood(self) -> None:
        text, ok = QInputDialog.getText(self, "DJ Buddy", "想听什么心情？")
        if not ok or not text.strip():
            return
        self._dj_panel.recommend_from_text(text)

    def show_now_playing(self) -> None:
        self._dj_panel.now_playing()

    def play_number_dialog(self) -> None:
        number, ok = QInputDialog.getInt(self, "DJ Buddy", "播放第几首？", 1, 1, 999, 1)
        if not ok:
            return
        self._run_pet_command(lambda: self.music_session.play_number(number), "正在播放选择...")

    def toggle_playback(self) -> None:
        self._run_pet_command(
            lambda: self._music_command_card("暂停/继续", self.controller.music.toggle), "切换播放中..."
        )

    def next_track(self) -> None:
        self._run_pet_command(
            lambda: self._music_command_card("下一首", self.controller.music.next_track), "切到下一首..."
        )

    def set_petdex_pet(self, pet: PetdexPet) -> None:
        self._load_petdex_pet(pet)
        self.settings.petdex_slug = pet.slug
        save_settings(self.settings)
        self.petdex_animator.set_action("recommend")
        self._show_bubble(f"宠物：{pet.name}")

    def cycle_petdex_pet(self) -> None:
        self._installed_pets = installed_petdex_pets()
        if not self._installed_pets:
            self._show_bubble("未发现本地 Petdex 宠物")
            return
        current_index = next(
            (index for index, pet in enumerate(self._installed_pets) if pet.slug == self.pet.slug),
            -1,
        )
        next_pet = self._installed_pets[(current_index + 1) % len(self._installed_pets)]
        self.set_petdex_pet(next_pet)

    def _load_petdex_pet(self, pet: PetdexPet) -> None:
        spritesheet = QPixmap(str(resolve_spritesheet_path(pet)))
        if spritesheet.isNull():
            raise RuntimeError(f"Could not load Petdex spritesheet: {pet.spritesheet_path}")
        self.pet = pet
        self._spritesheet = spritesheet
        frame_w, frame_h = frame_size(self._spritesheet.width(), self._spritesheet.height())
        self._petdex_display_size = display_size(frame_w, frame_h)
        if hasattr(self, "_label"):
            self._label.setFixedSize(*self._petdex_display_size)
            self._render()

    def _show_bubble(self, text: str) -> None:
        self._bubble.set_pixel_text(_trim_output(text))
        self._render()

    def _run_pet_command(self, command, pending_text: str = "思考中...") -> None:
        pending = PetSessionResult(True, "think", PetBubbleCard("status", pending_text, action="think"))
        self._apply_session_result(pending)
        accepted = self.command_runner.run(command)
        if not accepted:
            self._show_bubble("上一条命令还在进行中...")

    def _music_command_card(self, title: str, fn) -> PetSessionResult:
        result = fn()
        if not result.ok:
            return PetSessionResult(False, "sad", self.music_session.bubble.error(title, result.text))
        return PetSessionResult(True, "dance", self.music_session.bubble.confirmation(title, result.text))

    def _apply_session_result(self, result: PetSessionResult) -> None:
        self.petdex_animator.set_action(result.action)
        if self._dj_panel.isVisible() and _should_record_in_dj_panel(result):
            self._dj_panel.show_result(result)
        self._show_bubble(_pet_bubble_text(result))
        self._track_label.setText(self.controller.current_track_label())

    def _apply_live_result(self, result: PetSessionResult) -> None:
        if result.card.kind != "live":
            return
        self._last_live_playing = result.action == "dance"
        if self._last_live_playing:
            self.petdex_animator.set_action("dance")
        elif self.petdex_animator.action == "dance":
            self.petdex_animator.set_action(self.controller.refresh_action())
        if self._dj_panel.isVisible():
            self._dj_panel.refresh_live_snapshot()
        if not result.ok:
            self._last_live_label = result.card.text
            return
        if result.card.text == self._last_live_label:
            return
        self._last_live_label = result.card.text
        self._show_bubble(result.card.text)
        self._track_label.setText(_live_track_label(result.card.text))


def _petdex_frame_pixmap(spritesheet: QPixmap, animator: PetdexAnimator, target_size: tuple[int, int]) -> QPixmap:
    row, col = animator.current_cell()

    frame_w, frame_h = frame_size(spritesheet.width(), spritesheet.height())
    source = QRect(col * frame_w, row * frame_h, frame_w, frame_h)
    frame = spritesheet.copy(source)
    return frame.scaled(
        target_size[0],
        target_size[1],
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.FastTransformation,
    )
