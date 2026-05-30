from coding_with_beat.app_paths import CodeBeatPaths
from coding_with_beat.service_manager import ServiceManager, ServiceState


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


def test_status_stopped_when_no_process(tmp_path):
    manager = ServiceManager(paths=_paths(tmp_path), python="python3")

    assert manager.status().state == ServiceState.STOPPED


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


def test_stop_terminates_running_process(tmp_path):
    process = FakeProcess()
    manager = ServiceManager(paths=_paths(tmp_path), python="python3")
    manager._process = process

    status = manager.stop()

    assert status.state == ServiceState.STOPPED
    assert process.terminated is True
    assert process.waited is True
    assert manager._process is None


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
