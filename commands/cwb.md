---
description: Control coding-with-beat (play / pause / skip / now-playing / music source / like / mode / search / list). Use $ARGUMENTS as a free-form intent.
disable-model-invocation: true
allowed-tools: Bash
argument-hint: "<play|search|list|pause|next|prev|status|like|mode|source> [args]"
---

If the coding-with-beat UserPromptExpansion hook is installed, this command is handled
by a private one-shot headless Claude session. The child session interprets the
intent, runs a validated coding-with-beat action, returns a short result, and blocks
this fallback prompt so the main conversation context stays clean.

You are driving the local **coding-with-beat** music player via its globally-installed CLI. Do NOT call any MCP tools — they may not be loaded. Always shell out via Bash to the `cwb` command (installed by `install.sh` at `~/.local/bin/coding-with-beat`, backed by a venv at `~/.coding-with-beat/venv`).

User intent: `$ARGUMENTS`

## How to interpret

Parse the intent and pick exactly ONE action. If empty or ambiguous, default to `status`.

| Intent keywords | Command |
|---|---|
| play/start + `<query>` | `cwb play <query>` |
| play/resume with no query | `cwb play` |
| resume/继续/恢复 (after interruption) | `cwb resume` |
| search/find/搜索/找 + `<query>` | `cwb search <query>` |
| list/library/资料库/列表 | `cwb list` |
| pause/stop | `cwb pause` |
| next/skip | `cwb next` |
| previous/back | `cwb prev` |
| source/music source + `<apple_music|qq_music|local>` | `cwb source <apple_music|qq_music|local>` |
| like/favorite current | `cwb like` |
| shuffle/sequential/repeat | `cwb mode <shuffle|sequential|repeat>` |
| now playing/what's playing | `cwb np` |
| show player/player | `cwb player` |
| status | `cwb status` |
| lyrics/karaoke | `cwb karaoke` |

For search or play-by-query, the `<query>` is the rest of the text after the verb (artist name, song name, mood — pass it through verbatim, including Chinese). Quote it.

## Run it

```bash
cwb <action> [args...]
```

Examples:

```bash
cwb play "lofi beats"
cwb search "刘德华"
cwb list
cwb source apple_music
cwb source qq_music
cwb like
cwb mode shuffle
cwb next
cwb np
cwb status
```

If `cwb` is not on PATH (rare — only if `~/.local/bin` isn't exported), fall back to the absolute path: `~/.coding-with-beat/venv/bin/coding-with-beat`.

After running, give the user a **one-line** English confirmation, e.g. `▶ Now playing: lofi beats`. No extra commentary.
