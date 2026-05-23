---
name: cwb
description: Control music via coding-with-beat. Activate when the user asks to play, pause, skip, or search for music; asks what's playing; mentions a song/artist/genre; or types "cwb" or "/cwb" followed by a command.
metadata:
  short-description: Music control for coding sessions
---

# coding-with-beat — Music Control

You have a coding-with-beat MCP server running locally. Use its tools to control music without leaving the coding session.

## When to activate

- User says: "play", "pause", "skip", "next", "what's playing", "volume", "lyrics"
- User names a song, artist, or genre: "play some lofi", "put on 周杰伦"
- User types `cwb <command>` or `/cwb <command>`
- User asks about DJ Buddy or music status

## Available MCP tools

Call these tools directly — do not shell out to `cwb` unless MCP is unavailable.

| Tool | Purpose |
|------|---------|
| `play` | Resume playback |
| `play_song(query)` | Search and play by name/artist/genre |
| `play_number(number)` | Play track #n from last search or list |
| `pause` | Pause |
| `next_track` | Skip to next |
| `prev_track` | Go to previous |
| `now_playing` | Get current track info |
| `set_volume(percent)` | Volume 0–100 |
| `seek(seconds)` | Seek to position |
| `like_current` | Like / favourite current track |
| `search(query)` | Search library + Apple Music catalog |
| `list_library(limit)` | List all library tracks |
| `set_source(name)` | Switch source: `apple_music` \| `local` \| `qq_music` |
| `set_play_mode(mode)` | `shuffle` \| `sequential` \| `repeat` \| `repeat_one` |
| `status` | Full player state |
| `show_player` | Render pixel player UI |

## Natural language examples

| User says | Action |
|-----------|--------|
| "play some lofi" | `play_song("lofi")` |
| "skip this" | `next_track` |
| "what's playing?" | `now_playing` |
| "turn it up" | `set_volume(80)` (increase by ~15) |
| "pause the music" | `pause` |
| "shuffle mode" | `set_play_mode("shuffle")` |
| "like this song" | `like_current` |
| "search for Jay Chou" | `search("Jay Chou")` |
| "play #3" | `play_number(3)` |
| "switch to QQ Music" | `set_source("qq_music")` |

## Scene dispatch — mood / vibe / scene requests

Do NOT generate keywords. For any request that isn't a specific song/artist/command, match to a scene and call `smart_search` three times with the pre-defined angles:

| Scene | Trigger words | Angle 1 | Angle 2 | Angle 3 |
|---|---|---|---|---|
| 🎧 Lofi | lofi / 深夜 / 写代码 / 低保真 / chillhop | `lofi hip hop late night coding chill` | `lofi jazz rain study instrumental` | `chillhop beats lo-fi bedroom producer` |
| 🧠 Focus | 专注 / 心流 / ambient / 无人声 / flow state | `deep focus ambient instrumental no vocals` | `flow state drone minimal electronic` | `study music concentration piano quiet` |
| 🔥 Hype | 充能 / 运动 / 高能 / 早晨 / workout / hype | `morning energy upbeat pop indie fresh` | `workout motivation electronic dance` | `hype rap trap energetic beats pump` |
| ☕ Jazz | 爵士 / jazz / 咖啡馆 / smooth / bossa nova | `smooth jazz cafe background mellow` | `jazz trio acoustic bossa nova guitar` | `late night jazz piano bar cool relaxed` |
| 🌆 Synthwave | 赛博 / synthwave / 电子 / 夜驾 / neon | `synthwave retrowave night drive neon` | `cyberpunk electronic dark ambient synth` | `80s retro synth outrun vapor` |
| 🌅 Relax | 放松 / 解压 / 下班 / 傍晚 / unwind | `relaxing downtempo chill evening unwind` | `acoustic folk gentle calm soft` | `nature ambient breeze afternoon easy listening` |
| 🎹 Classical | 古典 / 钢琴 / 弦乐 / 交响 / classical | `classical piano solo nocturne gentle` | `string quartet orchestral cinematic calm` | `bach mozart ambient classical study` |
| 💙 Sad | 伤感 / 失落 / 难过 / melancholy / heartbreak | `melancholy emotional piano sad indie` | `heartbreak slow ballad rnb rainy` | `sorrowful strings cinematic emotional` |
| 🎉 Party | 派对 / 聚会 / party / dance / 蹦迪 / edm | `party dance pop upbeat celebratory` | `edm festival club electronic banger` | `latin pop reggaeton dance floor` |
| 🏮 Chinese | 国风 / 中国风 / 华语 / 民谣 / 古风 | `中国风 古风 古琴 传统乐器` | `华语流行 国语歌 indie 民谣` | `chinese traditional folk guzheng erhu instrumental` |
| 🌙 Sleep | 助眠 / 睡前 / 失眠 / sleep / white noise | `sleep music white noise ambient drone` | `lullaby soft piano rain sleep calm` | `meditation deep sleep binaural delta waves` |

Call all three `smart_search(query)` for the matched scene. Display results grouped by angle with emoji labels, number globally across groups (1, 2, 3…), end with: 喜欢哪首？说编号我来播。 Do NOT auto-play.

## CLI fallback

If MCP tools are unavailable, fall back to the `cwb` CLI:

```bash
cwb play "query"        # search and play
cwb pause               # pause
cwb next                # skip
cwb np                  # now playing
cwb volume 70           # volume
cwb like                # like current
```

## Response style

After any music action, give a **one-line** confirmation: `▶ Now playing: Midnight City — M83`. No extra commentary unless the user asks.
