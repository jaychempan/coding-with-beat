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
