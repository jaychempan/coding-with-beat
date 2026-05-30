"""Headless AI chat command helpers for the desktop pet."""

from __future__ import annotations

import json
import os
import shutil
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable

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

    def mark_started(self) -> None:
        self.started = True

    def reset(self) -> None:
        self.started = False
        if self.provider is AiProvider.CLAUDE:
            self.session_id = str(uuid.uuid4())

    def build_command(self, prompt: str, mode: AiPermissionMode) -> AiChatCommand:
        stdin = _wrap_prompt(prompt)
        if self.provider is AiProvider.CODEX:
            return AiChatCommand(args=self._build_codex_args(mode), stdin=stdin, cwd=self.cwd)
        return AiChatCommand(args=self._build_claude_args(mode), stdin=stdin, cwd=self.cwd)

    def _build_codex_args(self, mode: AiPermissionMode) -> list[str]:
        if self.started:
            return ["codex", "exec", "resume", "--json", "--last", "-"]
        args = ["codex", "exec", "--json", "--cd", str(self.cwd), "--color", "never"]
        if mode is AiPermissionMode.READ_ONLY:
            return [*args, "--sandbox", "read-only"]
        return [*args, "--sandbox", "workspace-write", "--ask-for-approval", "on-request"]

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
        self.busy = True

        self._configure_process(process, command.cwd)
        process.readyReadStandardOutput.connect(self._read_stdout)
        process.readyReadStandardError.connect(self._read_stderr)
        process.finished.connect(self._finish)
        process.start(executable, command.args[1:])
        process.write(command.stdin.encode("utf-8"))
        process.closeWriteChannel()
        self._timeout_timer.start(self._timeout_ms)
        return True

    def stop(self) -> None:
        if not self.busy:
            return
        process = self._process
        self._timeout_timer.stop()
        self.busy = False
        self._process = None
        self._active_provider = None
        if process is not None:
            process.kill()
        self.finished.emit(AiChatResult(False, "AI chat stopped."))

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
        process.setProcessEnvironment(environment)

    def _read_stdout(self) -> None:
        if self._process is not None:
            self._stdout.extend(_bytes_from_qt(self._process.readAllStandardOutput()))

    def _read_stderr(self) -> None:
        if self._process is not None:
            self._stderr.extend(_bytes_from_qt(self._process.readAllStandardError()))

    def _finish(self, exit_code: int, _exit_status=None) -> None:
        if not self.busy:
            return
        self._timeout_timer.stop()
        provider = self._active_provider
        self.busy = False
        self._process = None
        self._active_provider = None

        stdout = self._stdout.decode("utf-8", errors="replace").strip()
        stderr = self._stderr.decode("utf-8", errors="replace").strip()
        if exit_code == 0:
            if provider is not None:
                self._sessions[provider].mark_started()
            text = _extract_agent_text(provider, stdout)
            self.finished.emit(AiChatResult(True, text))
            return
        self.finished.emit(AiChatResult(False, stderr or stdout or "AI chat failed."))


def _bytes_from_qt(data: object) -> bytes:
    if isinstance(data, bytes):
        return data
    return bytes(data)


def _extract_agent_text(provider: AiProvider | None, stdout: str) -> str:
    if provider is not AiProvider.CODEX:
        return stdout
    final_message = ""
    for line in stdout.splitlines():
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("type") != "item.completed":
            continue
        item = payload.get("item")
        if isinstance(item, dict) and item.get("type") == "agent_message":
            text = item.get("text")
            if isinstance(text, str):
                final_message = text
    return final_message or stdout
