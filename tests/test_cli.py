import contextlib
import io
import sys
import unittest
from unittest import mock

from cc_jukebox import __main__ as cli
from cc_jukebox.sources.base import unsupported_now_playing


class CliUnsupportedReadbackTest(unittest.TestCase):
    def test_control_command_succeeds_when_only_now_playing_readback_is_unsupported(self):
        np = unsupported_now_playing(
            "qq_music",
            "qq_music cannot read the QQMusic desktop client's current track/state.",
        )
        out = io.StringIO()

        with contextlib.redirect_stdout(out):
            code = cli._print_control_result("play", "qq_music", np)

        self.assertEqual(code, 0)
        self.assertIn("play sent", out.getvalue())
        self.assertIn("now-playing unsupported", out.getvalue())

    def test_now_playing_request_still_fails_when_source_cannot_report_status(self):
        np = unsupported_now_playing(
            "qq_music",
            "qq_music cannot read the QQMusic desktop client's current track/state.",
        )
        out = io.StringIO()

        with contextlib.redirect_stdout(out):
            code = cli._print_np(np)

        self.assertEqual(code, 2)
        self.assertIn("unsupported", out.getvalue())
        self.assertIn("feature=now_playing", out.getvalue())

    def test_server_command_configures_streamable_http_server(self):
        from cc_jukebox.server import mcp

        old_host = mcp.settings.host
        old_port = mcp.settings.port
        old_path = mcp.settings.streamable_http_path
        old_stateless = mcp.settings.stateless_http
        old_log_level = mcp.settings.log_level
        try:
            with (
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        "cc-jukebox",
                        "server",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        "8765",
                        "--path",
                        "mcp",
                        "--stateless",
                        "--log-level",
                        "warning",
                    ],
                ),
                mock.patch.object(mcp, "run") as run,
            ):
                code = cli.cmd_server()

            self.assertEqual(code, 0)
            self.assertEqual(mcp.settings.host, "127.0.0.1")
            self.assertEqual(mcp.settings.port, 8765)
            self.assertEqual(mcp.settings.streamable_http_path, "/mcp")
            self.assertTrue(mcp.settings.stateless_http)
            self.assertEqual(mcp.settings.log_level, "WARNING")
            run.assert_called_once_with(transport="streamable-http")
        finally:
            mcp.settings.host = old_host
            mcp.settings.port = old_port
            mcp.settings.streamable_http_path = old_path
            mcp.settings.stateless_http = old_stateless
            mcp.settings.log_level = old_log_level


if __name__ == "__main__":
    unittest.main()
