# Pet Compact Idle Controls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hide the desktop pet bottom controls during idle and make the summoned controls tighter and more polished.

**Architecture:** Keep the existing `PetWindow` and `PetdexWindow` layout, but make `_controls_widget` hidden by default and compute render height from actual visibility. Add shared helpers for temporary visibility and compact button sizing.

**Tech Stack:** Python, PySide6, pytest.

---

## Tasks

### Task 1: Tests For Hidden Idle Controls

**Files:**
- Modify: `tests/test_pet_window_actions.py`

- [ ] Add tests asserting built-in and Petdex windows start with `_controls_widget.isVisible() is False`.
- [ ] Add tests asserting `_show_controls_temporarily()` sets controls visible.
- [ ] Add tests asserting `_hide_controls_if_idle()` hides controls when not hovered.
- [ ] Add tests asserting `_more_button.text() == "⋮"` and `_controls_widget.maximumWidth() == 94`.
- [ ] Run the new tests and verify they fail before implementation.

### Task 2: Compact Button Styling

**Files:**
- Modify: `coding_with_beat/pet/pixel_ui.py`
- Modify: `coding_with_beat/pet/window.py`

- [ ] Change icon button fixed size to `22x22`.
- [ ] Reduce button style visual weight with more transparent background and thinner border.
- [ ] Change `_controls_widget()` width math to `22 * count + 2 * gaps`.
- [ ] Change layout spacing to `2`.
- [ ] Change the more button label from `...` to `⋮`.

### Task 3: Idle Visibility Behavior

**Files:**
- Modify: `coding_with_beat/pet/window.py`

- [ ] Add `_controls_hide_timer` to both window classes.
- [ ] Hide controls after construction.
- [ ] Add `_show_controls_temporarily()` and `_hide_controls_if_idle()` helpers.
- [ ] Call `_show_controls_temporarily()` from mouse press, hover enter, bubble updates, live updates, and more-menu opening.
- [ ] Add `enterEvent()` and `leaveEvent()` to manage hover lifetime.
- [ ] Update `_render()` to reserve bottom height only when controls are visible.

### Task 4: Verification

**Files:**
- Modify: `README.md` if needed.

- [ ] Run `pytest tests/test_pet_window_actions.py -q`.
- [ ] Run `ruff check coding_with_beat tests scripts`.
- [ ] Run `ruff format --check coding_with_beat tests scripts`.
- [ ] Run `pytest -q`.
- [ ] Rebuild and restart `dist/CodeBeat.app`.
- [ ] Commit and push `pet`.
