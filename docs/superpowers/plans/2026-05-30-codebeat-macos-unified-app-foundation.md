# CodeBeat macOS Unified App Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the app-owned filesystem, settings migration, bundled resource manifest, and MCP service lifecycle foundation needed by the unified macOS app.

**Architecture:** Keep the existing lightweight `CodeBeat.app` and `python -m coding_with_beat app` path working while adding testable app-level modules. New app-owned modules live beside the existing package code and expose narrow APIs that the UI and future integration managers can call. This plan does not build the full Claude/Codex integration UI or production PyInstaller bundle; those are separate follow-up plans.

**Tech Stack:** Python 3.11+, dataclasses, pathlib, json, subprocess, existing pytest/unittest style, existing `scripts/build_macos_app.py`.

---

## Scope

This plan implements Phase 1 from the design spec:

- app-owned directories under `~/Library/Application Support/CodeBeat`
- app-level settings with legacy pet/MCP URL migration
- generated bundled resource manifest in the local app builder
- child-process MCP service manager with status, start, stop, restart, health check, and log paths
- app entrypoint wiring that initializes settings and can start the service manager
- MCP client compatibility that reads app support state before legacy `~/.coding-with-beat/mcp-url`

This plan intentionally does not implement:

- Claude Code install/repair/remove UI
- Codex install/repair/remove UI
- PyInstaller production bundling
- DMG generation
- signing/notarization
- LaunchAgent background service ownership

## File Structure

- Create: `coding_with_beat/app_paths.py`
  - Own standard CodeBeat macOS paths and legacy path references.
- Create: `coding_with_beat/app_settings.py`
  - Load, save, and migrate app-level settings.
- Create: `coding_with_beat/service_manager.py`
  - Manage a child-process MCP server and expose service status.
- Modify: `coding_with_beat/app.py`
  - Initialize app settings, mirror MCP URL compatibility file, and pass pet settings to existing pet app.
- Modify: `coding_with_beat/mcp_client.py`
  - Prefer app support service state for MCP URL, then legacy file, then default.
- Modify: `scripts/build_macos_app.py`
  - Generate `Contents/Resources/manifest.json`.
- Test: `tests/test_app_paths.py`
- Test: `tests/test_app_settings.py`
- Test: `tests/test_service_manager.py`
- Modify: `tests/test_codebeat_app.py`
- Modify: `tests/test_codebeat_app_builder.py`
- Modify: `tests/test_mcp_client.py`

---

### Task 1: App-Owned Paths

**Files:**
- Create: `coding_with_beat/app_paths.py`
- Test: `tests/test_app_paths.py`

- [ ] **Step 1: Write failing path tests**

Create `tests/test_app_paths.py`:

```python
from pathlib import Path
from unittest import mock

from coding_with_beat import app_paths


def test_app_paths_use_macos_application_locations():
    with mock.patch.object(app_paths.Path, "home", return_value=Path("/Users/alice")):
        paths = app_paths.CodeBeatPaths.default()

    assert paths.support_dir == Path("/Users/alice/Library/Application Support/CodeBeat")
    assert paths.logs_dir == Path("/Users/alice/Library/Logs/CodeBeat")
    assert paths.settings_file == paths.support_dir / "settings.json"
    assert paths.service_file == paths.support_dir / "service.json"
    assert paths.integrations_file == paths.support_dir / "integrations.json"
    assert paths.legacy_data_dir == Path("/Users/alice/.coding-with-beat")
    assert paths.legacy_mcp_url_file == Path("/Users/alice/.coding-with-beat/mcp-url")


def test_ensure_creates_app_owned_directories(tmp_path):
    paths = app_paths.CodeBeatPaths(
        support_dir=tmp_path / "support",
        logs_dir=tmp_path / "logs",
        settings_file=tmp_path / "support" / "settings.json",
        service_file=tmp_path / "support" / "service.json",
        integrations_file=tmp_path / "support" / "integrations.json",
        legacy_data_dir=tmp_path / "legacy",
        legacy_pet_settings_file=tmp_path / "legacy" / "pet.json",
        legacy_mcp_url_file=tmp_path / "legacy" / "mcp-url",
    )

    paths.ensure()

    assert paths.support_dir.is_dir()
    assert paths.logs_dir.is_dir()
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/test_app_paths.py -q
```

