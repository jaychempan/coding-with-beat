# Pet Live DJ Cockpit Design

**Date:** 2026-05-29
**Branch:** `pet`
**Feature:** Add live motion, lyrics, and CWB command controls to the CodeBeat DJ panel

## Goal

Upgrade the DJ Profile panel from a static recommendation panel into a live CWB cockpit. The panel should feel active while visible, show current playback and lyrics, and expose common CWB commands without forcing the user back to the terminal.

## Scope

- Add lightweight panel motion with `QTimer + paintEvent`.
- Add a Now Playing strip with title, artist/source/progress, and current lyric line.
- Poll `now_playing_snapshot` while the panel is visible, with a short timeout.
- Add common CWB command chips for pause/resume, next, like, and lyrics refresh.
- Allow command-style text in the prompt input:
  - `/like`
  - `/next`
  - `/pause`
  - `/volume 70`
  - `/seek 1:30`
  - `/mode shuffle`
- Keep normal non-command prompt text routed to music recommendation.

## Visual Behavior

- The existing dotted background drifts slowly.
- The signal field breathes subtly.
- When music is playing, small equalizer bars move in the panel background.
- Motion is active only while the panel is visible.
- The panel remains readable; motion must be subtle and low-frequency.

## Data Flow

- `CodeBeatDjPanel` owns the live UI state.
- `PetMusicClient.now_playing_snapshot()` calls MCP tool `now_playing_snapshot`.
- `CodeBeatDjPanel` parses the JSON payload and updates labels.
- Lyrics use `lyrics_snapshot.line_from_text()` to extract the current line from the full lyrics payload.
- CWB command chips call existing MCP tools through `PetMusicClient.control()`.

## Non-Goals

- Do not embed the full TUI `watch` renderer.
- Do not add album artwork in this pass.
- Do not add a full command autocomplete system.
- Do not run live polling while the panel is hidden.
