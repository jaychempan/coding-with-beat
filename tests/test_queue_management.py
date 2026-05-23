import json
import pathlib
import shutil
import tempfile
import unittest
from unittest import mock

import coding_with_beat.server as srv


def _make_tmp():
    return pathlib.Path(tempfile.mkdtemp())


class TestQueueFile(unittest.TestCase):
    def setUp(self):
        self.tmp = _make_tmp()
        self.patch = mock.patch.object(srv, "DATA_DIR", self.tmp)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_load_queue_file_returns_empty_when_missing(self):
        result = srv._load_queue_file("library")
        self.assertEqual(result, {"tracks": [], "index": 0, "expected_title": ""})

    def test_load_queue_file_returns_empty_when_missing_search(self):
        result = srv._load_queue_file("search")
        self.assertEqual(result, {"tracks": [], "index": 0, "expected_title": ""})

    def test_write_and_load_queue_file_roundtrip(self):
        data = {"tracks": [{"title": "Song A"}], "index": 0, "expected_title": "Song A"}
        srv._write_queue_file("library", data)
        result = srv._load_queue_file("library")
        self.assertEqual(result, data)

    def test_library_and_search_queues_are_independent(self):
        lib = {"tracks": [{"title": "Lib Song"}], "index": 0, "expected_title": ""}
        srch = {"tracks": [{"title": "Search Song"}], "index": 0, "expected_title": ""}
        srv._write_queue_file("library", lib)
        srv._write_queue_file("search", srch)
        self.assertEqual(srv._load_queue_file("library")["tracks"][0]["title"], "Lib Song")
        self.assertEqual(srv._load_queue_file("search")["tracks"][0]["title"], "Search Song")


class TestActiveMode(unittest.TestCase):
    def setUp(self):
        self.tmp = _make_tmp()
        self.patch = mock.patch.object(srv, "DATA_DIR", self.tmp)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_read_active_mode_defaults_to_library(self):
        result = srv._read_active_mode()
        self.assertEqual(result, {"mode": "library", "context": "library"})

    def test_write_active_mode_sets_mode(self):
        srv._write_active_mode(mode="search")
        result = srv._read_active_mode()
        self.assertEqual(result["mode"], "search")
        self.assertEqual(result["context"], "library")  # context unchanged

    def test_write_active_mode_sets_context(self):
        srv._write_active_mode(context="search")
        result = srv._read_active_mode()
        self.assertEqual(result["context"], "search")
        self.assertEqual(result["mode"], "library")  # mode unchanged

    def test_write_active_mode_sets_both(self):
        srv._write_active_mode(mode="search", context="search")
        result = srv._read_active_mode()
        self.assertEqual(result, {"mode": "search", "context": "search"})


class TestListLibraryWritesQueue(unittest.TestCase):
    def setUp(self):
        self.tmp = _make_tmp()
        self.p_data = mock.patch.object(srv, "DATA_DIR", self.tmp)
        self.p_data.start()

    def tearDown(self):
        self.p_data.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_list_library_writes_library_queue_json(self):
        fake_tracks = [{"title": "A", "artist": "X", "album": "Y"}]

        class FakeSrc:
            name = "apple_music"
            def list_library(self, limit=100):
                return fake_tracks

        with (
            mock.patch.object(srv, "get_source", return_value=FakeSrc()),
            mock.patch.object(srv.state, "load", return_value=srv.state.JukeboxState()),
        ):
            srv.list_library(limit=1)

        data = srv._load_queue_file("library")
        self.assertEqual(data["tracks"], fake_tracks)
        self.assertEqual(data["index"], 0)
        self.assertEqual(srv._read_active_mode()["context"], "library")

    def test_list_library_does_not_touch_search_queue(self):
        search_data = {"tracks": [{"title": "S"}], "index": 2, "expected_title": "S"}
        srv._write_queue_file("search", search_data)

        class FakeSrc:
            name = "apple_music"
            def list_library(self, limit=100):
                return [{"title": "L", "artist": "", "album": ""}]

        with (
            mock.patch.object(srv, "get_source", return_value=FakeSrc()),
            mock.patch.object(srv.state, "load", return_value=srv.state.JukeboxState()),
        ):
            srv.list_library()

        self.assertEqual(srv._load_queue_file("search"), search_data)


