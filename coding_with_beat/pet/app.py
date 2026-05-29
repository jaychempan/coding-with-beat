"""Desktop pet application entrypoint."""

from __future__ import annotations

import sys


def run() -> int:
    try:
        from PySide6.QtWidgets import QApplication
    except Exception as e:
        raise RuntimeError("PySide6 is required") from e

    from .window import PetWindow

    app = QApplication.instance() or QApplication(sys.argv)
    window = PetWindow()
    window.show()
    return int(app.exec())
