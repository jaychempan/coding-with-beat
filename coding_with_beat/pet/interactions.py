"""Gesture and quick-action routing for the desktop pet."""

from __future__ import annotations

from .bubble import PetBubbleView
from .session import PetMusicSession, PetSessionResult


class PetInteractionController:
    def __init__(
        self,
        session: PetMusicSession | None = None,
        bubble: PetBubbleView | None = None,
    ) -> None:
        self.session = session if session is not None else PetMusicSession()
        self.bubble = bubble if bubble is not None else PetBubbleView()

    def single_click(self) -> PetSessionResult:
        return self.session.now_playing()

    def double_click(self) -> PetSessionResult:
        return self.session.recommend_from_context()

    def long_press(self) -> PetSessionResult:
        return self.session.auto_play_from_context()

    def quick_action(self, action: str) -> PetSessionResult:
        if action == "now":
            return self.session.now_playing()
        if action == "recommend":
            return self.session.recommend_from_context()
        if action == "reroll":
            return self.session.reroll()
        return PetSessionResult(False, "sad", self.bubble.error("未知动作", action))