class TestSearchWritesQueue(unittest.TestCase):
    def setUp(self):
        self.tmp = _make_tmp()
        self.p_data = mock.patch.object(srv, "DATA_DIR", self.tmp)
        self.p_data.start()

    def tearDown(self):
        self.p_data.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_search_writes_search_queue_json(self):
        fake_hits = [{"title": "Hit", "artist": "B", "album": "C", "source": "library"}]

        class FakeSrc:
            def search(self, query, limit=8):
                return fake_hits

        with (
            mock.patch.object(srv, "get_source", return_value=FakeSrc()),
            mock.patch.object(srv.state, "load", return_value=srv.state.JukeboxState()),
        ):
            srv.search("hit")

        data = srv._load_queue_file("search")
        self.assertEqual(data["tracks"], fake_hits)
        self.assertEqual(srv._read_active_mode()["context"], "search")

    def test_search_does_not_touch_library_queue(self):
        lib_data = {"tracks": [{"title": "L"}], "index": 5, "expected_title": "L"}
        srv._write_queue_file("library", lib_data)

        class FakeSrc:
            def search(self, query, limit=8):
                return [{"title": "S", "artist": "", "album": ""}]

        with (
            mock.patch.object(srv, "get_source", return_value=FakeSrc()),
            mock.patch.object(srv.state, "load", return_value=srv.state.JukeboxState()),
        ):
            srv.search("s")

        self.assertEqual(srv._load_queue_file("library"), lib_data)

    def test_search_does_not_change_active_mode(self):
        srv._write_active_mode(mode="library")

        class FakeSrc:
            def search(self, query, limit=8):
                return [{"title": "S", "artist": "", "album": ""}]

        with (
            mock.patch.object(srv, "get_source", return_value=FakeSrc()),
            mock.patch.object(srv.state, "load", return_value=srv.state.JukeboxState()),
        ):
            srv.search("s")

        self.assertEqual(srv._read_active_mode()["mode"], "library")


class TestPlayNumber(unittest.TestCase):
    def setUp(self):
        self.tmp = _make_tmp()
        self.p_data = mock.patch.object(srv, "DATA_DIR", self.tmp)
        self.p_data.start()

    def tearDown(self):
        self.p_data.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _fake_np(self, title="Song A", artist="Art"):
        from coding_with_beat.sources.base import NowPlaying
        np = NowPlaying()
        np.title = title
        np.artist = artist
        np.album = "Alb"
        np.duration = 200.0
        np.position = 0.0
        np.playing = True
        np.source = "apple_music"
        return np

    def test_play_number_reads_from_context_queue(self):
        """play_number uses context (search) not library when context=search."""
        lib_tracks = [{"title": "Lib Song", "artist": "L"}]
        srch_tracks = [{"title": "Search Song", "artist": "S"}]
        srv._write_queue_file("library", {"tracks": lib_tracks, "index": 0, "expected_title": ""})
        srv._write_queue_file("search", {"tracks": srch_tracks, "index": 0, "expected_title": ""})
        srv._write_active_mode(context="search")

        played_queries = []

        class FakeSrc:
            def play_query(self, query):
                played_queries.append(query)
                from coding_with_beat.sources.base import NowPlaying
                np = NowPlaying()
                np.title = "Search Song"; np.artist = "S"; np.album = ""
                np.duration = 200.0; np.position = 0.0; np.playing = True
                np.source = "apple_music"
                return np

        from coding_with_beat.sources.base import NowPlaying as _NP
        _rnp_np = _NP()
        _rnp_np.title = "Search Song"; _rnp_np.artist = "S"; _rnp_np.album = ""
        _rnp_np.duration = 200.0; _rnp_np.position = 0.0; _rnp_np.playing = True
        _rnp_np.source = "apple_music"

        with (
            mock.patch.object(srv, "get_source", return_value=FakeSrc()),
            mock.patch.object(srv.state, "load", return_value=srv.state.JukeboxState()),
            mock.patch.object(srv, "_refresh_now_playing", return_value=(srv.state.JukeboxState(), _rnp_np)),
        ):
            result = srv.play_number(1)

        self.assertIn("Search Song", result)
        self.assertIn("Search Song", played_queries[0])

    def test_play_number_sets_mode_to_context(self):
        srch_tracks = [{"title": "S", "artist": "A"}]
        srv._write_queue_file("search", {"tracks": srch_tracks, "index": 0, "expected_title": ""})
        srv._write_active_mode(context="search", mode="library")

        class FakeSrc:
            def play_query(self, query):
                from coding_with_beat.sources.base import NowPlaying
                np = NowPlaying()
                np.title = "S"; np.artist = "A"; np.album = ""
                np.duration = 200.0; np.position = 0.0; np.playing = True
                np.source = "apple_music"
                return np

        with (
            mock.patch.object(srv, "get_source", return_value=FakeSrc()),
            mock.patch.object(srv.state, "load", return_value=srv.state.JukeboxState()),
            mock.patch.object(srv, "_refresh_now_playing", return_value=(srv.state.JukeboxState(), FakeSrc().play_query(""))),
        ):
            srv.play_number(1)

        self.assertEqual(srv._read_active_mode()["mode"], "search")

    def test_play_number_writes_expected_title_to_queue(self):
        srch_tracks = [{"title": "MySong", "artist": "Art"}]
        srv._write_queue_file("search", {"tracks": srch_tracks, "index": 0, "expected_title": ""})
        srv._write_active_mode(context="search")

        class FakeSrc:
            def play_query(self, query):
                from coding_with_beat.sources.base import NowPlaying
                np = NowPlaying()
                np.title = "MySong"; np.artist = "Art"; np.album = ""
                np.duration = 200.0; np.position = 0.0; np.playing = True
                np.source = "apple_music"
                return np

        with (
            mock.patch.object(srv, "get_source", return_value=FakeSrc()),
            mock.patch.object(srv.state, "load", return_value=srv.state.JukeboxState()),
            mock.patch.object(srv, "_refresh_now_playing", return_value=(srv.state.JukeboxState(), FakeSrc().play_query(""))),
        ):
            srv.play_number(1)

        data = srv._load_queue_file("search")
        self.assertEqual(data["expected_title"], "MySong")
        self.assertEqual(data["index"], 0)