Expected: FAIL with `ImportError` or `ModuleNotFoundError` for `coding_with_beat.app_paths`.

- [ ] **Step 3: Implement app paths**

Create `coding_with_beat/app_paths.py`:

```python
"""Filesystem paths for the CodeBeat macOS app."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


APP_SUPPORT_NAME = "CodeBeat"
LEGACY_DATA_NAME = ".coding-with-beat"


@dataclass(frozen=True)
class CodeBeatPaths:
    support_dir: Path
    logs_dir: Path
    settings_file: Path
    service_file: Path
    integrations_file: Path
    legacy_data_dir: Path
    legacy_pet_settings_file: Path
    legacy_mcp_url_file: Path

    @classmethod
    def default(cls) -> "CodeBeatPaths":
        home = Path.home()
        support_dir = home / "Library" / "Application Support" / APP_SUPPORT_NAME
        logs_dir = home / "Library" / "Logs" / APP_SUPPORT_NAME
        legacy_data_dir = home / LEGACY_DATA_NAME
        return cls(
            support_dir=support_dir,
            logs_dir=logs_dir,
            settings_file=support_dir / "settings.json",
            service_file=support_dir / "service.json",
            integrations_file=support_dir / "integrations.json",
            legacy_data_dir=legacy_data_dir,
            legacy_pet_settings_file=legacy_data_dir / "pet.json",
            legacy_mcp_url_file=legacy_data_dir / "mcp-url",
        )

    def ensure(self) -> None:
        self.support_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
pytest tests/test_app_paths.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add coding_with_beat/app_paths.py tests/test_app_paths.py
git commit -m "feat(app): add macos app-owned paths"
```

---

### Task 2: App Settings And Legacy Migration

**Files:**
- Create: `coding_with_beat/app_settings.py`
- Test: `tests/test_app_settings.py`

- [ ] **Step 1: Write failing settings tests**

Create `tests/test_app_settings.py`:

