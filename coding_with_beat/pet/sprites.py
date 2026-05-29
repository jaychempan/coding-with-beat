"""Built-in pixel skins for the desktop pet."""

from __future__ import annotations

from dataclasses import dataclass

ACTIONS = ("idle", "walk", "dance", "think", "recommend", "happy", "sad", "panic", "sleep")
WIDTH = 18
HEIGHT = 18


@dataclass(frozen=True)
class Frame:
    action: str
    pixels: tuple[str, ...]
    duration_ms: int = 180


@dataclass(frozen=True)
class Skin:
    id: str
    name: str
    palette: dict[str, str]
    actions: dict[str, tuple[Frame, ...]]


_PALETTES: dict[str, dict[str, str]] = {
    "dj": {
        "K": "#1f2430",
        "H": "#f3c9a5",
        "J": "#2f80ed",
        "A": "#ffb545",
        "N": "#f2e85c",
        "W": "#fff7e6",
        "S": "#475569",
    },
    "programmer": {
        "K": "#20242d",
        "H": "#efc39f",
        "J": "#2fbf71",
        "A": "#b07a4f",
        "N": "#a66cff",
        "W": "#f8fbff",
        "S": "#4b5563",
    },
    "sleepwear": {
        "K": "#566070",
        "H": "#f1cdb3",
        "J": "#96d9ff",
        "A": "#f5a8d4",
        "N": "#fff0a6",
        "W": "#fff9f0",
        "S": "#9aa8b8",
    },
    "cyber": {
        "K": "#0f172a",
        "H": "#d6fbff",
        "J": "#00c8ff",
        "A": "#ff2bd6",
        "N": "#a6ff2d",
        "W": "#f3ffff",
        "S": "#334155",
    },
    "chinese": {
        "K": "#301c1c",
        "H": "#f0c29c",
        "J": "#d94235",
        "A": "#f0c94a",
        "N": "#72c7a1",
        "W": "#fff4df",
        "S": "#6b3f3f",
    },
}

_NAMES = {
    "dj": "DJ Buddy",
    "programmer": "Programmer Buddy",
    "sleepwear": "Sleepy Buddy",
    "cyber": "Cyber Buddy",
    "chinese": "Guofeng Buddy",
}

_ACTION_SPECS: dict[str, tuple[dict[str, object], ...]] = {
    "idle": (
        {"face": "open", "arms": "down", "legs": "stand", "prop": "idle", "dy": 0},
        {"face": "blink", "arms": "sway_r", "legs": "stand", "prop": "idle", "dy": 1},
        {"face": "open", "arms": "sway_l", "legs": "stand", "prop": "idle", "dy": 0},
    ),
    "walk": (
        {"face": "open", "arms": "swing_l", "legs": "step_l", "prop": "walk", "dx": -1},
        {"face": "open", "arms": "swing_r", "legs": "step_r", "prop": "walk", "dx": 1},
        {"face": "open", "arms": "swing_l", "legs": "step_l", "prop": "walk", "dx": -1, "dy": 1},
        {"face": "open", "arms": "swing_r", "legs": "step_r", "prop": "walk", "dx": 1, "dy": 0},
    ),
    "dance": (
        {"face": "happy", "arms": "up", "legs": "wide_l", "prop": "music", "dx": -1},
        {"face": "grin", "arms": "wide", "legs": "wide_r", "prop": "music", "dy": 1},
        {"face": "happy", "arms": "up_r", "legs": "kick_l", "prop": "music", "dx": 1},
        {"face": "grin", "arms": "wide", "legs": "kick_r", "prop": "music", "dy": -1},
    ),
    "think": (
        {"face": "think", "arms": "chin", "legs": "stand", "prop": "think"},
        {"face": "think", "arms": "chin_r", "legs": "stand", "prop": "think", "dy": 1},
        {"face": "blink", "arms": "chin", "legs": "stand", "prop": "think"},
    ),
    "recommend": (
        {"face": "happy", "arms": "present", "legs": "stand", "prop": "sign"},
        {"face": "open", "arms": "present_r", "legs": "step_r", "prop": "sign", "dx": 1},
        {"face": "happy", "arms": "up", "legs": "wide_l", "prop": "sign", "dy": -1},
    ),
    "happy": (
        {"face": "happy", "arms": "up", "legs": "wide_l", "prop": "spark"},
        {"face": "grin", "arms": "up_r", "legs": "wide_r", "prop": "spark", "dy": -2},
        {"face": "happy", "arms": "wide", "legs": "kick_r", "prop": "spark", "dx": 1},
    ),
    "sad": (
        {"face": "sad", "arms": "droop", "legs": "stand", "prop": "rain", "dy": 1},
        {"face": "sad", "arms": "droop_r", "legs": "stand", "prop": "rain", "dy": 2},
    ),
    "panic": (
        {"face": "panic", "arms": "up", "legs": "wide_l", "prop": "alert", "dx": -1},
        {"face": "panic", "arms": "wide", "legs": "wide_r", "prop": "alert", "dx": 1},
        {"face": "panic", "arms": "up_r", "legs": "kick_l", "prop": "alert", "dx": -2},
        {"face": "panic", "arms": "wide", "legs": "kick_r", "prop": "alert", "dx": 2},
    ),
    "sleep": (
        {"face": "sleep", "arms": "down", "legs": "stand", "prop": "sleep", "dy": 2},
        {"face": "sleep", "arms": "sway_l", "legs": "stand", "prop": "sleep", "dy": 3},
        {"face": "blink", "arms": "down", "legs": "stand", "prop": "sleep", "dy": 2},
    ),
}


