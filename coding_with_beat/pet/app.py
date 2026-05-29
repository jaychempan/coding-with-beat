"""Desktop pet application entrypoint."""

from __future__ import annotations

import sys


def run(*, petdex_slug: str | None = None) -> int:
    try:
        from PySide6.QtWidgets import QApplication
    except Exception as e:
        raise RuntimeError("PySide6 is required") from e

    from .window import PetWindow

    app = QApplication.instance() or QApplication(sys.argv)
    if petdex_slug:
        try:
            window = PetWindow.from_petdex(petdex_slug)
        except Exception as e:
            window = PetWindow()
            window._show_bubble(f"Petdex 加载失败，已回退内置宠物：{e}")
    else:
        window = PetWindow()
    window.show()
    return int(app.exec())
