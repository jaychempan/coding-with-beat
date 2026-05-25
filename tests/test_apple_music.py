import unittest
from unittest import mock

from coding_with_beat.sources import apple_music as am
from coding_with_beat.sources.apple_music import AppleMusic
from coding_with_beat.sources.base import NowPlaying
from coding_with_beat.sources.local import LocalFiles


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


class AppleMusicPlayQueryTest(unittest.TestCase):
    def test_copied_search_row_is_parsed_for_catalog_and_matching(self):
        query = "1. 小小 — 容祖儿 · 小小 [Apple Music]"

        self.assertEqual(am._catalog_search_query(query), "小小 容祖儿")
        self.assertTrue(am._track_matches("小小", "容祖儿", query=query))
        self.assertFalse(am._track_matches("我怀念的", "孙燕姿", query=query))

    def test_catalog_target_accepts_localized_artist_from_query(self):
        self.assertTrue(
            am._track_matches_target(
                "小小",
                "容祖儿",
                "小小",
                "Joey Yung",
                "小小 容祖儿",
            )
        )
        self.assertFalse(
            am._track_matches_target(
                "我怀念的",
                "孙燕姿",
                "小小",
                "Joey Yung",
                "小小 容祖儿",
            )
        )

    def test_play_query_uses_display_query_for_catalog_search(self):
        music = AppleMusic()
        catalog_hit = NowPlaying(
            title="小小",
            artist="容祖儿",
            source="apple_music",
            playing=True,
        )

        with (
            mock.patch.object(am, "_play_local_match", return_value=False),
            mock.patch.object(am, "_play_local_tokens", return_value=False),
            mock.patch.object(am, "_play_catalog", return_value=catalog_hit) as play_catalog,
            mock.patch.object(
                music,
                "now_playing",
                return_value=NowPlaying(
                    title="我怀念的",
                    artist="孙燕姿",
                    source="apple_music",
                    playing=True,
                ),
            ),
            mock.patch("time.sleep", return_value=None),
        ):
            result = music.play_query("小小 — 容祖儿 · 小小")

        self.assertEqual(result, catalog_hit)
        play_catalog.assert_called_once_with("小小 容祖儿")

    def test_play_query_does_not_accept_unmatched_current_track(self):
        music = AppleMusic()

        with (
            mock.patch.object(am, "_play_local_match", return_value=True),
            mock.patch.object(am, "_play_catalog", return_value=None) as play_catalog,
            mock.patch.object(
                music,
                "now_playing",
                return_value=NowPlaying(
                    title="我怀念的",
                    artist="孙燕姿",
                    source="apple_music",
                    playing=True,
                ),
            ),
            mock.patch("time.sleep", return_value=None),
        ):
            result = music.play_query("小小")

        self.assertIsNone(result)
        play_catalog.assert_called_once_with("小小")


class AppleMusicLovedSearchTest(unittest.TestCase):
    def test_search_marks_loved_tracks(self):
        """search() sets source='loved' for loved tracks, 'library' for others."""
        SEP = "\x1f"
        raw = f"Loved Song{SEP}Artist A{SEP}Album X{SEP}true\nNormal Song{SEP}Artist B{SEP}Album Y{SEP}false\n"
        with mock.patch.object(am, "_osa", return_value=raw):
            with mock.patch.object(am, "_search_catalog_api", return_value=[]):
                results = AppleMusic().search("song", limit=8)
        loved = next(r for r in results if r["title"] == "Loved Song")
        normal = next(r for r in results if r["title"] == "Normal Song")
        self.assertEqual(loved["source"], "loved")
        self.assertEqual(normal["source"], "library")


class AppleMusicListLovedTest(unittest.TestCase):
    def test_list_loved_returns_loved_tracks(self):
        SEP = "\x1f"
        raw = f"Heart Song{SEP}DJ A{SEP}Vol 1\nFave Track{SEP}DJ B{SEP}Vol 2\n"
        with mock.patch.object(am, "_osa", return_value=raw):
            results = AppleMusic().list_loved(limit=10)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["title"], "Heart Song")
        self.assertEqual(results[0]["source"], "loved")

    def test_list_loved_returns_empty_on_error(self):
        with mock.patch.object(am, "_osa", side_effect=RuntimeError("no music")):
            results = AppleMusic().list_loved()
        self.assertEqual(results, [])


class AppleMusicSearchLovedTest(unittest.TestCase):
    def test_search_loved_returns_matching_loved_tracks(self):
        SEP = "\x1f"
        raw = f"Rain Song{SEP}Piano Artist{SEP}Calm Album\n"
        with mock.patch.object(am, "_osa", return_value=raw) as mock_osa:
            results = AppleMusic().search_loved("rain", limit=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Rain Song")
        self.assertEqual(results[0]["source"], "loved")
        # Verify AppleScript filtered by loved=true
        script = mock_osa.call_args[0][0]
        self.assertIn("favorited is true", script)

    def test_search_loved_returns_empty_on_no_match(self):
        with mock.patch.object(am, "_osa", return_value=""):
            results = AppleMusic().search_loved("xyz", limit=5)
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
