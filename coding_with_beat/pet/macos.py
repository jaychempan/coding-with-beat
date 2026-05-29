"""macOS-oriented app chrome for the desktop pet."""

from __future__ import annotations

import ctypes
import ctypes.util
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

APP_NAME = "Coding With Beat Pet"


def pet_icon_path() -> Path | None:
    path = Path(__file__).resolve().parents[2] / "assets" / "logo_icon.png"
    return path if path.exists() else None


def apply_app_metadata(app: QApplication) -> QIcon:
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Coding With Beat")
    icon = QIcon()
    path = pet_icon_path()
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
        self.icon = icon if icon is not None and not icon.isNull() else QIcon()
        self.menu = QMenu()
        self.tray = QSystemTrayIcon(self.icon, app)
        self.tray.setToolTip(APP_NAME)
        self._build_menu()
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._handle_activation)
        self.tray.show()

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
