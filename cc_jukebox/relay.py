"""Relay support for running Claude Code remotely while cc-jukebox stays local.

There are two supported transports:

1. Ping Island-style SSH attach:
   - remote: ``cc-jukebox relay agent-service`` listens on Unix sockets
   - local:  ``cc-jukebox relay attach user@host`` connects over ssh stdio
   - configured remote statusline/hooks call the request socket and are
     executed on the local Mac

2. HTTP relay:
   - local:  ``cc-jukebox relay serve``
   - configured remote statusline/hooks use
     ``CC_JUKEBOX_RELAY_URL=http://127.0.0.1:8765``

The request protocol is intentionally small and JSON-only. Automatic CLI
proxying is limited to remote statusline rendering; hooks forward themselves
after /juke prompt expansion has had a chance to run on the remote host.
"""
from __future__ import annotations

import argparse
import contextlib
import http.server
import json
import os
import shlex
import socket
import socketserver
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4


RELAY_SOCKET_ENV = "CC_JUKEBOX_RELAY_SOCKET"
RELAY_URL_ENV = "CC_JUKEBOX_RELAY_URL"
RELAY_TOKEN_ENV = "CC_JUKEBOX_RELAY_TOKEN"
RELAY_LOCAL_ENV = "CC_JUKEBOX_RELAY_LOCAL"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_TIMEOUT = 300
RUN_DIR = Path.home() / ".cc-jukebox" / "run"
DEFAULT_REQUEST_SOCKET = RUN_DIR / "agent-request.sock"
DEFAULT_CONTROL_SOCKET = RUN_DIR / "agent-control.sock"
REMOTE_DEFAULT_CONTROL_SOCKET = "~/.cc-jukebox/run/agent-control.sock"


def relay_configured() -> bool:
    return bool(os.environ.get(RELAY_SOCKET_ENV) or os.environ.get(RELAY_URL_ENV))


def relay_is_local() -> bool:
    return os.environ.get(RELAY_LOCAL_ENV) == "1"


def should_proxy_cli(argv: list[str]) -> bool:
    if relay_is_local() or not relay_configured() or not argv:
        return False
    return argv[0] == "statusline"


def proxy_cli_to_relay(argv: list[str]) -> int:
    response = cli_request(argv, sys.stdin.read())
    _print_cli_response(response)
    return int(response.get("exit_code") or (0 if response.get("ok", True) else 1))


def cli_request(argv: list[str], stdin_text: str = "") -> dict[str, Any]:
    request = {
        "id": str(uuid4()),
        "kind": "cli",
        "argv": argv,
        "stdin": stdin_text,
        "env": _safe_forward_env(),
    }
    try:
        return send_request(request)
    except Exception as e:
        return _error_response(request, f"cc-jukebox relay error: {e}")


def _print_cli_response(response: dict[str, Any]) -> None:
    stdout = str(response.get("stdout") or "")
    stderr = str(response.get("stderr") or "")
    if stdout:
        sys.stdout.write(stdout)
    if stderr:
        sys.stderr.write(stderr)


def send_request(request: dict[str, Any]) -> dict[str, Any]:
    if os.environ.get(RELAY_SOCKET_ENV):
        return _send_socket_request(request, os.environ[RELAY_SOCKET_ENV])
    if os.environ.get(RELAY_URL_ENV):
        return _send_http_request(request, os.environ[RELAY_URL_ENV])
    raise RuntimeError("set CC_JUKEBOX_RELAY_SOCKET or CC_JUKEBOX_RELAY_URL")


def execute_local_request(request: dict[str, Any]) -> dict[str, Any]:
    kind = request.get("kind")
    if kind == "cli":
        return _execute_local_cli(request)
    return _error_response(request, f"unknown relay request kind: {kind!r}")


