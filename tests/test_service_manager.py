import subprocess
from dataclasses import FrozenInstanceError

import pytest

from coding_with_beat.app_paths import CodeBeatPaths
from coding_with_beat.service_manager import ServiceManager, ServiceState, ServiceStatus


def _paths(tmp_path):
    return CodeBeatPaths(
        support_dir=tmp_path / "support",
        logs_dir=tmp_path / "logs",
        settings_file=tmp_path / "support" / "settings.json",
        service_file=tmp_path / "support" / "service.json",
        integrations_file=tmp_path / "support" / "integrations.json",
        legacy_data_dir=tmp_path / "legacy",
        legacy_pet_settings_file=tmp_path / "legacy" / "pet.json",
        legacy_mcp_url_file=tmp_path / "legacy" / "mcp-url",
    )


class FakeProcess:
    def __init__(self, returncode=None):
        self.returncode = returncode
        self.terminated = False
        self.waited = False
        self.killed = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = 0

    def wait(self, timeout=None):
        self.waited = True
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -9


class TimeoutProcess(FakeProcess):
    def __init__(self):
        super().__init__()
        self.wait_calls = 0

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        self.wait_calls += 1
        self.waited = True
        if self.wait_calls == 1:
            raise subprocess.TimeoutExpired(cmd="coding_with_beat server", timeout=timeout)
        return self.returncode


class FakeLogHandle:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def test_status_stopped_when_no_process(tmp_path):
    manager = ServiceManager(paths=_paths(tmp_path), python="python3")

    assert manager.status().state == ServiceState.STOPPED


def test_service_state_values_are_exact():
    assert ServiceState.STOPPED.value == "stopped"
    assert ServiceState.STARTING.value == "starting"
    assert ServiceState.RUNNING.value == "running"
    assert ServiceState.DEGRADED.value == "degraded"
    assert ServiceState.CRASHED.value == "crashed"


def test_service_status_defaults_and_frozen_behavior():
    status = ServiceStatus(ServiceState.STOPPED, "http://127.0.0.1:8765/mcp")

    assert status.pid is None
    assert status.returncode is None
    assert status.message == ""
    with pytest.raises(FrozenInstanceError):
        status.message = "changed"


def test_start_launches_server_process_and_writes_logs(tmp_path):
    process = FakeProcess()
    popen_calls = []

    def fake_popen(args, stdout, stderr):
        popen_calls.append((args, stdout, stderr))
        return process

    manager = ServiceManager(paths=_paths(tmp_path), python="/usr/bin/python3", popen=fake_popen)

    status = manager.start()

    assert status.state == ServiceState.STARTING
    assert popen_calls[0][0] == [
        "/usr/bin/python3",
        "-m",
        "coding_with_beat",
        "server",
        "--host",
        "127.0.0.1",
        "--port",
        "8765",
        "--path",
        "/mcp",
    ]
    assert (tmp_path / "logs").is_dir()
    assert (tmp_path / "logs" / "mcp.log").exists()
    assert (tmp_path / "logs" / "mcp.err.log").exists()


def test_start_closes_existing_log_handles_after_crash(tmp_path):
    process = FakeProcess()
    old_stdout = FakeLogHandle()
    old_stderr = FakeLogHandle()

    def fake_popen(args, stdout, stderr):
        return process

    manager = ServiceManager(paths=_paths(tmp_path), python="python3", popen=fake_popen)
    manager._process = FakeProcess(returncode=1)
    manager._stdout = old_stdout
    manager._stderr = old_stderr

    status = manager.start()

    assert status.state == ServiceState.STARTING
    assert old_stdout.closed is True
    assert old_stderr.closed is True
    assert manager._stdout is not None
    assert manager._stderr is not None
    assert manager._stdout is not old_stdout
    assert manager._stderr is not old_stderr


def test_start_closes_new_log_handles_when_popen_raises(tmp_path):
    popen_handles = []

    def fake_popen(args, stdout, stderr):
        popen_handles.append((stdout, stderr))
        raise RuntimeError("launch failed")

    manager = ServiceManager(paths=_paths(tmp_path), python="python3", popen=fake_popen)

    with pytest.raises(RuntimeError, match="launch failed"):
        manager.start()

    stdout, stderr = popen_handles[0]
    assert stdout.closed is True
    assert stderr.closed is True
    assert manager._stdout is None
    assert manager._stderr is None
    assert manager._process is None


def test_start_uses_custom_mcp_url_for_launch_args(tmp_path):
    popen_calls = []

    def fake_popen(args, stdout, stderr):
        popen_calls.append(args)
        return FakeProcess()

    manager = ServiceManager(
        paths=_paths(tmp_path),
        python="/usr/bin/python3",
        mcp_url="http://127.0.0.1:9876/custom",
        popen=fake_popen,
    )

    manager.start()

    assert popen_calls[0] == [
        "/usr/bin/python3",
        "-m",
        "coding_with_beat",
        "server",
        "--host",
        "127.0.0.1",
        "--port",
        "9876",
        "--path",
        "/custom",
    ]


