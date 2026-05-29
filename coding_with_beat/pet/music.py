"""Music-control wrapper used by the desktop pet UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from coding_with_beat.mcp_client import call_tool as _call_tool

ToolCaller = Callable[..., str]

DEFAULT_PET_MUSIC_TIMEOUT = 20.0
SNAPSHOT_TIMEOUT = 1.5


@dataclass(frozen=True)
class MusicResult:
    ok: bool
    text: str


class PetMusicClient:
    def __init__(self, call_tool: ToolCaller | None = None, timeout: float = DEFAULT_PET_MUSIC_TIMEOUT) -> None:
        self._call_tool = call_tool or _call_tool
        self.timeout = timeout

    def recommend(self, queries: list[str]) -> MusicResult:
        return self._call("smart_search", {"queries": queries})

    def search(self, query: str) -> MusicResult:
        return self._call("search", {"query": query})

    def list_library(self, limit: int = 40) -> MusicResult:
        return self._call("list_library", {"limit": limit})

    def list_loved(self, limit: int = 40) -> MusicResult:
        return self._call("list_loved", {"limit": limit})

    def search_loved(self, query: str) -> MusicResult:
        return self._call("search_loved", {"query": query})

    def list_playlists(self) -> MusicResult:
        return self._call("list_playlists", {})

    def play_playlist(self, name: str) -> MusicResult:
        return self._call("play_playlist", {"name": name})

    def play_number(self, number: int) -> MusicResult:
        return self._call("play_number", {"number": number})

    def now_playing(self) -> MusicResult:
        return self._call("now_playing", {})

    def now_playing_snapshot(self, known_lyrics_key: str = "") -> MusicResult:
        return self._call(
            "now_playing_snapshot",
            {"known_lyrics_key": known_lyrics_key},
            timeout=SNAPSHOT_TIMEOUT,
        )

    def control(self, tool: str, kwargs: dict) -> MusicResult:
        return self._call(tool, kwargs)

    def toggle(self) -> MusicResult:
        return self._call("toggle", {})

    def next_track(self) -> MusicResult:
        return self._call("next_track", {})

    def _call(self, name: str, kwargs: dict, timeout: float | None = None) -> MusicResult:
        try:
            return MusicResult(True, _call_with_timeout(self._call_tool, name, kwargs, timeout or self.timeout))
        except Exception as e:
            return MusicResult(False, str(e))


def _call_with_timeout(call_tool: ToolCaller, name: str, kwargs: dict[str, Any], timeout: float) -> str:
    try:
        return call_tool(name, kwargs, timeout=timeout)
    except TypeError as e:
        if "timeout" not in str(e):
            raise
        return call_tool(name, kwargs)
