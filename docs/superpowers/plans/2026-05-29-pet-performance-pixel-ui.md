# Pet Performance And Pixel UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the desktop pet responsive during music commands and replace editor-style white bubbles with transparent pixel-styled status, bubble, and action controls.

**Architecture:** Keep the existing DJ Buddy session model and add a Qt-facing async runner so MCP/music work happens off the UI thread. Replace `QTextEdit` bubbles with display-only pixel labels, trim text before display, and update both `PetWindow` and `PetdexWindow` to use the shared runner and visual helpers without introducing a shared base class.

**Tech Stack:** Python 3.13, PySide6 `QThread`/signals, pytest, existing `PetMusicSession`, `PetInteractionController`, `PetBubbleView`, and `PetWindow`/`PetdexWindow`.

---

## File Structure

- Create `coding_with_beat/pet/async_runner.py`
  - Owns background execution of pet session commands.
  - Emits `PetSessionResult` back to the Qt main thread.
  - Converts unexpected exceptions into sad error cards.
- Create `coding_with_beat/pet/pixel_ui.py`
  - Owns pixel-style UI helpers: display-only bubble label, status label styling, icon button styling, text trimming.
  - Contains no music/session logic.
- Modify `coding_with_beat/pet/window.py`
  - Use `PetCommandRunner` for music actions that can block.
  - Replace `QTextEdit` bubbles with `PixelBubbleLabel`.
  - Apply transparent status and button styling to both built-in and Petdex windows.
  - Keep existing click, drag, double-click, long-press, and menu behavior.
- Modify tests:
  - Add `tests/test_pet_async_runner.py`
  - Add `tests/test_pet_pixel_ui.py`
  - Extend `tests/test_pet_window_actions.py`

---

### Task 1: Add Pixel Text Formatting Helpers

**Files:**
- Create: `coding_with_beat/pet/pixel_ui.py`
- Test: `tests/test_pet_pixel_ui.py`

- [ ] **Step 1: Write failing tests for text trimming and label setup**

Create `tests/test_pet_pixel_ui.py`:

```python
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from coding_with_beat.pet.pixel_ui import PixelBubbleLabel, trim_pixel_text


def test_trim_pixel_text_caps_lines_and_width():
    text = "\n".join(
        [
            "Debug flow",
            "1. " + "A" * 80,
            "2. Track",
            "3. Track",
            "4. Track",
            "5. Track",
            "6. Track",
        ]
    )

    trimmed = trim_pixel_text(text, max_lines=5, max_chars=24)

    lines = trimmed.splitlines()
    assert len(lines) == 5
    assert lines[1].endswith("…")
    assert "6. Track" not in trimmed


def test_trim_pixel_text_removes_blank_runs():
    trimmed = trim_pixel_text("Title\n\n\n1. Track\n\n", max_lines=5, max_chars=40)

    assert trimmed == "Title\n\n1. Track"


def test_pixel_bubble_label_is_display_only_and_has_no_scrollbar():
    app = QApplication.instance() or QApplication([])

    label = PixelBubbleLabel()
    label.set_pixel_text("Debug flow\n1. Track")

    assert label.text() == "Debug flow\n1. Track"
    assert label.wordWrap() is True
    assert label.textFormat() == Qt.TextFormat.PlainText
    assert label.textInteractionFlags() == Qt.TextInteractionFlag.NoTextInteraction
    assert "background" in label.styleSheet()
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
pytest tests/test_pet_pixel_ui.py -q
```

Expected: FAIL during import with `ModuleNotFoundError: No module named 'coding_with_beat.pet.pixel_ui'`.

- [ ] **Step 3: Implement `pixel_ui.py`**

Create `coding_with_beat/pet/pixel_ui.py`:

