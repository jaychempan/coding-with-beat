# Local Playback Enhancement: M3U Playlist Support + mpv Backend

**Date:** 2026-05-23
**Status:** Approved

## Goal

Make local file playback genuinely convenient by:
1. Supporting user-defined M3U playlist files
2. Enabling real pause/seek via mpv (with afplay fallback)
3. Expanding supported audio formats
4. Integrating playlists into both natural language and explicit `/cwb` commands

## Scope

Changes are confined to:
- `coding_with_beat/sources/local.py` — backend abstraction + playlist manager
- `coding_with_beat/server.py` — three new MCP tools
- `coding_with_beat/cwb_agent.py` / `codex_vibe.py` — system prompt additions
- `commands/cwb.md` — documentation

No new files. No new source type. No changes to other sources.

---

## Section 1: Playback Backend Abstraction

### Detection

On module load, detect available player once and cache:

```python
_PLAYER_BACKEND: str  # "mpv" | "afplay"

def _detect_backend() -> str:
    if shutil.which("mpv"):
        return "mpv"
    return "afplay"
```

### mpv mode (when available)

Start with IPC socket for real-time control:

```
mpv --no-video --quiet --input-ipc-server=/tmp/cwb-mpv.sock <path>
```

Control via socket commands:
- **Pause/resume:** `{"command": ["set_property", "pause", true/false]}`
- **Seek:** `{"command": ["seek", <seconds>, "absolute"]}`
- **Position query:** `{"command": ["get_property", "time-pos"]}`

`now_playing()` reads actual position from mpv IPC instead of wall-clock math.
Pause and seek work correctly — audio does not restart from the beginning.

### afplay mode (fallback, current behavior)

Existing implementation unchanged. Internal functions renamed with `_afplay_` prefix for clarity. Wall-clock position arithmetic retained as-is.

### Behavior matrix

| Operation | mpv | afplay |
|-----------|-----|--------|
| Pause | Real pause | Kill process |
| Resume | Real resume | Restart from beginning* |
| Seek | Real seek | Restart from beginning* |
| Position | IPC query | Wall-clock math |

*afplay limitation, documented to user on first use.

---

## Section 2: M3U Support + Playlist Manager

### Supported audio formats

```python
AUDIO_EXTS = {
    ".mp3", ".m4a", ".flac", ".wav", ".aac", ".ogg",
    ".opus", ".wma", ".aiff", ".aif", ".alac",
    ".mp4", ".webm",
    ".ape", ".caf", ".dsf",
}
```

Used by `_scan()` for library mode. M3U files are not filtered by extension — whatever the user wrote is passed to the player.

### M3U parser

```python
def _parse_m3u(path: Path) -> list[Path]:
```

- Skips `#EXTM3U` header and `#EXTINF` metadata lines
- Resolves relative paths relative to the `.m3u` file's directory
- Encoding: UTF-8 first, fallback to `latin-1`
- Missing files are skipped with a warning (not an error)
- Returns only paths that exist on disk

### Playlist manager (three functions)

**Default playlist directory:** `~/.coding-with-beat/playlists/`

```python
def list_playlists() -> list[dict]:
    # Scans ~/.coding-with-beat/playlists/*.m3u
    # Returns: [{name, path, track_count}, ...]

def load_playlist(name_or_path: str | None) -> list[Path]:
    # name  → fuzzy match against filenames in default dir (stem, case-insensitive)
    # path  → direct load, supports absolute paths and ~ expansion
    # None  → clear playlist, return to library mode
    # Writes resolved tracks to local.json as "playlist_tracks"
    # Also writes "playlist_name" for display purposes

def active_playlist() -> dict | None:
    # Returns {name, track_count, current_index} or None (library mode)
```

### LocalFiles._scan() change

```python
def _scan(self) -> list[Path]:
    s = self._state()
    if s.get("playlist_tracks"):
        return [Path(p) for p in s["playlist_tracks"]]
    # existing library walk logic, with expanded AUDIO_EXTS
```

`next()` and `prev()` are unchanged — they call `_scan()` and index into the result.

### local.json additions

```json
{
  "playlist_tracks": ["/path/to/a.mp3", "/path/to/b.flac"],
  "playlist_name": "lofi-chill"
}
```

Both fields absent (or null) = library mode.

---

## Section 3: MCP Tools + Natural Language

### New MCP tools in server.py

Three tools added alongside existing `play_song`, `list_library`:

**`list_playlists()`**
```
Returns: [{name, track_count, path}]
Lists all .m3u files in ~/.coding-with-beat/playlists/
```

**`load_playlist(name_or_path: str | None)`**
```
name_or_path:
  str  → fuzzy match playlist name OR absolute/~ path to any .m3u
  None → exit playlist mode, return to library
Returns: NowPlaying (auto-plays first track)
```

**`active_playlist()`**
```
Returns: {name, track_count, current_index} | null
```

### Natural language mapping

Additions to cwb_agent.py / codex_vibe.py system prompt:

| User says | Tool called |
|-----------|-------------|
| "播放我的 lofi 歌单" / "play my lofi playlist" | `load_playlist("lofi")` |
| "有哪些歌单" / "list my playlists" | `list_playlists()` |
| "播放 ~/Music/jazz.m3u" | `load_playlist("~/Music/jazz.m3u")` |
| "切回音乐库" / "back to library" | `load_playlist(None)` |

### Explicit /cwb commands (commands/cwb.md)

```
/cwb playlist list           list available playlists
/cwb playlist <name>         load playlist by name (fuzzy match)
/cwb playlist <path>         load playlist from file path
/cwb playlist off            exit playlist mode, return to library
```

### now_playing output change

Optional field `playlist` added when a playlist is active:

```json
{
  "title": "Feather",
  "artist": "Nujabes",
  "playlist": "lofi-chill [3/24]"
}
```

Field is absent when in library mode (no breaking change).

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| mpv IPC socket not ready yet | Retry up to 500ms, then fall back to wall-clock position |
| M3U references missing files | Skip entry, log warning, continue |
| Playlist name matches nothing | Return error message: "No playlist matching '<name>' found" |
| All tracks in playlist missing | Return error, stay in library mode |
| mpv crashes mid-playback | Detect dead PID, same logic as afplay natural-end handling |

## Out of Scope

- Playlist editing / creating from within the tool
- Cross-platform support (Windows/Linux) — afplay and mpv paths are macOS-first
- Shuffle / repeat mode
- `like_current()` for local files (remains NotImplementedError)
- M3U8 (HLS streaming) format