```python
import json

from coding_with_beat.app_paths import CodeBeatPaths
from coding_with_beat.app_settings import AppSettings, IntegrationSettings, PetAppSettings, ServiceSettings, load_settings, save_settings


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


def test_load_settings_returns_defaults_when_no_files_exist(tmp_path):
    settings = load_settings(_paths(tmp_path))

    assert settings.version == 1
    assert settings.source == "apple_music"
    assert settings.pet.slug == "codebeat-buddy"
    assert settings.pet.show_dock_icon is True
    assert settings.pet.show_menu_bar_icon is True
    assert settings.service.mcp_url == "http://127.0.0.1:8765/mcp"
    assert settings.service.start_on_launch is True
    assert settings.service.restart_on_crash is True
    assert settings.integrations["claude"].enabled is False
    assert settings.integrations["codex"].enabled is False


def test_load_settings_migrates_legacy_pet_and_mcp_url(tmp_path):
    paths = _paths(tmp_path)
    paths.legacy_data_dir.mkdir()
    paths.legacy_pet_settings_file.write_text(
        json.dumps(
            {
                "petdex_slug": "boba",
                "show_dock_icon": False,
                "show_menu_bar_icon": False,
            }
        ),
        encoding="utf-8",
    )
    paths.legacy_mcp_url_file.write_text("http://127.0.0.1:9876/mcp\n", encoding="utf-8")

    settings = load_settings(paths)

    assert settings.pet.slug == "boba"
    assert settings.pet.show_dock_icon is False
    assert settings.pet.show_menu_bar_icon is False
    assert settings.service.mcp_url == "http://127.0.0.1:9876/mcp"
    assert paths.legacy_pet_settings_file.exists()
    assert paths.legacy_mcp_url_file.exists()


def test_save_settings_writes_camel_case_json(tmp_path):
    paths = _paths(tmp_path)
    settings = AppSettings(
        version=1,
        source="local",
        pet=PetAppSettings(slug="codebeat-buddy", show_dock_icon=False, show_menu_bar_icon=True),
        service=ServiceSettings(
            mcp_url="http://127.0.0.1:9999/mcp",
            start_on_launch=False,
            restart_on_crash=True,
        ),
        integrations={
            "claude": IntegrationSettings(enabled=True),
            "codex": IntegrationSettings(enabled=False),
        },
    )

    save_settings(settings, paths)

    raw = json.loads(paths.settings_file.read_text(encoding="utf-8"))
    assert raw["version"] == 1
    assert raw["source"] == "local"
    assert raw["pet"]["slug"] == "codebeat-buddy"
    assert raw["pet"]["showDockIcon"] is False
    assert raw["service"]["mcpUrl"] == "http://127.0.0.1:9999/mcp"
    assert raw["service"]["startOnLaunch"] is False
    assert raw["integrations"]["claude"]["enabled"] is True


def test_load_settings_preserves_existing_app_settings_over_legacy(tmp_path):
    paths = _paths(tmp_path)
    paths.support_dir.mkdir()
    paths.settings_file.write_text(
        json.dumps(
            {
                "version": 1,
                "source": "qq_music",
                "pet": {
                    "slug": "codebeat-buddy",
                    "showDockIcon": True,
                    "showMenuBarIcon": False,
                },
                "service": {
                    "mcpUrl": "http://127.0.0.1:8765/mcp",
                    "startOnLaunch": False,
                    "restartOnCrash": False,
                },
                "integrations": {
                    "claude": {"enabled": True},
                    "codex": {"enabled": False},
                },
            }
        ),
        encoding="utf-8",
    )
    paths.legacy_data_dir.mkdir()
    paths.legacy_mcp_url_file.write_text("http://127.0.0.1:9876/mcp\n", encoding="utf-8")

    settings = load_settings(paths)

    assert settings.source == "qq_music"
    assert settings.service.mcp_url == "http://127.0.0.1:8765/mcp"
    assert settings.service.start_on_launch is False
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/test_app_settings.py -q
```

Expected: FAIL because `coding_with_beat.app_settings` does not exist.

- [ ] **Step 3: Implement settings module**

Create `coding_with_beat/app_settings.py`:

```python
"""App-level settings for CodeBeat.app."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from .app_paths import CodeBeatPaths
from .mcp_client import DEFAULT_MCP_URL


@dataclass
class PetAppSettings:
    slug: str = "codebeat-buddy"
    show_dock_icon: bool = True
    show_menu_bar_icon: bool = True


@dataclass
class ServiceSettings:
    mcp_url: str = DEFAULT_MCP_URL
    start_on_launch: bool = True
    restart_on_crash: bool = True


@dataclass
class IntegrationSettings:
    enabled: bool = False


@dataclass
class AppSettings:
    version: int = 1
    source: str = "apple_music"
    pet: PetAppSettings = field(default_factory=PetAppSettings)
    service: ServiceSettings = field(default_factory=ServiceSettings)
    integrations: dict[str, IntegrationSettings] = field(
        default_factory=lambda: {
            "claude": IntegrationSettings(),
            "codex": IntegrationSettings(),
        }
    )


def load_settings(paths: CodeBeatPaths | None = None) -> AppSettings:
    paths = paths or CodeBeatPaths.default()
    raw = _read_json(paths.settings_file)
    if isinstance(raw, dict):
        return _settings_from_json(raw)
    return _settings_from_legacy(paths)


def save_settings(settings: AppSettings, paths: CodeBeatPaths | None = None) -> None:
    paths = paths or CodeBeatPaths.default()
    paths.ensure()
    tmp = paths.settings_file.with_suffix(".tmp")
    tmp.write_text(json.dumps(_settings_to_json(settings), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, paths.settings_file)


def mirror_mcp_url(settings: AppSettings, paths: CodeBeatPaths | None = None) -> None:
    paths = paths or CodeBeatPaths.default()
    paths.legacy_data_dir.mkdir(parents=True, exist_ok=True)
    tmp = paths.legacy_mcp_url_file.with_suffix(".tmp")
    tmp.write_text(settings.service.mcp_url + "\n", encoding="utf-8")
    os.replace(tmp, paths.legacy_mcp_url_file)


def _settings_from_legacy(paths: CodeBeatPaths) -> AppSettings:
    settings = AppSettings()
    pet_raw = _read_json(paths.legacy_pet_settings_file)
    if isinstance(pet_raw, dict):
        settings.pet.slug = str(pet_raw.get("petdex_slug") or settings.pet.slug)
        settings.pet.show_dock_icon = bool(pet_raw.get("show_dock_icon", settings.pet.show_dock_icon))
        settings.pet.show_menu_bar_icon = bool(pet_raw.get("show_menu_bar_icon", settings.pet.show_menu_bar_icon))
    try:
        legacy_url = paths.legacy_mcp_url_file.read_text(encoding="utf-8").strip()
    except OSError:
        legacy_url = ""
    if legacy_url:
        settings.service.mcp_url = legacy_url
    return settings


def _settings_from_json(raw: dict) -> AppSettings:
    pet = raw.get("pet") if isinstance(raw.get("pet"), dict) else {}
    service = raw.get("service") if isinstance(raw.get("service"), dict) else {}
    integrations_raw = raw.get("integrations") if isinstance(raw.get("integrations"), dict) else {}
    integrations = {
        "claude": IntegrationSettings(enabled=bool((integrations_raw.get("claude") or {}).get("enabled", False))),
        "codex": IntegrationSettings(enabled=bool((integrations_raw.get("codex") or {}).get("enabled", False))),
    }
    return AppSettings(
        version=int(raw.get("version", 1) or 1),
        source=str(raw.get("source") or "apple_music"),
        pet=PetAppSettings(
            slug=str(pet.get("slug") or "codebeat-buddy"),
            show_dock_icon=bool(pet.get("showDockIcon", True)),
            show_menu_bar_icon=bool(pet.get("showMenuBarIcon", True)),
        ),
        service=ServiceSettings(
            mcp_url=str(service.get("mcpUrl") or DEFAULT_MCP_URL),
            start_on_launch=bool(service.get("startOnLaunch", True)),
            restart_on_crash=bool(service.get("restartOnCrash", True)),
        ),
        integrations=integrations,
    )


def _settings_to_json(settings: AppSettings) -> dict:
    integrations = settings.integrations or {}
    return {
        "version": settings.version,
        "source": settings.source,
        "pet": {
            "slug": settings.pet.slug,
            "showDockIcon": settings.pet.show_dock_icon,
            "showMenuBarIcon": settings.pet.show_menu_bar_icon,
        },
        "service": {
            "mcpUrl": settings.service.mcp_url,
            "startOnLaunch": settings.service.start_on_launch,
            "restartOnCrash": settings.service.restart_on_crash,
        },
        "integrations": {
            "claude": {"enabled": integrations.get("claude", IntegrationSettings()).enabled},
            "codex": {"enabled": integrations.get("codex", IntegrationSettings()).enabled},
        },
    }


def _read_json(path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
pytest tests/test_app_settings.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add coding_with_beat/app_settings.py tests/test_app_settings.py
git commit -m "feat(app): add app settings migration"
```

---

### Task 3: Bundled Resource Manifest

**Files:**
- Modify: `scripts/build_macos_app.py`
- Modify: `tests/test_codebeat_app_builder.py`

- [ ] **Step 1: Add failing manifest test**

Append to `tests/test_codebeat_app_builder.py`:

```python
import json


def test_build_app_writes_resource_manifest(tmp_path):
    app_path = build_app(tmp_path)
    manifest_path = app_path / "Contents" / "Resources" / "manifest.json"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["version"] == 1
    assert manifest["appVersion"] == "0.1.0"
    assert "assets/waveform_app_icon.svg" in manifest["resources"]["assets"]
    assert "assets/waveform_menu_bar.svg" in manifest["resources"]["assets"]
    assert "pets/codebeat-buddy/pet.json" in manifest["resources"]["pets"]
    assert "pets/codebeat-buddy/spritesheet.png" in manifest["resources"]["pets"]
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
pytest tests/test_codebeat_app_builder.py::test_build_app_writes_resource_manifest -q
```

