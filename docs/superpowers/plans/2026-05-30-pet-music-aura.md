# Pet Music Aura Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a transparent, music-driven aura around the desktop pet with particles, ripples, and playback motion.

**Architecture:** Create a focused `MusicAuraWidget` under `coding_with_beat/pet/` and mount it behind the existing pet sprite labels in both `PetWindow` and `PetdexWindow`. Existing live playback polling remains the source of truth; windows call `set_playing()` and `burst()` when playback state or track text changes.

**Tech Stack:** Python, PySide6, Qt `QWidget`/`QPainter`, pytest with offscreen Qt.

---

## File Structure

- Create `coding_with_beat/pet/aura.py`
  - Owns `MusicAuraWidget`, particle geometry, burst/playing state, and transparent custom painting.
- Modify `coding_with_beat/pet/window.py`
  - Wrap each sprite label in a fixed-size transparent stage.
  - Add aura widgets for both built-in and Petdex windows.
  - Route live and manual playback results into aura state.
- Modify `tests/test_pet_aura.py`
  - Covers aura state API and construction in offscreen Qt.
- Modify `tests/test_pet_window_actions.py`
  - Covers window ownership, centering, and live state burst behavior.
- Modify `README.md`
  - Briefly mention music aura feedback in the desktop pet section.

---

### Task 1: Add Aura Widget State API

**Files:**
- Create: `coding_with_beat/pet/aura.py`
- Create: `tests/test_pet_aura.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_pet_aura.py`:

```python
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from coding_with_beat.pet.aura import MusicAuraWidget


def test_music_aura_starts_idle_and_transparent():
    app = QApplication.instance() or QApplication([])
    aura = MusicAuraWidget(sprite_size=(72, 78))
    try:
        assert app is not None
        assert aura.is_playing is False
        assert aura.burst_phase == 0.0
        assert aura.minimumWidth() >= 112
        assert aura.minimumHeight() >= 118
        assert aura.autoFillBackground() is False
    finally:
        aura.close()


def test_music_aura_set_playing_updates_state():
    app = QApplication.instance() or QApplication([])
    aura = MusicAuraWidget(sprite_size=(72, 78))
    try:
        assert app is not None
        aura.set_playing(True)
        assert aura.is_playing is True

        aura.set_playing(False)
        assert aura.is_playing is False
    finally:
        aura.close()


def test_music_aura_burst_sets_visible_phase():
    app = QApplication.instance() or QApplication([])
    aura = MusicAuraWidget(sprite_size=(72, 78))
    try:
        assert app is not None
        aura.burst()
        assert aura.burst_phase == 1.0
    finally:
        aura.close()


def test_music_aura_tick_advances_motion_and_fades_burst():
    app = QApplication.instance() or QApplication([])
    aura = MusicAuraWidget(sprite_size=(72, 78))
    try:
        assert app is not None
        aura.set_playing(True)
        aura.burst()
        start_rotation = aura.rotation

        aura.advance()

        assert aura.rotation != start_rotation
        assert 0.0 < aura.burst_phase < 1.0
    finally:
        aura.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_pet_aura.py -q
```

Expected: FAIL during import with `ModuleNotFoundError: No module named 'coding_with_beat.pet.aura'`.

- [ ] **Step 3: Implement minimal aura widget**

Create `coding_with_beat/pet/aura.py`:

