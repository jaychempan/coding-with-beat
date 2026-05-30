import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from coding_with_beat.pet.ai_chat import (
    AiChatResult,
    AiChatRunner,
    AiChatSession,
    AiPermissionMode,
    AiProvider,
)


class FakeSignal:
    def __init__(self):
        self._callbacks = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def emit(self, *args):
        for callback in list(self._callbacks):
            callback(*args)


class FakeProcess:
    def __init__(self, stdout=b"agent reply", stderr=b"", exit_code=0):
        self.readyReadStandardOutput = FakeSignal()
        self.readyReadStandardError = FakeSignal()
        self.errorOccurred = FakeSignal()
        self.finished = FakeSignal()
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.args = None
        self.cwd = None
        self.stdin = b""
        self.killed = False

    def setWorkingDirectory(self, cwd):
        self.cwd = cwd

    def setProcessEnvironment(self, _environment):
        pass

    def start(self, program, args):
        self.args = [program, *args]

    def write(self, data):
        self.stdin += bytes(data)

    def closeWriteChannel(self):
        if self.stdout:
            self.readyReadStandardOutput.emit()
        if self.stderr:
            self.readyReadStandardError.emit()
        self.finished.emit(self.exit_code, 0)

    def readAllStandardOutput(self):
        data = self.stdout
        self.stdout = b""
        return data

    def readAllStandardError(self):
        data = self.stderr
        self.stderr = b""
        return data

    def kill(self):
        self.killed = True

    def errorString(self):
        return "fake process error"


class HangingFakeProcess(FakeProcess):
    def closeWriteChannel(self):
        pass


class UndrainedFakeProcess(FakeProcess):
    def closeWriteChannel(self):
        self.finished.emit(self.exit_code, 0)


