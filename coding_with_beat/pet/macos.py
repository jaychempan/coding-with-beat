"""macOS-oriented app chrome for the desktop pet."""

from __future__ import annotations

import ctypes
import ctypes.util
import sys
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from .settings import PetSettings, load_settings, save_settings

APP_NAME = "CodeBeat"
_NS_APPLICATION_ACTIVATION_POLICY_REGULAR = 0
_NS_APPLICATION_ACTIVATION_POLICY_ACCESSORY = 1
_NS_STATUS_WINDOW_LEVEL = 25
_NS_WINDOW_COLLECTION_BEHAVIOR_CAN_JOIN_ALL_SPACES = 1 << 0
_NS_WINDOW_COLLECTION_BEHAVIOR_MOVE_TO_ACTIVE_SPACE = 1 << 1
_NS_WINDOW_COLLECTION_BEHAVIOR_STATIONARY = 1 << 4
_NS_WINDOW_COLLECTION_BEHAVIOR_FULL_SCREEN_AUXILIARY = 1 << 8


def app_icon_path() -> Path | None:
    return _first_existing_asset(("waveform_app_icon.svg", "waveform_logo.svg", "logo_icon.png"))


def pet_icon_path() -> Path | None:
    return app_icon_path()


def menu_bar_icon() -> QIcon:
    path = pet_icon_path()
    if path is not None:
        icon = QIcon(str(path))
        if not icon.isNull():
            return icon
    return _fallback_menu_bar_icon()


def _fallback_menu_bar_icon() -> QIcon:
    pixmap = QPixmap(22, 22)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    try:
        color = QColor("#8b5cf6")
        offset = 1.0
        scale = 0.1
        source_bars = (
            (38, 80, 18, 40, 128),
            (67, 58, 18, 84, 191),
            (91, 30, 18, 140, 255),
            (115, 52, 18, 96, 191),
            (144, 80, 18, 40, 128),
        )
        for source_x, source_y, source_w, source_h, alpha in source_bars:
            x = round(offset + source_x * scale)
            y = round(offset + source_y * scale)
            w = max(2, round(source_w * scale))
            h = max(2, round(source_h * scale))
            color.setAlpha(alpha)
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(x, y, w, h, 2, 2)
    finally:
        painter.end()
    return QIcon(pixmap)


def _first_existing_asset(names: tuple[str, ...]) -> Path | None:
    assets_dir = _assets_dir()
    for name in names:
        path = assets_dir / name
        if path.exists():
            return path
    return None


def _assets_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "assets"


def apply_app_metadata(app: QApplication) -> QIcon:
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Coding With Beat")
    icon = QIcon()
    path = app_icon_path()
    if path is not None:
        icon = QIcon(str(path))
        app.setWindowIcon(icon)
    return icon


def hide_dock_icon() -> bool:
    return set_dock_icon_visible(False)


def set_dock_icon_visible(visible: bool) -> bool:
    if sys.platform != "darwin":
        return False
    try:
        from AppKit import NSApplication

        policy = _NS_APPLICATION_ACTIVATION_POLICY_REGULAR if visible else _NS_APPLICATION_ACTIVATION_POLICY_ACCESSORY
        NSApplication.sharedApplication().setActivationPolicy_(policy)
    except Exception:
        return _set_dock_icon_visible_with_ctypes(visible)
    return True


def keep_window_above_apps(window) -> bool:
    """Put a Qt widget above normal app windows on macOS."""
    if sys.platform != "darwin" or QGuiApplication.platformName().lower() == "offscreen":
        return False
    try:
        return _keep_window_above_apps_with_pyobjc(window)
    except Exception:
        return _keep_window_above_apps_with_ctypes(window)


def _collection_behavior_with_pet_flags(current_behavior: int) -> int:
    behavior = int(current_behavior) & ~_NS_WINDOW_COLLECTION_BEHAVIOR_MOVE_TO_ACTIVE_SPACE
    return behavior | (
        _NS_WINDOW_COLLECTION_BEHAVIOR_CAN_JOIN_ALL_SPACES
        | _NS_WINDOW_COLLECTION_BEHAVIOR_STATIONARY
        | _NS_WINDOW_COLLECTION_BEHAVIOR_FULL_SCREEN_AUXILIARY
    )