Expected: FAIL because `manifest.json` is missing.

- [ ] **Step 3: Generate manifest from builder**

Modify `scripts/build_macos_app.py`.

Add imports:

```python
import json
```

Call manifest writer in `build_app()` after `_copy_icons(resources)`:

```python
    _write_resource_manifest(resources)
```

Add these functions near `_copy_icons`:

```python
def _write_resource_manifest(resources: Path) -> None:
    manifest = {
        "version": 1,
        "appVersion": "0.1.0",
        "resources": {
            "assets": _existing_relative_files(ROOT / "assets", ["waveform_app_icon.svg", "waveform_menu_bar.svg"]),
            "pets": _existing_pet_files(ROOT / "assets" / "pets"),
            "claude": [],
            "codex": [],
            "commands": [],
            "skills": [],
        },
    }
    (resources / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _existing_relative_files(root: Path, names: list[str]) -> list[str]:
    files: list[str] = []
    for name in names:
        if (root / name).exists():
            files.append(f"{root.name}/{name}")
    return files


def _existing_pet_files(root: Path) -> list[str]:
    if not root.exists():
        return []
    files: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            files.append(path.relative_to(root).as_posix())
    return [f"pets/{name}" for name in files]
```

- [ ] **Step 4: Run builder tests**

Run:

```bash
pytest tests/test_codebeat_app_builder.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_macos_app.py tests/test_codebeat_app_builder.py
git commit -m "feat(app): write bundled resource manifest"
```

---

### Task 4: Child-Process MCP Service Manager

**Files:**
- Create: `coding_with_beat/service_manager.py`
- Test: `tests/test_service_manager.py`

- [ ] **Step 1: Write failing service manager tests**

Create `tests/test_service_manager.py`:

```python
from pathlib import Path
from unittest import mock

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
    manager = ServiceManager(paths=_paths(tmp_path), python="python3", run=lambda args, check: calls.append((args, check)))

    manager.open_logs()

    assert calls == [(["open", str(tmp_path / "logs")], False)]
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/test_service_manager.py -q
```

Expected: FAIL because `coding_with_beat.service_manager` does not exist.

- [ ] **Step 3: Implement service manager**

Create `coding_with_beat/service_manager.py`:

```python
"""MCP service lifecycle management for CodeBeat.app."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable

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
            return ServiceStatus(ServiceState.CRASHED, self.mcp_url, returncode=returncode, message="MCP process exited")
        if self._health_check(self.mcp_url):
            return ServiceStatus(ServiceState.RUNNING, self.mcp_url, pid=getattr(self._process, "pid", None))
        return ServiceStatus(ServiceState.DEGRADED, self.mcp_url, pid=getattr(self._process, "pid", None), message="Health check failed")

    def start(self) -> ServiceStatus:
        current = self.status()
        if current.state in {ServiceState.RUNNING, ServiceState.STARTING, ServiceState.DEGRADED}:
            return current
        self.paths.ensure()
        self._stdout = (self.paths.logs_dir / "mcp.log").open("a", encoding="utf-8")
        self._stderr = (self.paths.logs_dir / "mcp.err.log").open("a", encoding="utf-8")
        self._process = self._popen(
            [
                self.python,
                "-m",
                "coding_with_beat",
                "server",
                "--host",
                "127.0.0.1",
                "--port",
                "8765",
                "--path",
                "/mcp",
            ],
            stdout=self._stdout,
            stderr=self._stderr,
        )
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

    @staticmethod
    def _default_health_check(url: str) -> bool:
        try:
            call_tool("status", url=url, timeout=1.0)
        except Exception:
            return False
        return True
```

- [ ] **Step 4: Run service manager tests**

Run:

