# Pet DJ Cockpit Visuals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add restrained animated cockpit material to the CodeBeat DJ panel.

**Architecture:** Keep `CodeBeatDjPanel` as the orchestrator and add small painted Qt widgets in `coding_with_beat/pet/dj_panel.py`: `CockpitSignalRail`, `LiquidNowPlayingBand`, and `QueueTrackRow`. The existing `_animation_timer` drives all motion through phase setters, so no extra timers are introduced.

**Tech Stack:** Python, PySide6, Qt `QPainter`, pytest.

---

## Tasks

### Task 1: Test Cockpit Visual Components

**Files:**
- Modify: `tests/test_pet_dj_panel.py`

- [ ] Add tests importing `CockpitSignalRail`, `LiquidNowPlayingBand`, and `QueueTrackRow`.
- [ ] Assert `CodeBeatDjPanel` contains a `CockpitSignalRail`.
- [ ] Assert `panel.now_band` is a `LiquidNowPlayingBand`.
- [ ] Assert `_tick_motion()` propagates phase into the rail and now band.
- [ ] Assert live snapshot sets `panel.now_band.live_playing`.
- [ ] Assert recommendation rows are `QueueTrackRow` and still include `QueuePlayButton`.
- [ ] Run the tests and confirm they fail before implementation.

### Task 2: Implement Painted Components

**Files:**
- Modify: `coding_with_beat/pet/dj_panel.py`

- [ ] Add `CockpitSignalRail(QWidget)` with `set_phase()` and custom `paintEvent()`.
- [ ] Add `LiquidNowPlayingBand(QFrame)` with `set_phase()`, `set_live_playing()`, and custom `paintEvent()`.
- [ ] Add `QueueTrackRow(QFrame)` with custom material paint.
- [ ] Use object names `SignalRail`, `NowPlayingBand`, and `QueueRow`.

### Task 3: Wire Components Into Panel

**Files:**
- Modify: `coding_with_beat/pet/dj_panel.py`

- [ ] Store `self.now_band` from `_build_now_playing_band()`.
- [ ] Store `self.signal_rail` and add it between stats/chips and scroll results.
- [ ] Create `QueueTrackRow` in `_append_result_item()`.
- [ ] In `_tick_motion()`, update phase on `signal_rail` and `now_band`.
- [ ] In `_apply_snapshot()`, update `now_band.live_playing`.

### Task 4: Style Polish And Verification

**Files:**
- Modify: `coding_with_beat/pet/dj_panel.py`
- Modify: `README.md` if useful

- [ ] Tune stylesheet colors for command deck, queue rows, now band, and play buttons.
- [ ] Run `pytest tests/test_pet_dj_panel.py -q`.
- [ ] Run `ruff check coding_with_beat tests scripts`.
- [ ] Run `ruff format --check coding_with_beat tests scripts`.
- [ ] Run `pytest -q`.
- [ ] Rebuild and restart `dist/CodeBeat.app`.
- [ ] Commit and push `pet`.