```python
"""Transparent music aura for the desktop pet."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class MusicAuraWidget(QWidget):
    def __init__(self, *, sprite_size: tuple[int, int], parent=None) -> None:
        super().__init__(parent)
        self.is_playing = False
        self.rotation = 0.0
        self.burst_phase = 0.0
        self._sprite_size = sprite_size
        self._particle_count = 18
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self.set_sprite_size(sprite_size)

    def set_sprite_size(self, sprite_size: tuple[int, int]) -> None:
        self._sprite_size = sprite_size
        width = max(112, sprite_size[0] + 48)
        height = max(118, sprite_size[1] + 48)
        self.setMinimumSize(width, height)
        self.setFixedSize(width, height)
        self.update()

    def set_playing(self, playing: bool) -> None:
        self.is_playing = bool(playing)
        self.update()

    def burst(self) -> None:
        self.burst_phase = 1.0
        self.update()

    def advance(self) -> None:
        self.rotation = (self.rotation + (8.0 if self.is_playing else 2.0)) % 360.0
        if self.burst_phase > 0.0:
            self.burst_phase = max(0.0, self.burst_phase - 0.08)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
            center = QPointF(self.width() / 2, self.height() / 2)
            radius = min(self.width(), self.height()) / 2 - 18
            self._paint_particles(painter, center, radius)
            self._paint_orbit(painter, center, radius)
            self._paint_wave_ticks(painter, center, radius)
            self._paint_burst(painter, center, radius)
        finally:
            painter.end()
        super().paintEvent(event)

    def _paint_particles(self, painter: QPainter, center: QPointF, radius: float) -> None:
        base_alpha = 135 if self.is_playing else 44
        for index in range(self._particle_count):
            angle = math.radians((360 / self._particle_count) * index + self.rotation)
            wobble = 5 * math.sin(math.radians(self.rotation * 2 + index * 23))
            distance = radius * 0.68 + wobble
            x = center.x() + math.cos(angle) * distance
            y = center.y() + math.sin(angle) * distance
            color = QColor("#5eead4" if index % 3 else "#a78bfa")
            color.setAlpha(base_alpha if index % 2 else max(28, base_alpha - 36))
            painter.fillRect(round(x), round(y), 2, 2, color)

    def _paint_orbit(self, painter: QPainter, center: QPointF, radius: float) -> None:
        if not self.is_playing and self.burst_phase <= 0.0:
            return
        color = QColor("#5eead4")
        color.setAlpha(150 if self.is_playing else 80)
        pen = QPen(color, 2)
        painter.setPen(pen)
        for offset in (0, 120, 240):
            start = int((self.rotation + offset) * 16)
            painter.drawArc(
                round(center.x() - radius),
                round(center.y() - radius),
                round(radius * 2),
                round(radius * 2),
                start,
                34 * 16,
            )

    def _paint_wave_ticks(self, painter: QPainter, center: QPointF, radius: float) -> None:
        if not self.is_playing:
            return
        color = QColor("#c4b5fd")
        color.setAlpha(130)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        baseline = center.y() + radius * 0.76
        for index in range(9):
            height = 3 + int(5 * (0.5 + 0.5 * math.sin(math.radians(self.rotation * 3 + index * 40))))
            x = center.x() - 24 + index * 6
            painter.drawRect(round(x), round(baseline - height), 3, height)

    def _paint_burst(self, painter: QPainter, center: QPointF, radius: float) -> None:
        if self.burst_phase <= 0.0:
            return
        alpha = int(180 * self.burst_phase)
        color = QColor("#5eead4")
        color.setAlpha(alpha)
        painter.setPen(QPen(color, 2))
        burst_radius = radius * (1.0 + (1.0 - self.burst_phase) * 0.55)
        painter.drawEllipse(center, burst_radius, burst_radius)
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
pytest tests/test_pet_aura.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add coding_with_beat/pet/aura.py tests/test_pet_aura.py
git commit -m "feat(pet): add music aura widget"
```

---

### Task 2: Mount Aura Behind Built-In Pet

**Files:**
- Modify: `coding_with_beat/pet/window.py`
- Modify: `tests/test_pet_window_actions.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_pet_window_actions.py`:

