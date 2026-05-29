# Pet Performance And Pixel UI — Design Spec

**Date:** 2026-05-29
**Status:** Pending written-spec review
**Feature:** Faster desktop pet interactions and transparent pixel-style UI
**Branch:** `pet`

---

## 1. Goal

Make the desktop pet feel responsive and visually native to Coding With Beat.

The current implementation can feel stuck because music commands run
synchronously from Qt event handlers. The current bubble also uses a text-edit
surface that can show a white background and scrollbar, which clashes with the
pixel pet.

This change should:

- keep the pet animation moving while music commands run
- remove white editor-style bubbles and scrollbars
- use transparent pixel-style text and controls
- preserve the DJ Buddy flow from the previous design

---

## 2. Root Cause

The performance issue is primarily UI-thread blocking:

- `smart_search`, `play_number`, `now_playing`, `toggle`, and `next_track`
  are called from Qt event handlers.
- These calls can take noticeable time, especially `smart_search`.
- While the call runs, the Qt event loop cannot repaint or advance animation.

The visual issue is primarily widget choice:

- `QTextEdit` is an editor widget, so it brings document styling,
  scrollbar behavior, and background assumptions.
- Result text can grow tall enough to resize the pet window.
- Buttons still read as ordinary app controls instead of pet UI affordances.

---

## 3. Product Design

The normal layout should be:

```text
colored status text
      pet
♪   ✨   🎲   ⋯
```

The pet remains transparent and compact. There is no white panel behind the
main status text.

When recommendations or errors appear, show a small pixel-style overlay:

```text
Debug flow
1. Track - Artist
2. Track - Artist
3. Track - Artist
点编号播放 · 🎲 换一组
```

The overlay should be readable but visually lightweight:

- transparent or very dark translucent background
- no scrollbar
- no text-edit cursor
- monospaced or pixel-like font
- colored heading/status text
- maximum visible rows; long output is trimmed, not scrolled

---

## 4. Performance Design

Move music actions out of the UI thread.

Add an async command runner for pet music interactions:

- UI event starts a command and immediately returns.
- Pet action changes to `think`.
- Bubble/status shows a short pending message.
- Worker runs the session call in a background thread.
- Result is delivered back to Qt via a signal.
- UI applies the `PetSessionResult` on the main thread.

Initial async actions:

- context recommendation
- text recommendation
- reroll
- auto-play
- play number
- now playing refresh
- toggle playback
- next track

The animation timers must keep running while these commands are active.

---

## 5. Visual Component Design

Replace `QTextEdit` bubbles with a display-only component.

The simplest target is a styled `QLabel`:

- `setTextFormat(Qt.PlainText)`
- `setWordWrap(True)`
- `setTextInteractionFlags(Qt.NoTextInteraction)`
- transparent or dark translucent pixel-card style
- no scrollbars possible

For longer result cards, trim before display:

- recommendation cards: show at most 5 numbered items
- other bubbles: show at most 5 lines
- each line should be capped to a practical width

Top status:

- use colored text only
- no heavy background
- compact height
- keep current song or current DJ intent readable

Bottom action strip:

- 4 transparent icon buttons
- no rectangular filled button look
- stronger color only on hover/press
- fixed dimensions so layout does not jump

---

## 6. Data Flow

User interaction:

```text
Qt event
-> start async pet command
-> set pending visual state
-> worker calls PetMusicSession
-> result signal returns to UI thread
-> apply PetSessionResult
```

State refresh:

```text
state timer
-> local JukeboxState read
-> update animation/status text
```

Normal state refresh should avoid network/MCP work. Explicit user actions can
run MCP work through the async command runner.

---

## 7. Error Handling

Background command errors should not crash the Qt app.

If a worker raises unexpectedly:

- return a `PetSessionResult` with `ok=False`
- use `sad` action
- show a short pixel bubble with the error message

If a command is already running and the user starts another command:

- ignore duplicate clicks for the same command while busy, or
- replace the pending command only for explicit reroll/recommend actions

The initial implementation can use a conservative single-command lock.

---

## 8. Testing

Tests should cover:

- async runner emits a result without blocking the caller
- command errors become error cards
- bubble formatting trims lines and never exposes scrollbar behavior
- `_action()` menu callback behavior remains safe
- pet session tests continue to pass

Manual smoke testing should cover:

- animation continues while a recommendation is running
- no white bubble background appears
- no scrollbar appears
- status text and icons remain readable on the desktop
- drag, single click, double click, and long press still behave correctly

---

## 9. Non-Goals

This pass does not include:

- full custom painting for every UI element
- bundled pixel font assets
- official Petdex Desktop binary integration
- large layout redesign
- adding a full playlist browser

The target is a fast, transparent, pixel-styled version of the existing DJ
Buddy flow.

---

## 10. Success Criteria

The change is successful when:

- recommendation/search no longer freezes pet animation
- main UI has no white background panel
- recommendation bubbles have no scrollbar
- text is readable and visually pixel-styled
- controls feel transparent and compact
- full pet tests and full test suite pass
- local `cwb pet` launches without traceback
