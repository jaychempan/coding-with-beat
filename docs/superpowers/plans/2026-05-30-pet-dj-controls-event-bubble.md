# Pet DJ Controls And Event Bubble Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add visible playback controls to the DJ panel and make pet bubble text hide after short events.

**Architecture:** Extend `CodeBeatDjPanel` with a focused now-playing control row that calls existing music control tools. Extend both pet window classes with a bubble hide timer that collapses the bubble after event feedback.

**Tech Stack:** Python, PySide6 widgets, pytest, ruff.

---

## Files

- Modify `coding_with_beat/pet/dj_panel.py`: add player control buttons and handlers.
- Modify `coding_with_beat/pet/window.py`: add event bubble hide timer for built-in and Petdex windows.
- Modify `tests/test_pet_dj_panel.py`: verify control buttons and tool calls.
- Modify `tests/test_pet_window_actions.py`: verify bubble auto-hide behavior.
- Modify `README.md`: document the DJ playback controls and event-only bubble.

## Tasks

### Task 1: DJ Panel Playback Controls

- [ ] Write failing tests in `tests/test_pet_dj_panel.py` asserting the panel has `♥`, `⏮`, `⏯`, `⏭`, and `⟳` buttons with object name `PlayerControlButton`.
- [ ] Write failing tests asserting `♥`, `⏮`, `⏯`, and `⏭` call `like_current`, `prev_track`, `toggle`, and `next_track`.
- [ ] Implement `_build_player_controls()` in `coding_with_beat/pet/dj_panel.py`.
- [ ] Add handler methods that reuse `_run_cwb_command()` for tool-backed controls and `refresh_live_snapshot()` for refresh.
- [ ] Run `pytest tests/test_pet_dj_panel.py -q`.

### Task 2: Event-Only Pet Bubble

- [ ] Write failing tests in `tests/test_pet_window_actions.py` for built-in and Petdex windows: `_show_bubble()` shows the bubble, `_hide_bubble()` hides it, and the window shrinks back.
- [ ] Add `_bubble_hide_timer` to both window classes.
- [ ] Start the timer from `_show_bubble()` with a shorter default duration and a longer duration for errors.
- [ ] Add shared `_hide_bubble()` helper and stop `_bubble_hide_timer` in `_stop_pet_timers()`.
- [ ] Run `pytest tests/test_pet_window_actions.py -q`.

### Task 3: Verification And Release

- [ ] Update `README.md` desktop pet notes.
- [ ] Run `pytest tests/test_pet_dj_panel.py tests/test_pet_window_actions.py -q`.
- [ ] Run `pytest -q`.
- [ ] Run `ruff check .` and `ruff format --check` on touched Python files.
- [ ] Rebuild and restart `dist/CodeBeat.app`.
- [ ] Commit and push to `origin pet`.

## Self-Review

- Spec coverage: DJ transport controls, refresh behavior, bubble hiding, both pet window classes, tests, docs, and local restart are all represented.
- Placeholder scan: no TODO/TBD placeholders.
- Type consistency: control tool names match existing MCP tools and slash command parser names.
