# Pet DJ Profile Panel Design

**Date:** 2026-05-29
**Branch:** `pet`
**Feature:** Redesign the desktop pet DJ panel as a structured "DJ profile" interface

## Goal

Make the CodeBeat DJ panel feel like a polished music companion instead of a generic utility dialog. The panel should borrow the structure language from the selected reference direction: dark dotted stage, pixel headline, DJ persona, live station stats, genre chips, and a clear recommendation queue with direct play controls.

This is a visual and interaction redesign of the existing `CodeBeatDjPanel`. It should preserve the current working music flow:

- pet bubble remains short and compact
- full recommendation output appears in the DJ panel
- each recommendation can be played directly
- users can type mood/style prompts
- background music commands still run through the existing async pet command runner

## Visual Direction

The approved direction is **A. DJ Profile Panel**.

Core visual rules:

- Use a dark near-black panel background with subtle dot-grid texture.
- Add a soft teal signal field in the upper/middle background to suggest audio, code, and "live station" energy.
- Use a large monospaced/pixel-feeling `CodeBeat DJ` title.
- Use a small circular identity mark near the title. It can be a rendered pet badge or a lightweight waveform/avatar mark; it should not look like a default app icon.
- Put one short persona line under the title, for example: `你的 mood 是我的 prompt`.
- Use thin dividers, low-opacity borders, and restrained teal/mint accents.
- Avoid white cards, system-looking grey panels, and large opaque blocks.
- Avoid copying the reference image directly; this should be a CodeBeat-specific interface.

## Layout

The panel keeps one window, but its content is reorganized into five layers:

1. **Identity header**
   - Circular DJ badge on the left.
   - Large `CodeBeat DJ` title.
   - Short status/persona subtitle.
   - Small live indicator such as `ON AIR`.

2. **Intro/status copy**
   - Two short lines that explain the current DJ state.
   - Examples:
     - `为当前 coding 状态打碟`
     - `Your mood is my prompt.`
   - This section should be compact; it should not push the recommendation queue off screen.

3. **Live stats**
   - Three compact columns:
     - `ON AIR`: `LIVE` or `24/7`
     - `MOOD`: current context label such as `FOCUS`, `RELAX`, `CUSTOM`
     - `QUEUE`: number of parsed recommendation items
   - Stats update when a recommendation result arrives.

4. **Taste chips**
   - A horizontal/wrapping chip row.
   - Default chips can include `LOFI`, `FOCUS`, `JAZZ`, `NO VOCAL`.
   - When a result has parsed items but no structured genres, chips stay as broad mood affordances rather than pretending to know exact genres.

5. **Queue and prompt**
   - Recommendation results render as compact queue rows.
   - Each row shows:
     - result number
     - label/title text with wrapping
     - direct circular play button
   - The queue area is scrollable.
   - The prompt input sits at the bottom as a transparent capsule.
   - Action buttons remain available but should look like compact command chips, not default rectangular buttons.

## Interaction Behavior

The interaction model remains the same as the current committed feature:

- `✨` / double-click / right-click "按当前状态推荐" opens the panel and runs contextual recommendation.
- `♪` opens the panel and shows current playback.
- `🎲` opens the panel and rerolls recommendation results.
- Typing in the panel prompt runs text-based recommendation.
- Clicking a row play button calls `play_number(number)`.
- The pet bubble summarizes recommendation results with short feedback such as `找到 5 首推荐，已放到 DJ 面板`.

New interaction details:

- The panel should not duplicate pending messages in the transcript.
- The panel should keep the latest queue visible, with older text lower priority.
- If there are no parsed recommendation rows, the panel still shows the raw message as a readable status block.
- The prompt should be usable without touching the old "播放编号" dialog.

## Implementation Boundaries

Primary file:

- `coding_with_beat/pet/dj_panel.py`

Likely supporting files:

- `tests/test_pet_dj_panel.py`
- `tests/test_pet_window_actions.py`
- `README.md`
- `README_CN.md`

The implementation should stay inside PySide6 widgets and stylesheet-driven visuals. It should not introduce a web view, image-heavy runtime dependency, or a separate rendering engine.

The current `PetSessionResult`, `PetBubbleCard`, and `PetResultItem` contracts are sufficient. If stats need derived state, compute it inside `CodeBeatDjPanel` from the latest card rather than changing the music session API.

## Test Plan

Add or update focused tests for:

- panel contains the DJ identity/header fields
- recommendation items still render with direct play buttons
- queue count/stat updates from parsed recommendation items
- prompt submission still routes to `recommend_from_text`
- play button still routes to `play_number`
- pending status does not duplicate in transcript
- pet window still owns a `CodeBeatDjPanel`

Run:

```bash
ruff check coding_with_beat tests scripts
pytest -q tests/test_pet_dj_panel.py tests/test_pet_window_actions.py
pytest -q
```

## Local Verification

After implementation:

1. Rebuild the local app wrapper with `python scripts/build_macos_app.py`.
2. Restart `dist/CodeBeat.app`.
3. Confirm the process runs from the current repository.
4. Open the panel via double-click, `✨`, and right-click "打开 DJ 面板".
5. Confirm the visual direction matches the DJ profile mockup: dark dotted stage, identity header, stats, chips, queue rows, and transparent prompt capsule.

## Non-Goals

- Do not redesign the pet sprite itself in this task.
- Do not add a full theme system.
- Do not change the music search/routing behavior.
- Do not remove the existing right-click fallback actions.
- Do not copy external artwork or the reference design verbatim.