```bash
pytest tests/test_service_manager.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add coding_with_beat/service_manager.py tests/test_service_manager.py
git commit -m "feat(app): add mcp service manager"
```

---

### Task 5: App Entrypoint Wiring

**Files:**
- Modify: `coding_with_beat/app.py`
- Modify: `tests/test_codebeat_app.py`

- [ ] **Step 1: Update app tests for settings migration and service start**

Replace `tests/test_codebeat_app.py` with:

```python
from unittest import mock

from coding_with_beat import app
from coding_with_beat.app_settings import AppSettings, PetAppSettings, ServiceSettings


def test_codebeat_app_keeps_dock_icon_visible():
    settings = AppSettings(
        pet=PetAppSettings(slug="codebeat-buddy", show_dock_icon=True, show_menu_bar_icon=True),
        service=ServiceSettings(start_on_launch=False),
    )
    with (
        mock.patch("coding_with_beat.app.load_app_settings", return_value=settings),
        mock.patch("coding_with_beat.app.save_app_settings") as save_settings,
        mock.patch("coding_with_beat.app.mirror_mcp_url") as mirror_mcp_url,
        mock.patch("coding_with_beat.app.run_pet_app", return_value=0) as run_pet_app,
    ):
        assert app.run() == 0

    save_settings.assert_called_once()
    mirror_mcp_url.assert_called_once_with(settings, mock.ANY)
    run_pet_app.assert_called_once_with(
        petdex_slug="codebeat-buddy",
        hide_dock=False,
        show_control=False,
        show_menu_bar=True,
    )


def test_codebeat_app_defaults_to_codebeat_buddy_when_saved_pet_is_empty():
    settings = AppSettings(
        pet=PetAppSettings(slug="", show_dock_icon=True, show_menu_bar_icon=True),
        service=ServiceSettings(start_on_launch=False),
    )
    with (
        mock.patch("coding_with_beat.app.load_app_settings", return_value=settings),
        mock.patch("coding_with_beat.app.save_app_settings"),
        mock.patch("coding_with_beat.app.mirror_mcp_url"),
        mock.patch("coding_with_beat.app.run_pet_app", return_value=0) as run_pet_app,
    ):
        assert app.run() == 0

    run_pet_app.assert_called_once_with(
        petdex_slug="codebeat-buddy",
        hide_dock=False,
        show_control=False,
        show_menu_bar=True,
    )


def test_codebeat_app_uses_saved_chrome_visibility():
    settings = AppSettings(
        pet=PetAppSettings(slug="codebeat-buddy", show_dock_icon=False, show_menu_bar_icon=False),
        service=ServiceSettings(start_on_launch=False),
    )
    with (
        mock.patch("coding_with_beat.app.load_app_settings", return_value=settings),
        mock.patch("coding_with_beat.app.save_app_settings"),
        mock.patch("coding_with_beat.app.mirror_mcp_url"),
        mock.patch("coding_with_beat.app.run_pet_app", return_value=0) as run_pet_app,
    ):
        assert app.run() == 0

    run_pet_app.assert_called_once_with(
        petdex_slug="codebeat-buddy",
        hide_dock=True,
        show_control=False,
        show_menu_bar=False,
    )


def test_codebeat_app_starts_service_when_enabled():
    settings = AppSettings(service=ServiceSettings(mcp_url="http://127.0.0.1:8765/mcp", start_on_launch=True))
    manager = mock.Mock()

    with (
        mock.patch("coding_with_beat.app.load_app_settings", return_value=settings),
        mock.patch("coding_with_beat.app.save_app_settings"),
        mock.patch("coding_with_beat.app.mirror_mcp_url"),
        mock.patch("coding_with_beat.app.ServiceManager", return_value=manager) as service_manager,
        mock.patch("coding_with_beat.app.run_pet_app", return_value=0),
    ):
        assert app.run() == 0

    service_manager.assert_called_once_with(paths=mock.ANY, mcp_url="http://127.0.0.1:8765/mcp")
    manager.start.assert_called_once_with()


def test_codebeat_app_does_not_start_service_when_disabled():
    settings = AppSettings(service=ServiceSettings(start_on_launch=False))

    with (
        mock.patch("coding_with_beat.app.load_app_settings", return_value=settings),
        mock.patch("coding_with_beat.app.save_app_settings"),
        mock.patch("coding_with_beat.app.mirror_mcp_url"),
        mock.patch("coding_with_beat.app.ServiceManager") as service_manager,
        mock.patch("coding_with_beat.app.run_pet_app", return_value=0),
    ):
        assert app.run() == 0

    service_manager.assert_not_called()
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/test_codebeat_app.py -q
```

