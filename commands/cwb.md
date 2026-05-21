---
description: Control coding-with-beat (play / pause / skip / now-playing / music source / like / mode). Use $ARGUMENTS as a free-form intent.
disable-model-invocation: true
allowed-tools: Bash
argument-hint: "[source <apple_music|qq_music|local> | play <query> | like | mode <shuffle|sequential|repeat> | karaoke | pause | next | prev | status]"
---

If the coding-with-beat UserPromptExpansion hook is installed, this command is handled
by a private one-shot headless Claude session. The child session interprets the
intent, runs a validated coding-with-beat action, returns a short result, and blocks
this fallback prompt so the main conversation context stays clean.

You are driving the local **coding-with-beat** music player via its globally-installed CLI. Do NOT call any MCP tools — they may not be loaded. Always shell out via Bash to the `cwb` command (installed by `install.sh` at `~/.local/bin/coding-with-beat`, backed by a venv at `~/.coding-with-beat/venv`).

User intent: `$ARGUMENTS`

## How to interpret

Parse the intent and pick exactly ONE action. If empty or ambiguous, default to `status`.

| Intent keywords (zh / en) | Command |
|---|---|
| 播放/放/听/来一首/play/start + `<query>` | `cwb play <query>` |
| 播放/play (no query) / 继续/恢复/resume | `cwb play` |
| 暂停/pause/stop | `cwb pause` |
| 下一首/跳过/next/skip | `cwb next` |
| 上一首/prev/back | `coding-with-beat prev` |
| 切换音乐源/source/music source + `<apple_music|qq_music|local>` | `cwb source <apple_music|qq_music|local>` |
| 喜欢/收藏当前歌/like/favorite current | `cwb like` |
| 随机/顺序/循环/shuffle/sequential/repeat | `cwb mode <shuffle|sequential|repeat>` |
| 在放什么/正在播放/什么歌/now playing/what | `cwb np` |
| 显示/show player/player | `cwb player` |
| 状态/status | `cwb status` |
| 歌词/卡拉OK/lyrics/karaoke | `cwb karaoke` |

For a play-by-query, the `<query>` is the rest of the text after the verb (artist name, song name, mood — pass it through verbatim, including Chinese). Quote it.

## Run it

```bash
cwb <action> [args...]
```

Examples:

```bash
cwb play "稻香 周杰伦"
cwb source apple_music
cwb source qq_music
cwb like
cwb mode shuffle
cwb next
cwb np
cwb status
```

If `cwb` is not on PATH (rare — only if `~/.local/bin` isn't exported), fall back to the absolute path: `~/.coding-with-beat/venv/bin/coding-with-beat`.

After running, give the user a **one-line** confirmation in their language (Chinese if they used Chinese): e.g. `▶ 正在播放：稻香 — 周杰伦`. No extra commentary.