```python
"""Pixel-styled Qt helpers for the desktop pet."""

from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QPushButton


PIXEL_FONT = "Menlo"
STATUS_STYLE = (
    "QLabel { color: #67e8f9; background: transparent; border: none;"
    " padding: 0 2px; font-size: 12px; font-weight: 700; }"
)
BUBBLE_STYLE = (
    "QLabel { color: #f8fafc; background: rgba(2, 6, 23, 188);"
    " border: 1px solid rgba(103, 232, 249, 160); border-radius: 0px;"
    " padding: 6px 7px; font-size: 11px; }"
)
ICON_BUTTON_STYLE = (
    "QPushButton { color: #f8fafc; background: rgba(2, 6, 23, 92);"
    " border: 1px solid rgba(103, 232, 249, 115); border-radius: 0px; padding: 0;"
    " font-size: 13px; }"
    "QPushButton:hover { color: #22d3ee; background: rgba(2, 6, 23, 150);"
    " border-color: rgba(34, 211, 238, 210); }"
    "QPushButton:pressed { color: #facc15; background: rgba(15, 23, 42, 210); }"
)


class PixelBubbleLabel(QLabel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setVisible(False)
        self.setWordWrap(True)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.setMaximumWidth(230)
        self.setMaximumHeight(120)
        self.setFont(_pixel_font(11))
        self.setStyleSheet(BUBBLE_STYLE)

    def set_pixel_text(self, text: str) -> None:
        self.setText(trim_pixel_text(text, max_lines=5, max_chars=42))
        self.setVisible(True)


def trim_pixel_text(text: str, max_lines: int = 5, max_chars: int = 42) -> str:
    clean = re.sub(r"\n{3,}", "\n\n", (text or "").strip()) or "没有返回内容"
    lines = clean.splitlines()[:max_lines]
    return "\n".join(_trim_line(line, max_chars) for line in lines).rstrip()


def style_status_label(label: QLabel) -> None:
    label.setFont(_pixel_font(12, bold=True))
    label.setStyleSheet(STATUS_STYLE)
    label.setTextFormat(Qt.TextFormat.PlainText)


def style_icon_button(button: QPushButton) -> None:
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setFixedSize(26, 26)
    button.setFont(_pixel_font(13, bold=True))
    button.setStyleSheet(ICON_BUTTON_STYLE)


def _trim_line(line: str, max_chars: int) -> str:
    if len(line) <= max_chars:
        return line
    return line[: max_chars - 1].rstrip() + "…"


def _pixel_font(size: int, *, bold: bool = False) -> QFont:
    font = QFont(PIXEL_FONT, size)
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setBold(bold)
    return font
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```bash
pytest tests/test_pet_pixel_ui.py -q
```

Expected: `3 passed`.

- [ ] **Step 5: Commit**

Run:

```bash
git add coding_with_beat/pet/pixel_ui.py tests/test_pet_pixel_ui.py
git commit -m "feat(pet): add pixel ui helpers"
```

---

### Task 2: Add Async Pet Command Runner

**Files:**
- Create: `coding_with_beat/pet/async_runner.py`
- Test: `tests/test_pet_async_runner.py`

- [ ] **Step 1: Write failing tests for background completion and error conversion**

Create `tests/test_pet_async_runner.py`:

```python
import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from coding_with_beat.pet.async_runner import PetCommandRunner
from coding_with_beat.pet.bubble import PetBubbleCard
from coding_with_beat.pet.session import PetSessionResult


