import unittest
from types import SimpleNamespace
from unittest import mock

from coding_with_beat import lyrics_snapshot
from coding_with_beat import server


class ServerLyricsSnapshotTest(unittest.TestCase):
    def tearDown(self):
        lyrics_snapshot._PREFETCHING.clear()
        lyrics_snapshot._ATTEMPTED_AT.clear()

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

    def test_failed_prefetch_retries_after_ttl(self):
        class ImmediateThread:
            def __init__(self, target, **_kwargs):
                self.target = target

            def start(self):
                self.target()

        source = SimpleNamespace(lyrics=lambda: None)
        with (
            mock.patch.object(lyrics_snapshot.threading, "Thread", ImmediateThread),
            mock.patch("coding_with_beat.sources.get_source", return_value=source),
            mock.patch.object(lyrics_snapshot, "_read_cached", return_value=""),
        ):
            self.assertTrue(lyrics_snapshot._prefetch_once("apple_music", "Artist", "Album", "Song"))
            self.assertFalse(lyrics_snapshot._prefetch_once("apple_music", "Artist", "Album", "Song"))

            with mock.patch.object(lyrics_snapshot, "_PREFETCH_RETRY_AFTER", 0):
                self.assertTrue(lyrics_snapshot._prefetch_once("apple_music", "Artist", "Album", "Song"))


class ServerPlaybackMessageTest(unittest.TestCase):
    def test_play_song_reports_preview_without_claiming_now_playing(self):
        source = SimpleNamespace(
            play_query=lambda _query: SimpleNamespace(
                title="牧马城市",
                artist="毛不易",
                source="apple_music",
                unsupported_reason="preview_playing",
            )
        )

        with (
            mock.patch.object(server.state, "load", return_value=SimpleNamespace(source="apple_music")),
            mock.patch.object(server, "get_source", return_value=source),
        ):
            text = server.play_song("牧马城市 毛不易")

        self.assertIn("30s preview", text)
        self.assertIn("牧马城市", text)
        self.assertNotIn("now playing", text)


if __name__ == "__main__":
    unittest.main()
