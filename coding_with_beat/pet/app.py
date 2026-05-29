"""Desktop pet application entrypoint."""

from __future__ import annotations

import sys


def run(
    *,
    petdex_slug: str | None = None,
    hide_dock: bool = True,
    show_control: bool = False,
    show_menu_bar: bool = True,
) -> int:
    try:
        from PySide6.QtWidgets import QApplication
    except Exception as e:
        raise RuntimeError("PySide6 is required") from e

    from .macos import (
        CodeBeatControlWindow,
        PetMenuBarController,
        apply_app_metadata,
        hide_dock_icon,
        menu_bar_icon,
        pet_icon_path,
    )
    from .window import PetWindow

    app = QApplication.instance() or QApplication(sys.argv)
    apply_app_metadata(app)
    if petdex_slug:
        try:
            window = PetWindow.from_petdex(petdex_slug)
        except Exception as e:
            window = PetWindow()
            window._show_bubble(f"Petdex 加载失败，已回退内置宠物：{e}")
    else:
        window = PetWindow()

    settings = window.settings
    menu_bar = PetMenuBarController(app, window, menu_bar_icon(), settings=settings, show_menu_bar=show_menu_bar)
    app._cwb_pet_menu_bar = menu_bar
    app.setQuitOnLastWindowClosed(False)
    print(
        f"CodeBeat tray available={menu_bar.available} visible={menu_bar.tray.isVisible()} icon={pet_icon_path()}",
        flush=True,
    )
    if show_control or not menu_bar.available:
        control_window = CodeBeatControlWindow(app, window)
        control_window.show()
        app._cwb_control_window = control_window
        print("CodeBeat control window shown.", flush=True)
    if hide_dock:
        hide_dock_icon()

    window.show()
    return int(app.exec())