def run_http_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, token: str = "") -> None:
    class Handler(http.server.BaseHTTPRequestHandler):
        server_version = "CCJukeboxRelay/0.1"

        def do_GET(self) -> None:  # noqa: N802 - stdlib hook name
            if self.path.rstrip("/") == "/health":
                self._write_json({"ok": True, "service": "cc-jukebox-relay"})
                return
            self.send_error(404)

        def do_POST(self) -> None:  # noqa: N802 - stdlib hook name
            if self.path.rstrip("/") != "/request":
                self.send_error(404)
                return
            if token and self.headers.get("Authorization") != f"Bearer {token}":
                self.send_error(401)
                return
            try:
                length = int(self.headers.get("Content-Length") or "0")
                payload = self.rfile.read(length)
                request = json.loads(payload.decode("utf-8"))
                response = execute_local_request(request)
            except Exception as e:
                response = {"ok": False, "error": str(e)}
            self._write_json(response)

        def log_message(self, fmt: str, *args: Any) -> None:
            if os.environ.get("CC_JUKEBOX_RELAY_DEBUG") == "1":
                super().log_message(fmt, *args)

        def _write_json(self, payload: dict[str, Any]) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    httpd = http.server.ThreadingHTTPServer((host, port), Handler)
    print(f"cc-jukebox relay listening on http://{host}:{port}/request", file=sys.stderr)
    httpd.serve_forever()


@dataclass
class _Pending:
    event: threading.Event
    response: dict[str, Any] | None = None


