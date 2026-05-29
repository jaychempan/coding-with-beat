# Pet macOS Menu Bar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the desktop pet a macOS menu bar summon point with the Coding With Beat logo and best-effort hiding of the Python Dock identity.

**Architecture:** Add a focused `coding_with_beat/pet/macos.py` module for app metadata, icon resolution, Dock policy, and `QSystemTrayIcon` menu wiring. Keep `window.py` unchanged for pet behavior; `app.py` owns app-level setup and passes the pet window to the menu bar controller.

**Tech Stack:** Python 3.13, PySide6 `QApplication`/`QSystemTrayIcon`, optional PyObjC `AppKit`, pytest.

---

## File Structure

- Create `coding_with_beat/pet/macos.py`
  - App name and icon setup.
  - Best-effort macOS Dock hiding.
  - Menu bar controller for show/hide, current playback, recommendations, next track, and quit.
- Modify `coding_with_beat/pet/app.py`
  - Use app metadata helpers.
  - Install menu bar controller.
  - Keep the controller referenced for the process lifetime.
- Modify `tests/test_pet_cli.py`
  - Verify `cmd_pet()` passes the default `hide_dock=True`.
- Add `tests/test_pet_macos.py`
  - Verify icon path resolution, non-macOS Dock hiding behavior, and controller menu action labels.
- Modify `README.md`
  - Document menu bar summon and Dock/Python hiding behavior.

## Task 1: Add macOS App Helper

**Files:**
- Create: `coding_with_beat/pet/macos.py`
- Test: `tests/test_pet_macos.py`

- [ ] Write failing tests for `pet_icon_path()`, `hide_dock_icon()` on non-macOS, and `PetMenuBarController` action labels.
- [ ] Run `pytest tests/test_pet_macos.py -q` and confirm it fails because `coding_with_beat.pet.macos` does not exist.
- [ ] Implement `macos.py` with:
  - `APP_NAME = "Coding With Beat Pet"`
  - `pet_icon_path() -> Path | None`
  - `apply_app_metadata(app) -> QIcon`
  - `hide_dock_icon() -> bool`
  - `PetMenuBarController`
- [ ] Run `pytest tests/test_pet_macos.py -q` and confirm it passes.
- [ ] Commit with `feat(pet): add macos menu bar helper`.

## Task 2: Wire App Entrypoint

**Files:**
- Modify: `coding_with_beat/pet/app.py`
- Modify: `coding_with_beat/__main__.py`
- Test: `tests/test_pet_cli.py`

- [ ] Write failing test that `cmd_pet()` calls `run(petdex_slug=..., hide_dock=True)`.
- [ ] Run the focused test and confirm it fails because `run()` is currently called without `hide_dock`.
- [ ] Update `pet.app.run(*, petdex_slug=None, hide_dock=True)` to apply metadata, create the menu bar controller, set `app.setQuitOnLastWindowClosed(False)` when the menu exists, and call `hide_dock_icon()` when requested.
- [ ] Update `cmd_pet()` to pass `hide_dock="--show-dock" not in args`.
- [ ] Run `pytest tests/test_pet_cli.py tests/test_pet_macos.py -q`.
- [ ] Commit with `feat(pet): add macos menu bar summon`.

## Task 3: Docs And Verification

**Files:**
- Modify: `README.md`

- [ ] Add README bullets documenting menu bar summon, `--show-dock`, and best-effort Dock hiding.
- [ ] Run `ruff check coding_with_beat tests`.
- [ ] Run `pytest -q`.
- [ ] Run `python -m py_compile coding_with_beat/pet/app.py coding_with_beat/pet/macos.py`.
- [ ] Restart local pet with launchctl and verify `cwb-petdex-boba` is running with no traceback.
- [ ] Commit docs and any verification fixes.

## Self-Review

- Spec coverage: app name, icon, menu bar summon, Dock hiding, fallback behavior, tests, and README are covered.
- Placeholder scan: no unresolved placeholders remain.
- Type consistency: `hide_dock`, `PetMenuBarController`, `pet_icon_path`, `apply_app_metadata`, and `hide_dock_icon` are defined before use.