def _keep_window_above_apps_with_pyobjc(window) -> bool:
    import objc

    native_view = objc.objc_object(c_void_p=ctypes.c_void_p(int(window.winId())))
    ns_window = native_view.window()
    if ns_window is None:
        return False
    ns_window.setLevel_(_NS_STATUS_WINDOW_LEVEL)
    ns_window.setCollectionBehavior_(_collection_behavior_with_pet_flags(ns_window.collectionBehavior()))
    return True


def _keep_window_above_apps_with_ctypes(window) -> bool:
    native_id = int(window.winId())
    if not native_id:
        return False
    objc = _objc_runtime()
    ns_window = _objc_send_id(objc, native_id, b"window") or native_id
    behavior = _objc_send_ulong(objc, ns_window, b"collectionBehavior")
    _objc_send_void_long(objc, ns_window, b"setLevel:", _NS_STATUS_WINDOW_LEVEL)
    _objc_send_void_ulong(objc, ns_window, b"setCollectionBehavior:", _collection_behavior_with_pet_flags(behavior))
    return True


def _objc_runtime():
    library = ctypes.util.find_library("objc")
    if not library:
        raise RuntimeError("Objective-C runtime not available")
    objc = ctypes.cdll.LoadLibrary(library)
    objc.sel_registerName.restype = ctypes.c_void_p
    objc.sel_registerName.argtypes = [ctypes.c_char_p]
    return objc


def _objc_selector(objc, name: bytes):
    selector = objc.sel_registerName(name)
    if not selector:
        raise RuntimeError(f"Objective-C selector not available: {name!r}")
    return selector


def _objc_send_id(objc, receiver: int, selector_name: bytes) -> int:
    objc.objc_msgSend.restype = ctypes.c_void_p
    objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    return int(objc.objc_msgSend(receiver, _objc_selector(objc, selector_name)) or 0)


def _objc_send_ulong(objc, receiver: int, selector_name: bytes) -> int:
    objc.objc_msgSend.restype = ctypes.c_ulong
    objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    return int(objc.objc_msgSend(receiver, _objc_selector(objc, selector_name)))


def _objc_send_void_long(objc, receiver: int, selector_name: bytes, value: int) -> None:
    objc.objc_msgSend.restype = None
    objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long]
    objc.objc_msgSend(receiver, _objc_selector(objc, selector_name), int(value))


def _objc_send_void_ulong(objc, receiver: int, selector_name: bytes, value: int) -> None:
    objc.objc_msgSend.restype = None
    objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
    objc.objc_msgSend(receiver, _objc_selector(objc, selector_name), int(value))


def _set_dock_icon_visible_with_ctypes(visible: bool) -> bool:
    library = ctypes.util.find_library("objc")
    if not library:
        return False
    try:
        objc = ctypes.cdll.LoadLibrary(library)
        objc.objc_getClass.restype = ctypes.c_void_p
        objc.objc_getClass.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]

        ns_application = objc.objc_getClass(b"NSApplication")
        shared_application = objc.sel_registerName(b"sharedApplication")
        set_activation_policy = objc.sel_registerName(b"setActivationPolicy:")
        if not ns_application or not shared_application or not set_activation_policy:
            return False

        objc.objc_msgSend.restype = ctypes.c_void_p
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        app = objc.objc_msgSend(ns_application, shared_application)
        if not app:
            return False

        policy = _NS_APPLICATION_ACTIVATION_POLICY_REGULAR if visible else _NS_APPLICATION_ACTIVATION_POLICY_ACCESSORY
        objc.objc_msgSend.restype = ctypes.c_bool
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long]
        return bool(objc.objc_msgSend(app, set_activation_policy, policy))
    except Exception:
        return False


