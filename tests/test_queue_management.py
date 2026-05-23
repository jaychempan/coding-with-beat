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