class TestNextPrev(unittest.TestCase):
    def setUp(self):
        self.tmp = _make_tmp()
        self.p_data = mock.patch.object(srv, "DATA_DIR", self.tmp)
        self.p_data.start()

    def tearDown(self):
        self.p_data.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _fake_play_queue_at(self, calls):
        def _fake(idx, queue_name=None):
            calls.append((idx, queue_name))
            return f"[{idx+1}] played"
        return _fake

    def test_next_track_advances_search_queue(self):
        tracks = [{"title": f"S{i}", "artist": ""} for i in range(3)]
        srv._write_queue_file("search", {"tracks": tracks, "index": 0, "expected_title": "S0"})
        srv._write_active_mode(mode="search")

        calls = []
        with mock.patch.object(srv, "_play_queue_at", side_effect=self._fake_play_queue_at(calls)):
            result = srv.next_track()

        self.assertEqual(calls[0], (1, "search"))
        self.assertIn("next", result)

    def test_next_track_falls_back_to_library_when_search_exhausted(self):
        srch_tracks = [{"title": "S0", "artist": ""}]
        lib_tracks = [{"title": "L0", "artist": ""}, {"title": "L1", "artist": ""}]
        srv._write_queue_file("search", {"tracks": srch_tracks, "index": 0, "expected_title": "S0"})
        srv._write_queue_file("library", {"tracks": lib_tracks, "index": 1, "expected_title": "L1"})
        srv._write_active_mode(mode="search")

        calls = []
        with mock.patch.object(srv, "_play_queue_at", side_effect=self._fake_play_queue_at(calls)):
            result = srv.next_track()

        # Should fall back to library at its current index
        self.assertEqual(calls[0][1], "library")
        self.assertIn("library", result)

    def test_prev_track_goes_back_in_active_queue(self):
        tracks = [{"title": f"S{i}", "artist": ""} for i in range(3)]
        srv._write_queue_file("library", {"tracks": tracks, "index": 2, "expected_title": "S2"})
        srv._write_active_mode(mode="library")

        calls = []
        with mock.patch.object(srv, "_play_queue_at", side_effect=self._fake_play_queue_at(calls)):
            result = srv.prev_track()

        self.assertEqual(calls[0], (1, "library"))

    def test_next_track_clears_one_off_file(self):
        srv._one_off_file().write_text("{}")
        tracks = [{"title": "S0", "artist": ""}, {"title": "S1", "artist": ""}]
        srv._write_queue_file("library", {"tracks": tracks, "index": 0, "expected_title": "S0"})
        srv._write_active_mode(mode="library")

        with mock.patch.object(srv, "_play_queue_at", return_value="ok"):
            srv.next_track()

        self.assertFalse(srv._one_off_file().exists())


