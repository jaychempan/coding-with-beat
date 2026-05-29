"""Background command runner for desktop pet music actions."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QThread, Signal

from .bubble import PetBubbleView
from .session import PetSessionResult

Command = Callable[[], PetSessionResult]


class _CommandWorker(QObject):
    finished = Signal(object)

    def __init__(self, command: Command) -> None:
        super().__init__()
        self.command = command

    def run(self) -> None:
        try:
            result = self.command()
        except Exception as e:
            card = PetBubbleView().error("命令失败", str(e))
            result = PetSessionResult(False, "sad", card)
        self.finished.emit(result)


class PetCommandRunner(QObject):
    finished = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.busy = False
        self._thread: QThread | None = None
        self._worker: _CommandWorker | None = None

    def run(self, command: Command) -> bool:
        if self.busy:
            return False
        self.busy = True
        thread = QThread(self)
        worker = _CommandWorker(command)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._complete)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._thread = thread
        self._worker = worker
        thread.start()
        return True

    def _complete(self, result: PetSessionResult) -> None:
        self.busy = False
        self._thread = None
        self._worker = None
        self.finished.emit(result)
