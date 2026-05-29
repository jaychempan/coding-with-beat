#!/usr/bin/env python3
"""Generate the bundled CodeBeat Buddy Petdex spritesheet."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
PET_DIR = ROOT / "assets" / "pets" / "codebeat-buddy"
SPRITESHEET_PATH = PET_DIR / "spritesheet.png"
FRAME_W = 192
FRAME_H = 208
COLS = 8
ROWS = 9

INK = "#090910"
OUTLINE = "#171522"
HOOD = "#222238"
HOOD_DARK = "#151523"
PURPLE = "#8b5cf6"
PURPLE_LIGHT = "#a78bfa"
PURPLE_DARK = "#6d44d8"
CYAN = "#67e8f9"
SKIN = "#f0c7a2"
SKIN_SHADE = "#d8a37d"
WHITE = "#fff7ed"


def main() -> int:
    PET_DIR.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGBA", (FRAME_W * COLS, FRAME_H * ROWS), (0, 0, 0, 0))
    for row in range(ROWS):
        for col in range(COLS):
            frame = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
            draw = ImageDraw.Draw(frame)
            action = _action_for_row(row)
            _draw_buddy(draw, action, col)
            sheet.alpha_composite(frame, (col * FRAME_W, row * FRAME_H))
    sheet.save(SPRITESHEET_PATH)
    print(SPRITESHEET_PATH)
    return 0


def _action_for_row(row: int) -> str:
    return {
        0: "idle",
        1: "walk",
        2: "idle",
        3: "recommend",
        4: "happy",
        5: "sad",
        6: "think",
        7: "dance",
        8: "sleep",
    }.get(row, "idle")


def _draw_buddy(draw: ImageDraw.ImageDraw, action: str, frame: int) -> None:
    bob = _bob(action, frame)
    lean = _lean(action, frame)
    arm_pose = _arm_pose(action, frame)
    leg_pose = _leg_pose(action, frame)
    face = _face(action, frame)

    if action == "sleep":
        _draw_sleeping_buddy(draw, frame)
        return

    x = 96 + lean
    y = 66 + bob
    _draw_legs(draw, x, y, leg_pose)
    _draw_body(draw, x, y, action)
    _draw_arms(draw, x, y, arm_pose, action)
    _draw_head(draw, x, y, face, action)
    _draw_props(draw, x, y, action, frame)


def _bob(action: str, frame: int) -> int:
    if action in {"dance", "happy"}:
        return (-6, -2, 3, -1, -7, -2, 2, -2)[frame % 8]
    if action == "walk":
        return (0, 2, 0, -1, 1, 2, 0, -1)[frame % 8]
    if action == "sad":
        return (5, 6, 5, 7, 6, 7, 6, 5)[frame % 8]
    return (0, 1, 0, -1, 0, 1, 0, -1)[frame % 8]


def _lean(action: str, frame: int) -> int:
    if action in {"dance", "happy"}:
        return (-5, -2, 3, 6, 4, 0, -4, -6)[frame % 8]
    if action == "walk":
        return (-4, -2, 1, 4, 3, 1, -2, -4)[frame % 8]
    if action == "sad":
        return -2
    return 0


def _arm_pose(action: str, frame: int) -> str:
    if action == "dance":
        return ("up_l", "wide", "up_r", "wide", "up_both", "wide", "up_l", "up_r")[frame % 8]
    if action == "recommend":
        return ("present", "present", "point", "point", "present", "up_r", "present", "point")[frame % 8]
    if action == "happy":
        return ("up_both", "up_both", "wide", "up_l", "up_r", "wide", "up_both", "wide")[frame % 8]
    if action == "think":
        return "chin"
    if action == "sad":
        return "down"
    if action == "walk":
        return ("swing_l", "swing_r")[frame % 2]
    return ("down", "swing_l", "down", "swing_r")[frame % 4]


def _leg_pose(action: str, frame: int) -> str:
    if action == "dance":
        return ("wide_l", "wide_r", "kick_l", "kick_r")[frame % 4]
    if action == "walk":
        return ("step_l", "step_r")[frame % 2]
    if action == "happy":
        return ("wide_l", "wide_r", "wide_l", "kick_r")[frame % 4]
    return "stand"


def _face(action: str, frame: int) -> str:
    if action in {"dance", "happy", "recommend"}:
        return "happy" if frame % 3 else "grin"
    if action == "think":
        return "think"
    if action == "sad":
        return "sad"
    return "blink" if frame == 2 else "open"


def _draw_head(draw: ImageDraw.ImageDraw, x: int, y: int, face: str, action: str) -> None:
    draw.rounded_rectangle((x - 40, y - 65, x + 40, y + 15), radius=24, fill=OUTLINE)
    draw.rounded_rectangle((x - 31, y - 56, x + 31, y + 7), radius=18, fill=SKIN)
    draw.rectangle((x - 31, y - 56, x + 31, y - 43), fill=HOOD_DARK)
    draw.rectangle((x - 27, y - 43, x - 18, y - 35), fill=HOOD_DARK)
    draw.rectangle((x + 18, y - 43, x + 27, y - 35), fill=HOOD_DARK)
    draw.rounded_rectangle((x - 52, y - 38, x - 37, y - 4), radius=7, fill=OUTLINE)
    draw.rounded_rectangle((x + 37, y - 38, x + 52, y - 4), radius=7, fill=OUTLINE)
    draw.rounded_rectangle((x - 48, y - 34, x - 39, y - 8), radius=5, fill=PURPLE)
    draw.rounded_rectangle((x + 39, y - 34, x + 48, y - 8), radius=5, fill=PURPLE)
    draw.arc((x - 38, y - 73, x + 38, y - 15), 202, 338, fill=PURPLE_LIGHT, width=6)
    draw.rectangle((x - 15, y - 68, x + 15, y - 62), fill=PURPLE_LIGHT)
    _draw_face(draw, x, y, face)
    if action == "think":
        draw.rectangle((x + 30, y - 70, x + 37, y - 63), fill=CYAN)


def _draw_face(draw: ImageDraw.ImageDraw, x: int, y: int, face: str) -> None:
    if face == "blink":
        draw.rectangle((x - 16, y - 28, x - 7, y - 24), fill=INK)
        draw.rectangle((x + 7, y - 28, x + 16, y - 24), fill=INK)
    else:
        draw.rectangle((x - 16, y - 32, x - 8, y - 22), fill=INK if face != "happy" else WHITE)
        draw.rectangle((x + 8, y - 32, x + 16, y - 22), fill=INK if face != "happy" else WHITE)
    draw.rectangle((x - 24, y - 15, x - 18, y - 10), fill="#f5a3b7")
    draw.rectangle((x + 18, y - 15, x + 24, y - 10), fill="#f5a3b7")
    if face == "sad":
        draw.arc((x - 13, y - 9, x + 13, y + 12), 200, 340, fill=INK, width=3)
        draw.rectangle((x + 21, y - 20, x + 27, y - 11), fill=CYAN)
    elif face == "think":
        draw.rectangle((x - 7, y - 6, x + 12, y - 2), fill=INK)
    elif face == "grin":
        draw.rectangle((x - 13, y - 8, x + 13, y - 1), fill=INK)
        draw.rectangle((x - 10, y - 7, x + 10, y - 5), fill=WHITE)
    else:
        draw.rectangle((x - 7, y - 8, x + 7, y - 4), fill=INK)


def _draw_body(draw: ImageDraw.ImageDraw, x: int, y: int, action: str) -> None:
    draw.rounded_rectangle((x - 35, y + 5, x + 35, y + 70), radius=18, fill=OUTLINE)
    draw.rounded_rectangle((x - 28, y + 12, x + 28, y + 63), radius=13, fill=HOOD)
    draw.polygon(((x - 20, y + 12), (x, y + 31), (x + 20, y + 12)), fill=HOOD_DARK)
    draw.rectangle((x - 2, y + 31, x + 2, y + 59), fill=HOOD_DARK)
    draw.rounded_rectangle((x - 23, y + 27, x + 23, y + 58), radius=9, fill="#181827")
    _draw_chest_wave(draw, x, y + 43, action)
    draw.rectangle((x - 18, y + 21, x - 14, y + 32), fill=PURPLE_LIGHT)
    draw.rectangle((x + 14, y + 21, x + 18, y + 32), fill=PURPLE_LIGHT)


def _draw_chest_wave(draw: ImageDraw.ImageDraw, x: int, y: int, action: str) -> None:
    boost = 7 if action in {"dance", "happy", "recommend"} else 0
    draw.rounded_rectangle((x - 20, y - 18 - boost // 2, x + 20, y + 18 + boost // 2), radius=8, fill="#211b3a")
    bars = ((-13, 8), (-7, 18 + boost), (0, 30 + boost), (7, 20 + boost), (13, 10))
    for bx, height in bars:
        alpha_color = PURPLE_LIGHT if bx == 0 else PURPLE_DARK if abs(bx) == 13 else PURPLE
        draw.rounded_rectangle((x + bx - 3, y - height // 2, x + bx + 3, y + height // 2), radius=3, fill=alpha_color)


def _draw_arms(draw: ImageDraw.ImageDraw, x: int, y: int, pose: str, action: str) -> None:
    sleeve = HOOD
    hand = SKIN_SHADE
    coords = {
        "down": ((x - 44, y + 21, x - 32, y + 62), (x + 32, y + 21, x + 44, y + 62)),
        "swing_l": ((x - 50, y + 17, x - 37, y + 54), (x + 31, y + 26, x + 44, y + 64)),
        "swing_r": ((x - 44, y + 26, x - 31, y + 64), (x + 37, y + 17, x + 50, y + 54)),
        "wide": ((x - 65, y + 14, x - 33, y + 28), (x + 33, y + 14, x + 65, y + 28)),
        "up_l": ((x - 58, y - 22, x - 44, y + 29), (x + 32, y + 21, x + 44, y + 61)),
        "up_r": ((x - 44, y + 21, x - 32, y + 61), (x + 44, y - 22, x + 58, y + 29)),
        "up_both": ((x - 58, y - 22, x - 44, y + 29), (x + 44, y - 22, x + 58, y + 29)),
        "present": ((x - 50, y + 22, x - 36, y + 58), (x + 30, y + 12, x + 70, y + 27)),
        "point": ((x - 45, y + 22, x - 32, y + 58), (x + 32, y + 4, x + 76, y + 18)),
        "chin": ((x - 44, y + 21, x - 32, y + 62), (x + 20, y - 8, x + 39, y + 34)),
    }.get(pose, ((x - 44, y + 21, x - 32, y + 62), (x + 32, y + 21, x + 44, y + 62)))
    for arm in coords:
        draw.rounded_rectangle(arm, radius=6, fill=OUTLINE)
        inset = 4
        draw.rounded_rectangle(
            (arm[0] + inset, arm[1] + inset, arm[2] - inset, arm[3] - inset),
            radius=4,
            fill=sleeve,
        )
    if action == "recommend":
        draw.rounded_rectangle((x + 68, y - 1, x + 100, y + 29), radius=7, fill=WHITE)
        draw.rectangle((x + 75, y + 8, x + 92, y + 12), fill=PURPLE)
        draw.rectangle((x + 75, y + 17, x + 87, y + 21), fill=CYAN)
    draw.ellipse((coords[0][0] - 2, coords[0][3] - 6, coords[0][0] + 10, coords[0][3] + 6), fill=hand)
    draw.ellipse((coords[1][2] - 10, coords[1][3] - 6, coords[1][2] + 2, coords[1][3] + 6), fill=hand)


def _draw_legs(draw: ImageDraw.ImageDraw, x: int, y: int, pose: str) -> None:
    legs = {
        "stand": ((x - 22, y + 64, x - 7, y + 111), (x + 7, y + 64, x + 22, y + 111)),
        "step_l": ((x - 31, y + 64, x - 15, y + 108), (x + 11, y + 64, x + 31, y + 112)),
        "step_r": ((x - 31, y + 64, x - 11, y + 112), (x + 15, y + 64, x + 31, y + 108)),
        "wide_l": ((x - 35, y + 64, x - 17, y + 108), (x + 10, y + 64, x + 31, y + 112)),
        "wide_r": ((x - 31, y + 64, x - 10, y + 112), (x + 17, y + 64, x + 35, y + 108)),
        "kick_l": ((x - 48, y + 63, x - 20, y + 82), (x + 8, y + 64, x + 24, y + 112)),
        "kick_r": ((x - 24, y + 64, x - 8, y + 112), (x + 20, y + 63, x + 48, y + 82)),
    }.get(pose, ((x - 22, y + 64, x - 7, y + 111), (x + 7, y + 64, x + 22, y + 111)))
    for leg in legs:
        draw.rounded_rectangle(leg, radius=7, fill=OUTLINE)
        draw.rounded_rectangle((leg[0] + 3, leg[1] + 3, leg[2] - 3, leg[3] - 3), radius=5, fill=HOOD_DARK)
        draw.rectangle((leg[0] - 5, leg[3] - 4, leg[2] + 7, leg[3] + 4), fill=INK)


def _draw_props(draw: ImageDraw.ImageDraw, x: int, y: int, action: str, frame: int) -> None:
    if action in {"dance", "happy"}:
        notes = ((36, 29), (152, 23), (42, 76), (151, 82))
        for i, (nx, ny) in enumerate(notes):
            dy = ((frame + i) % 4) * -3
            draw.rectangle((nx, ny + dy, nx + 5, ny + 20 + dy), fill=PURPLE_LIGHT)
            draw.ellipse((nx - 5, ny + 15 + dy, nx + 8, ny + 27 + dy), fill=PURPLE_LIGHT)
            draw.rectangle((nx + 5, ny + dy, nx + 14, ny + 4 + dy), fill=PURPLE_LIGHT)
    if action == "think":
        for i in range(3):
            draw.rectangle((140 + i * 10, 48 - i * 8, 146 + i * 10, 54 - i * 8), fill=CYAN)
    if action == "sad":
        for i, rx in enumerate((44, 62, 145, 160)):
            offset = (frame * 5 + i * 8) % 28
            draw.rectangle((rx, 40 + offset, rx + 3, 53 + offset), fill=CYAN)


def _draw_sleeping_buddy(draw: ImageDraw.ImageDraw, frame: int) -> None:
    y = 98 + (frame % 3)
    draw.rounded_rectangle((48, y + 20, 140, y + 72), radius=18, fill=OUTLINE)
    draw.rounded_rectangle((56, y + 28, 132, y + 65), radius=13, fill=HOOD)
    draw.rounded_rectangle((52, y - 20, 111, y + 33), radius=17, fill=OUTLINE)
    draw.rounded_rectangle((60, y - 13, 105, y + 25), radius=12, fill=SKIN)
    draw.rectangle((72, y + 4, 96, y + 7), fill=INK)
    draw.rounded_rectangle((38, y + 37, 148, y + 77), radius=14, fill=(139, 92, 246, 190))
    for i, scale in enumerate((0, 1, 2)):
        z_y = 45 - i * 13 - (frame % 3)
        draw.rectangle((127 + scale * 8, z_y, 145 + scale * 8, z_y + 5), fill=PURPLE_LIGHT)
        draw.rectangle((140 + scale * 8, z_y - 8, 146 + scale * 8, z_y + 5), fill=PURPLE_LIGHT)
        draw.rectangle((127 + scale * 8, z_y - 8, 146 + scale * 8, z_y - 3), fill=PURPLE_LIGHT)


if __name__ == "__main__":
    raise SystemExit(main())
