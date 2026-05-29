# Pet Music Aura — Design Spec

**Date:** 2026-05-30
**Status:** Pending written-spec review
**Feature:** Transparent music-driven aura, particles, ripples, and playback motion for the desktop pet
**Branch:** `pet`

---

## 1. Goal

Make the desktop pet feel more alive while music is playing.

The current pet can react with sprite actions, but the surrounding UI still
feels too static. This change adds a lightweight transparent visual layer that
looks like music is driving the pet: small particles, expanding ripples, and a
rotating playback status ring.

The feature should:

- keep the pet body centered and readable
- avoid white panels, opaque cards, or heavy app chrome
- show obvious feedback when the terminal/player starts or changes a song
- stay smooth and cheap enough to run continuously on the desktop
- work for both built-in pixel pets and Petdex spritesheet pets

---

## 2. Visual Direction

The pet remains the main character. Effects should feel like an aura around it,
not a separate dashboard.

Idle or paused:

- very faint particles drifting near the pet
- slow breathing opacity
- no constant visual noise

Playing:

- a thin rotating ring or segmented orbit around the sprite
- low-density cyan/purple particles moving outward
- soft pixel-style waveform ticks near the bottom edge
- subtle expanding ripple every few seconds

Song changed:

- one stronger ripple burst from the pet center
- a short particle sparkle around the sprite
- current bubble/status updates as it already does

The palette should stay close to CodeBeat's existing cyan/purple dark UI:
cyan for active playback, purple for accent motion, white only for small
highlights.

---

## 3. Component Design

Add a small custom painted Qt widget, tentatively `MusicAuraWidget`.

It should:

- subclass `QWidget`
- use `WA_TranslucentBackground` and no system background
- expose `set_playing(bool)` and `burst()` methods
- own a lightweight animation timer or be ticked by the parent window timer
- paint only transparent vector/pixel primitives with `QPainter`

The aura widget sits behind or around the pet sprite in the existing layout.
It must not become a large background image and must not create a solid card
behind the character.

Both `PetWindow` and `PetdexWindow` should use the same component. The parent
window passes the sprite display size so the aura can stay centered around the
character.

---

## 4. State Flow

Playback state already arrives through `_apply_live_result()`.

The aura should follow this data flow:

```text
live music poll
-> PetSessionResult(action="dance" or "idle")
-> window updates animator
-> window calls aura.set_playing(...)
-> if live track text changed, window calls aura.burst()
```

Manual actions should also update the aura:

- successful play, playlist start, or auto-play sets playing visuals on
- pause or stopped state fades the active visuals down
- errors should not trigger a burst

No new music polling API is required for this pass.

---

## 5. Performance Constraints

The effect must stay lightweight:

- no image generation at runtime
- no per-frame allocation of large pixmaps
- low particle count, roughly 14-24 dots
- fixed widget size relative to the sprite, not the full screen
- animation interval around the existing pet timer cadence

If Qt is running in offscreen test mode, the widget should still construct and
paint without relying on platform-specific behavior.

---

## 6. Testing

Automated tests should cover:

- the aura widget starts in non-playing mode
- `set_playing(True)` switches to active mode
- `burst()` records a visible burst phase
- built-in `PetWindow` owns and centers an aura widget
- `PetdexWindow` owns and centers an aura widget
- live track change triggers `set_playing(True)` and `burst()`
- repeated identical live track updates do not repeat the burst

Manual smoke testing should cover:

- the pet remains transparent with no white or black block behind it
- the sprite is still centered in the visual cluster
- active playback creates visible motion
- terminal-started songs make the pet react within the existing poll interval
- CPU usage stays reasonable while the app idles

---

## 7. Non-Goals

This pass does not include:

- replacing the pet sprite assets
- adding beat-perfect audio analysis
- adding a WebGL/canvas layer
- redesigning the DJ panel
- changing the existing music command flow

The target is a vivid but controlled music aura that makes playback state feel
alive without turning the desktop pet into a full visualizer.
