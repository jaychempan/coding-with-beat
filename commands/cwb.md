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
| **anything else** (mood, scene, vibe, free-form description) | multi-angle smart search (see below) |

**Routing rule:** if the argument does NOT start with one of the fixed verbs above (play, search, list, pause, next, prev, source, like, mode, np, player, status, karaoke, resume), treat the entire argument as a mood/scene description and run **multi-angle smart search**.

For search or play-by-query, the `<query>` is the rest of the text after the verb (artist name, song name, mood — pass it through verbatim, including Chinese). Quote it.

## Scene dispatch — act immediately, no keyword generation

Do NOT generate keywords. Match the intent to a scene below and run its Bash commands right away.

| Scene | Trigger words |
|---|---|
| 🎧 Lofi | lofi / 深夜 / 写代码 / 低保真 / chillhop / 熬夜 / late night coding |
| 🧠 Focus | 专注 / 心流 / ambient / 无人声 / flow state / deep work |
| 🔥 Hype | 充能 / 运动 / 高能 / 早晨 / workout / 跑步 / hype / motivation |
| ☕ Jazz | 爵士 / jazz / 咖啡馆 / smooth / bossa nova / 慵懒 |
| 🌆 Synthwave | 赛博 / synthwave / 电子 / 夜驾 / neon / retrowave / cyberpunk |
| 🌅 Relax | 放松 / 解压 / 下班 / 傍晚 / unwind / chill out / 轻松 |
| 🎹 Classical | 古典 / 钢琴 / 弦乐 / 交响 / classical / piano |
| 💙 Sad | 伤感 / 失落 / 难过 / melancholy / heartbreak / sad / 失恋 |
| 🎉 Party | 派对 / 聚会 / 节日 / party / dance / 蹦迪 / edm / 狂欢 |
| 🏮 Chinese | 国风 / 中国风 / 华语 / 民谣 / 古风 / guzheng / 古琴 |
| 🌙 Sleep | 助眠 / 睡前 / 失眠 / sleep / white noise / 白噪音 |

For each matched scene, run its three Bash commands in parallel and display grouped results:

**🎧 Lofi:**
```bash
cwb smart_search "lofi hip hop late night coding chill" > /tmp/cwb_1.txt 2>&1 &
cwb smart_search "lofi jazz rain study instrumental" > /tmp/cwb_2.txt 2>&1 &
cwb smart_search "chillhop beats lo-fi bedroom producer" > /tmp/cwb_3.txt 2>&1 &
wait && cat /tmp/cwb_1.txt /tmp/cwb_2.txt /tmp/cwb_3.txt
```
Groups: **🎧 Lofi Hip Hop** · **🌧 Lofi Jazz Rain** · **🛏 Chillhop**

**🧠 Focus:**
```bash
cwb smart_search "deep focus ambient instrumental no vocals" > /tmp/cwb_1.txt 2>&1 &
cwb smart_search "flow state drone minimal electronic" > /tmp/cwb_2.txt 2>&1 &
cwb smart_search "study music concentration piano quiet" > /tmp/cwb_3.txt 2>&1 &
wait && cat /tmp/cwb_1.txt /tmp/cwb_2.txt /tmp/cwb_3.txt
```
Groups: **🧠 Deep Focus Ambient** · **⚡ Flow State** · **📚 Study Piano**

**🔥 Hype:**
```bash
cwb smart_search "morning energy upbeat pop indie fresh" > /tmp/cwb_1.txt 2>&1 &
cwb smart_search "workout motivation electronic dance" > /tmp/cwb_2.txt 2>&1 &
cwb smart_search "hype rap trap energetic beats pump" > /tmp/cwb_3.txt 2>&1 &
wait && cat /tmp/cwb_1.txt /tmp/cwb_2.txt /tmp/cwb_3.txt
```
Groups: **☀️ Morning Energy** · **💪 Workout** · **🔥 Hype Beats**

**☕ Jazz:**
```bash
cwb smart_search "smooth jazz cafe background mellow" > /tmp/cwb_1.txt 2>&1 &
cwb smart_search "jazz trio acoustic bossa nova guitar" > /tmp/cwb_2.txt 2>&1 &
cwb smart_search "late night jazz piano bar cool relaxed" > /tmp/cwb_3.txt 2>&1 &
wait && cat /tmp/cwb_1.txt /tmp/cwb_2.txt /tmp/cwb_3.txt
```
Groups: **☕ Smooth Jazz** · **🎸 Bossa Nova** · **🎹 Jazz Piano Bar**

