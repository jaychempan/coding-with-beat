"""Session orchestration for desktop pet music recommendations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from coding_with_beat import state as state_mod

from .bubble import PetBubbleCard, PetBubbleView
from .dj_brain import DjIntent, PetDjBrain
from .music import PetMusicClient


@dataclass(frozen=True)
class PetSessionResult:
    ok: bool
    action: str
    card: PetBubbleCard


class PetMusicSession:
    def __init__(
        self,
        music: PetMusicClient | None = None,
        brain: PetDjBrain | None = None,
        bubble: PetBubbleView | None = None,
        load_state: Callable[[], object] = state_mod.load,
    ) -> None:
        self.music = music or PetMusicClient()
        self.brain = brain or PetDjBrain()
        self.bubble = bubble or PetBubbleView()
        self.load_state = load_state
        self.current_intent: DjIntent | None = None
        self.reroll_count = 0

    def recommend_from_context(self) -> PetSessionResult:
        self.current_intent = self.brain.intent_from_state(self.load_state())
        self.reroll_count = 0
        return self._recommend_current()

    def recommend_from_text(self, text: str) -> PetSessionResult:
        st = self.load_state()
        self.current_intent = self.brain.intent_from_text(text, st)
        self.reroll_count = 0
        return self._recommend_current()

    def reroll(self) -> PetSessionResult:
        if self.current_intent is None:
            self.current_intent = self.brain.intent_from_state(self.load_state())
            self.reroll_count = 0
        else:
            self.reroll_count += 1
        return self._recommend_current()

    def play_number(self, number: int) -> PetSessionResult:
        result = self.music.play_number(number)
        if not result.ok:
            card = self.bubble.error("播放失败", result.text)
            return PetSessionResult(False, "sad", card)
        card = self.bubble.confirmation("已开播", result.text, action="dance")
        return PetSessionResult(True, "dance", card)

    def auto_play_from_context(self) -> PetSessionResult:
        recommendation = self.recommend_from_context()
        if not recommendation.ok:
            return recommendation

        result = self.music.play_number(1)
        if not result.ok:
            card = self.bubble.error("自动开播失败", result.text)
            return PetSessionResult(False, "sad", card)

        title = self.current_intent.title if self.current_intent is not None else ""
        card = self.bubble.confirmation(f"已按 {title} 开播", result.text, action="dance")
        return PetSessionResult(True, "dance", card)

    def now_playing(self) -> PetSessionResult:
        result = self.music.now_playing()
        if not result.ok:
            card = self.bubble.error("当前播放读取失败", result.text)
            return PetSessionResult(False, "sad", card)
        card = self.bubble.status("当前播放", result.text)
        return PetSessionResult(True, card.action, card)

    def _recommend_current(self) -> PetSessionResult:
        if self.current_intent is None:
            self.current_intent = self.brain.intent_from_state(self.load_state())

        query_set = self.brain.queries_for_intent(self.current_intent, self.reroll_count)
        result = self.music.recommend(query_set.queries)
        if not result.ok:
            card = self.bubble.error("推荐失败", result.text)
            return PetSessionResult(False, "sad", card)

        card = self.bubble.recommendations(query_set.title, query_set.message, result.text)
        if card.kind == "empty":
            return PetSessionResult(False, card.action, card)
        return PetSessionResult(True, card.action, card)
