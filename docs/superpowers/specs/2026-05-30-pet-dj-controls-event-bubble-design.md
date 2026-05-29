# Pet DJ Controls And Event Bubble Design

**Date:** 2026-05-30
**Branch:** `pet`
**Feature:** Add player controls to the DJ panel and make pet bubble text event-only.

## Problem

The DJ panel currently has strong discovery controls for recommendation, library,
loved tracks, playlists, current status, and reroll. It does not have visible
transport controls. Playback controls exist in the pet right-click menu and slash
commands, but that is too indirect for a panel that already shows now-playing
state.

The pet bubble also stays visible after status updates. That makes the desktop
pet feel like it always has text above its head, even when idle.

## Goals

- Add visible player controls inside the `NOW PLAYING` band.
- Keep bottom DJ buttons focused on discovery and queue entry points.
- Hide pet bubble text during idle desktop use.
- Show pet bubble text only for short events: pending, current track changes,
  result summaries, and errors.
- Apply the same bubble behavior to built-in pets and Petdex pets.

## Design

The `NOW PLAYING` band gets a compact control row:

- `♥` like current track
- `⏮` previous track
- `⏯` pause/resume
- `⏭` next track
- `⟳` refresh now-playing snapshot

The first four controls call the existing CWB MCP tools through
`PetMusicClient.control()`: `like_current`, `prev_track`, `toggle`, and
`next_track`. Refresh calls the existing panel snapshot refresh path. Control
results are appended to the transcript so the user can see what happened.

The pet bubble remains a `PixelBubbleLabel`, but `_show_bubble()` starts a
single-shot hide timer. When the timer fires, the bubble is hidden and the pet
window is re-rendered so idle space collapses. Errors stay visible longer than
normal status updates.

## Non-Goals

- Do not redesign the full DJ panel layout.
- Do not add volume or seek sliders in this pass.
- Do not remove slash command support.
- Do not remove right-click playback controls.

## Acceptance Criteria

- The DJ panel contains visible playback control buttons in the now-playing band.
- Clicking `♥`, `⏮`, `⏯`, and `⏭` sends the expected CWB control tool.
- Clicking refresh reloads the live snapshot without adding an unsupported tool call.
- Built-in and Petdex pet bubbles start hidden and hide again after the event timer.
- Existing search, library, recommendation, and queue play behavior continues to pass.