def test_start_uses_launch_defaults_for_missing_mcp_url_parts(tmp_path):
    popen_calls = []

    def fake_popen(args, stdout, stderr):
        popen_calls.append(args)
        return FakeProcess()

    manager = ServiceManager(
        paths=_paths(tmp_path),
        python="/usr/bin/python3",
        mcp_url="http://127.0.0.1",
        popen=fake_popen,
    )

    manager.start()

    assert popen_calls[0] == [
        "/usr/bin/python3",
        "-m",
        "coding_with_beat",
        "server",
        "--host",
        "127.0.0.1",
        "--port",
        "8765",
        "--path",
        "/mcp",
    ]


def test_status_running_when_health_check_succeeds(tmp_path):
    process = FakeProcess()
    manager = ServiceManager(paths=_paths(tmp_path), python="python3", health_check=lambda _url: True)
    manager._process = process

    assert manager.status().state == ServiceState.RUNNING


def test_status_degraded_when_process_alive_but_health_fails(tmp_path):
    process = FakeProcess()
    manager = ServiceManager(paths=_paths(tmp_path), python="python3", health_check=lambda _url: False)
    manager._process = process

    assert manager.status().state == ServiceState.DEGRADED


def test_status_crashed_when_process_exited(tmp_path):
    process = FakeProcess(returncode=1)
    manager = ServiceManager(paths=_paths(tmp_path), python="python3")
    manager._process = process

    status = manager.status()

    assert status.state == ServiceState.CRASHED
    assert status.returncode == 1


def test_status_crashed_closes_logs_and_clears_process(tmp_path):
    stdout = FakeLogHandle()
    stderr = FakeLogHandle()
    manager = ServiceManager(paths=_paths(tmp_path), python="python3")
    manager._process = FakeProcess(returncode=7)
    manager._stdout = stdout
    manager._stderr = stderr

    status = manager.status()

    assert status.state == ServiceState.CRASHED
    assert status.returncode == 7
    assert stdout.closed is True
    assert stderr.closed is True
    assert manager._stdout is None
    assert manager._stderr is None
    assert manager._process is None


def test_stop_terminates_running_process(tmp_path):
    process = FakeProcess()
    manager = ServiceManager(paths=_paths(tmp_path), python="python3")
    manager._process = process

    status = manager.stop()

    assert status.state == ServiceState.STOPPED
    assert process.terminated is True
    assert process.waited is True
    assert manager._process is None


def test_stop_kills_process_when_wait_times_out(tmp_path):
    process = TimeoutProcess()
    manager = ServiceManager(paths=_paths(tmp_path), python="python3")
    manager._process = process

    status = manager.stop()

    assert status.state == ServiceState.STOPPED
    assert process.terminated is True
    assert process.killed is True
    assert process.wait_calls == 2
    assert manager._process is None


def test_stop_closes_log_handles(tmp_path):
    stdout = FakeLogHandle()
    stderr = FakeLogHandle()
    manager = ServiceManager(paths=_paths(tmp_path), python="python3")
    manager._stdout = stdout
    manager._stderr = stderr

    manager.stop()

    assert stdout.closed is True
    assert stderr.closed is True
    assert manager._stdout is None
    assert manager._stderr is None


def test_restart_stops_and_starts(tmp_path):
    first = FakeProcess()
    second = FakeProcess()
    processes = [second]

    def fake_popen(*_args, **_kwargs):
        return processes.pop(0)

    manager = ServiceManager(paths=_paths(tmp_path), python="python3", popen=fake_popen)
    manager._process = first

    status = manager.restart()

    assert first.terminated is True
    assert manager._process is second
    assert status.state == ServiceState.STARTING


def test_open_logs_uses_macos_open(tmp_path):
    calls = []
    manager = ServiceManager(
        paths=_paths(tmp_path), python="python3", run=lambda args, check: calls.append((args, check))
    )

    manager.open_logs()

    assert calls == [(["open", str(tmp_path / "logs")], False)]


def test_default_health_check_calls_status_tool(monkeypatch, tmp_path):
    calls = []

    def fake_call_tool(name, *, url, timeout):
        calls.append((name, url, timeout))
        return {"ok": True}

    monkeypatch.setattr("coding_with_beat.service_manager.call_tool", fake_call_tool)
    manager = ServiceManager(paths=_paths(tmp_path), python="python3")

    assert manager._default_health_check("http://example.test/mcp") is True
    assert calls == [("status", "http://example.test/mcp", 1.0)]


def test_default_health_check_returns_false_on_call_tool_exception(monkeypatch, tmp_path):
    def fake_call_tool(name, *, url, timeout):
        raise RuntimeError("boom")

    monkeypatch.setattr("coding_with_beat.service_manager.call_tool", fake_call_tool)
    manager = ServiceManager(paths=_paths(tmp_path), python="python3")

    assert manager._default_health_check("http://example.test/mcp") is False