```python
from coding_with_beat.pet.aura import MusicAuraWidget


def test_builtin_pet_window_owns_centered_music_aura():
    app = QApplication.instance() or QApplication([])
    window = PetWindow()
    try:
        assert app is not None
        assert isinstance(window._aura, MusicAuraWidget)
        stage_item = window.layout().itemAt(2)
        assert stage_item.widget() is window._sprite_stage
        assert stage_item.alignment() & Qt.AlignmentFlag.AlignHCenter
        assert window._aura.parent() is window._sprite_stage
        assert window._label.parent() is window._sprite_stage
    finally:
        window.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_pet_window_actions.py::test_builtin_pet_window_owns_centered_music_aura -q
```

Expected: FAIL with `AttributeError: 'PetWindow' object has no attribute '_aura'`.

- [ ] **Step 3: Implement sprite stage helper and built-in mount**

Modify imports in `coding_with_beat/pet/window.py`:

```python
from .aura import MusicAuraWidget
```

Add helper functions near `_controls_widget()`:

```python
def _sprite_stage(aura: MusicAuraWidget, label: QLabel) -> QWidget:
    widget = QWidget()
    widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    widget.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
    widget.setAutoFillBackground(False)
    aura.setParent(widget)
    label.setParent(widget)
    return widget


def _layout_sprite_stage(stage: QWidget, aura: MusicAuraWidget, label: QLabel) -> None:
    width = max(aura.width(), label.width())
    height = max(aura.height(), label.height())
    stage.setFixedSize(width, height)
    aura.move((width - aura.width()) // 2, (height - aura.height()) // 2)
    label.move((width - label.width()) // 2, (height - label.height()) // 2)
```

In `PetWindow.__init__`, create the aura and stage after `_label` is styled:

```python
self._aura = MusicAuraWidget(sprite_size=(1, 1), parent=self)
self._sprite_stage = _sprite_stage(self._aura, self._label)
```

Replace:

```python
layout.addWidget(self._label, alignment=Qt.AlignmentFlag.AlignHCenter)
```

with:

```python
layout.addWidget(self._sprite_stage, alignment=Qt.AlignmentFlag.AlignHCenter)
```

In `PetWindow._render()`, after `self._label.setPixmap(pixmap)`:

```python
self._label.setFixedSize(pixmap.size())
self._aura.set_sprite_size((pixmap.width(), pixmap.height()))
self._aura.advance()
_layout_sprite_stage(self._sprite_stage, self._aura, self._label)
```

Adjust resize height to use the stage height:

```python
self.resize(max(172, self._sprite_stage.width() + 12), self._sprite_stage.height() + extra)
```

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/test_pet_window_actions.py::test_builtin_pet_window_owns_centered_music_aura tests/test_pet_window_actions.py::test_builtin_pet_window_centers_pet_sprite_widget -q
```

Expected: PASS after updating older centering expectation if needed.

- [ ] **Step 5: Update older centering test if necessary**

If `test_builtin_pet_window_centers_pet_sprite_widget` still expects `_label` directly in the layout, update it to assert the stage:

```python
def test_builtin_pet_window_centers_pet_sprite_widget():
    app = QApplication.instance() or QApplication([])
    window = PetWindow()
    try:
        assert app is not None
        label_item = window.layout().itemAt(2)

        assert label_item.widget() is window._sprite_stage
        assert label_item.alignment() & Qt.AlignmentFlag.AlignHCenter
    finally:
        window.close()
```

- [ ] **Step 6: Commit**

```bash
git add coding_with_beat/pet/window.py tests/test_pet_window_actions.py
git commit -m "feat(pet): mount aura behind built-in pet"
```

---

### Task 3: Mount Aura Behind Petdex Pet

**Files:**
- Modify: `coding_with_beat/pet/window.py`
- Modify: `tests/test_pet_window_actions.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_pet_window_actions.py`:

```python
def test_petdex_window_owns_centered_music_aura():
    app = QApplication.instance() or QApplication([])
    window = PetdexWindow(ensure_petdex_pet("codebeat-buddy"))
    try:
        assert app is not None
        assert isinstance(window._aura, MusicAuraWidget)
        stage_item = window.layout().itemAt(2)
        assert stage_item.widget() is window._sprite_stage
        assert stage_item.alignment() & Qt.AlignmentFlag.AlignHCenter
        assert window._aura.parent() is window._sprite_stage
        assert window._label.parent() is window._sprite_stage
    finally:
        window.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_pet_window_actions.py::test_petdex_window_owns_centered_music_aura -q
