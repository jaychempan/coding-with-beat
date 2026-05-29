"""Background command runner for desktop pet music actions."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from .bubble import PetBubbleView
from .session import PetSessionResult

Command = Callable[[], PetSessionResult]


class _CommandWorker(QObject):
    finished = Signal(int, object)

    def __init__(self, command_id: int, command: Command) -> None:
        super().__init__()
        self.command_id = command_id
        self.command = command

    def run(self) -> None:
        try:
            result = self.command()
        except Exception as e:
            card = PetBubbleView().error("命令失败", str(e))
            result = PetSessionResult(False, "sad", card)
        self.finished.emit(self.command_id, result)


class PetCommandRunner(QObject):
    finished = Signal(object)

    def __init__(self, parent=None, timeout_ms: int = 25_000) -> None:
        super().__init__(parent)
        self.busy = False
        self._thread: QThread | None = None
        self._worker: _CommandWorker | None = None
        self._active_command_id = 0
        self._timeout_ms = timeout_ms
        self._timeout_timer = QTimer(self)
        self._timeout_timer.setSingleShot(True)
        self._timeout_timer.timeout.connect(self._timeout_active_command)

    def run(self, command: Command) -> bool:
        if self.busy:
            return False
        self.busy = True
        self._active_command_id += 1
        command_id = self._active_command_id
        thread = QThread(self)
        worker = _CommandWorker(command_id, command)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._complete)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._thread = thread
        self._worker = worker
        thread.start()
        self._timeout_timer.start(self._timeout_ms)
        return True

    def _complete(self, command_id: int, result: PetSessionResult) -> None:
        if command_id != self._active_command_id:
            return
        self._timeout_timer.stop()
        self.busy = False
        self._thread = None
        self._worker = None
        self.finished.emit(result)

    def _timeout_active_command(self) -> None:
        if not self.busy:
            return
        self._active_command_id += 1
        self.busy = False
        self._thread = None
        self._worker = None
        card = PetBubbleView().error(
            "命令超时",
            "这次音乐操作没有及时返回，可能还在等待 Apple Music 加入资料库。可以点添加后再重试。",
        )
        self.finished.emit(PetSessionResult(False, "sad", card))
