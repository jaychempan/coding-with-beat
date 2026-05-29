# Pet DJ Flow — Design Spec

**Date:** 2026-05-29
**Status:** Pending written-spec review
**Feature:** Context-aware desktop pet interaction and playback flow
**Branch:** `pet`

---

## 1. Goal

Turn the desktop pet from a small button panel into a Coding With Beat desktop
companion.

The pet should feel like a DJ Buddy that understands the coding session:

- It reacts to CWB state and current playback without requiring interaction.
- It recommends music from coding context or short user mood text.
- It keeps playback control lightweight and practical.
- It uses right-click as an advanced fallback, not the primary workflow.

The target behavior is **DJ assistant + reactive companion first**, with only
the most common mini-player controls kept close at hand.

---

## 2. Product Direction

The approved direction is:

- Use **Pet as DJ Buddy** as the main model.
- Borrow the automatic state awareness from a reactive statusline.
- Avoid turning the pet into a full floating app or button-heavy mini player.

This means the normal desktop presence stays small. The pet and a compact
status line are visible most of the time. Richer controls appear only when the
user interacts with the pet.

---

## 3. Interaction Layers

### Layer 1: Ambient Status

The default surface is intentionally quiet:

- Petdex sprite animation.
- A short status line, such as `▶ 晴天 - 周杰伦` or `Debug flow`.
- No always-expanded button row.

Animation follows CWB state:

- playing music -> dance
- searching or forming recommendations -> think
- recommendation ready -> wave/recommend
- playback started -> dance or happy
- repeated tool failures or panic mood -> panic
- sad mood or failed music command -> sad
- long idle without playback -> sleep

The pet acts as a living desktop statusline for Coding With Beat.

### Layer 2: DJ Buddy Interaction

Primary interaction uses the pet itself:

- Single click opens a compact bubble with current status and 2-3 relevant
  quick actions.
- Double click starts the recommendation flow from current coding context.
- Long press starts quick auto-play from current coding context.
- Clicking a recommendation number plays that numbered result.
- The bubble stays concise and avoids dumping raw MCP output.

Recommended bubble actions:

- `按当前状态推荐`
- `换个氛围`
- `当前播放`

### Layer 3: Advanced Menu

Right-click remains available for less frequent or fallback operations:

- play/pause
- next track
- play by result number
- switch Petdex pet
- show or hide detail panel
- quit

The right-click menu should not be the main product experience.

---

## 4. Quick Action Bar

Replace the current persistent text buttons with a compact action strip.

The strip may be hidden, translucent, or only emphasized on hover/focus. It
should be visually secondary to the pet.

Actions:

- `♪` current playback or play/pause
- `✨` recommend from current context
- `🎲` reroll the current recommendation intent
- `⋯` open more actions

Text labels belong in tooltips or the bubble, not as permanent large buttons.
The UI should feel like a pet accessory, not a form toolbar.

---

## 5. Playback Flow

### Context Recommendation

Double click or `✨` starts a recommendation session:

1. Read current `JukeboxState`: `vibe`, `dj_mood`, playback status, current
   track, recent tool activity, and failure streak.
2. Build a DJ intent from state. If the user supplied mood text, that text wins
   over inferred state.
3. Convert the intent into 2-3 smart search query angles.
4. Call `smart_search(queries=[...])`.
5. Show a compact numbered result card.
6. Wait for the user to choose a result.

Default recommendation does not auto-play.

### Numbered Playback

When the user picks a number:

1. Call `play_number(N)`.
2. On success, update the status line and set the pet to dance or happy.
3. On failure, set the pet to sad and show a short error message.

### Quick Auto-Play

Long press or an explicit `自动开播` action starts a faster flow:

1. Build the same current-context DJ intent.
2. Call `smart_search(queries=[...])`.
3. Automatically call `play_number(1)`.
4. Show a short confirmation with `下一首` and `换一组` affordances.

Auto-play is intentionally opt-in. It does not replace the normal
recommend-then-pick flow.

### Reroll

`🎲` keeps the current intent but changes query angles.

Example:

- First `debug_focus` set: ambient, no-vocal focus, quiet piano.
- Rerolled `debug_focus` set: lofi, calm electronic, jazz study.