```

Expected: FAIL with `AttributeError: 'PetdexWindow' object has no attribute '_aura'`.

- [ ] **Step 3: Implement Petdex mount**

In `PetdexWindow.__init__`, create the aura and stage after `_label` is styled and fixed:

```python
self._aura = MusicAuraWidget(sprite_size=self._petdex_display_size, parent=self)
self._sprite_stage = _sprite_stage(self._aura, self._label)
```

Replace:

```python
layout.addWidget(self._label, alignment=Qt.AlignmentFlag.AlignHCenter)
```

with:

```python
layout.addWidget(self._sprite_stage, alignment=Qt.AlignmentFlag.AlignHCenter)
```

In `PetdexWindow._render()`, after `self._label.setPixmap(pixmap)`:

```python
self._aura.set_sprite_size(self._petdex_display_size)
self._aura.advance()
_layout_sprite_stage(self._sprite_stage, self._aura, self._label)
```

In `PetdexWindow._resize_shell()`, compute width/height from stage:

```python
width = max(150, self._sprite_stage.width() + 12)
height = self._sprite_stage.height() + extra
```

In `_load_petdex_pet()`, after `self._label.setFixedSize(*self._petdex_display_size)`:

```python
self._aura.set_sprite_size(self._petdex_display_size)
```

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/test_pet_window_actions.py::test_petdex_window_owns_centered_music_aura tests/test_pet_window_actions.py::test_petdex_window_centers_pet_sprite_widget -q
```

Expected: PASS after updating older centering expectation if needed.

- [ ] **Step 5: Update older Petdex centering test if necessary**

If `test_petdex_window_centers_pet_sprite_widget` expects `_label` directly in the layout, update it:

```python
def test_petdex_window_centers_pet_sprite_widget():
    app = QApplication.instance() or QApplication([])
    window = PetdexWindow(ensure_petdex_pet("codebeat-buddy"))
    try:
        assert app is not None
        label_item = window.layout().itemAt(2)

        assert label_item.widget() is window._sprite_stage
        assert label_item.alignment() & Qt.AlignmentFlag.AlignHCenter
    finally:
        window.close()
```

- [ ] **Step 6: Commit**

```bash
git add coding_with_beat/pet/window.py tests/test_pet_window_actions.py
git commit -m "feat(pet): mount aura behind petdex pet"
```

---

### Task 4: Connect Playback State And Burst

**Files:**
- Modify: `coding_with_beat/pet/window.py`
- Modify: `tests/test_pet_window_actions.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_pet_window_actions.py`:

```python
def test_builtin_live_track_change_updates_aura():
    app = QApplication.instance() or QApplication([])
    window = PetWindow()
    try:
        assert app is not None
        result = PetSessionResult(True, "dance", PetBubbleCard("live", "当前播放\n▶ 晴天 — 周杰伦", action="dance"))

        window._apply_live_result(result)

        assert window._aura.is_playing is True
        assert window._aura.burst_phase == 1.0
    finally:
        window.close()


def test_builtin_repeated_live_track_does_not_repeat_aura_burst():
    app = QApplication.instance() or QApplication([])
    window = PetWindow()
    try:
        assert app is not None
        result = PetSessionResult(True, "dance", PetBubbleCard("live", "当前播放\n▶ 晴天 — 周杰伦", action="dance"))

        window._apply_live_result(result)
        window._aura.burst_phase = 0.25
        window._apply_live_result(result)

        assert window._aura.is_playing is True
        assert window._aura.burst_phase == 0.25
    finally:
        window.close()


def test_petdex_live_track_change_updates_aura():
    app = QApplication.instance() or QApplication([])
    window = PetdexWindow(ensure_petdex_pet("codebeat-buddy"))
    try:
        assert app is not None
        result = PetSessionResult(True, "dance", PetBubbleCard("live", "当前播放\n▶ 晴天 — 周杰伦", action="dance"))

        window._apply_live_result(result)

        assert window._aura.is_playing is True
        assert window._aura.burst_phase == 1.0
    finally:
        window.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_pet_window_actions.py::test_builtin_live_track_change_updates_aura tests/test_pet_window_actions.py::test_builtin_repeated_live_track_does_not_repeat_aura_burst tests/test_pet_window_actions.py::test_petdex_live_track_change_updates_aura -q
```

