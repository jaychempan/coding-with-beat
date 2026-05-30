# CodeBeat AI DJ Intent Router Design

## Goal

Repackage the current pet DJ experience around a dedicated AI music intent router. The pet remains the desktop companion and UI shell, while the new AI DJ layer calls an external AI API directly to turn natural-language music requests into validated Coding With Beat MCP action plans.

The router must not call `codex exec`, Claude Code CLI, or any coding-agent CLI for normal music interaction. Those tools remain available only for explicit advanced code/project tasks.

## Problem

The current merged pet panel sends ordinary text input to `codex exec` first. Even a minimal Codex request can take tens of seconds because it starts a coding agent, loads project context, reads instructions, and produces a full response. That is too slow for music control, where users expect immediate buttons and playback actions.

The desired behavior is not "no AI"; it is a smaller AI role:

1. Understand the user's music intent.
2. Choose the right MCP tool.
3. Produce typed arguments and UI labels.
4. Let local code validate and execute the plan.

## Product Shape

The product becomes two cooperating pieces:

- **Pet DJ UI**: desktop pet, now playing, lyrics, transcript, buttons, recommendation rows, action buttons, and playback controls.
- **AI DJ Intent Router**: an app-owned service/module that accepts user text, calls a configured AI API, and returns a structured plan for MCP calls.

The router can start inside this repo under `coding_with_beat/ai_dj/` and later be extracted into a standalone package or app bundle. The interface should be independent enough that the pet is only one client.

## Non-Goals

- Do not build a full autonomous music agent that directly controls playback without local validation.
- Do not require Codex or Claude Code to be installed for AI DJ music routing.
- Do not replace the existing Coding With Beat MCP server.
- Do not move all pet UI code into the new AI DJ layer.
- Do not require a local model in the first version.

## Architecture

```text
Pet DJ input
  -> AI DJ Router
  -> External AI API provider
  -> JSON action plan
  -> Plan validator
  -> Pet DJ renders buttons or auto-runs low-risk actions
  -> Coding With Beat MCP server executes allowed tools
```

The pet owns display and execution. The AI router owns intent recognition and plan generation. The MCP server owns actual music capability.

## Modules

### `coding_with_beat/ai_dj/schema.py`

Defines stable dataclasses or Pydantic-style schemas:

- `IntentRouteRequest`
- `IntentRoutePlan`
- `IntentAction`
- `ExecutionPolicy`
- `IntentKind`

The plan shape should be compact:

```json
{
  "kind": "music",
  "message": "我帮你找几首适合写代码的中文歌。",
  "actions": [
    {
      "tool": "smart_search",
      "args": {
        "queries": ["华语 专注 写代码", "中文 lofi coding", "国语 indie mellow"]
      },
      "label": "搜索中文写代码歌",
      "execute": "on_click"
    }
  ]
}
```

### `coding_with_beat/ai_dj/providers.py`

Hides AI API differences behind one interface:

```python
class AiDjProvider:
    def route(self, request: IntentRouteRequest) -> IntentRoutePlan:
        ...
```

First version should support an OpenAI-compatible HTTP API:

- `base_url`
- `api_key`
- `model`
- `timeout`

This covers OpenAI, OpenRouter, and many compatible gateways without adding provider-specific code up front.

### `coding_with_beat/ai_dj/router.py`

Builds the short routing prompt, sends the request to the provider, parses JSON, and returns a plan. The prompt includes only:

- user text
- allowed tool schema
- execution policy rules
- optional lightweight context such as current track, source, and whether liked/library features are available

It must ask for JSON only, not a full chat answer.

### `coding_with_beat/ai_dj/validator.py`

Validates AI output before the pet can render or execute it.

Allowed tools for the first version:

- `smart_search`
- `play_song`
- `play_number`
- `search`
- `search_loved`
- `list_loved`
- `list_library`
- `list_playlists`
- `play_playlist`
- `next_track`
- `prev_track`
- `toggle`
- `set_volume`
- `now_playing`

Validation rules:

- Unknown tools are rejected.
- Arguments must match the tool schema.
- `set_volume` is clamped to `0..100`.
- `play_number` must be a positive integer.
- `smart_search` must include 1 to 3 non-empty query strings.
- Search/play query strings must be non-empty and bounded in length.
- `execute=auto` is allowed only for low-risk controls: `next_track`, `prev_track`, `toggle`, `set_volume`, and `now_playing`.
- Search, recommendation, playlist, and specific track playback default to `on_click`.

