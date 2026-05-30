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
    _merge_local_no_proxy,
    _proxy_env_from_mapping,
    _proxy_env_from_scutil_output,
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
        self.environment = None

    def setWorkingDirectory(self, cwd):
        self.cwd = cwd

    def setProcessEnvironment(self, environment):
        self.environment = environment

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


def test_codex_workspace_write_command_omits_unsupported_approval_flag(tmp_path):
    session = AiChatSession(provider=AiProvider.CODEX, cwd=tmp_path)

    command = session.build_command("edit this", AiPermissionMode.WORKSPACE_WRITE)

    assert "--sandbox" in command.args
    assert "workspace-write" in command.args
    assert "--ask-for-approval" not in command.args
    assert "on-request" not in command.args


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


def test_runner_stores_codex_thread_id_from_jsonl_and_resumes_explicit_thread(tmp_path):
    app = QApplication.instance() or QApplication([])
    thread_id = "00000000-0000-4000-8000-000000000123"
    stdout = (
        f'{{"type":"thread.started","thread_id":"{thread_id}"}}\n'
        '{"type":"item.completed","item":{"type":"agent_message","text":"real answer"}}\n'
    ).encode()
    runner = AiChatRunner(
        cwd=tmp_path,
        process_factory=lambda: FakeProcess(stdout=stdout),
        executable_resolver=lambda provider: provider.value,
    )
    results = []
    runner.finished.connect(results.append)

    assert runner.send("hello", AiProvider.CODEX, AiPermissionMode.READ_ONLY) is True
    _wait_for(lambda: bool(results), app)
    command = runner._sessions[AiProvider.CODEX].build_command("continue", AiPermissionMode.READ_ONLY)

    assert results == [AiChatResult(ok=True, text="real answer")]
    assert runner._sessions[AiProvider.CODEX].session_id == thread_id
    assert command.args == ["codex", "exec", "resume", "--json", thread_id, "-"]


def test_proxy_env_from_mapping_copies_upper_and_lowercase_proxy_values():
    proxy_env = _proxy_env_from_mapping(
        {
            "HTTPS_PROXY": "http://127.0.0.1:7890",
            "NO_PROXY": "example.com",
        }
    )

    assert proxy_env["HTTPS_PROXY"] == "http://127.0.0.1:7890"
    assert proxy_env["https_proxy"] == "http://127.0.0.1:7890"
    assert proxy_env["NO_PROXY"] == "example.com,127.0.0.1,localhost,::1"
    assert proxy_env["no_proxy"] == "example.com,127.0.0.1,localhost,::1"


def test_proxy_env_from_scutil_output_uses_enabled_http_and_https_proxy():
    proxy_env = _proxy_env_from_scutil_output(
        """
<dictionary> {
  HTTPEnable : 1
  HTTPPort : 7890
  HTTPProxy : 127.0.0.1
  HTTPSEnable : 1
  HTTPSPort : 7890
  HTTPSProxy : 127.0.0.1
  SOCKSEnable : 1
  SOCKSPort : 7890
  SOCKSProxy : 127.0.0.1
}
"""
    )

    assert proxy_env["HTTP_PROXY"] == "http://127.0.0.1:7890"
    assert proxy_env["HTTPS_PROXY"] == "http://127.0.0.1:7890"
    assert proxy_env["http_proxy"] == "http://127.0.0.1:7890"
    assert proxy_env["https_proxy"] == "http://127.0.0.1:7890"
    assert proxy_env["ALL_PROXY"] == "socks5://127.0.0.1:7890"
    assert proxy_env["NO_PROXY"] == "127.0.0.1,localhost,::1"


def test_merge_local_no_proxy_preserves_existing_entries_without_duplicates():
    assert _merge_local_no_proxy("localhost,example.com") == "localhost,example.com,127.0.0.1,::1"
