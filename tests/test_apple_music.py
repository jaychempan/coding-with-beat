import unittest
from unittest import mock

from coding_with_beat.sources.apple_music import AppleMusic
from coding_with_beat.sources.local import LocalFiles
from coding_with_beat.sources import apple_music as am


class AppleMusicControlsTest(unittest.TestCase):
    def test_like_current_favorites_current_track(self):
        scripts = []

        def capture(script):
            scripts.append(script)
            return "ok"

        with mock.patch.object(am, "_osa", side_effect=capture):
            self.assertTrue(AppleMusic().like_current())

        self.assertIn("set favorited of current track to true", scripts[-1])

    def test_like_current_returns_false_on_applescript_failure(self):
        with mock.patch.object(am, "_osa", side_effect=RuntimeError("no track")):
            self.assertFalse(AppleMusic().like_current())

    def test_set_play_mode_shuffle(self):
        scripts = []

        def capture(script):
            scripts.append(script)
            return "ok"

        with mock.patch.object(am, "_osa", side_effect=capture):
            self.assertTrue(AppleMusic().set_play_mode("shuffle"))

        self.assertIn("set shuffle enabled to true", scripts[-1])
        self.assertIn("set song repeat to off", scripts[-1])

    def test_set_play_mode_sequential(self):
        scripts = []

        def capture(script):
            scripts.append(script)
            return "ok"

        with mock.patch.object(am, "_osa", side_effect=capture):
            self.assertTrue(AppleMusic().set_play_mode("sequential"))

        self.assertIn("set shuffle enabled to false", scripts[-1])
        self.assertIn("set song repeat to off", scripts[-1])

    def test_set_play_mode_repeat_all_and_repeat_one(self):
        scripts = []

        def capture(script):
            scripts.append(script)
            return "ok"

        with mock.patch.object(am, "_osa", side_effect=capture):
            self.assertTrue(AppleMusic().set_play_mode("repeat"))
            self.assertTrue(AppleMusic().set_play_mode("repeat_one"))

        self.assertIn("set song repeat to all", scripts[0])
        self.assertIn("set song repeat to one", scripts[1])

    def test_set_play_mode_unsupported_raises_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            AppleMusic().set_play_mode("party")

    def test_local_source_explicitly_does_not_support_like_or_modes(self):
        local = LocalFiles()
        with self.assertRaises(NotImplementedError):
            local.like_current()
        with self.assertRaises(NotImplementedError):
            local.set_play_mode("shuffle")


if __name__ == "__main__":
    unittest.main()
