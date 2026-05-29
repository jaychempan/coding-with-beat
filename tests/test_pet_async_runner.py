import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from coding_with_beat.pet.async_runner import PetCommandRunner
from coding_with_beat.pet.bubble import PetBubbleCard
from coding_with_beat.pet.session import PetSessionResult


def _wait_for(predicate, app, timeout=2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.processEvents()
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition was not met")


def _thread_stopped(thread) -> bool:
    try:
        return thread is None or not thread.isRunning()
    except RuntimeError:
        return True


def test_runner_returns_result_without_blocking_caller():
    app = QApplication.instance() or QApplication([])
    runner = PetCommandRunner()
    results = []
    runner.finished.connect(results.append)

    started = time.time()
    accepted = runner.run(lambda: PetSessionResult(True, "dance", PetBubbleCard("status", "done")))

    assert accepted is True
    assert time.time() - started < 0.2
    _wait_for(lambda: bool(results), app)
    assert results[0].ok is True
    assert results[0].card.text == "done"


def test_runner_ignores_duplicate_while_busy():
    app = QApplication.instance() or QApplication([])
    runner = PetCommandRunner()
    release = {"ready": False}

    def slow():
        while not release["ready"]:
            time.sleep(0.01)
        return PetSessionResult(True, "idle", PetBubbleCard("status", "done"))

    assert runner.run(slow) is True
    assert runner.run(lambda: PetSessionResult(True, "idle", PetBubbleCard("status", "second"))) is False
    release["ready"] = True
    _wait_for(lambda: not runner.busy, app)


def test_runner_converts_exception_to_error_result():
    app = QApplication.instance() or QApplication([])
    runner = PetCommandRunner()
    results = []
    runner.finished.connect(results.append)

    runner.run(lambda: (_ for _ in ()).throw(RuntimeError("boom")))

    _wait_for(lambda: bool(results), app)
    assert results[0].ok is False
    assert results[0].action == "sad"
    assert results[0].card.kind == "error"
    assert "boom" in results[0].card.text


def test_runner_times_out_and_accepts_next_command():
    app = QApplication.instance() or QApplication([])
    runner = PetCommandRunner(timeout_ms=50)
    results = []
    runner.finished.connect(results.append)

    def stuck():
        time.sleep(0.2)
        return PetSessionResult(True, "idle", PetBubbleCard("status", "late"))

    assert runner.run(stuck) is True
    first_thread = runner._thread
    _wait_for(lambda: bool(results), app, timeout=1.0)

    assert results[0].ok is False
    assert results[0].action == "sad"
    assert "超时" in results[0].card.text
    assert runner.busy is False
    assert runner.run(lambda: PetSessionResult(True, "idle", PetBubbleCard("status", "next"))) is True
    second_thread = runner._thread
    _wait_for(lambda: not runner.busy, app, timeout=1.0)
    _wait_for(lambda: _thread_stopped(first_thread), app, timeout=1.0)
    _wait_for(lambda: _thread_stopped(second_thread), app, timeout=1.0)
    deadline = time.time() + 0.3
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.01)


def test_runner_ignores_late_result_after_timeout():
    app = QApplication.instance() or QApplication([])
    runner = PetCommandRunner(timeout_ms=50)
    results = []
    runner.finished.connect(results.append)

    def stuck():
        time.sleep(0.2)
        return PetSessionResult(True, "idle", PetBubbleCard("status", "late"))

    assert runner.run(stuck) is True
    first_thread = runner._thread
    _wait_for(lambda: len(results) == 1, app, timeout=1.0)
    _wait_for(lambda: _thread_stopped(first_thread), app, timeout=1.0)
    deadline = time.time() + 0.3
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.01)

    assert len(results) == 1
    assert "超时" in results[0].card.text
