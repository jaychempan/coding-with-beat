# Pet DJ Profile Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the desktop pet DJ panel into a polished CodeBeat DJ profile interface with identity header, live stats, taste chips, scrollable queue rows, and direct play controls.

**Architecture:** Keep the existing PySide6 `CodeBeatDjPanel` as the single owner of panel visuals and interaction state. Split the panel into focused widget-building helpers inside `coding_with_beat/pet/dj_panel.py`, derive stats from `PetBubbleCard.items`, and preserve the existing `PetSessionResult` / `PetResultItem` contracts.

**Tech Stack:** Python, PySide6 widgets/stylesheets, pytest, ruff.

---

## File Structure

- `coding_with_beat/pet/dj_panel.py`
  - Owns the DJ profile panel widgets, stylesheet, queue rendering, stats/chips, prompt input, and command routing.
- `tests/test_pet_dj_panel.py`
  - Verifies the panel visual structure and interaction routing.
- `tests/test_pet_window_actions.py`
  - Verifies window-level integration stays intact.
- `README.md`
  - Documents the refreshed panel behavior if wording needs adjustment.
- `README_CN.md`
  - Documents the refreshed panel behavior in Chinese if wording needs adjustment.

## Task 1: Lock the DJ Profile Structure With Tests

**Files:**
- Modify: `tests/test_pet_dj_panel.py`
- Test: `tests/test_pet_dj_panel.py`

- [ ] **Step 1: Add failing tests for profile structure and stats**

Append these tests to `tests/test_pet_dj_panel.py`:

```python
def test_dj_panel_has_profile_identity_stats_and_chips():
    app = QApplication.instance() or QApplication([])
    panel = CodeBeatDjPanel(FakeHost())

    assert app is not None
    assert panel.findChild(QLabel, "DjTitle").text() == "CodeBeat DJ"
    assert "mood" in panel.findChild(QLabel, "DjSubtitle").text().lower()
    assert panel.findChild(QLabel, "StatOnAirValue").text() == "LIVE"
    assert panel.findChild(QLabel, "StatMoodValue").text() == "IDLE"
    assert panel.findChild(QLabel, "StatQueueValue").text() == "0"
    assert "LOFI" in panel.chip_text()
    assert "NO VOCAL" in panel.chip_text()


def test_dj_panel_updates_queue_stat_when_recommendations_render():
    app = QApplication.instance() or QApplication([])
    panel = CodeBeatDjPanel(FakeHost())
    result = PetSessionResult(
        True,
        "recommend",
        PetBubbleCard(
            "recommendations",
            "Debug flow",
            items=[
                PetResultItem(1, "Night Owl - Luna"),
                PetResultItem(2, "Rain Debug - Soft Keys"),
                PetResultItem(3, "Green Terminal - Byte"),
            ],
        ),
    )

    panel.show_result(result)

    assert app is not None
    assert panel.findChild(QLabel, "StatMoodValue").text() == "FOCUS"
    assert panel.findChild(QLabel, "StatQueueValue").text() == "3"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
pytest -q tests/test_pet_dj_panel.py::test_dj_panel_has_profile_identity_stats_and_chips tests/test_pet_dj_panel.py::test_dj_panel_updates_queue_stat_when_recommendations_render
```

Expected: fail because object-named labels and `chip_text()` do not exist yet.

## Task 2: Implement the Profile Header, Stats, and Chips

**Files:**
- Modify: `coding_with_beat/pet/dj_panel.py`
- Test: `tests/test_pet_dj_panel.py`

- [ ] **Step 1: Replace the flat title/actions layout with profile sections**

In `CodeBeatDjPanel.__init__`, create:

```python
self.title_label = QLabel("CodeBeat DJ")
self.title_label.setObjectName("DjTitle")
self.subtitle_label = QLabel("Your mood is my prompt.")
self.subtitle_label.setObjectName("DjSubtitle")
self.on_air_value = QLabel("LIVE")
self.on_air_value.setObjectName("StatOnAirValue")
self.mood_value = QLabel("IDLE")
self.mood_value.setObjectName("StatMoodValue")
self.queue_value = QLabel("0")
self.queue_value.setObjectName("StatQueueValue")
self._chip_labels = []
```

Build the layout in this order:

1. identity header with circular badge, title, subtitle, `ON AIR` pill
2. intro copy
3. stats row
4. chips row
5. scroll area
6. prompt row
7. compact action row

- [ ] **Step 2: Add `chip_text()` and stat update helpers**

Add these methods:

```python
def chip_text(self) -> str:
    return " ".join(label.text() for label in self._chip_labels)

def _update_stats(self, card: PetBubbleCard) -> None:
    self.queue_value.setText(str(len(card.items)))
    if card.kind == "recommendations":
        self.mood_value.setText("FOCUS")
    elif card.kind == "confirmation":
        self.mood_value.setText("PLAY")
    elif card.kind == "error":
        self.mood_value.setText("ERROR")
    else:
        self.mood_value.setText("IDLE")
```

Call `_update_stats(card)` at the start of `_append_card`.

- [ ] **Step 3: Run profile tests**

