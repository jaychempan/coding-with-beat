"""MCP service lifecycle management for CodeBeat.app."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Callable
from urllib.parse import urlparse

from .app_paths import CodeBeatPaths
from .mcp_client import DEFAULT_MCP_URL, call_tool


class ServiceState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    CRASHED = "crashed"


@dataclass(frozen=True)
class ServiceStatus:
    state: ServiceState
    mcp_url: str
    pid: int | None = None
    returncode: int | None = None
    message: str = ""


class ServiceManager:
    def __init__(
        self,
        *,
        paths: CodeBeatPaths | None = None,
        python: str | None = None,
        mcp_url: str = DEFAULT_MCP_URL,
        popen: Callable[..., subprocess.Popen] = subprocess.Popen,
        run: Callable[..., object] = subprocess.run,
        health_check: Callable[[str], bool] | None = None,
    ) -> None:
        self.paths = paths or CodeBeatPaths.default()
        self.python = python or sys.executable
        self.mcp_url = mcp_url
        self._popen = popen
        self._run = run
        self._health_check = health_check or self._default_health_check
        self._process = None
        self._stdout = None
        self._stderr = None

    def status(self) -> ServiceStatus:
        if self._process is None:
            return ServiceStatus(ServiceState.STOPPED, self.mcp_url)
        returncode = self._process.poll()
        if returncode is not None:
            return ServiceStatus(
                ServiceState.CRASHED, self.mcp_url, returncode=returncode, message="MCP process exited"
            )
        if self._health_check(self.mcp_url):
            return ServiceStatus(ServiceState.RUNNING, self.mcp_url, pid=getattr(self._process, "pid", None))
        return ServiceStatus(
            ServiceState.DEGRADED, self.mcp_url, pid=getattr(self._process, "pid", None), message="Health check failed"
        )

    def start(self) -> ServiceStatus:
        current = self.status()
        if current.state in {ServiceState.RUNNING, ServiceState.STARTING, ServiceState.DEGRADED}:
            return current
        self.paths.ensure()
        self._process = None
        self._close_logs()
        try:
            self._stdout = (self.paths.logs_dir / "mcp.log").open("a", encoding="utf-8")
            self._stderr = (self.paths.logs_dir / "mcp.err.log").open("a", encoding="utf-8")
            self._process = self._popen(
                self._launch_args(),
                stdout=self._stdout,
                stderr=self._stderr,
            )
        except Exception:
            self._process = None
            self._close_logs()
            raise
        return ServiceStatus(ServiceState.STARTING, self.mcp_url, pid=getattr(self._process, "pid", None))

    def stop(self) -> ServiceStatus:
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=5)
        self._process = None
        self._close_logs()
        return ServiceStatus(ServiceState.STOPPED, self.mcp_url)

    def restart(self) -> ServiceStatus:
        self.stop()
        return self.start()

    def open_logs(self) -> None:
        self.paths.logs_dir.mkdir(parents=True, exist_ok=True)
        self._run(["open", str(self.paths.logs_dir)], check=False)

    def _close_logs(self) -> None:
        for handle in (self._stdout, self._stderr):
            if handle is not None:
                handle.close()
        self._stdout = None
        self._stderr = None

    def _launch_args(self) -> list[str]:
        parsed = urlparse(self.mcp_url)
        host = parsed.hostname or "127.0.0.1"
        try:
            port = parsed.port or 8765
        except ValueError:
            port = 8765
        path = parsed.path or "/mcp"
        return [
            self.python,
            "-m",
            "coding_with_beat",
            "server",
            "--host",
            host,
            "--port",
            str(port),
            "--path",
            path,
        ]

    @staticmethod
    def _default_health_check(url: str) -> bool:
        try:
            call_tool("status", url=url, timeout=1.0)
        except Exception:
            return False
        return True
