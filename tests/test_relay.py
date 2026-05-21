import os
import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from cc_jukebox import relay
from scripts import install_settings


class RelayProtocolTest(unittest.TestCase):
    def test_execute_local_cli_runs_without_relay_recursion(self):
        response = relay.execute_local_request({
            "id": "test-1",
            "kind": "cli",
            "argv": ["banner"],
            "stdin": "",
            "env": {
                relay.RELAY_SOCKET_ENV: "/tmp/should-not-be-forwarded.sock",
            },
        })

        self.assertTrue(response["ok"])
        self.assertEqual(response["exit_code"], 0)
        self.assertIn("pixel companion", response["stdout"])

    def test_cli_proxy_is_disabled_for_mcp_server_and_relay_commands(self):
        with mock.patch.dict(os.environ, {relay.RELAY_SOCKET_ENV: "/tmp/relay.sock"}, clear=False):
            self.assertFalse(relay.should_proxy_cli(["server"]))
            self.assertFalse(relay.should_proxy_cli(["relay", "agent-service"]))
            self.assertFalse(relay.should_proxy_cli(["hook"]))
            self.assertTrue(relay.should_proxy_cli(["statusline"]))

    def test_local_attach_uses_remote_default_control_socket(self):
        launched = {}

        class FakeProcess:
            stdout = []
            stderr = []

            def __init__(self):
                self.stdin = mock.Mock()
                self.stdin.close = mock.Mock()

            def wait(self):
                return 0

        def fake_popen(cmd, **kwargs):
            launched["cmd"] = cmd
            return FakeProcess()

        with mock.patch("subprocess.Popen", side_effect=fake_popen):
            code = relay.run_local_attach("dev@example.com")

        self.assertEqual(code, 0)
        remote_command = launched["cmd"][-1]
        self.assertIn("~/.cc-jukebox/run/agent-control.sock", remote_command)
        self.assertNotIn(str(Path.home()), remote_command)

    def test_install_settings_can_write_relay_environment(self):
        settings = install_settings.merge(
            {},
            "python3",
            "/remote/repo",
            relay_socket="/home/dev/.cc-jukebox/run/agent-request.sock",
        )

        server = settings["mcpServers"]["cc-jukebox"]
        self.assertEqual(server["type"], "http")
        self.assertEqual(server["url"], install_settings.DEFAULT_MCP_URL)
        self.assertIn(relay.RELAY_SOCKET_ENV, settings["statusLine"]["command"])
        hook_command = settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        self.assertIn(relay.RELAY_SOCKET_ENV, hook_command)

    def test_install_settings_defaults_to_http_mcp_server(self):
        settings = install_settings.merge({}, "python3", "/remote/repo")

        server = settings["mcpServers"]["cc-jukebox"]
        self.assertEqual(server, {
            "type": "http",
            "url": install_settings.DEFAULT_MCP_URL,
        })

    def test_install_settings_can_write_http_mcp_server(self):
        settings = install_settings.merge(
            {},
            "python3",
            "/remote/repo",
            mcp_url="http://127.0.0.1:8765/mcp",
        )

        server = settings["mcpServers"]["cc-jukebox"]
        self.assertEqual(server, {
            "type": "http",
            "url": "http://127.0.0.1:8765/mcp",
        })

    def test_agent_service_round_trips_through_stdio_attach(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            request_socket = Path(tmpdir) / "request.sock"
            control_socket = Path(tmpdir) / "control.sock"
            service = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "cc_jukebox",
                    "relay",
                    "agent-service",
                    "--request-socket",
                    str(request_socket),
                    "--control-socket",
                    str(control_socket),
                    "--timeout",
                    "10",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            attach = None
            try:
                for _ in range(100):
                    if request_socket.exists() and control_socket.exists():
                        break
                    if service.poll() is not None:
                        self.fail(service.stderr.read() if service.stderr else "relay service exited")
                    time.sleep(0.02)

                attach = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "cc_jukebox",
                        "relay",
                        "agent-attach",
                        "--control-socket",
                        str(control_socket),
                    ],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                )

                def local_executor():
                    assert attach is not None
                    assert attach.stdout is not None
                    assert attach.stdin is not None
                    for line in attach.stdout:
                        request = json.loads(line)
                        response = relay.execute_local_request(request)
                        attach.stdin.write(json.dumps(response) + "\n")
                        attach.stdin.flush()

                threading.Thread(target=local_executor, daemon=True).start()
                time.sleep(0.2)

                with mock.patch.dict(os.environ, {relay.RELAY_SOCKET_ENV: str(request_socket)}, clear=False):
                    response = relay.send_request({
                        "id": "round-trip",
                        "kind": "cli",
                        "argv": ["banner"],
                        "stdin": "",
                    })

                self.assertTrue(response["ok"], response)
                self.assertIn("pixel companion", response["stdout"])
            finally:
                for process in (attach, service):
                    if process is not None and process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            process.kill()
                    if process is not None:
                        for stream in (process.stdin, process.stdout, process.stderr):
                            if stream is not None and not stream.closed:
                                stream.close()


if __name__ == "__main__":
    unittest.main()
