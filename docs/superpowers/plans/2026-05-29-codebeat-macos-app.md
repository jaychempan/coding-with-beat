# CodeBeat macOS App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local `CodeBeat.app` wrapper that launches the Coding With Beat menu-bar control center while preserving the existing `cwb` CLI.

**Architecture:** Add a small app-shell layer on top of the existing pet/menu-bar infrastructure. Keep the CLI and MCP server behavior unchanged; generate a local `.app` bundle that runs `python -m coding_with_beat app` through the installed venv/repo-path. Use separate padded waveform assets for App and menu-bar contexts so the icon does not look oversized.

**Tech Stack:** Python 3.13, PySide6, plistlib, pathlib, pytest, macOS app bundle structure.

---

## File Structure

- Create `assets/waveform_app_icon.svg`
  - Padded waveform mark for Finder/Launchpad/Dock.
- Create `assets/waveform_menu_bar.svg`
  - Transparent small-footprint waveform mark for menu bar/tray.
- Modify `coding_with_beat/pet/macos.py`
  - App identity changes from `Coding With Beat Pet` to `CodeBeat`.
  - Menu-bar icon uses `waveform_menu_bar.svg`.
  - App icon uses `waveform_app_icon.svg`.
- Create `coding_with_beat/app.py`
  - Menu-bar control-center entrypoint for `python -m coding_with_beat app`.
  - Reuses pet window/menu controller and adds app-specific repair/help actions.
- Modify `coding_with_beat/__main__.py`
  - Register `app` command.
- Create `scripts/build_macos_app.py`
  - Generates `dist/CodeBeat.app`.
  - Writes `Info.plist`, launcher shell script, and copied icon assets.
- Add/modify tests:
  - `tests/test_codebeat_app_builder.py`
  - `tests/test_pet_macos.py`
  - `tests/test_pet_cli.py`
- Modify `README.md`
  - Document `python scripts/build_macos_app.py` and `dist/CodeBeat.app`.

## Task 1: Add Padded App/Menu Icons

**Files:**
- Create: `assets/waveform_app_icon.svg`
- Create: `assets/waveform_menu_bar.svg`
- Modify: `coding_with_beat/pet/macos.py`
- Modify: `tests/test_pet_macos.py`

- [ ] Write failing tests asserting `pet_icon_path()` returns `waveform_menu_bar.svg` and `app_icon_path()` returns `waveform_app_icon.svg`.
- [ ] Run `pytest tests/test_pet_macos.py -q`; expect failure because `app_icon_path()` does not exist and `pet_icon_path()` still returns `waveform_logo.svg`.
- [ ] Add the two SVG assets. The app icon must include transparent padding; the menu-bar icon must have transparent background and a smaller waveform body.
- [ ] Update `macos.py` with `app_icon_path()` and menu-bar-first `pet_icon_path()`.
- [ ] Run `pytest tests/test_pet_macos.py -q`.
- [ ] Commit `feat(app): add restrained waveform icons`.

## Task 2: Add CodeBeat App Entrypoint

**Files:**
- Create: `coding_with_beat/app.py`
- Modify: `coding_with_beat/__main__.py`
- Modify: `coding_with_beat/pet/macos.py`
- Test: `tests/test_pet_cli.py`, `tests/test_pet_macos.py`

- [ ] Write failing tests that `COMMANDS["app"]` is registered and app metadata name is `CodeBeat`.
- [ ] Run focused tests and confirm failure.
- [ ] Implement `coding_with_beat/app.py` with `run()` that starts the same pet/menu-bar control center.
- [ ] Update `__main__.py` command table with `"app": cmd_app`.
- [ ] Update `APP_NAME = "CodeBeat"` in `pet/macos.py`.
- [ ] Run `pytest tests/test_pet_cli.py tests/test_pet_macos.py -q`.
- [ ] Commit `feat(app): add codebeat app entrypoint`.

## Task 3: Add macOS App Builder

**Files:**
- Create: `scripts/build_macos_app.py`
- Test: `tests/test_codebeat_app_builder.py`

- [ ] Write failing tests that build into a temp directory and assert:
  - `CodeBeat.app/Contents/Info.plist` exists
  - `CFBundleName` is `CodeBeat`
  - `CFBundleDisplayName` is `CodeBeat`
  - `CFBundleIdentifier` is `top.codebeat.CodeBeat`
  - `LSUIElement` is true
  - launcher contains `python -m coding_with_beat app`
- [ ] Run `pytest tests/test_codebeat_app_builder.py -q`; expect import failure.
- [ ] Implement the builder with `build_app(output_dir: Path | None = None) -> Path`.
- [ ] Run `pytest tests/test_codebeat_app_builder.py -q`.
- [ ] Commit `feat(app): build local codebeat mac app`.

## Task 4: Documentation And Local Verification

**Files:**
- Modify: `README.md`

- [ ] Add README instructions:
  - `python scripts/build_macos_app.py`
  - `open dist/CodeBeat.app`
  - Terminal CLI remains `cwb`
  - App/Menu icons are padded to avoid oversized appearance
- [ ] Run `ruff check coding_with_beat tests scripts`.
- [ ] Stop running pet processes before Qt tests.
- [ ] Run `pytest -q`.
- [ ] Run `python scripts/build_macos_app.py`.
- [ ] Run `open dist/CodeBeat.app` if available; otherwise run the launcher directly.
- [ ] Confirm app or launcher starts without traceback and `cwb` still works.
- [ ] Commit docs and any verification fixes.

## Self-Review

- Spec coverage: `CodeBeat.app`, smaller icons, menu-bar control center, CLI coexistence, builder, README, and tests are covered.
- Placeholder scan: no unresolved placeholders remain.
- Type consistency: `app_icon_path`, `pet_icon_path`, `build_app`, `cmd_app`, and `APP_NAME` are defined before use.