class RelayAgentService:
    def __init__(
        self,
        request_socket: str | Path = DEFAULT_REQUEST_SOCKET,
        control_socket: str | Path = DEFAULT_CONTROL_SOCKET,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.request_socket = _expand_path(request_socket)
        self.control_socket = _expand_path(control_socket)
        self.timeout = timeout
        self.pending: dict[str, _Pending] = {}
        self.pending_lock = threading.Lock()
        self.control: socket.socket | None = None
        self.control_lock = threading.Lock()
        self.send_lock = threading.Lock()

    def serve_forever(self) -> None:
        _prepare_socket_path(self.request_socket)
        _prepare_socket_path(self.control_socket)

        agent = self

        class RequestServer(socketserver.ThreadingUnixStreamServer):
            daemon_threads = True

        class ControlServer(socketserver.ThreadingUnixStreamServer):
            daemon_threads = True

        class RequestHandler(socketserver.BaseRequestHandler):
            def handle(self) -> None:
                agent.handle_request(self.request)

        class ControlHandler(socketserver.BaseRequestHandler):
            def handle(self) -> None:
                agent.handle_control(self.request)

        request_server = RequestServer(str(self.request_socket), RequestHandler)
        control_server = ControlServer(str(self.control_socket), ControlHandler)
        os.chmod(self.request_socket, 0o700)
        os.chmod(self.control_socket, 0o700)

        print(f"cc-jukebox relay agent request socket: {self.request_socket}", file=sys.stderr)
        print(f"cc-jukebox relay agent control socket: {self.control_socket}", file=sys.stderr)

        request_thread = threading.Thread(target=request_server.serve_forever, daemon=True)
        control_thread = threading.Thread(target=control_server.serve_forever, daemon=True)
        request_thread.start()
        control_thread.start()
        try:
            while True:
                time.sleep(3600)
        finally:
            request_server.shutdown()
            control_server.shutdown()

    def handle_request(self, client: socket.socket) -> None:
        try:
            request = json.loads(_recv_all(client).decode("utf-8"))
        except Exception as e:
            _write_socket_json(client, {"ok": False, "error": f"bad request: {e}"})
            return

        request_id = str(request.get("id") or uuid4())
        request["id"] = request_id
        pending = _Pending(threading.Event())
        with self.pending_lock:
            self.pending[request_id] = pending

        try:
            if not self._send_to_control(request):
                pending.response = _error_response(request, "no local cc-jukebox attach connection")
                pending.event.set()
            if not pending.event.wait(self.timeout):
                pending.response = _error_response(request, f"relay request timed out after {self.timeout}s")
        finally:
            with self.pending_lock:
                self.pending.pop(request_id, None)

        _write_socket_json(client, pending.response or _error_response(request, "relay request failed"))

    def handle_control(self, control: socket.socket) -> None:
        with self.control_lock:
            if self.control is not None:
                with contextlib.suppress(Exception):
                    self.control.close()
            self.control = control

        try:
            control_file = control.makefile("rb")
            for line in control_file:
                if not line.strip():
                    continue
                try:
                    response = json.loads(line.decode("utf-8"))
                    request_id = str(response.get("id") or "")
                except Exception:
                    continue
                with self.pending_lock:
                    pending = self.pending.get(request_id)
                if pending is not None:
                    pending.response = response
                    pending.event.set()
        finally:
            with self.control_lock:
                if self.control is control:
                    self.control = None
            self._fail_pending("local cc-jukebox attach disconnected")

    def _send_to_control(self, request: dict[str, Any]) -> bool:
        with self.control_lock:
            control = self.control
        if control is None:
            return False
        data = json.dumps(request, ensure_ascii=False).encode("utf-8") + b"\n"
        try:
            with self.send_lock:
                control.sendall(data)
            return True
        except OSError:
            return False

    def _fail_pending(self, message: str) -> None:
        with self.pending_lock:
            pending_items = list(self.pending.items())
        for request_id, pending in pending_items:
            pending.response = {"id": request_id, "ok": False, "error": message, "exit_code": 1}
            pending.event.set()


def run_agent_attach(control_socket: str | Path = DEFAULT_CONTROL_SOCKET) -> None:
    path = _expand_path(control_socket)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(str(path))

    def stdin_to_socket() -> None:
        try:
            while True:
                chunk = os.read(sys.stdin.fileno(), 4096)
                if not chunk:
                    break
                sock.sendall(chunk)
        finally:
            with contextlib.suppress(Exception):
                sock.shutdown(socket.SHUT_WR)

    writer = threading.Thread(target=stdin_to_socket, daemon=True)
    writer.start()
    try:
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()
    finally:
        with contextlib.suppress(Exception):
            sock.close()
        writer.join(timeout=1)


def run_local_attach(
    ssh_target: str,
    *,
    port: int = 22,
    remote_bin: str = "$HOME/.local/bin/cc-jukebox",
    control_socket: str = REMOTE_DEFAULT_CONTROL_SOCKET,
    extra_ssh_args: list[str] | None = None,
) -> int:
    remote_cmd = (
        f"{_remote_executable(remote_bin)} relay agent-attach "
        f"--control-socket {shlex.quote(control_socket)}"
    )
    ssh_cmd = ["ssh", "-T"]
    if port != 22:
        ssh_cmd += ["-p", str(port)]
    ssh_cmd += extra_ssh_args or []
    ssh_cmd += [ssh_target, remote_cmd]

    proc = subprocess.Popen(
        ssh_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    def stderr_reader() -> None:
        assert proc.stderr is not None
        for line in proc.stderr:
            sys.stderr.write(line)

    threading.Thread(target=stderr_reader, daemon=True).start()
    assert proc.stdout is not None
    assert proc.stdin is not None

    try:
        for line in proc.stdout:
            if not line.strip():
                continue
            try:
                request = json.loads(line)
                response = execute_local_request(request)
            except Exception as e:
                request_id = ""
                with contextlib.suppress(Exception):
                    request_id = str(json.loads(line).get("id") or "")
                response = {"id": request_id, "ok": False, "error": str(e), "exit_code": 1}
            proc.stdin.write(json.dumps(response, ensure_ascii=False) + "\n")
            proc.stdin.flush()
    except KeyboardInterrupt:
        proc.terminate()
    finally:
        with contextlib.suppress(Exception):
            proc.stdin.close()
    return proc.wait()


def run_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cc-jukebox relay")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="run a local HTTP relay server")
    serve.add_argument("--host", default=DEFAULT_HOST)
    serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve.add_argument("--token", default=os.environ.get(RELAY_TOKEN_ENV, ""))

    service = sub.add_parser("agent-service", help="run the remote Unix-socket relay service")
    service.add_argument("--request-socket", default=str(DEFAULT_REQUEST_SOCKET))
    service.add_argument("--control-socket", default=str(DEFAULT_CONTROL_SOCKET))
    service.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)

    attach = sub.add_parser("agent-attach", help="attach stdio to a remote relay control socket")
    attach.add_argument("--control-socket", default=str(DEFAULT_CONTROL_SOCKET))

    local_attach = sub.add_parser("attach", help="ssh to a remote relay and execute requests locally")
    local_attach.add_argument("ssh_target")
    local_attach.add_argument("--port", type=int, default=22)
    local_attach.add_argument("--remote-bin", default="$HOME/.local/bin/cc-jukebox")
    local_attach.add_argument("--control-socket", default=REMOTE_DEFAULT_CONTROL_SOCKET)
    local_attach.add_argument("--ssh-arg", action="append", default=[])

    call = sub.add_parser("call", help="debug: forward one CLI command through the relay")
    call.add_argument("relay_argv", nargs=argparse.REMAINDER)

    args = parser.parse_args(argv)
    if args.command == "serve":
        run_http_server(args.host, args.port, args.token)
        return 0
    if args.command == "agent-service":
        RelayAgentService(args.request_socket, args.control_socket, args.timeout).serve_forever()
        return 0
    if args.command == "agent-attach":
        run_agent_attach(args.control_socket)
        return 0
    if args.command == "attach":
        return run_local_attach(
            args.ssh_target,
            port=args.port,
            remote_bin=args.remote_bin,
            control_socket=args.control_socket,
            extra_ssh_args=args.ssh_arg,
        )
    if args.command == "call":
        relay_argv = args.relay_argv
        if relay_argv and relay_argv[0] == "--":
            relay_argv = relay_argv[1:]
        return proxy_cli_to_relay(relay_argv)
    return 2


def _execute_local_cli(request: dict[str, Any]) -> dict[str, Any]:
    argv = request.get("argv")
    if not isinstance(argv, list) or not all(isinstance(item, str) for item in argv):
        return _error_response(request, "cli request requires argv: list[str]")
    stdin = request.get("stdin")
    env_delta = request.get("env") if isinstance(request.get("env"), dict) else {}
    env = os.environ.copy()
    for key, value in env_delta.items():
        if isinstance(key, str) and isinstance(value, str):
            env[key] = value
    _mark_local_env(env)
    timeout = int(request.get("timeout") or os.environ.get("CC_JUKEBOX_RELAY_TIMEOUT", DEFAULT_TIMEOUT))
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "cc_jukebox", *argv],
            input=str(stdin or ""),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            timeout=timeout,
        )
        return {
            "id": request.get("id"),
            "ok": proc.returncode == 0,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "exit_code": proc.returncode,
        }
    except subprocess.TimeoutExpired as e:
        return _error_response(request, f"local cli timed out after {timeout}s: {e}")