### `coding_with_beat/ai_dj/executor.py`

Maps a validated `IntentAction` to existing MCP calls through `PetMusicSession` or `PetMusicClient`. The executor should be local and deterministic. AI output never calls MCP directly.

### `coding_with_beat/pet/dj_panel.py`

The panel changes from:

```text
ordinary text -> AiChatRunner -> parse music_actions
```

to:

```text
ordinary text -> AiDjRouter -> validated action plan -> buttons/auto action
```

Codex/Claude controls remain available only as an advanced mode for code/project questions. They should not be the default for music prompts.

## Interaction Model

### Music Search

User: "来点适合写代码的中文歌"

Router returns a `smart_search` action with `execute=on_click`. The pet immediately shows the message and a clear action button. Clicking the button executes MCP and renders queue rows with `▶` buttons.

### Specific Track

User: "播放周杰伦晴天"

Router returns `play_song(query="周杰伦 晴天")` with `execute=on_click`, not auto. This avoids surprising playback from ambiguous model output.

### Transport Control

User: "下一首"

Router or local shortcut returns `next_track` with `execute=auto`. The pet runs it immediately and refreshes now playing.

### Non-Music or Advanced Code Request

User: "解释一下这个项目为什么启动慢"

Router returns `kind="not_music"` or the pet routes the text to advanced AI mode. Codex/Claude CLI can be used here only when the user explicitly selects that mode.

## Settings

The first version needs persistent settings for:

- AI DJ enabled/disabled
- provider type: OpenAI-compatible
- API base URL
- API key
- model
- timeout
- fallback behavior when routing fails

Secrets should not be committed or printed into transcripts. If the current settings layer is not ready for secret storage, the first version can read environment variables and expose UI settings later.

Suggested environment variables:

- `CWB_AI_DJ_BASE_URL`
- `CWB_AI_DJ_API_KEY`
- `CWB_AI_DJ_MODEL`

## Fallback Behavior

If the router is disabled, missing an API key, times out, or returns invalid JSON:

1. Keep existing local transport shortcuts.
2. Fall back to `PetMusicSession.handle_prompt(text)` for likely music prompts.
3. Show a short recoverable message for ambiguous failures.
4. Do not silently call Codex for music prompts.

This keeps the music UI usable even without AI configuration.

## Error Handling

- Provider timeout: show "AI DJ 识别超时，已改用本地音乐搜索。"
- Invalid JSON: show "AI DJ 返回格式无效，已改用本地音乐搜索。"
- Unknown tool: show "AI DJ 建议了不支持的音乐动作。"
- Missing API key: show setup hint and use local fallback.
- MCP execution failure: render the existing error card/result.

## Testing

Unit tests:

- Router prompt contains allowed tool schema and asks for JSON-only output.
- OpenAI-compatible provider parses valid JSON.
- Provider handles timeout and malformed responses.
- Validator rejects unknown tools.
- Validator clamps volume.
- Validator rejects unsafe `execute=auto`.
- Pet panel renders router actions as buttons.
- Pet panel auto-executes low-risk controls.
- Pet panel falls back to local music routing on router failure.
- Pet panel routes explicit advanced AI mode to Codex/Claude.

Integration tests with fake provider and fake MCP client:

- "来点适合写代码的中文歌" returns a search button and then queue rows.
- "下一首" auto-runs next track.
- "播放周杰伦晴天" shows a play button.
- Router failure still produces a local search result.

## Migration

Existing code that remains useful:

- `PetMusicSession`
- `PetMusicClient`
- DJ panel queue rendering
- `MusicActionButton`
- now playing and lyrics refresh
- local command parsing for transport controls

Existing code to de-emphasize:

- `AiChatRunner` as default input path
- `parse_ai_music_reply` as the primary music-action path
- provider/mode combo boxes in the default DJ input row

The current pet branch is still valuable. It becomes the UI client for the new AI DJ router instead of being discarded.

## Open Decisions

1. Whether the first implementation stores API config in app settings or reads environment variables only.
2. Whether advanced Codex/Claude mode stays visible in the DJ panel or moves to a settings/advanced menu.
3. Whether the router runs in-process first or as a local HTTP sidecar from day one.

Recommended first cut:

- In-process router module.
- OpenAI-compatible API provider.
- Environment-variable config plus minimal UI status.
- Pet DJ uses router by default for ordinary input.
- Codex/Claude remains available behind an explicit advanced action.
