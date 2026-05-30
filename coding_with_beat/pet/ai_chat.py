"""Headless AI chat command helpers for the desktop pet."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Mapping

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, Signal


class AiProvider(Enum):
    CODEX = "codex"
    CLAUDE = "claude"


class AiPermissionMode(Enum):
    READ_ONLY = "read_only"
    WORKSPACE_WRITE = "workspace_write"


@dataclass(frozen=True)
class AiChatCommand:
    args: list[str]
    stdin: str
    cwd: Path


@dataclass(frozen=True)
class AiChatResult:
    ok: bool
    text: str


@dataclass(frozen=True)
class _ExtractedAgentOutput:
    text: str
    thread_id: str | None = None


MUSIC_ACTION_PROMPT_CONTRACT = """You are inside CodeBeat DJ, a desktop coding companion with music controls.
Answer the user's prompt normally. When your answer should trigger or suggest music, also include one fenced JSON block.
The JSON block must use this shape:

```json
{
  "music_actions": [
    {"kind": "play_track", "query": "song and artist", "label": "Song - Artist"},
    {"kind": "search_music", "query": "mood genre activity", "label": "Search label"},
    {"kind": "play_number", "query": "1", "label": "Play first result"},
    {"kind": "control", "query": "next_track", "label": "Next track"},
    {"kind": "playlist", "query": "playlist name", "label": "Playlist label"}
  ]
}
```

Use an empty or omitted music_actions list when no music action is useful.