Expected: FAIL because `_apply_live_result()` does not call the aura.

- [ ] **Step 3: Implement shared aura update helper**

Add helper near `_live_track_label()`:

```python
def _apply_aura_playback(owner, *, playing: bool, changed: bool) -> None:
    owner._aura.set_playing(playing)
    if playing and changed:
        owner._aura.burst()
```

In both `PetWindow._apply_session_result()` and `PetdexWindow._apply_session_result()`, after setting the animator:

```python
_apply_aura_playback(self, playing=result.action == "dance" and result.ok, changed=result.ok)
```

In both `_apply_live_result()` methods, compute changed before updating `_last_live_label`:

```python
changed = result.ok and result.card.text != self._last_live_label
_apply_aura_playback(self, playing=self._last_live_playing, changed=changed)
```

Keep the existing early return for repeated labels after the aura update, so repeated tracks do not burst again.

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/test_pet_window_actions.py::test_builtin_live_track_change_updates_aura tests/test_pet_window_actions.py::test_builtin_repeated_live_track_does_not_repeat_aura_burst tests/test_pet_window_actions.py::test_petdex_live_track_change_updates_aura -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add coding_with_beat/pet/window.py tests/test_pet_window_actions.py
git commit -m "feat(pet): animate aura from playback state"
```

---

### Task 5: Documentation And Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README**

In the desktop pet bullet list, add:

```markdown
- Playback adds a transparent music aura around the pet: faint idle particles, active rotating waveform motion while music plays, and a short ripple burst when the current song changes.
```

- [ ] **Step 2: Run focused tests**

Run:

```bash
pytest tests/test_pet_aura.py tests/test_pet_window_actions.py -q
```

Expected: PASS.

- [ ] **Step 3: Run full checks**

Run:

```bash
ruff check coding_with_beat tests scripts
ruff format --check coding_with_beat tests scripts
pytest -q
```

Expected: all checks pass.

- [ ] **Step 4: Rebuild and restart the local macOS app**

Run:

```bash
python scripts/build_macos_app.py
pkill -f "python -m coding_with_beat app" || true
pkill -f "python -m coding_with_beat pet" || true
sleep 0.5
open dist/CodeBeat.app
sleep 2
ps -ax -o pid,ppid,command | rg "coding_with_beat app|coding_with_beat pet|CodeBeat.app" || true
tail -20 ~/.coding-with-beat/logs/app.log
```

Expected: `python -m coding_with_beat app` is running and app log has no new traceback.

- [ ] **Step 5: Commit and push**

```bash
git add README.md
git commit -m "docs(pet): document music aura feedback"
git push origin pet
```

Expected: remote `pet` branch receives the implementation commits.

---

## Self-Review

- Spec coverage: The plan covers the custom aura component, transparent rendering, playback state, track-change burst, performance constraints, both built-in and Petdex windows, automated tests, README update, local rebuild, and restart.
- Incomplete-marker scan: No task uses incomplete markers; code snippets name exact paths, functions, and commands.
- Type consistency: `MusicAuraWidget`, `set_playing()`, `burst()`, `advance()`, `is_playing`, `burst_phase`, `_sprite_stage`, `_layout_sprite_stage`, and `_apply_aura_playback()` are consistently named across tasks.
