---
description: Control cc-jukebox (play / pause / skip / now-playing / source / like / mode). Use $ARGUMENTS as a free-form intent.
allowed-tools: Bash
argument-hint: "[source qq_music | play <query> | like | mode shuffle | pause | next | status]"
---

You are driving the local **cc-jukebox** music player via its globally-installed CLI. Do NOT call any MCP tools — they may not be loaded. Always shell out via Bash to the `cc-jukebox` command (installed by `install.sh` at `~/.local/bin/cc-jukebox`, backed by a venv at `~/.cc-jukebox/venv`).

User intent: `$ARGUMENTS`

## How to interpret

Parse the intent and pick exactly ONE action. If empty or ambiguous, default to `status`.

| Intent keywords (zh / en) | Command |
|---|---|
| 播放/放/听/来一首/play/start + `<query>` | `cc-jukebox play <query>` |
| 播放/play (no query) / 继续/恢复/resume | `cc-jukebox play` |
| 暂停/pause/stop | `cc-jukebox pause` |
| 下一首/跳过/next/skip | `cc-jukebox next` |
| 上一首/prev/back | `cc-jukebox prev` |
| 切到QQ音乐/使用QQ音乐/source qq | `cc-jukebox source qq_music` |
| 切到Apple Music/source apple | `cc-jukebox source apple_music` |
| 喜欢/收藏当前歌/like/favorite current | `cc-jukebox like` |
| 随机/顺序/循环/shuffle/sequential/repeat | `cc-jukebox mode <shuffle|sequential|repeat>` |
| 在放什么/正在播放/什么歌/now playing/what | `cc-jukebox np` |
| 显示/show player/player | `cc-jukebox player` |
| 状态/status | `cc-jukebox status` |

For a play-by-query, the `<query>` is the rest of the text after the verb (artist name, song name, mood — pass it through verbatim, including Chinese). Quote it.

## Run it

```bash
cc-jukebox <action> [args...]
```

Examples:

```bash
cc-jukebox play "稻香 周杰伦"
cc-jukebox source qq_music
cc-jukebox like
cc-jukebox mode shuffle
cc-jukebox next
cc-jukebox np
cc-jukebox status
```

If `cc-jukebox` is not on PATH (rare — only if `~/.local/bin` isn't exported), fall back to the absolute path: `~/.cc-jukebox/venv/bin/cc-jukebox`.

After running, give the user a **one-line** confirmation in their language (Chinese if they used Chinese): e.g. `▶ 正在播放：稻香 — 周杰伦`. No extra commentary.