User prompt:
"""


def _wrap_prompt(prompt: str) -> str:
    return f"{MUSIC_ACTION_PROMPT_CONTRACT}{prompt}"


@dataclass
class AiChatSession:
    provider: AiProvider
    cwd: Path
    session_id: str | None = None
    started: bool = False

    def __post_init__(self) -> None:
        self.cwd = Path(self.cwd)
        if self.provider is AiProvider.CLAUDE and not self.session_id:
            self.session_id = str(uuid.uuid4())

    def mark_started(self, session_id: str | None = None) -> None:
        self.started = True
        if self.provider is AiProvider.CODEX and session_id:
            self.session_id = session_id

    def reset(self) -> None:
        self.started = False
        if self.provider is AiProvider.CLAUDE:
            self.session_id = str(uuid.uuid4())
        else:
            self.session_id = None

    def build_command(self, prompt: str, mode: AiPermissionMode) -> AiChatCommand:
        stdin = _wrap_prompt(prompt)
        if self.provider is AiProvider.CODEX:
            return AiChatCommand(args=self._build_codex_args(mode), stdin=stdin, cwd=self.cwd)
        return AiChatCommand(args=self._build_claude_args(mode), stdin=stdin, cwd=self.cwd)

    def _build_codex_args(self, mode: AiPermissionMode) -> list[str]:
        if self.started:
            if self.session_id:
                return ["codex", "exec", "resume", "--json", self.session_id, "-"]
            return ["codex", "exec", "resume", "--json", "--last", "-"]
        args = ["codex", "exec", "--json", "--cd", str(self.cwd), "--color", "never"]
        if mode is AiPermissionMode.READ_ONLY:
            return [*args, "--sandbox", "read-only"]
        return [*args, "--sandbox", "workspace-write"]

    def _build_claude_args(self, mode: AiPermissionMode) -> list[str]:
        permission_mode = "acceptEdits" if mode is AiPermissionMode.WORKSPACE_WRITE else "default"
        session_id = self.session_id or str(uuid.uuid4())
        self.session_id = session_id
        return [
            "claude",
            "--print",
            "--session-id",
            session_id,
            "--permission-mode",
            permission_mode,
        ]


def resolve_ai_executable(provider: AiProvider) -> str | None:
    env_name = "CWB_CODEX" if provider is AiProvider.CODEX else "CWB_CLAUDE"
    if configured := os.environ.get(env_name):
        return configured
    if found := shutil.which(provider.value):
        return found
    for directory in (
        Path.home() / ".local" / "bin",
        Path.home() / ".npm-global" / "bin",
        Path.home() / ".bun" / "bin",
        Path("/opt/homebrew/bin"),
        Path("/usr/local/bin"),
    ):
        candidate = directory / provider.value
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


ProcessFactory = Callable[[], object]
ExecutableResolver = Callable[[AiProvider], str | None]

_LOCAL_NO_PROXY = ("127.0.0.1", "localhost", "::1")
_PROXY_KEY_PAIRS = (
    ("HTTP_PROXY", "http_proxy"),
    ("HTTPS_PROXY", "https_proxy"),
    ("ALL_PROXY", "all_proxy"),
)


class AiChatRunner(QObject):
    finished = Signal(object)

    def __init__(
        self,
        parent=None,
        cwd: str | Path | None = None,
        process_factory: ProcessFactory | None = None,
        executable_resolver: ExecutableResolver = resolve_ai_executable,
        timeout_ms: int = 120_000,
    ) -> None:
        super().__init__(parent)
        self.cwd = Path(cwd or Path.cwd())
        self.busy = False
        self._process_factory = process_factory or QProcess
        self._executable_resolver = executable_resolver
        self._timeout_ms = timeout_ms
        self._timeout_timer = QTimer(self)
        self._timeout_timer.setSingleShot(True)
        self._timeout_timer.timeout.connect(self.stop)
        self._process = None
        self._active_provider: AiProvider | None = None
        self._stdout = bytearray()
        self._stderr = bytearray()
        self._stopping = False
        self._sessions = {
            AiProvider.CODEX: AiChatSession(AiProvider.CODEX, self.cwd),
            AiProvider.CLAUDE: AiChatSession(AiProvider.CLAUDE, self.cwd),
        }

    def send(self, prompt: str, provider: AiProvider, mode: AiPermissionMode) -> bool:
        if self.busy:
            return False
        executable = self._executable_resolver(provider)
        if not executable:
            self.finished.emit(AiChatResult(False, f"{provider.value} CLI not found."))
            return False

        session = self._sessions[provider]
        command = session.build_command(prompt, mode)
        process = self._process_factory()
        self._process = process
        self._active_provider = provider
        self._stdout = bytearray()
        self._stderr = bytearray()
        self._stopping = False
        self.busy = True

        self._configure_process(process, command.cwd)
        process.readyReadStandardOutput.connect(self._read_stdout)
        process.readyReadStandardError.connect(self._read_stderr)
        if hasattr(process, "errorOccurred"):
            process.errorOccurred.connect(self._process_error)
        process.finished.connect(self._finish)
        process.start(executable, command.args[1:])
        process.write(command.stdin.encode("utf-8"))
        process.closeWriteChannel()
        self._timeout_timer.start(self._timeout_ms)
        return True

    def stop(self) -> None:
        if not self.busy:
            return
        self._timeout_timer.stop()
        self._stopping = True
        process = self._process
        if process is not None:
            process.kill()

    def reset_session(self, provider: AiProvider | None = None) -> None:
        if provider is None:
            for session in self._sessions.values():
                session.reset()
            return
        self._sessions[provider].reset()

    def _configure_process(self, process: object, cwd: Path) -> None:
        if hasattr(process, "setWorkingDirectory"):
            process.setWorkingDirectory(str(cwd))
        if not isinstance(process, QProcess):
            return
        environment = QProcessEnvironment.systemEnvironment()
        environment.insert("CWB_DISABLE_HOOK", "1")
        path_parts = [
            str(Path.home() / ".local" / "bin"),
            str(Path.home() / ".npm-global" / "bin"),
            str(Path.home() / ".bun" / "bin"),
            "/opt/homebrew/bin",
            "/usr/local/bin",
            environment.value("PATH"),
        ]
        environment.insert("PATH", os.pathsep.join(part for part in path_parts if part))
        for key, value in _collect_proxy_environment().items():
            environment.insert(key, value)
        process.setProcessEnvironment(environment)

    def _read_stdout(self) -> None:
        if self._process is not None:
            self._stdout.extend(_bytes_from_qt(self._process.readAllStandardOutput()))

    def _read_stderr(self) -> None:
        if self._process is not None:
            self._stderr.extend(_bytes_from_qt(self._process.readAllStandardError()))

    def _process_error(self, _error=None) -> None:
        if not self.busy:
            return
        if self._stopping:
            return
        process = self._process
        message = "unknown process error"
        if process is not None and hasattr(process, "errorString"):
            message = str(process.errorString())
        self._timeout_timer.stop()
        self._clear_active_state()
        self.finished.emit(AiChatResult(False, f"AI chat process failed: {message}"))

    def _finish(self, exit_code: int, _exit_status=None) -> None:
        if not self.busy:
            return
        self._timeout_timer.stop()
        process = self._process
        if process is not None:
            self._stdout.extend(_bytes_from_qt(process.readAllStandardOutput()))
            self._stderr.extend(_bytes_from_qt(process.readAllStandardError()))
        provider = self._active_provider
        stopping = self._stopping
        self._clear_active_state()

        stdout = self._stdout.decode("utf-8", errors="replace").strip()
        stderr = self._stderr.decode("utf-8", errors="replace").strip()
        if stopping:
            self.finished.emit(AiChatResult(False, "AI chat stopped."))
            return
        if exit_code == 0:
            extracted = _extract_agent_text(provider, stdout)
            if provider is not None:
                self._sessions[provider].mark_started(extracted.thread_id)
            self.finished.emit(AiChatResult(True, extracted.text))
            return
        self.finished.emit(AiChatResult(False, stderr or stdout or "AI chat failed."))

    def _clear_active_state(self) -> None:
        self.busy = False
        self._process = None
        self._active_provider = None
        self._stopping = False


def _bytes_from_qt(data: object) -> bytes:
    if isinstance(data, bytes):
        return data
    return bytes(data)


def _merge_local_no_proxy(value: str | None) -> str:
    entries = [entry.strip() for entry in (value or "").split(",") if entry.strip()]
    seen = set(entries)
    for entry in _LOCAL_NO_PROXY:
        if entry not in seen:
            entries.append(entry)
            seen.add(entry)
    return ",".join(entries)


def _proxy_env_from_mapping(mapping: Mapping[str, str]) -> dict[str, str]:
    proxy_env: dict[str, str] = {}
    for upper_key, lower_key in _PROXY_KEY_PAIRS:
        value = mapping.get(upper_key) or mapping.get(lower_key)
        if value:
            proxy_env[upper_key] = value
            proxy_env[lower_key] = value
    if proxy_env:
        no_proxy = _merge_local_no_proxy(mapping.get("NO_PROXY") or mapping.get("no_proxy"))
        proxy_env["NO_PROXY"] = no_proxy
        proxy_env["no_proxy"] = no_proxy
    return proxy_env


def _proxy_env_from_scutil_output(output: str) -> dict[str, str]:
    values = dict(re.findall(r"^\s*([A-Z]+(?:Proxy|Port|Enable))\s*:\s*(.+?)\s*$", output, re.MULTILINE))
    proxy_env: dict[str, str] = {}
    if values.get("HTTPEnable") == "1" and values.get("HTTPProxy") and values.get("HTTPPort"):
        proxy_env["HTTP_PROXY"] = f"http://{values['HTTPProxy']}:{values['HTTPPort']}"
        proxy_env["http_proxy"] = proxy_env["HTTP_PROXY"]
    if values.get("HTTPSEnable") == "1" and values.get("HTTPSProxy") and values.get("HTTPSPort"):
        proxy_env["HTTPS_PROXY"] = f"http://{values['HTTPSProxy']}:{values['HTTPSPort']}"
        proxy_env["https_proxy"] = proxy_env["HTTPS_PROXY"]
    if values.get("SOCKSEnable") == "1" and values.get("SOCKSProxy") and values.get("SOCKSPort"):
        proxy_env["ALL_PROXY"] = f"socks5://{values['SOCKSProxy']}:{values['SOCKSPort']}"
        proxy_env["all_proxy"] = proxy_env["ALL_PROXY"]
    if proxy_env:
        no_proxy = _merge_local_no_proxy(None)
        proxy_env["NO_PROXY"] = no_proxy
        proxy_env["no_proxy"] = no_proxy
    return proxy_env


def _scutil_proxy_environment() -> dict[str, str]:
    if sys.platform != "darwin":
        return {}
    try:
        result = subprocess.run(
            ["scutil", "--proxy"],
            check=False,
            capture_output=True,
            text=True,
            timeout=1,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    if result.returncode != 0:
        return {}
    return _proxy_env_from_scutil_output(result.stdout)


def _collect_proxy_environment() -> dict[str, str]:
    return _proxy_env_from_mapping(os.environ) or _scutil_proxy_environment()


def _extract_agent_text(provider: AiProvider | None, stdout: str) -> _ExtractedAgentOutput:
    if provider is not AiProvider.CODEX:
        return _ExtractedAgentOutput(stdout)
    final_message = ""
    thread_id = None
    for line in stdout.splitlines():
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("type") == "thread.started":
            value = payload.get("thread_id")
            if isinstance(value, str) and value:
                thread_id = value
            continue
        if payload.get("type") != "item.completed":
            continue
        item = payload.get("item")
        if isinstance(item, dict) and item.get("type") == "agent_message":
            text = item.get("text")
            if isinstance(text, str):
                final_message = text
    return _ExtractedAgentOutput(final_message or stdout, thread_id)
