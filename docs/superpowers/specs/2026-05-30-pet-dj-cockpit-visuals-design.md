# Pet DJ Cockpit Visuals — Design Spec

**Date:** 2026-05-30
**Status:** Approved
**Feature:** Add richer motion and material texture to the CodeBeat DJ panel
**Branch:** `pet`

---

## Goal

Make the DJ panel feel like a living CodeBeat music cockpit instead of a flat
Qt form.

The panel already has a dark profile layout, but most components are static.
This pass should add motion and material quality while keeping the panel useful
for search, queue selection, lyrics, and command routing.

---

## Visual Direction

Use a "Liquid Pixel Cockpit" language:

- dark layered base with dotted grid, scan lines, and subtle moving glow
- animated ON AIR signal rail
- current playback band with internal waveform and liquid highlight
- queue rows with track-cell styling and better play controls
- bottom command deck with stronger command-line presence

The motion should be rhythmic and restrained. The panel should feel active
while music is playing, but it must not become noisy or expensive to repaint.

---

## Component Design

Add small focused painted widgets instead of putting all rendering in
`CodeBeatDjPanel.paintEvent()`:

- `CockpitSignalRail`: slim animated rail between stats/chips and results.
- `LiquidNowPlayingBand`: replaces the plain now-playing `QFrame` and paints a
  liquid highlight plus waveform ticks when live playback is active.
- `QueueTrackRow`: replaces plain queue rows with track-cell hover/material
  styling and keeps the direct play button behavior.

The existing `_animation_timer` remains the single motion clock. On every tick,
the panel increments `_motion_phase`, updates the painted widgets, and repaints.

---

## Data Flow

No music command behavior changes.

Snapshot flow:

```text
refresh_live_snapshot()
-> _apply_snapshot(data)
-> _live_playing updated
-> LiquidNowPlayingBand.set_live_playing(...)
-> paint uses current motion phase
```

Recommendation flow:

```text
show_result()
-> _append_card()
-> _append_result_item()
-> QueueTrackRow(number, label) inserted
```

---

## Testing

Automated tests should verify:

- the panel creates a `CockpitSignalRail`
- the now-playing band is a `LiquidNowPlayingBand`
- motion ticks propagate phase into the rail and now-playing band
- live snapshot updates the now-playing band playing state
- queue results render `QueueTrackRow` objects and keep direct play buttons

Manual verification should cover:

- richer panel texture without opaque white/flat areas
- current playback band has active waveform when music is playing
- queue rows feel more like track cells
- search, recommendation, play-number, and slash commands still work