class TestPlaySongAndResume(unittest.TestCase):
    def setUp(self):
        self.tmp = _make_tmp()
        self.p_data = mock.patch.object(srv, "DATA_DIR", self.tmp)
        self.p_data.start()

    def tearDown(self):
        self.p_data.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_np(self, title, playing=True):
        from coding_with_beat.sources.base import NowPlaying
        np = NowPlaying()
        np.title = title; np.artist = "A"; np.album = "B"
        np.duration = 200.0; np.position = 0.0
        np.playing = playing; np.source = "apple_music"
        return np

    def test_play_song_saves_resume_mode_to_one_off_file(self):
        """play_song with active search queue saves resume_mode=search."""
        srch = {"tracks": [{"title": "S0", "artist": ""}], "index": 0, "expected_title": "S0"}
        srv._write_queue_file("search", srch)
        srv._write_active_mode(mode="search")

        class FakeSrc:
            def play_query(self, q):
                from coding_with_beat.sources.base import NowPlaying
                np = NowPlaying()
                np.title = "One Off"; np.artist = ""; np.album = ""; np.duration = 180.0
                np.position = 0.0; np.playing = True; np.source = "apple_music"
                return np

        with (
            mock.patch.object(srv, "get_source", return_value=FakeSrc()),
            mock.patch.object(srv.state, "load", return_value=srv.state.JukeboxState()),
            mock.patch.object(srv, "_refresh_now_playing", return_value=(srv.state.JukeboxState(), FakeSrc().play_query(""))),
        ):
            srv.play_song("One Off")

        data = json.loads(srv._one_off_file().read_text())
        self.assertEqual(data["resume_mode"], "search")
        self.assertEqual(data["one_off_title"], "One Off")

    def test_maybe_resume_queue_uses_resume_mode(self):
        """_maybe_resume_queue resumes the correct queue when title changes."""
        srch = {"tracks": [{"title": "S0", "artist": ""}, {"title": "S1", "artist": ""}],
                "index": 0, "expected_title": "S0"}
        srv._write_queue_file("search", srch)

        srv._one_off_file().write_text(json.dumps({
            "one_off_title": "One Off",
            "resume_mode": "search",
            "resume_index": 1,
        }))

        played = []
        with mock.patch.object(srv, "_play_queue_at", side_effect=lambda idx, qn=None: played.append((idx, qn))):
            srv._maybe_resume_queue(self._make_np("S1"))  # title changed from one-off

        self.assertEqual(played[0], (1, "search"))
        self.assertFalse(srv._one_off_file().exists())

    def test_maybe_resume_queue_does_nothing_when_still_on_one_off(self):
        srv._one_off_file().write_text(json.dumps({
            "one_off_title": "One Off",
            "resume_mode": "library",
            "resume_index": 2,
        }))
        played = []
        with mock.patch.object(srv, "_play_queue_at", side_effect=lambda idx, qn=None: played.append((idx, qn))):
            srv._maybe_resume_queue(self._make_np("One Off"))  # same title

        self.assertEqual(played, [])
        self.assertTrue(srv._one_off_file().exists())