def _blank() -> list[list[str]]:
    return [["." for _ in range(WIDTH)] for _ in range(HEIGHT)]


def _put(canvas: list[list[str]], x: int, y: int, color: str) -> None:
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        canvas[y][x] = color


def _rect(canvas: list[list[str]], x: int, y: int, width: int, height: int, color: str) -> None:
    for yy in range(y, y + height):
        for xx in range(x, x + width):
            _put(canvas, xx, yy, color)


def _outline_rect(canvas: list[list[str]], x: int, y: int, width: int, height: int, fill: str) -> None:
    _rect(canvas, x, y, width, height, "K")
    if width > 2 and height > 2:
        _rect(canvas, x + 1, y + 1, width - 2, height - 2, fill)


def _frame(skin_id: str, action: str, spec: dict[str, object]) -> Frame:
    canvas = _blank()
    dx = int(spec.get("dx", 0))
    dy = int(spec.get("dy", 0))
    _draw_shadow(canvas, dx)
    _draw_body(canvas, skin_id, dx, dy)
    _draw_head(canvas, skin_id, str(spec["face"]), dx, dy)
    _draw_arms(canvas, str(spec["arms"]), dx, dy)
    _draw_legs(canvas, str(spec["legs"]), dx, dy)
    _draw_skin_props(canvas, skin_id, str(spec["prop"]), dx, dy)
    return Frame(action=action, pixels=tuple("".join(row) for row in canvas))


def _draw_shadow(canvas: list[list[str]], dx: int) -> None:
    _rect(canvas, 5 + dx, 17, 8, 1, "S")


def _draw_head(canvas: list[list[str]], skin_id: str, face: str, dx: int, dy: int) -> None:
    x = 6 + dx
    y = 2 + dy
    _outline_rect(canvas, x, y, 6, 5, "H")
    if skin_id in {"programmer", "chinese"}:
        _rect(canvas, x, y, 6, 1, "K")
        _put(canvas, x - 1, y + 1, "K")
    if skin_id == "sleepwear":
        _rect(canvas, x + 2, y - 1, 5, 1, "A")
        _put(canvas, x + 7, y, "A")
        _put(canvas, x + 8, y + 1, "N")
    if skin_id == "dj":
        _rect(canvas, x - 1, y - 1, 8, 1, "N")
        _rect(canvas, x - 2, y + 1, 2, 3, "K")
        _rect(canvas, x + 6, y + 1, 2, 3, "K")
        _put(canvas, x - 2, y + 2, "N")
        _put(canvas, x + 7, y + 2, "N")
    if skin_id == "cyber":
        _rect(canvas, x, y + 2, 6, 1, "A")
        _put(canvas, x + 2, y - 1, "N")
        _put(canvas, x + 3, y - 2, "N")
    if skin_id == "chinese":
        _put(canvas, x + 6, y, "A")
        _put(canvas, x + 7, y + 1, "N")

    _draw_face(canvas, x, y, face, skin_id)