class PetMenuBarController:
    def __init__(
        self,
        app: QApplication,
        window,
        icon: QIcon | None = None,
        *,
        settings: PetSettings | None = None,
        save_settings_func: Callable[[PetSettings], object] = save_settings,
        dock_visibility_func: Callable[[bool], object] = set_dock_icon_visible,
        show_menu_bar: bool = True,
    ) -> None:
        self.app = app
        self.window = window
        self.settings = settings or load_settings()
        self.save_settings_func = save_settings_func
        self.dock_visibility_func = dock_visibility_func
        self.icon = icon if icon is not None and not icon.isNull() else menu_bar_icon()
        self.menu = QMenu()
        self.tray = QSystemTrayIcon(self.icon, app)
        self.tray.setToolTip(APP_NAME)
        self._build_menu()
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._handle_activation)
        if show_menu_bar:
            self.tray.show()
        else:
            self.tray.hide()
        self.available = QSystemTrayIcon.isSystemTrayAvailable()

    def toggle_window(self) -> None:
        if self.window.isVisible():
            self.window.hide()
            return
        self.window.show()
        keep_window_above_apps(self.window)
        self.window.raise_()
        self.window.activateWindow()

    def _build_menu(self) -> None:
        self.menu.addAction("显示/隐藏宠物", self.toggle_window)
        self.menu.addSeparator()
        self.menu.addAction("当前播放", self.window.show_now_playing)
        self.menu.addAction("推荐歌曲", self._recommend)
        self.menu.addAction("下一首", self.window.next_track)
        settings_menu = self.menu.addMenu("显示设置")
        self.menu_bar_action = QAction("显示菜单栏图标", self.menu)
        self.menu_bar_action.setCheckable(True)
        self.menu_bar_action.setChecked(self.settings.show_menu_bar_icon)
        self.menu_bar_action.toggled.connect(self.set_menu_bar_visible)
        settings_menu.addAction(self.menu_bar_action)
        self.dock_action = QAction("显示程序坞图标", self.menu)
        self.dock_action.setCheckable(True)
        self.dock_action.setChecked(self.settings.show_dock_icon)
        self.dock_action.toggled.connect(self.set_dock_icon_visible)
        settings_menu.addAction(self.dock_action)
        self.menu.addSeparator()
        self.menu.addAction("退出", self.app.quit)

    def set_menu_bar_visible(self, visible: bool) -> None:
        self.settings.show_menu_bar_icon = bool(visible)
        _set_checked_without_signal(self.menu_bar_action, self.settings.show_menu_bar_icon)
        if self.settings.show_menu_bar_icon:
            self.tray.show()
        else:
            self.tray.hide()
        self.save_settings_func(self.settings)

    def set_dock_icon_visible(self, visible: bool) -> bool:
        self.settings.show_dock_icon = bool(visible)
        _set_checked_without_signal(self.dock_action, self.settings.show_dock_icon)
        applied = bool(self.dock_visibility_func(self.settings.show_dock_icon))
        self.save_settings_func(self.settings)
        return applied

    def _recommend(self) -> None:
        self.window._run_pet_command(self.window.interactions.double_click, "正在按当前状态找歌...")

    def _handle_activation(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in {
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        }:
            self.toggle_window()


class CodeBeatControlWindow(QWidget):
    def __init__(self, app: QApplication, window) -> None:
        super().__init__()
        self.app = app
        self.window = window
        self.setWindowTitle(APP_NAME)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setFixedWidth(184)

        title = QLabel(APP_NAME)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("QLabel { color: #8b5cf6; font-weight: 700; padding: 4px; }")

        self.show_hide_button = _control_button("显示/隐藏", self.toggle_window)
        now_button = _control_button("当前播放", self.window.show_now_playing)
        recommend_button = _control_button("推荐", self._recommend)
        next_button = _control_button("下一首", self.window.next_track)
        quit_button = _control_button("退出", self.app.quit)

        row1 = QHBoxLayout()
        row1.addWidget(self.show_hide_button)
        row1.addWidget(now_button)
        row2 = QHBoxLayout()
        row2.addWidget(recommend_button)
        row2.addWidget(next_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(title)
        layout.addLayout(row1)
        layout.addLayout(row2)
        layout.addWidget(quit_button)

    def toggle_window(self) -> None:
        if self.window.isVisible():
            self.window.hide()
            return
        self.window.show()
        keep_window_above_apps(self.window)
        self.window.raise_()
        self.window.activateWindow()

    def _recommend(self) -> None:
        self.window._run_pet_command(self.window.interactions.double_click, "正在按当前状态找歌...")


def _control_button(text: str, callback) -> QPushButton:
    button = QPushButton(text)
    button.clicked.connect(callback)
    button.setStyleSheet(
        "QPushButton { color: #f8fafc; background: rgba(15, 23, 42, 220);"
        " border: 1px solid rgba(139, 92, 246, 160); border-radius: 4px; padding: 5px 7px; }"
        "QPushButton:hover { border-color: rgba(167, 139, 250, 230); }"
    )
    return button


def _set_checked_without_signal(action: QAction, checked: bool) -> None:
    previous = action.blockSignals(True)
    try:
        action.setChecked(checked)
    finally:
        action.blockSignals(previous)