Run:

```bash
pytest -q tests/test_pet_dj_panel.py::test_dj_panel_has_profile_identity_stats_and_chips tests/test_pet_dj_panel.py::test_dj_panel_updates_queue_stat_when_recommendations_render
```

Expected: pass.

## Task 3: Restyle Queue Rows and Prompt Controls

**Files:**
- Modify: `coding_with_beat/pet/dj_panel.py`
- Modify: `tests/test_pet_dj_panel.py`
- Test: `tests/test_pet_dj_panel.py`

- [ ] **Step 1: Add failing tests for queue row object names and circular play controls**

Append this test:

```python
def test_dj_panel_queue_rows_use_profile_objects_and_play_controls():
    app = QApplication.instance() or QApplication([])
    panel = CodeBeatDjPanel(FakeHost())
    result = PetSessionResult(
        True,
        "recommend",
        PetBubbleCard(
            "recommendations",
            "Debug flow",
            items=[PetResultItem(1, "Night Owl - Luna")],
        ),
    )

    panel.show_result(result)
    row = panel.findChild(QFrame, "QueueRow")
    play_button = next(button for button in panel.findChildren(QPushButton) if button.objectName() == "QueuePlayButton")

    assert app is not None
    assert row is not None
    assert play_button.text() == "▶"
    assert panel.prompt_input.objectName() == "DjPromptInput"
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
pytest -q tests/test_pet_dj_panel.py::test_dj_panel_queue_rows_use_profile_objects_and_play_controls
```

Expected: fail because queue objects and play text have old names/styles.

- [ ] **Step 3: Update queue and prompt widgets**

In `_append_result_item`:

```python
row.setObjectName("QueueRow")
play_button.setObjectName("QueuePlayButton")
play_button.setText("▶")
```

In `__init__`:

```python
self.prompt_input.setObjectName("DjPromptInput")
```

- [ ] **Step 4: Run focused panel tests**

Run:

```bash
pytest -q tests/test_pet_dj_panel.py
```

Expected: pass.

## Task 4: Apply the Final DJ Profile Stylesheet

**Files:**
- Modify: `coding_with_beat/pet/dj_panel.py`
- Test: `tests/test_pet_dj_panel.py`, `tests/test_pet_window_actions.py`

- [ ] **Step 1: Add stylesheet selectors for the visual direction**

Update `PANEL_STYLE` with selectors for:

- `QWidget#CodeBeatDjPanel`
- `QFrame#IdentityBadge`
- `QLabel#DjTitle`
- `QLabel#DjSubtitle`
- `QFrame#LivePill`
- `QFrame#StatsBand`
- `QFrame#TasteChip`
- `QFrame#QueueRow`
- `QPushButton#QueuePlayButton`
- `QLineEdit#DjPromptInput`
- `QPushButton#ActionChip`

The style should use near-black backgrounds, mint/teal accents, thin translucent borders, and rounded but compact controls.

- [ ] **Step 2: Run integration tests**

Run:

```bash
pytest -q tests/test_pet_dj_panel.py tests/test_pet_window_actions.py
ruff check coding_with_beat/pet/dj_panel.py tests/test_pet_dj_panel.py
```

Expected: pass.

## Task 5: Update Docs, Rebuild, Restart, and Verify

**Files:**
- Modify: `README.md`
- Modify: `README_CN.md`
- Test: full suite

- [ ] **Step 1: Update docs if current wording is too generic**

Ensure the README mentions:

- CodeBeat DJ profile panel
- scrollable recommendation queue
- direct play buttons
- prompt input

- [ ] **Step 2: Run full verification**

Run:

```bash
ruff check coding_with_beat tests scripts
pytest -q
```

Expected: all checks pass.

- [ ] **Step 3: Rebuild the app**

Run:

```bash
python scripts/build_macos_app.py
```

Expected: prints `/Users/jianchengpan/Projects/coding-with-beat/dist/CodeBeat.app`.

- [ ] **Step 4: Restart the app**

Run:

```bash
pkill -TERM -f 'python -m coding_with_beat app' || true
pkill -TERM -f 'python -m coding_with_beat pet' || true
pkill -TERM -f '/dist/CodeBeat.app/Contents/MacOS/CodeBeat' || true
sleep 2
open /Users/jianchengpan/Projects/coding-with-beat/dist/CodeBeat.app
sleep 5
pgrep -fl 'python -m coding_with_beat (app|pet)' || true
```

Expected: one running `python -m coding_with_beat app` process.

- [ ] **Step 5: Commit**

Run:

```bash
git add README.md README_CN.md coding_with_beat/pet/dj_panel.py tests/test_pet_dj_panel.py tests/test_pet_window_actions.py
git commit -m "feat(pet): redesign dj profile panel"
```

Expected: commit on branch `pet`.

## Self-Review

- Spec coverage: identity header, dark visual direction, stats, chips, queue, prompt, direct play, no duplicate pending, and verification are covered.
- Placeholder scan: no unresolved placeholders are intentionally left in the plan.
- Type consistency: planned object names and helper names are used consistently across tasks.
