"""Built-in pixel skins for the desktop pet."""

from __future__ import annotations

from dataclasses import dataclass

ACTIONS = ("idle", "walk", "dance", "think", "recommend", "happy", "sad", "panic", "sleep")


@dataclass(frozen=True)
class Frame:
    action: str
    pixels: tuple[str, ...]
    duration_ms: int = 220


@dataclass(frozen=True)
class Skin:
    id: str
    name: str
    palette: dict[str, str]
    actions: dict[str, tuple[Frame, ...]]


_PALETTES: dict[str, dict[str, str]] = {
    "dj": {"K": "#20232a", "H": "#f4d7b5", "J": "#2f80ed", "A": "#f2994a", "N": "#f2c94c"},
    "programmer": {"K": "#1f2933", "H": "#f0c7a4", "J": "#27ae60", "A": "#8d6e63", "N": "#9b51e0"},
    "sleepwear": {"K": "#4b5563", "H": "#f2d2b6", "J": "#9bdbff", "A": "#f7b2d9", "N": "#fff1a8"},
    "cyber": {"K": "#111827", "H": "#d1f7ff", "J": "#00d1ff", "A": "#ff2bd6", "N": "#b8ff2c"},
    "chinese": {"K": "#2d1b1b", "H": "#f2c6a0", "J": "#d94235", "A": "#f2c94c", "N": "#7ac7a7"},
}

_NAMES = {
    "dj": "DJ Buddy",
    "programmer": "Programmer Buddy",
    "sleepwear": "Sleepy Buddy",
    "cyber": "Cyber Buddy",
    "chinese": "Guofeng Buddy",
}

_ACCENTS = {
    "dj": ("NN", "AN"),
    "programmer": ("KK", "AK"),
    "sleepwear": ("AA", "NA"),
    "cyber": ("NA", "AN"),
    "chinese": ("AN", "JN"),
}


def _body(face: str, arms: str, legs: str, accent: str) -> tuple[str, ...]:
    left_arm, right_arm = arms[0], arms[1]
    left_leg, right_leg = legs[0], legs[1]
    return (
        "............",
        f"...{accent}KKKK{accent}...",
        "..KHHHHHHK..",
        f"..KH{face}HK..",
        "..KHHHHHHK..",
        "...KJJJJK...",
        f"..{left_arm}KJJJJK{right_arm}..",
        "...KJJJJK...",
        f"...{left_leg}K..K{right_leg}...",
        "..KK....KK..",
        "............",
        "............",
    )


_POSES: dict[str, tuple[tuple[str, ...], ...]] = {
    "idle": (_body("oo", "HH", "HH", "NN"), _body("--", "HH", "HH", "NN")),
    "walk": (_body("oo", "HA", "AH", "NN"), _body("oo", "AH", "HA", "NN")),
    "dance": (_body("^^", "AA", "HA", "NN"), _body("^^", "AA", "AH", "NN"), _body("~~", "HA", "AA", "NN")),
    "think": (_body("o?", "HH", "HH", "AN"), _body("o?", "HA", "HH", "AN")),
    "recommend": (_body("^^", "AA", "HH", "NA"), _body("oo", "AA", "HH", "NA")),
    "happy": (_body("^^", "AA", "AH", "NN"), _body("^^", "AA", "HA", "NN")),
    "sad": (_body("tt", "HH", "HH", "AN"),),
    "panic": (_body("!!", "AA", "AA", "NA"), _body("!!", "AH", "HA", "NA")),
    "sleep": (_body("--", "HH", "HH", "AA"), _body("zz", "HH", "HH", "AA")),
}


def _skin_actions(skin_id: str) -> dict[str, tuple[Frame, ...]]:
    accent_a, accent_b = _ACCENTS[skin_id]
    actions: dict[str, tuple[Frame, ...]] = {}
    for action, poses in _POSES.items():
        frames: list[Frame] = []
        for idx, pose in enumerate(poses):
            accent = accent_a if idx % 2 == 0 else accent_b
            pixels = tuple(line.replace("N", accent[0]).replace("A", accent[1]) for line in pose)
            frames.append(Frame(action=action, pixels=pixels))
        actions[action] = tuple(frames)
    return actions


BUILTIN_SKINS: dict[str, Skin] = {
    skin_id: Skin(id=skin_id, name=_NAMES[skin_id], palette=_PALETTES[skin_id], actions=_skin_actions(skin_id))
    for skin_id in ("dj", "programmer", "sleepwear", "cyber", "chinese")
}


def get_skin(skin_id: str) -> Skin:
    return BUILTIN_SKINS.get(skin_id, BUILTIN_SKINS["dj"])