def _send_socket_request(request: dict[str, Any], path: str) -> dict[str, Any]:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(float(os.environ.get("CC_JUKEBOX_RELAY_TIMEOUT", DEFAULT_TIMEOUT)))
    sock.connect(str(_expand_path(path)))
    try:
        _write_socket_json(sock, request)
        sock.shutdown(socket.SHUT_WR)
        data = _recv_all(sock)
    finally:
        sock.close()
    return json.loads(data.decode("utf-8"))


def _send_http_request(request: dict[str, Any], url: str) -> dict[str, Any]:
    endpoint = url.rstrip("/")
    if not endpoint.endswith("/request"):
        endpoint += "/request"
    data = json.dumps(request, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json; charset=utf-8"}
    token = os.environ.get(RELAY_TOKEN_ENV, "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    http_request = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(
            http_request,
            timeout=float(os.environ.get("CC_JUKEBOX_RELAY_TIMEOUT", DEFAULT_TIMEOUT)),
        ) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.reason}") from e


def _recv_all(sock: socket.socket) -> bytes:
    chunks: list[bytes] = []
    while True:
        chunk = sock.recv(65536)
        if not chunk:
            break
        chunks.append(chunk)
    return b"".join(chunks)


def _write_socket_json(sock: socket.socket, payload: dict[str, Any]) -> None:
    sock.sendall(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


def _error_response(request: dict[str, Any], message: str) -> dict[str, Any]:
    return {
        "id": request.get("id"),
        "ok": False,
        "error": message,
        "stdout": "",
        "stderr": message + "\n",
        "exit_code": 1,
    }


def _safe_forward_env() -> dict[str, str]:
    allowed = {
        "COLUMNS",
        "LINES",
        "TERM",
        "LANG",
        "LC_ALL",
        "CLAUDE_PROJECT_DIR",
        "PWD",
    }
    return {key: value for key, value in os.environ.items() if key in allowed and isinstance(value, str)}


def _mark_local_env(env: dict[str, str]) -> None:
    env[RELAY_LOCAL_ENV] = "1"
    env.pop(RELAY_SOCKET_ENV, None)
    env.pop(RELAY_URL_ENV, None)
    env.pop(RELAY_TOKEN_ENV, None)


def _expand_path(path: str | Path) -> Path:
    return Path(str(path)).expanduser()


def _remote_executable(value: str) -> str:
    if value.startswith("$HOME/") or value.startswith("~/"):
        return value
    return shlex.quote(value)


def _prepare_socket_path(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(FileNotFoundError):
        path.unlink()