class TestAutoAdvance(unittest.TestCase):
    def setUp(self):
        self.tmp = _make_tmp()
        self.p_data = mock.patch.object(srv, "DATA_DIR", self.tmp)
        self.p_data.start()
        # Reset module-level state tracker between tests
        srv._np_state.update({"title": "", "position": 0.0, "duration": 0.0})

    def tearDown(self):
        self.p_data.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_np(self, title, position=0.0, duration=200.0, playing=True):
        from coding_with_beat.sources.base import NowPlaying
        np = NowPlaying()
        np.title = title; np.artist = "A"; np.album = "B"
        np.duration = duration; np.position = position
        np.playing = playing; np.source = "apple_music"
        return np

    def test_auto_advance_triggers_on_natural_end(self):
        """Title change after position near duration → advance queue."""
        tracks = [{"title": "S0", "artist": ""}, {"title": "S1", "artist": ""}]
        srv._write_queue_file("library", {"tracks": tracks, "index": 0, "expected_title": "S0"})
        srv._write_active_mode(mode="library")

        # Simulate previous snapshot: S0 at 198s / 200s (near end)
        srv._np_state.update({"title": "S0", "position": 198.0, "duration": 200.0})

        played = []
        with mock.patch.object(srv, "_play_queue_at", side_effect=lambda idx, qn=None: played.append((idx, qn))):
            srv._auto_advance_if_needed(self._make_np("S1", position=0.0, duration=200.0))

        self.assertEqual(played[0], (1, "library"))

    def test_auto_advance_does_not_trigger_on_external_switch(self):
        """Title change when position was mid-song → external switch, no advance."""
        tracks = [{"title": "S0", "artist": ""}, {"title": "S1", "artist": ""}]
        srv._write_queue_file("library", {"tracks": tracks, "index": 0, "expected_title": "S0"})
        srv._write_active_mode(mode="library")

        # Previous snapshot: S0 at 60s / 200s (mid-song)
        srv._np_state.update({"title": "S0", "position": 60.0, "duration": 200.0})

        played = []
        with mock.patch.object(srv, "_play_queue_at", side_effect=lambda idx, qn=None: played.append((idx, qn))):
            srv._auto_advance_if_needed(self._make_np("External Song"))

        self.assertEqual(played, [])

    def test_auto_advance_does_not_trigger_when_title_unchanged(self):
        srv._np_state.update({"title": "S0", "position": 198.0, "duration": 200.0})
        played = []
        with mock.patch.object(srv, "_play_queue_at", side_effect=lambda idx, qn=None: played.append((idx, qn))):
            srv._auto_advance_if_needed(self._make_np("S0"))
        self.assertEqual(played, [])

    def test_auto_advance_falls_back_to_library_when_search_exhausted(self):
        srch = [{"title": "S0", "artist": ""}]
        lib = [{"title": "L0", "artist": ""}, {"title": "L1", "artist": ""}]
        srv._write_queue_file("search", {"tracks": srch, "index": 0, "expected_title": "S0"})
        srv._write_queue_file("library", {"tracks": lib, "index": 1, "expected_title": "L1"})
        srv._write_active_mode(mode="search")

        srv._np_state.update({"title": "S0", "position": 198.0, "duration": 200.0})

        played = []
        with mock.patch.object(srv, "_play_queue_at", side_effect=lambda idx, qn=None: played.append((idx, qn))):
            srv._auto_advance_if_needed(self._make_np("something new"))

        # Should fall back to library at its saved index
        self.assertEqual(played[0][1], "library")
        self.assertEqual(srv._read_active_mode()["mode"], "library")

    def test_auto_advance_skips_when_one_off_active(self):
        srv._one_off_file().write_text(json.dumps({"one_off_title": "OO", "resume_mode": "library", "resume_index": 0}))
        srv._np_state.update({"title": "OO", "position": 198.0, "duration": 200.0})

        played = []
        with mock.patch.object(srv, "_play_queue_at", side_effect=lambda idx, qn=None: played.append((idx, qn))):
            srv._auto_advance_if_needed(self._make_np("Next Song"))

        self.assertEqual(played, [])

    def test_auto_advance_only_fires_for_cwb_managed_tracks(self):
        """If expected_title doesn't match prev title, it's not a cwb track."""
        tracks = [{"title": "CWB Song", "artist": ""}]
        srv._write_queue_file("library", {"tracks": tracks, "index": 0, "expected_title": "CWB Song"})
        srv._write_active_mode(mode="library")

        # Previous track was something else (not cwb-managed)
        srv._np_state.update({"title": "External Track", "position": 198.0, "duration": 200.0})

        played = []
        with mock.patch.object(srv, "_play_queue_at", side_effect=lambda idx, qn=None: played.append((idx, qn))):
            srv._auto_advance_if_needed(self._make_np("Another External"))

        self.assertEqual(played, [])
