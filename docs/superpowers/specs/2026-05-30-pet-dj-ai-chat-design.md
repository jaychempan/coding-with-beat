# Pet DJ AI Chat Design

**Date:** 2026-05-30
**Branch:** `pet`
**Feature:** AI-first DJ chat with playable music actions

## Goal

Make AI chat the primary interaction surface inside the CodeBeat DJ panel. The user talks naturally to the AI, and when the AI recommends songs, playlists, genres, moods, or playback operations, the panel turns those recommendations into one-click music actions.

This is not a separate music prompt plus a separate AI prompt. It is one conversation where the AI can explain, recommend, and produce playable DJ actions.

## Product Behavior

The panel keeps the live playback band at the top. Below it, the main scroll area becomes a unified AI/DJ conversation timeline:

- user messages appear as chat turns
- AI replies appear as natural language
- detected music actions render inline as buttons or compact cards
- music search results still render with direct play buttons
- status, errors, and command results appear in the same timeline

The bottom input is primarily an AI chat input. The user can ask things like:

- `我今天写代码有点烦，推荐几首能继续干活的歌`
- `给我一些像 Taylor Swift 但更适合晚上写代码的`
- `解释一下这个项目，然后顺手放点专注音乐`
- `下一首`
- `/volume 70`

The system handles direct playback commands locally when it can, but the default conversational path is AI-first.

## Music Action Model

AI responses may contain music actions. The UI should render those actions as clickable controls rather than asking the user to copy text back into the DJ.

Supported action kinds:

- `play_track`: a specific song, artist, or album query that can be played or searched precisely
- `search_music`: a mood, genre, scene, similar-artist, era, or fuzzy query that should use the existing music router / smart search path
- `play_number`: a numbered result from the current queue
- `control`: direct playback controls such as next, previous, pause, like current, seek, volume, or playback mode
- `playlist`: list playlists or play a named playlist through the existing playlist command route

Each rendered action has a readable label and a single click target. The action execution reuses existing `PetMusicSession` / CWB command behavior so queue numbering, library-only handling, loved tracks, playlist behavior, and direct play semantics stay consistent with the rest of Coding With Beat.

## AI Output Contract

The AI runner wraps user prompts with a small instruction that asks the provider to include machine-readable music actions whenever it recommends music or suggests a playable operation.

The preferred response format is natural text plus a fenced JSON block:

```json
{
  "music_actions": [
    {
      "kind": "play_track",
      "query": "周杰伦 晴天",
      "label": "晴天 - 周杰伦"
    },
    {
      "kind": "search_music",
      "query": "lofi hip hop late night coding chill",
      "label": "Late-night coding lofi"
    }
  ]
}
```

The panel strips or hides this JSON from the visible chat reply and renders the actions as interactive rows.

## Fallback Parsing

The structured action contract is preferred but not trusted as the only source. If the provider returns plain text without valid JSON, the panel runs a conservative fallback parser over the final AI reply.

The parser should detect:

- Chinese book-title song notation like `《晴天》- 周杰伦`
- numbered recommendation lines like `1. 晴天 - 周杰伦`
- English forms like `Song Title by Artist`
- direct command words such as `下一首`, `暂停`, `音量 70`

Fallback parsing should avoid aggressive extraction. If confidence is low, leave the text as normal AI chat instead of creating a bad play button.

## Local Command Priority

Some inputs should execute immediately without waiting for AI:

1. Slash commands such as `/next`, `/pause`, `/volume 70`, and `/seek 1:30`
2. clear playback controls like `下一首`, `暂停`, `继续`, `喜欢这首`, `音量 70`
3. direct click actions from an AI-rendered music card

Everything else goes through the AI-first chat path. This preserves the feeling that the user is talking to the DJ assistant while keeping fast transport controls instant.

## Architecture

Keep `coding_with_beat/pet/ai_chat.py` as the provider/process boundary. It owns provider names, permission modes, command construction, subprocess lifecycle, result extraction, and Qt signals.

Extend it with an AI prompt wrapper that requests optional `music_actions` JSON. The runner still returns a completed result rather than streaming partial tokens in this version.

Move DJ-panel-specific parsing and rendering into `coding_with_beat/pet/dj_panel.py` or a small helper module if the parsing grows beyond simple rules. `CodeBeatDjPanel` owns:

- appending chat turns to the unified timeline
- stripping action JSON from visible AI text
- rendering inline music action cards
- routing action clicks to the existing music session and CWB control APIs
- preserving existing queue result rows and direct play buttons

The existing standalone AI section is removed. Provider and permission controls become compact controls attached to the unified input row or a small settings row near it.

## Provider Behavior

Codex:

- initial turn uses `codex exec`
- follow-up turns use `codex exec resume --json --last -`
- read-only mode passes `--sandbox read-only`
- workspace-write mode passes `--sandbox workspace-write --ask-for-approval on-request`
- initial commands run with `--cd <project root>` and `--color never`
- JSONL output is parsed so the panel shows the final agent message instead of CLI banners or hook logs

Claude Code:

- turns use `claude --print`
- read-only mode passes `--permission-mode default`
- workspace-write mode passes `--permission-mode acceptEdits`
- follow-up state is tracked with a generated `--session-id <uuid>`
- commands run in the project root

Both providers set `CWB_DISABLE_HOOK=1` to prevent Coding With Beat hooks from recursively reacting to the child agent.

## Error Handling

If the CLI is missing, the timeline shows a short provider error. If a process exits non-zero, stdout/stderr is shown as an error message. If the user clicks Stop, the process is terminated and the timeline records that the turn was stopped.

Invalid or malformed action JSON should not fail the chat turn. The visible reply still appears, and the action parser simply skips invalid actions.

## Testing

Add focused tests for:

- command construction for Codex read-only and workspace-write modes
- command construction for Claude Code session id and permission mode
- runner success, missing executable, stop behavior, and JSONL result extraction with fake subprocess factories
- action JSON extraction from AI replies
- fallback parsing for common Chinese and English song recommendation lines
- direct command detection for local playback controls
- DJ panel uses one unified prompt/timeline rather than a separate `AiChatPanel`
- AI replies render playable action buttons that call the existing music routes
- ordinary AI replies without actions remain plain chat rows

Run:

```bash
pytest tests/test_pet_ai_chat.py tests/test_pet_dj_panel.py -q
ruff check coding_with_beat/pet/ai_chat.py coding_with_beat/pet/dj_panel.py tests/test_pet_ai_chat.py tests/test_pet_dj_panel.py
```

## Non-Goals

- No terminal emulator in Qt.
- No live token streaming in the first pass.
- No interactive approval prompts inside the DJ panel.
- No new music backend.
- No broad natural-language parser that tries to guess every possible song mention.