def _draw_face(canvas: list[list[str]], x: int, y: int, face: str, skin_id: str) -> None:
    if face == "blink":
        _put(canvas, x + 2, y + 2, "K")
        _put(canvas, x + 4, y + 2, "K")
    elif face == "happy":
        _put(canvas, x + 2, y + 2, "W")
        _put(canvas, x + 4, y + 2, "W")
        _put(canvas, x + 3, y + 3, "K")
    elif face == "grin":
        _put(canvas, x + 2, y + 2, "W")
        _put(canvas, x + 4, y + 2, "W")
        _rect(canvas, x + 2, y + 3, 3, 1, "K")
    elif face == "think":
        _put(canvas, x + 2, y + 2, "W")
        _put(canvas, x + 4, y + 2, "K")
        _put(canvas, x + 4, y + 1, "N")
    elif face == "sad":
        _put(canvas, x + 2, y + 2, "K")
        _put(canvas, x + 4, y + 2, "K")
        _rect(canvas, x + 2, y + 4, 3, 1, "K")
        _put(canvas, x + 1, y + 3, "N" if skin_id == "cyber" else "A")
    elif face == "panic":
        _put(canvas, x + 2, y + 2, "W")
        _put(canvas, x + 4, y + 2, "W")
        _put(canvas, x + 3, y + 4, "K")
        _put(canvas, x + 1, y + 1, "A")
        _put(canvas, x + 5, y + 1, "A")
    elif face == "sleep":
        _put(canvas, x + 2, y + 2, "K")
        _put(canvas, x + 3, y + 2, "K")
        _put(canvas, x + 4, y + 2, "K")
    else:
        _put(canvas, x + 2, y + 2, "W")
        _put(canvas, x + 4, y + 2, "W")
        _put(canvas, x + 3, y + 3, "K")


def _draw_body(canvas: list[list[str]], skin_id: str, dx: int, dy: int) -> None:
    x = 6 + dx
    y = 8 + dy
    _outline_rect(canvas, x, y, 6, 6, "J")
    _rect(canvas, x + 1, y, 4, 1, "A" if skin_id in {"dj", "chinese", "cyber"} else "N")
    if skin_id == "programmer":
        _rect(canvas, x + 2, y + 3, 5, 2, "N")
        _rect(canvas, x + 3, y + 3, 3, 1, "W")
    elif skin_id == "sleepwear":
        _rect(canvas, x - 1, y + 3, 8, 2, "A")
    elif skin_id == "cyber":
        _put(canvas, x - 1, y + 1, "A")
        _put(canvas, x + 6, y + 1, "N")
        _rect(canvas, x + 2, y + 1, 2, 4, "A")
    elif skin_id == "chinese":
        _rect(canvas, x + 1, y + 1, 1, 4, "A")
        _rect(canvas, x + 4, y + 1, 1, 4, "N")


def _draw_arms(canvas: list[list[str]], pose: str, dx: int, dy: int) -> None:
    cx = 6 + dx
    cy = 9 + dy
    arms = {
        "down": ((cx - 1, cy, "H"), (cx - 2, cy + 1, "H"), (cx + 6, cy, "H"), (cx + 7, cy + 1, "H")),
        "sway_r": ((cx - 1, cy + 1, "H"), (cx - 2, cy + 2, "H"), (cx + 6, cy - 1, "H"), (cx + 7, cy, "H")),
        "sway_l": ((cx - 1, cy - 1, "H"), (cx - 2, cy, "H"), (cx + 6, cy + 1, "H"), (cx + 7, cy + 2, "H")),
        "swing_l": ((cx - 2, cy, "H"), (cx - 3, cy - 1, "H"), (cx + 6, cy + 1, "H"), (cx + 7, cy + 2, "H")),
        "swing_r": ((cx - 1, cy + 1, "H"), (cx - 2, cy + 2, "H"), (cx + 7, cy, "H"), (cx + 8, cy - 1, "H")),
        "up": ((cx - 2, cy - 2, "H"), (cx - 3, cy - 3, "H"), (cx + 7, cy - 2, "H"), (cx + 8, cy - 3, "H")),
        "up_r": ((cx - 1, cy - 2, "H"), (cx - 2, cy - 3, "H"), (cx + 7, cy - 3, "H"), (cx + 8, cy - 4, "H")),
        "wide": ((cx - 2, cy - 1, "H"), (cx - 3, cy - 1, "H"), (cx + 7, cy - 1, "H"), (cx + 8, cy - 1, "H")),
        "chin": ((cx - 1, cy + 1, "H"), (cx + 3, cy - 1, "H"), (cx + 6, cy + 1, "H"), (cx + 7, cy + 2, "H")),
        "chin_r": ((cx - 2, cy + 2, "H"), (cx - 1, cy + 1, "H"), (cx + 4, cy - 1, "H"), (cx + 7, cy + 1, "H")),
        "present": ((cx - 3, cy, "H"), (cx - 4, cy, "H"), (cx + 7, cy, "H"), (cx + 8, cy, "H")),
        "present_r": ((cx - 3, cy - 1, "H"), (cx - 4, cy - 1, "H"), (cx + 7, cy + 1, "H"), (cx + 8, cy + 1, "H")),
        "droop": ((cx - 1, cy + 2, "H"), (cx - 1, cy + 3, "H"), (cx + 6, cy + 2, "H"), (cx + 6, cy + 3, "H")),
        "droop_r": ((cx - 2, cy + 2, "H"), (cx - 2, cy + 3, "H"), (cx + 7, cy + 2, "H"), (cx + 7, cy + 3, "H")),
    }
    for x, y, color in arms.get(pose, arms["down"]):
        _put(canvas, x, y, color)


