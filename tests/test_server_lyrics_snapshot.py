import unittest
from types import SimpleNamespace
from unittest import mock

from cc_jukebox import lyrics_snapshot
from cc_jukebox import server


class ServerLyricsSnapshotTest(unittest.TestCase):
    def _state(self):
        return SimpleNamespace(source="apple_music")

    def _now_playing(self):
        return SimpleNamespace(
            source="apple_music",
            title="Song",
            artist="Artist",
            album="Album",
            duration=20.0,
            position=10.0,
            playing=True,
            artwork_path="",
        )

    def test_snapshot_returns_whole_lyrics_when_cache_is_available(self):
        with mock.patch.object(server, "current_lyrics_text", return_value=("first\nsecond\n", False)) as lyrics_text:
            payload = server._now_playing_payload(self._state(), self._now_playing())

        self.assertEqual(payload["lyrics_key"], "apple_music\0Artist\0Album\0Song")
        self.assertEqual(payload["lyrics_text"], "first\nsecond\n")
        self.assertFalse(payload["lyrics_pending"])
        lyrics_text.assert_called_once_with("apple_music", "Artist", "Album", "Song")

    def test_snapshot_omits_whole_lyrics_when_client_already_has_them(self):
        key = "apple_music\0Artist\0Album\0Song"
        with mock.patch.object(server, "current_lyrics_text", return_value=("first\nsecond\n", False)):
            payload = server._now_playing_payload(self._state(), self._now_playing(), known_lyrics_key=key)

        self.assertEqual(payload["lyrics_key"], key)
        self.assertEqual(payload["lyrics_text"], "")

    def test_snapshot_prefetches_when_lyrics_cache_is_missing(self):
        with mock.patch.object(server, "current_lyrics_text", return_value=("", True)):
            payload = server._now_playing_payload(self._state(), self._now_playing())

        self.assertEqual(payload["lyrics_text"], "")
        self.assertTrue(payload["lyrics_pending"])

    def test_plain_lyrics_are_interpolated_by_position(self):
        text = "one\ntwo\nthree\n"

        self.assertEqual(lyrics_snapshot.line_from_text(text, position=10.0, duration=20.0), "two")

    def test_lrc_lyrics_use_latest_cue(self):
        text = "[00:00.00]one\n[00:09.50]two\n"

        self.assertEqual(lyrics_snapshot.line_from_text(text, position=10.0, duration=20.0), "two")


if __name__ == "__main__":
    unittest.main()