Reroll should call `smart_search` once and update the active result list.

---

## 6. DJ Intents

Introduce a small intent layer between raw CWB state and music search.

Initial intents:

| Intent | Trigger | Search Direction | Pet Tone |
|---|---|---|---|
| `debug_focus` | `vibe` is debug or review | low-distraction focus | calm, thinking |
| `victory_boost` | `dj_mood` is victory | upbeat celebration | happy |
| `panic_recover` | panic mood or high failure streak | calming reset music | concerned, supportive |
| `late_idle` | long idle with no playback | relaxed return music | sleepy, gentle |
| `playing_companion` | music already playing | similar or next vibe | dancing |
| `free_text` | user typed mood text | derived from mood text | matches result |

Intent names are internal. Bubble copy should be natural, such as `Debug flow`
or `缓一下`.

---

## 7. Components

### `PetInteractionController`

Translates UI events into interaction commands:

- single click -> show status bubble
- double click -> recommend from context
- long press -> auto-play from context
- quick action -> now, recommend, reroll, more

It should return structured interaction results instead of directly formatting
widgets.

### `PetDjBrain`

Owns the CWB-specific decision logic:

- reads state and optional user mood text
- chooses a DJ intent
- generates smart search query angles
- generates concise bubble copy
- provides alternate query sets for reroll

It can reuse `queries_for_mood()` for free-text mood prompts, but context-aware
intents should live here.

### `PetMusicSession`

Tracks the active recommendation session:

- current intent
- current query set
- current numbered results
- reroll count
- last command outcome

It exposes:

- `recommend_from_context()`
- `recommend_from_text(text)`
- `reroll()`
- `play_number(number)`
- `auto_play_from_context()`

### `PetBubbleView`

Formats compact cards for display:

- current status
- numbered recommendation results
- playback confirmations
- short errors

It should cap recommendation display at 5 items and avoid raw tool dumps.

### `PetdexWindow` and `PetWindow`

Remain responsible for windowing, rendering, animation, mouse events, and Qt
wiring. They delegate music and interaction decisions to the controller and
session classes.

---

## 8. Data Flow

Recommendation flow:

```text
UI event
-> PetInteractionController
-> PetMusicSession
-> PetDjBrain
-> PetMusicClient.smart_search
-> PetBubbleView
-> PetdexWindow animation + bubble
```

Playback flow:

```text
number selected
-> PetMusicSession.play_number
-> PetMusicClient.play_number
-> status refresh
-> PetBubbleView confirmation
-> PetdexWindow dance/sad animation
```

Auto-play flow:

```text
long press
-> context intent
-> smart_search
-> play_number(1)
-> concise confirmation
```

---

## 9. Error Handling

Errors should be short and useful:

- `smart_search` failure: show one short line and set pet to sad.
- no results: suggest reroll or entering a mood.
- `play_number` failure: preserve the recommendation list and show the failure.
- state read failure: fall back to free-text or neutral focus intent.
- MCP output too long: trim into a compact card.

The UI should never expand into a huge raw log bubble during normal use.

---

## 10. Testing

Unit tests should cover:

- state to DJ intent mapping
- user text overriding inferred state
- intent to query generation
- reroll using the same intent with alternate angles
- double click recommending without playback
- long press running smart search then `play_number(1)`
- play-number success and failure actions
- result formatting into compact cards
- right-click menu remaining available for fallback commands

Existing pet rendering tests should remain separate from DJ flow tests.

---

## 11. Non-Goals

This design does not include:

- building a full floating music library browser
- replacing the terminal or MCP command flows
- auto-playing on every recommendation request
- implementing official Petdex Desktop binary integration
- adding complex account or source-management UI

Those can be considered later if the core pet interaction proves useful.

---

## 12. Success Criteria

The change is successful when:

- The normal pet view feels small and alive, not like a button toolbar.
- A user can double click the pet and get useful context-aware recommendations.
- A user can long press for quick auto-play.
- A user can choose a numbered recommendation without opening the terminal.
- The current song and coding vibe are visible in a compact way.
- Right-click remains useful but is no longer the primary interaction path.
- The implementation is testable without needing a live Qt window for the core
  DJ logic.