def _draw_legs(canvas: list[list[str]], pose: str, dx: int, dy: int) -> None:
    cx = 7 + dx
    cy = 14 + dy
    legs = {
        "stand": ((cx, cy, "K"), (cx, cy + 1, "K"), (cx + 3, cy, "K"), (cx + 3, cy + 1, "K")),
        "step_l": ((cx - 1, cy, "K"), (cx - 2, cy + 1, "K"), (cx + 3, cy, "K"), (cx + 4, cy + 1, "K")),
        "step_r": ((cx, cy, "K"), (cx - 1, cy + 1, "K"), (cx + 4, cy, "K"), (cx + 5, cy + 1, "K")),
        "wide_l": ((cx - 1, cy, "K"), (cx - 2, cy + 1, "K"), (cx + 4, cy, "K"), (cx + 5, cy + 1, "K")),
        "wide_r": ((cx - 2, cy, "K"), (cx - 3, cy + 1, "K"), (cx + 3, cy, "K"), (cx + 4, cy + 1, "K")),
        "kick_l": ((cx - 2, cy, "K"), (cx - 4, cy, "K"), (cx + 3, cy, "K"), (cx + 3, cy + 1, "K")),
        "kick_r": ((cx, cy, "K"), (cx, cy + 1, "K"), (cx + 4, cy, "K"), (cx + 6, cy, "K")),
    }
    for x, y, color in legs.get(pose, legs["stand"]):
        _put(canvas, x, y, color)


def _draw_skin_props(canvas: list[list[str]], skin_id: str, prop: str, dx: int, dy: int) -> None:
    if skin_id == "dj":
        _dj_props(canvas, prop, dx, dy)
    elif skin_id == "programmer":
        _programmer_props(canvas, prop, dx, dy)
    elif skin_id == "sleepwear":
        _sleepwear_props(canvas, prop, dx, dy)
    elif skin_id == "cyber":
        _cyber_props(canvas, prop, dx, dy)
    elif skin_id == "chinese":
        _chinese_props(canvas, prop, dx, dy)


def _dj_props(canvas: list[list[str]], prop: str, dx: int, dy: int) -> None:
    if prop in {"music", "spark"}:
        _put(canvas, 3 + dx, 3, "A")
        _put(canvas, 14 + dx, 2, "N")
        _put(canvas, 15 + dx, 4, "A")
    if prop == "sign":
        _rect(canvas, 3 + dx, 7 + dy, 4, 2, "N")
        _put(canvas, 4 + dx, 8 + dy, "K")
    if prop == "think":
        _put(canvas, 13 + dx, 4 + dy, "N")
        _put(canvas, 14 + dx, 3 + dy, "N")
    if prop == "alert":
        _put(canvas, 2 + dx, 2, "A")
        _put(canvas, 15 + dx, 2, "A")
    if prop == "sleep":
        _put(canvas, 13 + dx, 2, "N")
        _put(canvas, 14 + dx, 1, "N")


