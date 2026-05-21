import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from coding_with_beat.sources import local as local_source
from coding_with_beat.sources import qq_music as qm
from coding_with_beat.sources.base import NowPlaying


class FakeResponse:
    def __init__(self, json_data=None, content=b"", status_code=200):
        self._json_data = json_data or {}
        self.content = content
        self.status_code = status_code

    def json(self):
        return self._json_data


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def get(self, url, params=None):
        self.requests.append((url, params or {}))
        if not self.responses:
            raise AssertionError("unexpected HTTP call")
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class QQMusicTest(unittest.TestCase):
    def isolated_paths(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        patches = [
            mock.patch.object(qm, "QQ_STATE", root / "qq_music.json"),
            mock.patch.object(qm, "PREVIEW_FILE", root / "qq_preview.m4a"),
            mock.patch.object(qm, "LYRICS_CACHE", root / "lyrics"),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        (root / "lyrics").mkdir()
        self.addCleanup(tmp.cleanup)
        return root

    def test_query_variants_split_combo_queries(self):
        self.assertEqual(
            qm._query_variants("稻香 周杰伦"),
            ["稻香 周杰伦", "稻香", "周杰伦"],
        )
        self.assertEqual(qm._query_variants("稻香"), ["稻香"])

    def test_decode_qq_lyric_decodes_base64_and_preserves_plain_text(self):
        encoded = base64.b64encode("第一行\n第二行".encode()).decode()
        self.assertEqual(qm._decode_qq_lyric(encoded), "第一行\n第二行")
        self.assertEqual(qm._decode_qq_lyric("[ti:稻香]\n[ar:周杰伦]"), "[ti:稻香]\n[ar:周杰伦]")

    def test_api_search_once_normalizes_legacy_payload(self):
        source = qm.QQMusic()
        source._client = FakeClient([
            FakeResponse({
                "data": {
                    "song": {
                        "list": [{
                            "songname": "稻香",
                            "singer": [{"name": "周杰伦"}],
                            "albumname": "魔杰座",
                            "songmid": "003aAYrm3GE0Ac",
                            "strMediaMid": "0020wJDo3cx0j3",
                            "albummid": "002Neh8l0uciQZ",
                            "interval": 223,
                        }]
                    }
                }
            })
        ])

        hits = source._api_search_once("稻香", limit=3, new_json=False)

        self.assertEqual(hits, [{
            "title": "稻香",
            "artist": "周杰伦",
            "album": "魔杰座",
            "mid": "003aAYrm3GE0Ac",
            "media_mid": "0020wJDo3cx0j3",
            "albummid": "002Neh8l0uciQZ",
            "duration": 223.0,
            "url": "https://y.qq.com/n/ryqq/songDetail/003aAYrm3GE0Ac",
        }])

    def test_api_search_normalization_tolerates_bad_duration_values(self):
        source = qm.QQMusic()
        hit = source._normalize_hit({
            "songname": "坏时长",
            "singer": [],
            "songmid": "mid",
            "interval": "not-a-number",
        })

        self.assertEqual(hit["duration"], 0.0)

    def test_api_search_falls_back_and_ranks_by_all_query_tokens(self):
        source = qm.QQMusic()

        def fake_search_once(query, limit, *, new_json):
            if query == "稻香" and not new_json:
                return [
                    {"title": "稻香", "artist": "周杰伦", "album": "魔杰座", "mid": "jay"},
                    {"title": "稻香", "artist": "白允y", "album": "稻香", "mid": "other"},
                ]
            return []

        with mock.patch.object(source, "_api_search_once", side_effect=fake_search_once):
            hits = source.search("稻香 周杰伦", limit=2)

        self.assertEqual([h["mid"] for h in hits], ["jay", "other"])

    def test_play_query_returns_metadata_only_when_preview_is_not_audio(self):
        self.isolated_paths()

        class MetadataOnlyQQ(qm.QQMusic):
            def _api_search(self, query, limit):
                return [{
                    "title": "稻香",
                    "artist": "周杰伦",
                    "album": "魔杰座",
                    "mid": "songmid",
                    "media_mid": "mediamid",
                    "albummid": "albummid",
                    "duration": 223.0,
                }]

            def _download_cover(self, url, key):
                return "/tmp/cover.jpg"

            def _start(self, path):
                raise AssertionError("invalid preview should not be started")

        source = MetadataOnlyQQ()
        source._client = FakeClient([FakeResponse(content=b'{"error":"no playable preview"}')])

        np = source.play_query("稻香 周杰伦")

        self.assertEqual(np.title, "")
        self.assertFalse(np.playing)
        self.assertIn("cannot ask the QQMusic desktop", np.unsupported_reason)
        saved = json.loads(qm.QQ_STATE.read_text())
        self.assertEqual(saved["mode"], "metadata_only")
        self.assertEqual(saved["track"]["artist"], "周杰伦")

    def test_play_query_starts_valid_preview_and_marks_local_state_as_qq(self):
        self.isolated_paths()
        writes = []

        class PreviewQQ(qm.QQMusic):
            def _api_search(self, query, limit):
                return [{
                    "title": "稻香",
                    "artist": "周杰伦",
                    "album": "魔杰座",
                    "mid": "songmid",
                    "media_mid": "mediamid",
                    "albummid": "albummid",
                    "duration": 223.0,
                }]

            def _download_cover(self, url, key):
                return "/tmp/cover.jpg"

            def _start(self, path):
                self.started_path = path
                return NowPlaying(duration=9.0, playing=True, source=self.name)

        source = PreviewQQ()
        source._client = FakeClient([FakeResponse(content=b"\x00\x00\x00\x18ftypM4A " + b"x" * 3000)])

        with mock.patch.object(qm, "_read", return_value={"pid": 123, "path": str(qm.PREVIEW_FILE)}), \
                mock.patch.object(qm, "_write", side_effect=writes.append):
            np = source.play_query("稻香 周杰伦")

        self.assertEqual(source.started_path, qm.PREVIEW_FILE)
        self.assertTrue(np.playing)
        self.assertEqual(np.duration, 9.0)
        self.assertEqual(writes[-1]["source"], "qq_music")

    def test_now_playing_ignores_unrelated_local_afplay_state(self):
        self.isolated_paths()
        qm._write_qq_state({
            "track": {
                "title": "稻香",
                "artist": "周杰伦",
                "album": "魔杰座",
                "duration": 223.0,
                "artwork": "/tmp/cover.jpg",
            },
            "mode": "metadata_only",
        })

        source = qm.QQMusic()
        with mock.patch.object(qm, "_read", return_value={
            "source": "local",
            "pid": 99,
            "path": "/tmp/unrelated.mp3",
            "started_at": 10.0,
        }), mock.patch.object(qm, "_pid_alive", return_value=True):
            np = source.now_playing()

        self.assertEqual(np.title, "")
        self.assertEqual(np.artist, "")
        self.assertFalse(np.playing)
        self.assertEqual(np.position, 0.0)
        self.assertIn("cannot read the QQMusic desktop", np.unsupported_reason)

    def test_now_playing_overlays_metadata_on_active_qq_preview(self):
        self.isolated_paths()
        qm._write_qq_state({
            "track": {
                "title": "稻香",
                "artist": "周杰伦",
                "album": "魔杰座",
                "duration": 223.0,
                "artwork": "/tmp/cover.jpg",
            },
            "mode": "preview",
        })

        source = qm.QQMusic()
        local_state = {
            "source": "qq_music",
            "pid": 99,
            "path": str(qm.PREVIEW_FILE),
            "started_at": 10.0,
            "paused_total": 0.0,
            "duration": 30.0,
        }
        with mock.patch.object(qm, "_read", return_value=local_state), \
                mock.patch.object(local_source, "_read", return_value=local_state), \
                mock.patch.object(local_source, "_pid_alive", return_value=True):
            np = source.now_playing()

        self.assertEqual(np.title, "稻香")
        self.assertEqual(np.artist, "周杰伦")
        self.assertTrue(np.playing)
        self.assertEqual(np.duration, 30.0)

    def test_lyrics_fetches_qq_lrc_and_uses_cache(self):
        self.isolated_paths()
        qm._write_qq_state({
            "track": {
                "title": "稻香",
                "artist": "周杰伦",
                "album": "魔杰座",
                "mid": "003aAYrm3GE0Ac",
            }
        })
        lyric = "[ti:稻香]\n[00:00.00]稻香 - 周杰伦"
        source = qm.QQMusic()
        source._client = FakeClient([
            FakeResponse({"lyric": base64.b64encode(lyric.encode()).decode()})
        ])

        self.assertEqual(source.lyrics(), lyric)

        source._client = FakeClient([AssertionError("cache should avoid HTTP")])
        self.assertEqual(source.lyrics(), lyric)

    def test_desktop_menu_uses_system_events_for_qqmusic_menu(self):
        source = qm.QQMusic()
        scripts = []

        def capture(script, timeout=8.0):
            scripts.append(script)
            return True

        with mock.patch.object(qm, "_run_osascript", side_effect=capture):
            self.assertTrue(source.like_current())

        self.assertIn('application id "com.tencent.QQMusicMac"', scripts[-1])
        self.assertIn('menu "播放控制"', scripts[-1])
        self.assertIn('menu item "喜欢歌曲"', scripts[-1])

    def test_set_volume_is_noop_at_current_hint_and_updates_only_on_success(self):
        self.isolated_paths()
        qm._write_qq_state({"volume_hint": 50})
        source = qm.QQMusic()

        with mock.patch.object(source, "_desktop_menu_item", return_value=True) as menu:
            source.set_volume(50)
        menu.assert_not_called()

        with mock.patch.object(source, "_desktop_menu_item", return_value=False) as menu:
            source.set_volume(70)
        self.assertEqual(menu.call_count, 2)
        self.assertEqual(json.loads(qm.QQ_STATE.read_text())["volume_hint"], 50)

        with mock.patch.object(source, "_desktop_menu_item", return_value=True) as menu:
            source.set_volume(70)
        self.assertEqual(menu.call_count, 2)
        self.assertEqual(json.loads(qm.QQ_STATE.read_text())["volume_hint"], 70)

    def test_set_play_mode_uses_unified_modes_and_raises_for_unknown_modes(self):
        source = qm.QQMusic()
        calls = []

        with mock.patch.object(source, "_desktop_play_mode", side_effect=lambda idx: calls.append(idx) or True), \
                mock.patch.object(source, "_desktop_menu_item", return_value=True):
            self.assertTrue(source.set_play_mode("shuffle"))
            self.assertTrue(source.set_play_mode("sequential"))
            self.assertTrue(source.set_play_mode("repeat"))
            self.assertTrue(source.set_play_mode("off"))

        self.assertEqual(calls, [1, 3, 2, 3])
        with self.assertRaises(NotImplementedError):
            source.set_play_mode("repeat_one")


if __name__ == "__main__":
    unittest.main()
