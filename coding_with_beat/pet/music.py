"""Music-control wrapper used by the desktop pet UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from coding_with_beat.mcp_client import call_tool as _call_tool

ToolCaller = Callable[[str, dict], str]


@dataclass(frozen=True)
class MusicResult:
    ok: bool
    text: str


class PetMusicClient:
    def __init__(self, call_tool: ToolCaller | None = None) -> None:
        self._call_tool = call_tool or _call_tool

    def recommend(self, queries: list[str]) -> MusicResult:
        return self._call("smart_search", {"queries": queries})

    def play_number(self, number: int) -> MusicResult:
        return self._call("play_number", {"number": number})

    def now_playing(self) -> MusicResult:
        return self._call("now_playing", {})

    def toggle(self) -> MusicResult:
        return self._call("toggle", {})

    def next_track(self) -> MusicResult:
        return self._call("next_track", {})

    def _call(self, name: str, kwargs: dict) -> MusicResult:
        try:
            return MusicResult(True, self._call_tool(name, kwargs))
        except Exception as e:
            return MusicResult(False, str(e))
