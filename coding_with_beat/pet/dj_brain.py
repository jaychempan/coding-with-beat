"""Context-aware DJ intent selection for the desktop pet."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from .mood import queries_for_mood


@dataclass(frozen=True)
class DjIntent:
    name: str
    title: str
    message: str
    pet_action: str
    queries: list[str] | None = None


@dataclass(frozen=True)
class DjQuerySet:
    intent: DjIntent
    title: str
    message: str
    queries: list[str]


class PetDjBrain:
    def __init__(self, now: Callable[[], float] | None = None) -> None:
        self._now = now or time.time

    def intent_from_text(self, text: str, st: object | None = None) -> DjIntent:
        clean = (text or "").strip()
        title = clean[:18] or "想听点什么"
        return DjIntent(
            name="free_text",
            title=title,
            message=f"按你的心情找：{title}",
            pet_action="think",
            queries=queries_for_mood(clean),
        )

    def intent_from_state(self, st: object) -> DjIntent:
        if getattr(st, "companion_failure_streak", 0) >= 3 or getattr(st, "dj_mood", "") == "panic":
            return DjIntent("panic_recover", "缓一下", "刚才有点乱，先找点稳住节奏的。", "panic")
        if getattr(st, "dj_mood", "") == "victory":
            return DjIntent("victory_boost", "庆祝一下", "这波很顺，来点亮一点的。", "happy")
        if getattr(st, "playing", False):
            return DjIntent("playing_companion", "继续这个感觉", "基于当前播放，找相近或下一段氛围。", "dance")
        last_tool_at = float(getattr(st, "last_tool_at", 0.0) or 0.0)
        if last_tool_at and self._now() - last_tool_at > 1800:
            return DjIntent("late_idle", "慢慢回来", "空了一会儿，来点轻松回到状态。", "sleep")
        vibe = getattr(st, "vibe", "") or ""
        if vibe in {"debug", "review", "focus"}:
            return DjIntent("debug_focus", "Debug flow", "给你找低干扰的专注音乐。", "think")
        return DjIntent("debug_focus", "Debug flow", "给你找低干扰的专注音乐。", "think")

    def queries_for_intent(self, intent: DjIntent, reroll: int = 0) -> DjQuerySet:
        if intent.queries is not None:
            return DjQuerySet(intent, intent.title, intent.message, list(intent.queries))
        sets = _QUERY_SETS[intent.name]
        queries = sets[reroll % len(sets)]
        return DjQuerySet(intent, intent.title, intent.message, list(queries))


_QUERY_SETS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "debug_focus": (
        (
            "deep focus ambient instrumental no vocals",
            "flow state drone minimal electronic",
            "study music concentration piano quiet",
        ),
        (
            "lofi hip hop late night coding chill",
            "calm electronic coding focus",
            "jazz study background mellow",
        ),
    ),
    "victory_boost": (
        (
            "victory feel good indie pop",
            "celebration upbeat bright positive",
            "happy dance pop fresh energy",
        ),
        (
            "morning energy upbeat pop indie fresh",
            "funky groove celebration coding win",
            "upbeat electronic bright success",
        ),
    ),
    "panic_recover": (
        (
            "calming ambient reset no vocals",
            "soft piano breathe stress relief",
            "relaxing downtempo chill evening unwind",
        ),
        (
            "minimal electronic calm focus recovery",
            "warm acoustic gentle calm soft",
            "rainy lofi decompress coding",
        ),
    ),
    "late_idle": (
        (
            "relaxing downtempo chill evening unwind",
            "nature ambient breeze afternoon easy listening",
            "soft acoustic gentle calm",
        ),
        (
            "lofi rain cafe cozy return to work",
            "quiet piano focus gentle",
            "ambient study music soft restart",
        ),
    ),
    "playing_companion": (
        (
            "similar vibe current track coding",
            "fresh adjacent music flow state",
            "next song same mood energetic enough",
        ),
        (
            "discover similar artist coding background",
            "related indie electronic focus",
            "same mood playlist smooth transition",
        ),
    ),
}
