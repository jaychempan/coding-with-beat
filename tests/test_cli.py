import contextlib
import io
import sys
import unittest
from unittest import mock

from coding_with_beat import __main__ as cli
from coding_with_beat import mcp_client


class CliCommandTest(unittest.TestCase):
    def test_server_command_configures_streamable_http_server(self):
        from coding_with_beat.server import mcp

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
                        "cwb",
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

    def test_music_cli_commands_call_http_mcp_tools(self):
        cases = [
            (["np"], "now_playing", {}),
            (["play"], "play", {}),
            (["play", "稻香", "周杰伦"], "play_song", {"query": "稻香 周杰伦"}),
            (["pause"], "pause", {}),
            (["next"], "next_track", {}),
            (["prev"], "prev_track", {}),
            (["like"], "like_current", {}),
            (["mode", "shuffle"], "set_play_mode", {"mode": "shuffle"}),
            (["mode", "随机"], "set_play_mode", {"mode": "shuffle"}),
            (["source"], "current_source", {}),
            (["source", "qq_music"], "set_source", {"name": "qq_music"}),
            (["volume", "70"], "set_volume", {"percent": 70}),
            (["seek", "1:30"], "seek", {"seconds": 90.0}),
            (["cover"], "show_cover", {"style": "rgb", "width": 40, "height": 20}),
            (["cover", "gameboy"], "show_cover", {"style": "gameboy", "width": 40, "height": 20}),
            (["lyrics"], "show_lyrics", {"window": 7}),
            (["lyrics", "5"], "show_lyrics", {"window": 5}),
            (["player"], "show_player", {"width": 40, "with_lyrics": True}),
            (["status"], "status", {}),
            (["banner"], "banner", {}),
        ]

        for argv, tool, kwargs in cases:
            with self.subTest(argv=argv):
                out = io.StringIO()
                with (
                    mock.patch.object(sys, "argv", ["cwb", *argv]),
                    mock.patch.object(mcp_client, "call_tool", return_value="ok") as call_tool,
                    contextlib.redirect_stdout(out),
                ):
                    code = cli.main()

                self.assertEqual(code, 0)
                call_tool.assert_called_once_with(tool, kwargs)
                self.assertEqual(out.getvalue(), "ok\n")

    def test_music_cli_mcp_errors_do_not_fallback_to_local_source(self):
        err = mcp_client.MCPClientError("server unavailable")
        out = io.StringIO()
        stderr = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["cwb", "next"]),
            mock.patch.object(mcp_client, "call_tool", side_effect=err) as call_tool,
            contextlib.redirect_stdout(out),
            contextlib.redirect_stderr(stderr),
        ):
            code = cli.main()

        self.assertEqual(code, 1)
        call_tool.assert_called_once_with("next_track", {})
        self.assertEqual(out.getvalue(), "")
        self.assertIn("server unavailable", stderr.getvalue())

    def test_music_cli_treats_needs_library_message_as_error(self):
        output = (
            'Found "孤勇者 — 陈奕迅" in the Apple Music catalog, but full playback did not start.\n'
            "Opened the Music.app search page. Add the track to your library, then try again."
        )
        out = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["cwb", "play", "1"]),
            mock.patch.object(mcp_client, "call_tool", return_value=output) as call_tool,
            contextlib.redirect_stdout(out),
        ):
            code = cli.main()

        self.assertEqual(code, 1)
        call_tool.assert_called_once_with("play_number", {"number": 1})
        self.assertEqual(out.getvalue(), output + "\n")


if __name__ == "__main__":
    unittest.main()
