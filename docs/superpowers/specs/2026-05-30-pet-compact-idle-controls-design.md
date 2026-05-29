# Pet Compact Idle Controls — Design Spec

**Date:** 2026-05-30
**Status:** Approved
**Feature:** Hide desktop pet controls during idle and tighten the button strip
**Branch:** `pet`

---

## Goal

Make the desktop pet look like a pet during normal desktop use, not a floating
control panel.

The current bottom controls are always visible and the window reserves vertical
space for them even when the user is not interacting. This creates too much
blank space and makes the buttons feel visually heavy.

---

## Design

Idle state:

- Hide the bottom control strip by default.
- Do not reserve height for hidden controls.
- Keep the pet sprite and music aura centered.
- Keep right-click menu as the reliable always-available command path.

Summoned state:

- Show the control strip when the user hovers, presses, clicks, drags, opens a
  bubble, or receives a playback update.
- Hide the strip again after a short idle timeout.
- Keep controls visible while the pointer is over the pet window.

Button treatment:

- Reduce buttons from `26x26` to `22x22`.
- Reduce spacing from `4px` to `2px`.
- Use a more transparent background and thinner border.
- Replace the final `...` text with `⋮`.
- Keep fixed dimensions so the layout does not jump.

---

## Implementation Notes

Use a small visibility timer on both `PetWindow` and `PetdexWindow`.

Both windows should share helper functions for:

- creating the tighter control widget
- showing controls temporarily
- hiding controls after timeout
- calculating render height based on actual control visibility

No music command behavior changes in this pass.

---

## Testing

Automated tests should verify:

- built-in and Petdex windows start with controls hidden
- hidden controls do not reserve layout height in `_render()`
- `show_controls_temporarily()` reveals controls
- controls hide again when the timeout handler runs and the pointer is not hovering
- the compact strip width reflects `22px` buttons and `2px` gaps
- the final button displays `⋮`
