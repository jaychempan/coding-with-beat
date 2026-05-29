"""Controller logic connecting desktop pet state, UI events, and music."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from coding_with_beat import state as state_mod

from .animator import PetAnimator
from .mood import queries_for_mood
from .music import MusicResult, PetMusicClient
from .sprites import BUILTIN_SKINS


def action_for_state(st, now: float | None = None) -> str:
    current = time.time() if now is None else now
    if getattr(st, "companion_failure_streak", 0) >= 3:
        return "panic"
    mood = getattr(st, "dj_mood", "") or ""
    if mood == "victory":
        return "happy"
    if mood == "panic":
        return "panic"
    if mood == "sad":
        return "sad"
    if getattr(st, "playing", False):
        return "dance"
    last_tool_at = float(getattr(st, "last_tool_at", 0.0) or 0.0)
    if last_tool_at and current - last_tool_at > 1800:
        return "sleep"
    vibe = getattr(st, "vibe", "") or ""
    if vibe in {"debug", "review"}:
        return "think"
    return "idle"


@dataclass
class PetController:
    animator: PetAnimator = field(default_factory=PetAnimator)
    music: PetMusicClient = field(default_factory=PetMusicClient)
    load_state: Callable[[], object] = state_mod.load
    last_results: str = ""
    ambient_actions: tuple[str, ...] = ("idle", "walk", "think", "happy")
    ambient_index: int = 0

    def refresh_action(self) -> str:
        action = action_for_state(self.load_state())
        self.animator.set_action(action)
        return action

    def next_ambient_action(self) -> str:
        action = self.ambient_actions[self.ambient_index % len(self.ambient_actions)]
        self.ambient_index += 1
        return action

    def current_track_label(self) -> str:
        st = self.load_state()
        track = getattr(st, "track", None)
        title = (getattr(track, "title", "") or "").strip()
        artist = (getattr(track, "artist", "") or "").strip()
        if not title and not artist:
            return "未播放"
        marker = "▶" if getattr(st, "playing", False) else "▷"
        if title and artist:
            return f"{marker} {title} — {artist}"
        return f"{marker} {title or artist}"

    def cycle_skin(self) -> str:
        skin_ids = list(BUILTIN_SKINS)
        current = self.animator.skin.id
        try:
            idx = skin_ids.index(current)
        except ValueError:
            idx = 0
        next_skin = skin_ids[(idx + 1) % len(skin_ids)]
        self.animator.set_skin(next_skin)
        return next_skin

    def handle_mood_text(self, text: str) -> MusicResult:
        self.animator.set_action("think")
        result = self.music.recommend(queries_for_mood(text))
        if result.ok:
            self.last_results = result.text
            self.animator.set_action("recommend")
        else:
            self.animator.set_action("sad")
        return result

    def play_number(self, number: int) -> MusicResult:
        result = self.music.play_number(number)
        self.animator.set_action("dance" if result.ok else "sad")
        return result