Expected: FAIL because `coding_with_beat.app` still imports pet settings directly and does not wire app settings or service manager.

- [ ] **Step 3: Wire app entrypoint**

Replace `coding_with_beat/app.py` with:

```python
"""CodeBeat macOS app control-center entrypoint."""

from __future__ import annotations

from .app_paths import CodeBeatPaths
from .app_settings import load_settings as load_app_settings
from .app_settings import mirror_mcp_url, save_settings as save_app_settings
from .pet.app import run as run_pet_app
from .pet.petdex import default_petdex_slug
from .service_manager import ServiceManager


def run() -> int:
    paths = CodeBeatPaths.default()
    paths.ensure()

    settings = load_app_settings(paths)
    save_app_settings(settings, paths)
    mirror_mcp_url(settings, paths)

    if settings.service.start_on_launch:
        ServiceManager(paths=paths, mcp_url=settings.service.mcp_url).start()

    petdex_slug = default_petdex_slug(settings.pet.slug)
    return run_pet_app(
        petdex_slug=petdex_slug,
        hide_dock=not settings.pet.show_dock_icon,
        show_control=False,
        show_menu_bar=settings.pet.show_menu_bar_icon,
    )
```

- [ ] **Step 4: Run app tests**

Run:

```bash
pytest tests/test_codebeat_app.py -q
```

Expected: PASS.

- [ ] **Step 5: Run pet app regression tests**

Run:

```bash
pytest tests/test_pet_settings.py tests/test_pet_macos.py tests/test_codebeat_app.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add coding_with_beat/app.py tests/test_codebeat_app.py
git commit -m "feat(app): wire app settings and service startup"
```

---

### Task 6: MCP URL Compatibility

**Files:**
- Modify: `coding_with_beat/mcp_client.py`
- Modify: `tests/test_mcp_client.py`

- [ ] **Step 1: Add failing app support MCP URL test**

Append to `tests/test_mcp_client.py` in `MCPClientConfigTest`:

```python
    def test_configured_url_prefers_app_support_service_settings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app_settings = Path(tmpdir) / "settings.json"
            legacy_url_file = Path(tmpdir) / "mcp-url"
            app_settings.write_text(
                '{"service": {"mcpUrl": "http://127.0.0.1:9999/mcp"}}',
                encoding="utf-8",
            )
            legacy_url_file.write_text("http://127.0.0.1:9876/mcp\n", encoding="utf-8")

            with (
                mock.patch.dict(os.environ, {}, clear=True),
                mock.patch.object(mcp_client, "APP_SETTINGS_FILE", app_settings),
                mock.patch.object(mcp_client, "MCP_URL_FILE", legacy_url_file),
            ):
                self.assertEqual(mcp_client.configured_url(), "http://127.0.0.1:9999/mcp")
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
pytest tests/test_mcp_client.py::MCPClientConfigTest::test_configured_url_prefers_app_support_service_settings -q
```

Expected: FAIL because `APP_SETTINGS_FILE` does not exist or is not read.

- [ ] **Step 3: Update MCP client URL lookup**

Modify `coding_with_beat/mcp_client.py`.

Add imports:

```python
import json
from pathlib import Path
```

Add module constant after `DEFAULT_MCP_URL`:

```python
APP_SETTINGS_FILE = Path.home() / "Library" / "Application Support" / "CodeBeat" / "settings.json"
```

Replace `configured_url()` with:

```python
def configured_url() -> str:
    env_url = os.environ.get(MCP_URL_ENV, "").strip() or os.environ.get(LEGACY_MCP_URL_ENV, "").strip()
    if env_url:
        return env_url
    app_url = _app_settings_url()
    if app_url:
        return app_url
    try:
        saved_url = MCP_URL_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        saved_url = ""
    return saved_url or DEFAULT_MCP_URL
```

Add helper:

```python
def _app_settings_url() -> str:
    try:
        raw = json.loads(APP_SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    service = raw.get("service") if isinstance(raw, dict) else None
    if not isinstance(service, dict):
        return ""
    return str(service.get("mcpUrl") or "").strip()
```

- [ ] **Step 4: Run MCP client tests**

Run:

```bash
pytest tests/test_mcp_client.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add coding_with_beat/mcp_client.py tests/test_mcp_client.py
git commit -m "feat(app): prefer app-managed mcp url"
```

---

### Task 7: Phase 1 Verification

**Files:**
- No new files

- [ ] **Step 1: Run focused test set**

Run:

```bash
pytest \
  tests/test_app_paths.py \
  tests/test_app_settings.py \
  tests/test_service_manager.py \
  tests/test_codebeat_app.py \
  tests/test_codebeat_app_builder.py \
  tests/test_mcp_client.py \
  -q
```

Expected: PASS.

- [ ] **Step 2: Run broader pet/app regression set**

Run:

```bash
pytest \
  tests/test_pet_settings.py \
  tests/test_pet_macos.py \
  tests/test_pet_petdex.py \
  tests/test_pet_cli.py \
  tests/test_codebeat_app.py \
  tests/test_codebeat_app_builder.py \
  -q
```

Expected: PASS.

- [ ] **Step 3: Build local app wrapper**

Run:

```bash
python scripts/build_macos_app.py
```

Expected: command prints `.../dist/CodeBeat.app`.

- [ ] **Step 4: Inspect generated manifest**

Run:

```bash
python - <<'PY'
import json
from pathlib import Path
p = Path("dist/CodeBeat.app/Contents/Resources/manifest.json")
data = json.loads(p.read_text())
print(data["version"], data["appVersion"])
print("pets/codebeat-buddy/pet.json" in data["resources"]["pets"])
PY
```

Expected output contains:

```text
1 0.1.0
True
```

- [ ] **Step 5: Confirm forbidden-marker scan**

Run:

```bash
rg -n "TB[D]|TO[DO]|FIX[ME]|place[holder]|implement late[r]|Similar to Tas[k]" docs/superpowers/plans/2026-05-30-codebeat-macos-unified-app-foundation.md
```

Expected: no matches and exit code 1.

- [ ] **Step 6: Commit final verification notes if any docs changed**

If no files changed during verification, skip this commit. If the plan or docs needed corrections, run:

```bash
git add docs/superpowers/plans/2026-05-30-codebeat-macos-unified-app-foundation.md
git commit -m "docs(app): refine unified app foundation plan"
```

---

## Follow-Up Plans

After this plan lands, write separate plans for:

- Claude Code integration manager extraction and tests
- Codex integration manager extraction and tests
- PySide6 settings window and menu-bar control-center UI
- production bundled app packaging with embedded Python
- DMG generation and distribution hardening

## Self-Review

- Spec coverage: This plan covers Phase 1 and the compatibility rules relevant to app-owned settings and MCP URL lookup. It deliberately leaves integration UI, production bundling, DMG, signing, notarization, and LaunchAgent persistence for follow-up plans.
- Forbidden-marker scan target: `rg -n "TB[D]|TO[DO]|FIX[ME]|place[holder]|implement late[r]|Similar to Tas[k]" docs/superpowers/plans/2026-05-30-codebeat-macos-unified-app-foundation.md` should return no matches.
- Type consistency: `CodeBeatPaths`, `AppSettings`, `PetAppSettings`, `ServiceSettings`, `IntegrationSettings`, `ServiceManager`, `ServiceState`, and `ServiceStatus` are introduced before later tasks reference them.
