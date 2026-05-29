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
    window = PetWindow.from_petdex(petdex_slug) if petdex_slug else PetWindow()
    window.show()
    return int(app.exec())
