# Pet Sidecar Controls — Design Spec

**Date:** 2026-05-30
**Status:** Approved
**Feature:** Move desktop pet controls from bottom strip to a sidecar next to the pet
**Branch:** `pet`

---

## Goal

Make pet actions feel physically close to the pet instead of floating below it.

The bottom action strip solves idle clutter, but when it appears it can still
feel visually detached. This change moves the controls into a compact vertical
sidecar directly beside the sprite/aura stage.

---

## Design

- Controls remain hidden by default.
- When summoned, controls appear vertically on the pet's right side.
- The sidecar uses the existing four actions: current, recommend, reroll, more.
- Button size stays `22x22`; vertical spacing stays `2px`.
- Hidden controls do not reserve width or height.
- The pet body remains transparent, compact, and centered as a visual cluster.

---

## Testing

Automated tests should verify:

- controls are no longer a separate bottom layout item
- both built-in and Petdex windows own a `_pet_body` wrapper
- `_pet_body` contains `_sprite_stage` and `_controls_widget`
- controls are vertical and have max height `94`
- hidden controls do not reserve side width
- shown controls expand width but not height below the sprite body
