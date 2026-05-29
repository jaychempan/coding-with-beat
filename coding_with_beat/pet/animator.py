"""Frame animation state for the desktop pet."""

from __future__ import annotations

from dataclasses import dataclass

from .sprites import ACTIONS, Frame, get_skin


@dataclass
class PetAnimator:
    skin_id: str = "dj"
    action: str = "idle"
    frame_index: int = 0

    def __post_init__(self) -> None:
        self.skin = get_skin(self.skin_id)
        if self.action not in ACTIONS:
            self.action = "idle"

    def set_skin(self, skin_id: str) -> None:
        self.skin = get_skin(skin_id)
        self.skin_id = self.skin.id
        self.frame_index = 0

    def set_action(self, action: str) -> None:
        next_action = action if action in ACTIONS else "idle"
        if next_action != self.action:
            self.action = next_action
            self.frame_index = 0

    def tick(self) -> Frame:
        frames = self.skin.actions[self.action]
        self.frame_index = (self.frame_index + 1) % len(frames)
        return self.current_frame()

    def current_frame(self) -> Frame:
        frames = self.skin.actions[self.action]
        return frames[self.frame_index % len(frames)]
