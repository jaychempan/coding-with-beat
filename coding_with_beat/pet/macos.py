"""macOS-oriented app chrome for the desktop pet."""

from __future__ import annotations

import ctypes
import ctypes.util
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
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

APP_NAME = "CodeBeat"


def app_icon_path() -> Path | None:
    return _first_existing_asset(("waveform_app_icon.svg", "waveform_logo.svg", "logo_icon.png"))


def pet_icon_path() -> Path | None:
    return _first_existing_asset(("waveform_menu_bar.svg", "waveform_logo.svg", "logo_icon.png"))


def menu_bar_icon() -> QIcon:
    pixmap = QPixmap(22, 22)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    try:
        color = QColor("#8b5cf6")
        bars = (
            (4, 9, 3, 8, 130),
            (8, 6, 3, 14, 190),
            (12, 3, 4, 18, 255),
            (17, 7, 3, 13, 190),
        )
        for x, y, w, h, alpha in bars:
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
    if sys.platform != "darwin":
        return False
    try:
        from AppKit import NSApplication, NSApplicationActivationPolicyAccessory

        NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    except Exception:
        return _hide_dock_icon_with_ctypes()
    return True


def _hide_dock_icon_with_ctypes() -> bool:
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

        objc.objc_msgSend.restype = ctypes.c_bool
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long]
        return bool(objc.objc_msgSend(app, set_activation_policy, 1))
    except Exception:
        return False


class PetMenuBarController:
    def __init__(self, app: QApplication, window, icon: QIcon | None = None) -> None:
        self.app = app
        self.window = window
        self.icon = icon if icon is not None and not icon.isNull() else menu_bar_icon()
        self.menu = QMenu()
        self.tray = QSystemTrayIcon(self.icon, app)
        self.tray.setToolTip(APP_NAME)
        self._build_menu()
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._handle_activation)
        self.tray.show()
        self.available = QSystemTrayIcon.isSystemTrayAvailable()

    def toggle_window(self) -> None:
        if self.window.isVisible():
            self.window.hide()
            return
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def _build_menu(self) -> None:
        self.menu.addAction("显示/隐藏宠物", self.toggle_window)
        self.menu.addSeparator()
        self.menu.addAction("当前播放", self.window.show_now_playing)
        self.menu.addAction("推荐歌曲", self._recommend)
        self.menu.addAction("下一首", self.window.next_track)
        self.menu.addSeparator()
        self.menu.addAction("退出", self.app.quit)

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
