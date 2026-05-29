# Pet Sidecar Controls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the pet action buttons from a bottom strip to a compact right-side tool sidecar.

**Architecture:** Add a transparent `_pet_body` wrapper that manually positions `_sprite_stage` and `_controls_widget`. Reuse the existing visibility timer and action callbacks; only change geometry and tests.

**Tech Stack:** Python, PySide6, pytest.

---

## Tasks

### Task 1: Tests

- [ ] Update built-in and Petdex layout tests to expect `_pet_body` at layout item 2.
- [ ] Assert `_controls_widget.parent() is _pet_body`.
- [ ] Assert `_controls_widget.maximumWidth() == 22` and `maximumHeight() == 94`.
- [ ] Add tests that hidden controls do not reserve side width, and shown controls increase width while keeping height stable.
- [ ] Run focused tests and confirm failures before implementation.

### Task 2: Implementation

- [ ] Add `_pet_body(sprite_stage, controls)` and `_layout_pet_body(body, sprite_stage, controls)`.
- [ ] Change `_controls_widget()` to vertical layout with `22px` width and `94px` height.
- [ ] Replace bottom layout insertion with `_pet_body`.
- [ ] Update `_render()` / `_resize_shell()` to size from `_pet_body`.

### Task 3: Verification

- [ ] Run `pytest tests/test_pet_window_actions.py -q`.
- [ ] Run `ruff check coding_with_beat tests scripts`.
- [ ] Run `ruff format --check coding_with_beat tests scripts`.
- [ ] Run `pytest -q`.
- [ ] Rebuild and restart `dist/CodeBeat.app`.
- [ ] Commit and push `pet`.
