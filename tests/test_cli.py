import contextlib
import io
import unittest

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


if __name__ == "__main__":
    unittest.main()
