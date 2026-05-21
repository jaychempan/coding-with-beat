import json
import time
import unittest
from types import SimpleNamespace
from unittest import mock

from cc_jukebox import state, statusline


class StatuslineLyricsTest(unittest.TestCase):
    def _focus_off(self):
        return SimpleNamespace(active=False, phase="off", remaining=0, elapsed=0, cycle=0)

    def test_render_uses_whole_lyrics_from_mcp_snapshot(self):
        st = state.JukeboxState()
        payload = {
            "source": "apple_music",
            "title": "Song",
            "artist": "Artist",
            "album": "Album",
            "duration": 100.0,
            "position": 42.0,
            "playing": True,
            "artwork_path": "",
            "lyrics_key": "apple_music\0Artist\0Album\0Song",
            "lyrics_text": "[00:00.00]first line\n[00:40.00]snapshot lyric\n",
            "lyrics_pending": False,
            "unsupported_reason": "",
        }

        with (
            mock.patch.object(statusline.state, "load", return_value=st),
            mock.patch.object(statusline.state, "save"),
            mock.patch.object(statusline.focus, "status", return_value=self._focus_off()),
            mock.patch.object(statusline, "call_tool", return_value=json.dumps(payload)) as call_tool,
        ):
            rendered = statusline.render(term_width=120)

        call_tool.assert_called_once_with("now_playing_snapshot", {"known_lyrics_key": ""})
        self.assertIn("snapshot lyric", rendered)
        self.assertEqual(st.track.lyrics_key, "apple_music\0Artist\0Album\0Song")
        self.assertIn("snapshot lyric", st.track.lyrics_text)

    def test_render_calculates_line_from_saved_whole_lyrics_between_mcp_refreshes(self):
        st = state.JukeboxState()
        st.source = "apple_music"
        st.playing = True
        st.track.title = "Song"
        st.track.artist = "Artist"
        st.track.album = "Album"
        st.track.duration = 100.0
        st.track.position = 42.0
        st.track.position_sampled_at = time.time()
        st.track.source = "apple_music"
        st.track.lyrics_key = "apple_music\0Artist\0Album\0Song"
        st.track.lyrics_text = "[00:00.00]first line\n[00:40.00]saved lyric\n"

        with (
            mock.patch.object(statusline.state, "load", return_value=st),
            mock.patch.object(statusline.focus, "status", return_value=self._focus_off()),
            mock.patch.object(statusline, "call_tool") as call_tool,
        ):
            rendered = statusline.render(term_width=120)

        call_tool.assert_not_called()
        self.assertIn("saved lyric", rendered)

    def test_refresh_does_not_redownload_known_whole_lyrics(self):
        st = state.JukeboxState()
        st.track.lyrics_key = "apple_music\0Artist\0Album\0Song"
        st.track.lyrics_text = "[00:00.00]first line\n"
        payload = {
            "source": "apple_music",
            "title": "Song",
            "artist": "Artist",
            "album": "Album",
            "duration": 100.0,
            "position": 1.0,
            "playing": True,
            "artwork_path": "",
            "lyrics_key": "apple_music\0Artist\0Album\0Song",
            "lyrics_text": "",
            "lyrics_pending": False,
            "unsupported_reason": "",
        }

        with (
            mock.patch.object(statusline.state, "load", return_value=st),
            mock.patch.object(statusline.state, "save"),
            mock.patch.object(statusline.focus, "status", return_value=self._focus_off()),
            mock.patch.object(statusline, "call_tool", return_value=json.dumps(payload)) as call_tool,
        ):
            rendered = statusline.render(term_width=120)

        call_tool.assert_called_once_with(
            "now_playing_snapshot",
            {"known_lyrics_key": "apple_music\0Artist\0Album\0Song"},
        )
        self.assertIn("first line", rendered)


if __name__ == "__main__":
    unittest.main()