def _wait_for(predicate, app, timeout=2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.processEvents()
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition was not met")


def test_runner_returns_result_without_blocking_caller():
    app = QApplication.instance() or QApplication([])
    runner = PetCommandRunner()
    results = []
    runner.finished.connect(results.append)

    started = time.time()
    accepted = runner.run(lambda: PetSessionResult(True, "dance", PetBubbleCard("status", "done")))

    assert accepted is True
    assert time.time() - started < 0.2
    _wait_for(lambda: bool(results), app)
    assert results[0].ok is True
    assert results[0].card.text == "done"


def test_runner_ignores_duplicate_while_busy():
    app = QApplication.instance() or QApplication([])
    runner = PetCommandRunner()
    release = {"ready": False}

    def slow():
        while not release["ready"]:
            time.sleep(0.01)
        return PetSessionResult(True, "idle", PetBubbleCard("status", "done"))

    assert runner.run(slow) is True
    assert runner.run(lambda: PetSessionResult(True, "idle", PetBubbleCard("status", "second"))) is False
    release["ready"] = True
    _wait_for(lambda: not runner.busy, app)


def test_runner_converts_exception_to_error_result():
    app = QApplication.instance() or QApplication([])
    runner = PetCommandRunner()
    results = []
    runner.finished.connect(results.append)

    runner.run(lambda: (_ for _ in ()).throw(RuntimeError("boom")))

    _wait_for(lambda: bool(results), app)
    assert results[0].ok is False
    assert results[0].action == "sad"
    assert results[0].card.kind == "error"
    assert "boom" in results[0].card.text
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
pytest tests/test_pet_async_runner.py -q
```

Expected: FAIL during import with `ModuleNotFoundError: No module named 'coding_with_beat.pet.async_runner'`.

- [ ] **Step 3: Implement `async_runner.py`**

Create `coding_with_beat/pet/async_runner.py`:

```python
"""Background command runner for desktop pet music actions."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QObject, QThread, Signal

from .bubble import PetBubbleView
from .session import PetSessionResult


Command = Callable[[], PetSessionResult]


class _CommandWorker(QObject):
    finished = Signal(object)

    def __init__(self, command: Command) -> None:
        super().__init__()
        self.command = command

    def run(self) -> None:
        try:
            result = self.command()
        except Exception as e:
            card = PetBubbleView().error("命令失败", str(e))
            result = PetSessionResult(False, "sad", card)
        self.finished.emit(result)


class PetCommandRunner(QObject):
    finished = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.busy = False
        self._thread: QThread | None = None
        self._worker: _CommandWorker | None = None

    def run(self, command: Command) -> bool:
        if self.busy:
            return False
        self.busy = True
        thread = QThread(self)
        worker = _CommandWorker(command)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._complete)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._thread = thread
        self._worker = worker
        thread.start()
        return True

    def _complete(self, result: PetSessionResult) -> None:
        self.busy = False
        self._thread = None
        self._worker = None
        self.finished.emit(result)
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```bash
pytest tests/test_pet_async_runner.py -q
```

Expected: `3 passed`.

- [ ] **Step 5: Commit**

Run:

```bash
git add coding_with_beat/pet/async_runner.py tests/test_pet_async_runner.py
git commit -m "feat(pet): run music commands off ui thread"
```

---

### Task 3: Wire Pixel UI Into Both Pet Windows

**Files:**
- Modify: `coding_with_beat/pet/window.py`
- Test: `tests/test_pet_window_actions.py`, `tests/test_pet_pixel_ui.py`

- [ ] **Step 1: Add focused regression test for pixel bubble class usage**

Append to `tests/test_pet_window_actions.py`:

```python
from coding_with_beat.pet.pixel_ui import PixelBubbleLabel
from coding_with_beat.pet.window import PetWindow


def test_builtin_pet_window_uses_pixel_bubble_label():
    app = QApplication.instance() or QApplication([])
    window = PetWindow()
    try:
        assert isinstance(window._bubble, PixelBubbleLabel)
    finally:
        window.close()
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
QT_QPA_PLATFORM=offscreen pytest tests/test_pet_window_actions.py::test_builtin_pet_window_uses_pixel_bubble_label -q
```

Expected: FAIL because `_bubble` is currently `QTextEdit`.

- [ ] **Step 3: Replace bubble/status/button helpers in `window.py`**

Modify imports in `coding_with_beat/pet/window.py`:

```python
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from .pixel_ui import PixelBubbleLabel, style_icon_button, style_status_label
```

Remove `QTextEdit` import.

In both `PetWindow.__init__` and `PetdexWindow.__init__`, replace:

```python
self._bubble = QTextEdit(self)
self._bubble.setReadOnly(True)
self._bubble.setVisible(False)
self._bubble.setMaximumHeight(120)
```

with:

```python
self._bubble = PixelBubbleLabel(self)
```

After creating `_track_label`, replace inline stylesheet calls with:

```python
style_status_label(self._track_label)
```

Update `_icon_button`:

```python
def _icon_button(text: str, tooltip: str) -> QPushButton:
    button = QPushButton(text)
    button.setToolTip(tooltip)
    style_icon_button(button)
    return button
```

Update both `_show_bubble()` methods:

```python
    def _show_bubble(self, text: str) -> None:
        self._bubble.set_pixel_text(_trim_output(text))
        self._render()
```

- [ ] **Step 4: Adjust window sizing for trimmed pixel labels**

In `PetWindow._render()`, keep the same structure but use smaller bubble extra:

```python
extra = 66 + (self._bubble.sizeHint().height() + 8 if self._bubble.isVisible() else 0)
self.resize(max(172, pixmap.width() + 12), pixmap.height() + extra)
```

In `PetdexWindow._resize_shell()`, use:

```python
extra = 62 + (self._bubble.sizeHint().height() + 8 if self._bubble.isVisible() else 0)
```

Do not introduce scrollbars.

- [ ] **Step 5: Run UI helper and pet tests**

Run:

```bash
QT_QPA_PLATFORM=offscreen pytest tests/test_pet_window_actions.py tests/test_pet_pixel_ui.py -q
pytest tests/test_pet_*.py -q
python -m py_compile coding_with_beat/pet/window.py
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

Run:

```bash
git add coding_with_beat/pet/window.py tests/test_pet_window_actions.py
git commit -m "feat(pet): apply transparent pixel ui"
```

---

### Task 4: Wire Async Runner Into Both Pet Windows

**Files:**
- Modify: `coding_with_beat/pet/window.py`
- Test: `tests/test_pet_window_actions.py`, `tests/test_pet_async_runner.py`

- [ ] **Step 1: Add focused tests for pending display helper**

Append to `tests/test_pet_window_actions.py`:

```python
from coding_with_beat.pet.session import PetSessionResult
from coding_with_beat.pet.bubble import PetBubbleCard


def test_builtin_pet_window_applies_pending_result():
    app = QApplication.instance() or QApplication([])
    window = PetWindow()
    try:
        window._apply_session_result(PetSessionResult(True, "think", PetBubbleCard("status", "思考中…")))
        assert "思考中" in window._bubble.text()
    finally:
        window.close()
```

- [ ] **Step 2: Run test and verify current behavior passes**

Run:

```bash
QT_QPA_PLATFORM=offscreen pytest tests/test_pet_window_actions.py::test_builtin_pet_window_applies_pending_result -q
```

Expected: PASS. This locks the helper that async pending state will use.

- [ ] **Step 3: Add async runner fields to both windows**

Modify imports in `coding_with_beat/pet/window.py`:

```python
from .async_runner import PetCommandRunner
from .bubble import PetBubbleCard
```

In both `PetWindow.__init__` and `PetdexWindow.__init__`, after creating `self.interactions`, add:

```python
self.command_runner = PetCommandRunner(self)
self.command_runner.finished.connect(self._apply_session_result)
```

- [ ] **Step 4: Add `_run_pet_command()` to both windows**

Add to both classes:

```python
    def _run_pet_command(self, command, pending_text: str = "思考中…") -> None:
        pending = PetSessionResult(True, "think", PetBubbleCard("status", pending_text, action="think"))
        self._apply_session_result(pending)
        accepted = self.command_runner.run(command)
        if not accepted:
            self._show_bubble("上一条命令还在进行中…")
```

For `PetdexWindow`, `_apply_session_result` already maps `think` to the Petdex action through `petdex_animator.set_action(result.action)`.

- [ ] **Step 5: Replace blocking action calls with async runner**

In both `PetWindow` and `PetdexWindow`, update:

```python
self._now_button.clicked.connect(lambda: self._run_pet_command(lambda: self.interactions.quick_action("now"), "读取当前播放…"))
self._recommend_button.clicked.connect(lambda: self._run_pet_command(lambda: self.interactions.quick_action("recommend"), "正在按当前状态找歌…"))
self._reroll_button.clicked.connect(lambda: self._run_pet_command(lambda: self.interactions.quick_action("reroll"), "正在换一组…"))
```

Update click handlers:

```python
def _handle_long_press(self) -> None:
    self._long_press_fired = True
    self._run_pet_command(self.interactions.long_press, "正在自动开播…")

def _handle_single_click(self) -> None:
    self._run_pet_command(self.interactions.single_click, "读取当前播放…")
```

Update double-click body to:

```python
self._run_pet_command(self.interactions.double_click, "正在按当前状态找歌…")
```

Update menu lambdas for current/context/auto to call `_run_pet_command(...)`.

Update `ask_mood()` after text input:

```python
self._run_pet_command(lambda: self.music_session.recommend_from_text(text.strip()), "正在按心情找歌…")
```

Update `play_number_dialog()`:

```python
self._run_pet_command(lambda: self.music_session.play_number(number), "正在播放选择…")
```

Update `toggle_playback()` and `next_track()`:

```python
def toggle_playback(self) -> None:
    self._run_pet_command(lambda: self._music_command_card("暂停/继续", self.controller.music.toggle), "切换播放中…")

def next_track(self) -> None:
    self._run_pet_command(lambda: self._music_command_card("下一首", self.controller.music.next_track), "切到下一首…")
```

Add helper to both classes:

```python
    def _music_command_card(self, title: str, fn) -> PetSessionResult:
        result = fn()
        if not result.ok:
            return PetSessionResult(False, "sad", self.music_session.bubble.error(title, result.text))
        return PetSessionResult(True, "dance", self.music_session.bubble.confirmation(title, result.text))
```

- [ ] **Step 6: Run tests**

Run:

```bash
QT_QPA_PLATFORM=offscreen pytest tests/test_pet_window_actions.py tests/test_pet_async_runner.py -q
pytest tests/test_pet_*.py -q
python -m py_compile coding_with_beat/pet/window.py
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

Run:

```bash
git add coding_with_beat/pet/window.py tests/test_pet_window_actions.py
git commit -m "feat(pet): make pet commands asynchronous"
```

---

### Task 5: Documentation And Final Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README desktop pet text**

In the desktop pet section of `README.md`, add a short note under Petdex mode:

```markdown
- Music actions run in the background, so the pet keeps animating while recommendations load.
- Bubbles are display-only pixel cards: no white editor background and no scrollbars.
```

- [ ] **Step 2: Run full verification**

Run:

```bash
ruff check coding_with_beat tests
pytest -q
python -m py_compile coding_with_beat/pet/window.py coding_with_beat/pet/async_runner.py coding_with_beat/pet/pixel_ui.py
```

Expected:

```text
All checks passed!
300+ tests passed
py_compile exits 0
```

- [ ] **Step 3: Restart local desktop pet**

Run:

```bash
launchctl remove cwb-petdex-boba 2>/dev/null || true
launchctl submit -l cwb-petdex-boba -- /bin/zsh -lc 'cd /Users/jianchengpan/Projects/coding-with-beat && /Users/jianchengpan/miniconda3/bin/python -m coding_with_beat pet >/tmp/cwb-petdex-launchctl.log 2>&1'
sleep 2
launchctl list | rg 'cwb-petdex-boba' || true
tail -80 /tmp/cwb-petdex-launchctl.log 2>/dev/null || true
```

Expected: launchctl lists `cwb-petdex-boba`; log has no traceback.

- [ ] **Step 4: Manual smoke checklist**

Check the running pet:

```text
1. Pet animation continues while double-click recommendation is loading.
2. Bubble has no white background.
3. Bubble has no scrollbar.
4. Top status text is colored and transparent.
5. Bottom buttons look transparent/pixel styled.
6. Single click, double click, long press, drag, more menu, and play number still work.
```

- [ ] **Step 5: Commit docs and any verification fixes**

If only README changed:

```bash
git add README.md
git commit -m "docs: update pet performance ui notes"
```

If verification required code fixes, include those exact files:

```bash
git add README.md coding_with_beat/pet tests
git commit -m "fix(pet): polish async pixel ui"
```

Do not create an empty commit.

---

## Self-Review

Spec coverage:

- UI-thread blocking is addressed by Task 2 and Task 4.
- Transparent pixel-style visuals are addressed by Task 1 and Task 3.
- No white `QTextEdit` bubble and no scrollbars are addressed by Task 3.
- Existing DJ Buddy flow is preserved by Task 4.
- Error conversion from worker exceptions is addressed by Task 2.
- Duplicate command behavior is addressed by Task 2's busy lock.
- README and local launch verification are addressed by Task 5.

Placeholder scan:

- The plan contains no unresolved implementation markers.
- Every task includes concrete files, code snippets, commands, and expected outcomes.

Type consistency:

- `PetCommandRunner`, `PixelBubbleLabel`, `trim_pixel_text`, `style_status_label`, and `style_icon_button` are defined before use.
- `PetSessionResult` and `PetBubbleCard` already exist from the DJ flow implementation and are used consistently.