def _programmer_props(canvas: list[list[str]], prop: str, dx: int, dy: int) -> None:
    _rect(canvas, 13 + dx, 11 + dy, 2, 2, "A")
    if prop in {"think", "sign"}:
        _rect(canvas, 4 + dx, 12 + dy, 10, 2, "N")
        _rect(canvas, 6 + dx, 12 + dy, 4, 1, "W")
    if prop in {"music", "spark"}:
        _put(canvas, 4 + dx, 3, "N")
        _put(canvas, 14 + dx, 4, "A")
    if prop == "alert":
        _rect(canvas, 2 + dx, 2, 2, 2, "A")
        _rect(canvas, 14 + dx, 2, 2, 2, "A")
    if prop == "sleep":
        _put(canvas, 14 + dx, 3, "N")


def _sleepwear_props(canvas: list[list[str]], prop: str, dx: int, dy: int) -> None:
    _rect(canvas, 3 + dx, 13 + dy, 12, 2, "A")
    if prop == "sleep":
        _put(canvas, 13 + dx, 2, "N")
        _put(canvas, 14 + dx, 1, "N")
        _put(canvas, 15 + dx, 0, "N")
    if prop in {"music", "spark"}:
        _put(canvas, 3 + dx, 4, "N")
        _put(canvas, 15 + dx, 5, "A")
    if prop == "rain":
        _put(canvas, 4 + dx, 3, "N")
        _put(canvas, 13 + dx, 4, "N")
    if prop == "sign":
        _rect(canvas, 4 + dx, 8 + dy, 4, 2, "N")
    if prop == "alert":
        _put(canvas, 3 + dx, 2, "A")
        _put(canvas, 14 + dx, 2, "A")


def _cyber_props(canvas: list[list[str]], prop: str, dx: int, dy: int) -> None:
    _put(canvas, 4 + dx, 8 + dy, "A")
    _put(canvas, 13 + dx, 8 + dy, "N")
    if prop in {"music", "spark"}:
        _put(canvas, 2 + dx, 3, "A")
        _put(canvas, 15 + dx, 3, "N")
        _put(canvas, 14 + dx, 5, "A")
    if prop == "sign":
        _rect(canvas, 12 + dx, 6 + dy, 3, 3, "N")
        _put(canvas, 13 + dx, 7 + dy, "K")
    if prop == "think":
        _put(canvas, 14 + dx, 4 + dy, "A")
        _put(canvas, 15 + dx, 3 + dy, "N")
    if prop == "alert":
        _rect(canvas, 2 + dx, 2, 2, 2, "A")
        _rect(canvas, 14 + dx, 2, 2, 2, "N")
    if prop == "sleep":
        _put(canvas, 13 + dx, 2, "A")


def _chinese_props(canvas: list[list[str]], prop: str, dx: int, dy: int) -> None:
    _rect(canvas, 5 + dx, 13 + dy, 8, 1, "A")
    if prop in {"music", "spark"}:
        _put(canvas, 3 + dx, 4, "N")
        _put(canvas, 14 + dx, 3, "A")
        _put(canvas, 15 + dx, 4, "N")
    if prop == "sign":
        _rect(canvas, 3 + dx, 8 + dy, 5, 2, "A")
        _put(canvas, 5 + dx, 8 + dy, "N")
    if prop == "think":
        _put(canvas, 13 + dx, 4 + dy, "A")
        _put(canvas, 14 + dx, 3 + dy, "N")
    if prop == "alert":
        _put(canvas, 3 + dx, 2, "A")
        _put(canvas, 14 + dx, 2, "A")
    if prop == "sleep":
        _put(canvas, 13 + dx, 2, "N")


def _skin_actions(skin_id: str) -> dict[str, tuple[Frame, ...]]:
    return {action: tuple(_frame(skin_id, action, spec) for spec in specs) for action, specs in _ACTION_SPECS.items()}


BUILTIN_SKINS: dict[str, Skin] = {
    skin_id: Skin(id=skin_id, name=_NAMES[skin_id], palette=_PALETTES[skin_id], actions=_skin_actions(skin_id))
    for skin_id in ("dj", "programmer", "sleepwear", "cyber", "chinese")
}


def get_skin(skin_id: str) -> Skin:
    return BUILTIN_SKINS.get(skin_id, BUILTIN_SKINS["dj"])