**🌆 Synthwave:**
```bash
cwb smart_search "synthwave retrowave night drive neon" > /tmp/cwb_1.txt 2>&1 &
cwb smart_search "cyberpunk electronic dark ambient synth" > /tmp/cwb_2.txt 2>&1 &
cwb smart_search "80s retro synth outrun vapor" > /tmp/cwb_3.txt 2>&1 &
wait && cat /tmp/cwb_1.txt /tmp/cwb_2.txt /tmp/cwb_3.txt
```
Groups: **🌆 Synthwave** · **🤖 Cyberpunk** · **📼 Retro Synth**

**🌅 Relax:**
```bash
cwb smart_search "relaxing downtempo chill evening unwind" > /tmp/cwb_1.txt 2>&1 &
cwb smart_search "acoustic folk gentle calm soft" > /tmp/cwb_2.txt 2>&1 &
cwb smart_search "nature ambient breeze afternoon easy listening" > /tmp/cwb_3.txt 2>&1 &
wait && cat /tmp/cwb_1.txt /tmp/cwb_2.txt /tmp/cwb_3.txt
```
Groups: **🌅 Downtempo Chill** · **🎸 Acoustic Folk** · **🌿 Nature Ambient**

**🎹 Classical:**
```bash
cwb smart_search "classical piano solo nocturne gentle" > /tmp/cwb_1.txt 2>&1 &
cwb smart_search "string quartet orchestral cinematic calm" > /tmp/cwb_2.txt 2>&1 &
cwb smart_search "bach mozart ambient classical study" > /tmp/cwb_3.txt 2>&1 &
wait && cat /tmp/cwb_1.txt /tmp/cwb_2.txt /tmp/cwb_3.txt
```
Groups: **🎹 Piano Solo** · **🎻 String Quartet** · **🎼 Baroque & Classical**

**💙 Sad:**
```bash
cwb smart_search "melancholy emotional piano sad indie" > /tmp/cwb_1.txt 2>&1 &
cwb smart_search "heartbreak slow ballad rnb rainy" > /tmp/cwb_2.txt 2>&1 &
cwb smart_search "sorrowful strings cinematic emotional" > /tmp/cwb_3.txt 2>&1 &
wait && cat /tmp/cwb_1.txt /tmp/cwb_2.txt /tmp/cwb_3.txt
```
Groups: **💙 Melancholy** · **🌧 Heartbreak Ballad** · **🎻 Sorrowful Strings**

**🎉 Party:**
```bash
cwb smart_search "party dance pop upbeat celebratory" > /tmp/cwb_1.txt 2>&1 &
cwb smart_search "edm festival club electronic banger" > /tmp/cwb_2.txt 2>&1 &
cwb smart_search "latin pop reggaeton dance floor" > /tmp/cwb_3.txt 2>&1 &
wait && cat /tmp/cwb_1.txt /tmp/cwb_2.txt /tmp/cwb_3.txt
```
Groups: **🎉 Dance Pop** · **🎛 EDM Festival** · **💃 Latin Dance**

**🏮 Chinese:**
```bash
cwb smart_search "中国风 古风 古琴 传统乐器" > /tmp/cwb_1.txt 2>&1 &
cwb smart_search "华语流行 国语歌 indie 民谣" > /tmp/cwb_2.txt 2>&1 &
cwb smart_search "chinese traditional folk guzheng erhu instrumental" > /tmp/cwb_3.txt 2>&1 &
wait && cat /tmp/cwb_1.txt /tmp/cwb_2.txt /tmp/cwb_3.txt
```
Groups: **🏮 古风国乐** · **🎤 华语独立** · **🪘 传统器乐**

**🌙 Sleep:**
```bash
cwb smart_search "sleep music white noise ambient drone" > /tmp/cwb_1.txt 2>&1 &
cwb smart_search "lullaby soft piano rain sleep calm" > /tmp/cwb_2.txt 2>&1 &
cwb smart_search "meditation deep sleep binaural delta waves" > /tmp/cwb_3.txt 2>&1 &
wait && cat /tmp/cwb_1.txt /tmp/cwb_2.txt /tmp/cwb_3.txt
```
Groups: **🌙 Sleep Ambient** · **💤 Lullaby** · **🧘 Deep Sleep**

After collecting results: display grouped with emoji labels, renumber tracks globally (1, 2, 3… across all groups), end with: "喜欢哪首？说编号我来播。" Do NOT auto-play.

If intent doesn't match any scene above, fall back to: `cwb search "<user's query>"`

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