def _wait_for(predicate, app, timeout=1.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.processEvents()
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition was not met")


def test_codex_read_only_initial_command_uses_safe_exec(tmp_path):
    session = AiChatSession(provider=AiProvider.CODEX, cwd=tmp_path)

    command = session.build_command("explain this repo", AiPermissionMode.READ_ONLY)

    assert command.args[:2] == ["codex", "exec"]
    assert "--json" in command.args
    assert "--sandbox" in command.args
    assert "read-only" in command.args
    assert "--cd" in command.args
    assert str(tmp_path) in command.args
    assert "explain this repo" in command.stdin
    assert "music_actions" in command.stdin


def test_codex_followup_command_resumes_last_non_interactive(tmp_path):
    session = AiChatSession(provider=AiProvider.CODEX, cwd=tmp_path)
    session.mark_started()

    command = session.build_command("continue", AiPermissionMode.WORKSPACE_WRITE)

    assert command.args[:3] == ["codex", "exec", "resume"]
    assert "--json" in command.args
    assert "--last" in command.args
    assert "-" in command.args
    assert "continue" in command.stdin
    assert "music_actions" in command.stdin


def test_claude_command_uses_print_and_session_id(tmp_path):
    session = AiChatSession(
        provider=AiProvider.CLAUDE,
        cwd=tmp_path,
        session_id="00000000-0000-4000-8000-000000000001",
    )

    command = session.build_command("hello", AiPermissionMode.WORKSPACE_WRITE)

    assert command.args[:2] == ["claude", "--print"]
    assert "00000000-0000-4000-8000-000000000001" in command.args
    assert "--permission-mode" in command.args
    assert "acceptEdits" in command.args
    assert "hello" in command.stdin
    assert "music_actions" in command.stdin


def test_ai_chat_session_wraps_prompt_with_music_action_contract(tmp_path):
    session = AiChatSession(provider=AiProvider.CODEX, cwd=tmp_path)

    command = session.build_command("来点适合写代码的中文歌", AiPermissionMode.READ_ONLY)

    assert "music_actions" in command.stdin
    assert "play_track" in command.stdin
    assert "search_music" in command.stdin
    assert "来点适合写代码的中文歌" in command.stdin


def test_runner_successful_output_emits_result_and_marks_session_started(tmp_path):
    app = QApplication.instance() or QApplication([])
    runner = AiChatRunner(
        cwd=tmp_path,
        process_factory=lambda: FakeProcess(stdout=b"agent reply"),
        executable_resolver=lambda provider: provider.value,
    )
    results = []
    runner.finished.connect(results.append)

    assert runner.send("hello", AiProvider.CODEX, AiPermissionMode.READ_ONLY) is True
    _wait_for(lambda: bool(results), app)

    assert results == [AiChatResult(ok=True, text="agent reply")]
    assert runner._sessions[AiProvider.CODEX].started is True


def test_runner_drains_stdout_when_finish_arrives_before_ready_read(tmp_path):
    app = QApplication.instance() or QApplication([])
    runner = AiChatRunner(
        cwd=tmp_path,
        process_factory=lambda: UndrainedFakeProcess(stdout=b"agent reply"),
        executable_resolver=lambda provider: provider.value,
    )
    results = []
    runner.finished.connect(results.append)

    assert runner.send("hello", AiProvider.CODEX, AiPermissionMode.READ_ONLY) is True
    _wait_for(lambda: bool(results), app)

    assert results == [AiChatResult(ok=True, text="agent reply")]


def test_runner_missing_cli_emits_not_found(tmp_path):
    app = QApplication.instance() or QApplication([])
    runner = AiChatRunner(cwd=tmp_path, executable_resolver=lambda _provider: None)
    results = []
    runner.finished.connect(results.append)

    assert runner.send("hello", AiProvider.CODEX, AiPermissionMode.READ_ONLY) is False
    _wait_for(lambda: bool(results), app)

    assert results == [AiChatResult(ok=False, text="codex CLI not found.")]


def test_runner_process_error_emits_failure_and_clears_busy(tmp_path):
    app = QApplication.instance() or QApplication([])
    process = HangingFakeProcess()
    runner = AiChatRunner(
        cwd=tmp_path,
        process_factory=lambda: process,
        executable_resolver=lambda provider: provider.value,
    )
    results = []
    runner.finished.connect(results.append)

    assert runner.send("hello", AiProvider.CODEX, AiPermissionMode.READ_ONLY) is True
    process.errorOccurred.emit(1)
    _wait_for(lambda: bool(results), app)

    assert results == [AiChatResult(ok=False, text="AI chat process failed: fake process error")]
    assert runner.busy is False


def test_runner_stop_waits_for_killed_process_to_finish_before_accepting_next_send(tmp_path):
    app = QApplication.instance() or QApplication([])
    process = HangingFakeProcess()
    runner = AiChatRunner(
        cwd=tmp_path,
        process_factory=lambda: process,
        executable_resolver=lambda provider: provider.value,
    )
    results = []
    runner.finished.connect(results.append)

    assert runner.send("hello", AiProvider.CODEX, AiPermissionMode.READ_ONLY) is True
    runner.stop()

    assert process.killed is True
    assert runner.busy is True
    assert runner.send("again", AiProvider.CODEX, AiPermissionMode.READ_ONLY) is False
    assert results == []

    process.finished.emit(9, 0)
    _wait_for(lambda: bool(results), app)

    assert results == [AiChatResult(ok=False, text="AI chat stopped.")]
    assert runner.busy is False


def test_runner_ignores_process_error_after_stop_until_finished(tmp_path):
    app = QApplication.instance() or QApplication([])
    process = HangingFakeProcess()
    runner = AiChatRunner(
        cwd=tmp_path,
        process_factory=lambda: process,
        executable_resolver=lambda provider: provider.value,
    )
    results = []
    runner.finished.connect(results.append)

    assert runner.send("hello", AiProvider.CODEX, AiPermissionMode.READ_ONLY) is True
    runner.stop()
    process.errorOccurred.emit(1)

    assert runner.busy is True
    assert results == []
    assert runner.send("again", AiProvider.CODEX, AiPermissionMode.READ_ONLY) is False

    process.finished.emit(9, 0)
    _wait_for(lambda: bool(results), app)

    assert results == [AiChatResult(ok=False, text="AI chat stopped.")]
    assert runner.busy is False


def test_runner_extracts_codex_jsonl_final_agent_message(tmp_path):
    app = QApplication.instance() or QApplication([])
    stdout = b'{"type":"item.completed","item":{"type":"agent_message","text":"real answer"}}\n'
    runner = AiChatRunner(
        cwd=tmp_path,
        process_factory=lambda: FakeProcess(stdout=stdout),
        executable_resolver=lambda provider: provider.value,
    )
    results = []
    runner.finished.connect(results.append)

    assert runner.send("hello", AiProvider.CODEX, AiPermissionMode.READ_ONLY) is True
    _wait_for(lambda: bool(results), app)

    assert results == [AiChatResult(ok=True, text="real answer")]
