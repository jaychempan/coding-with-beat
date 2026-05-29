"""Desktop pet application entrypoint."""

from __future__ import annotations

import sys


def run(*, petdex_slug: str | None = None, hide_dock: bool = True) -> int:
    try:
        from PySide6.QtWidgets import QApplication
    except Exception as e:
        raise RuntimeError("PySide6 is required") from e

    from .macos import PetMenuBarController, apply_app_metadata, hide_dock_icon
    from .window import PetWindow

    app = QApplication.instance() or QApplication(sys.argv)
    icon = apply_app_metadata(app)
    if petdex_slug:
        try:
            window = PetWindow.from_petdex(petdex_slug)
        except Exception as e:
            window = PetWindow()
            window._show_bubble(f"Petdex 加载失败，已回退内置宠物：{e}")
    else:
        window = PetWindow()

    menu_bar = PetMenuBarController(app, window, icon)
    app._cwb_pet_menu_bar = menu_bar
    app.setQuitOnLastWindowClosed(False)
    if hide_dock:
        hide_dock_icon()

    window.show()
    return int(app.exec())
