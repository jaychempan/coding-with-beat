# Desktop Pet — Design Spec

**Date:** 2026-05-29
**Status:** Approved
**Feature:** Python native macOS desktop pet for coding-with-beat
**Branch:** `pet`

---

## 1. Goal

Build a native Python desktop pet for macOS, launched with `cwb pet`.
The pet is a transparent always-on-top pixel character that can be dragged,
clicked, used for mood-based song recommendations, and driven by existing
coding-with-beat music and coding-state signals.

The first version includes the complete built-in skin set:

- `dj`
- `programmer`
- `sleepwear`
- `cyber`
- `chinese`

Each skin supports the same action set so behavior can change without special
case logic per skin.

---

## 2. Product Scope

The desktop pet supports three interaction layers.

### Lightweight Interaction

- Drag the pet anywhere on screen.
- Left click triggers a small reaction animation.
- Double click opens a compact mood input bubble.
- Right click opens a menu for recommendations, now playing, pause/resume,
  next track, skin switching, and quit.
- The last position and selected skin are persisted.

### Conversation Interaction

The mood input bubble accepts short natural-language prompts such as:

- `我今天很顺利`
- `有点累`
- `想听国风`
- `写代码专注点`
- `something upbeat for debugging`

The pet maps the text to 2-3 `smart_search` queries, shows numbered results,
and waits for the user to pick a number. It never auto-plays recommendation
results.

### Proactive Companion Behavior

The pet reads existing `JukeboxState` signals and reacts:

- `playing == true` -> `dance`
- `dj_mood == victory` -> `happy`
- `dj_mood == sad` or `panic` -> `sad` or `panic`
- `companion_failure_streak >= 3` -> `panic`
- long idle with no playback -> `sleep`
- active focus/debug/review vibes -> low-distraction `idle` or `think`

---

## 3. Technical Approach

Use PySide6 / Qt for Python for the desktop UI.
It provides a practical Python-native path for transparent frameless windows,
always-on-top behavior, dragging, context menus, input bubbles, timers, and
pixel rendering.

GUI support is optional. The base package remains usable without installing
desktop dependencies.

`pyproject.toml` adds:

```toml
[project.optional-dependencies]
pet = ["PySide6>=6.7"]
```

If `PySide6` is missing, `cwb pet` prints a clear install hint and exits
without affecting normal CLI commands.

---

## 4. Module Design

### `coding_with_beat/pet/app.py`

Starts the Qt application and creates the main pet window.
It is the boundary for importing PySide6 so non-GUI code can be tested without
having PySide6 installed.

### `coding_with_beat/pet/window.py`

Owns the transparent always-on-top window:

- frameless translucent widget
- pet sprite label/canvas
- speech bubble
- mood input
- right-click menu
- drag handling

### `coding_with_beat/pet/sprites.py`

Defines built-in skins and action frames.
Each skin is represented as structured Python data:

```python
Skin(
    id="dj",
    name="DJ Buddy",
    palette={...},
    actions={
        "idle": [Frame(...), Frame(...)],
        "dance": [Frame(...), Frame(...), Frame(...)],
    },
)
```

The first implementation stores frames in code. External skin directories can
be added later without changing the state machine.

### `coding_with_beat/pet/animator.py`

Converts action names into timed frames. It owns the current skin, action, frame
index, and frame interval.

### `coding_with_beat/pet/controller.py`

Connects UI events to state and music behavior:

- click reactions
- skin changes
- periodic `JukeboxState` polling
- action choice from state
- recommendation requests
- play-number requests

### `coding_with_beat/pet/music.py`

Wraps existing MCP calls used by the pet:

- `smart_search`
- `play_number`
- `status`
- `toggle_play`
- `next_track`

It returns simple success/error values so the UI can degrade cleanly.

### `coding_with_beat/pet/mood.py`

Maps mood text to 2-3 search queries. It handles Chinese and English hints for
focus, success, sadness, fatigue, sleep, party, jazz, synthwave, and Chinese
music.

### `coding_with_beat/pet/settings.py`

Persists pet-only preferences:

- screen position
- selected skin
- last window scale

---

## 5. Skin And Action System

All built-in skins support these actions:

- `idle`: standing, blinking, breathing
- `walk`: light pacing or stepping
- `dance`: music playback animation
- `think`: waiting for recommendations
- `recommend`: presenting results
- `happy`: success or good mood
- `sad`: low mood or failure
- `panic`: repeated test failure or error state
- `sleep`: idle, session end, sleep music

Built-in skins:

| Skin | Visual Direction | Strong Actions |
|---|---|---|
| `dj` | headphones, jacket, music notes | `dance`, `recommend` |
| `programmer` | keyboard, coffee, screen glow | `think`, `panic`, `happy` |
| `sleepwear` | sleep cap, pillow, blanket | `sleep`, `sad`, `idle` |
| `cyber` | neon visor, glowing trim | `dance`, `walk`, `panic` |
| `chinese` | short robe, hair ornament, traditional instrument cue | `dance`, `recommend`, `happy` |

Frames are rendered as pixel art at integer scale so edges stay crisp.

---

## 6. Recommendation Flow

1. User opens the input bubble or chooses `推荐歌曲`.
2. Pet enters `think`.
3. `mood.py` maps the text to 2-3 query angles.
4. `music.py` calls `smart_search(queries=[...])`.
5. Pet enters `recommend` and shows numbered results.
6. User clicks or types a number.
7. `music.py` calls `play_number(N)`.
8. On success, pet enters `dance` or `happy`.

The pet follows the existing project rule: recommendations are shown first and
not auto-played.

---

## 7. Error Handling

- Missing `PySide6`: print an install hint and exit.
- MCP server unavailable: keep pet visible; recommendation bubble shows that
  music service is not connected and offers retry through the menu.
- No search results: show a short retry prompt and return to input.
- `play_number` out of range: keep the latest results and show the valid range.
- State file read failure: use default idle state.
- macOS transparency or always-on-top limitation: degrade to a normal frameless
  window and show a startup note.

---

## 8. Testing

Unit tests cover:

- mood text to query mapping
- built-in skin completeness
- animator frame cycling and action switching
- settings load/save defaults
- music wrapper error normalization
- controller state-to-action selection

GUI smoke tests are limited to import and object construction behind optional
dependency checks. CI should not require a live macOS desktop.

---

## 9. Out Of Scope

- Voice input or speech synthesis.
- Global hotkeys.
- Store/downloadable skin marketplace.
- Real physics walking around windows.
- Rewriting music source implementations.
- Auto-playing recommendations without explicit user selection.
