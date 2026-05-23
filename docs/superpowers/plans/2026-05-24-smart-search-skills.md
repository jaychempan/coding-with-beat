# Smart Search Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace runtime LLM keyword generation in multi-angle smart search with 11 pre-defined scene skill files (Codex + Claude Code), so music plays immediately without inference delay.

**Architecture:** Router layer (existing cwb files, updated) pattern-matches intent to a scene name and delegates. Scene skill files (22 new files) contain hardcoded keyword angles and run `cwb smart_search` in parallel immediately on activation.

**Tech Stack:** Markdown skill files (YAML frontmatter), Bash, existing `cwb smart_search` CLI command.

---

## File Map

**Create (22 files):**
```
codex_skills/cwb-lofi/SKILL.md
codex_skills/cwb-focus/SKILL.md
codex_skills/cwb-hype/SKILL.md
codex_skills/cwb-jazz/SKILL.md
codex_skills/cwb-synthwave/SKILL.md
codex_skills/cwb-relax/SKILL.md
codex_skills/cwb-classical/SKILL.md
codex_skills/cwb-sad/SKILL.md
codex_skills/cwb-party/SKILL.md
codex_skills/cwb-chinese/SKILL.md
codex_skills/cwb-sleep/SKILL.md
commands/cwb-lofi.md
commands/cwb-focus.md
commands/cwb-hype.md
commands/cwb-jazz.md
commands/cwb-synthwave.md
commands/cwb-relax.md
commands/cwb-classical.md
commands/cwb-sad.md
commands/cwb-party.md
commands/cwb-chinese.md
commands/cwb-sleep.md
```

**Modify (2 files):**
```
commands/cwb.md           — replace "generate keywords" with scene dispatch table
codex_skills/cwb/SKILL.md — add scene dispatch section
```

---

## Task 1: cwb-lofi scene skill

**Files:**
- Create: `codex_skills/cwb-lofi/SKILL.md`
- Create: `commands/cwb-lofi.md`

- [ ] **Step 1: Create Codex skill**

```bash
mkdir -p codex_skills/cwb-lofi
```

Write `codex_skills/cwb-lofi/SKILL.md`:

```markdown
---
name: cwb-lofi
description: Play lofi / chill background music. Activate when the user mentions lofi, 深夜, 写代码, 低保真, chillhop, 熬夜, late night coding, or asks for background beats for coding or studying.
metadata:
  short-description: Lofi & chill for coding
---

# Lofi — 深夜写代码

## Trigger patterns
深夜 / 写代码 / lofi / 低保真 / chillhop / 熬夜 / late night / coding music / study beats

## Action — run immediately in parallel

Run all three at once, collect output:

```bash
cwb smart_search "lofi hip hop late night coding chill" > /tmp/cwb_lofi_1.txt 2>&1 &
cwb smart_search "lofi jazz rain study instrumental" > /tmp/cwb_lofi_2.txt 2>&1 &
cwb smart_search "chillhop beats lo-fi bedroom producer" > /tmp/cwb_lofi_3.txt 2>&1 &
wait
```

## Display format

Show three groups. Renumber tracks globally (1, 2, 3… across all groups):

**🎧 Lofi Hip Hop**
(results from angle 1)

**🌧 Lofi Jazz Rain**
(results from angle 2)

**🛏 Chillhop**
(results from angle 3)

End with: 喜欢哪首？说编号我来播。
Do NOT auto-play.
```

- [ ] **Step 2: Create Claude Code command**

Write `commands/cwb-lofi.md`:

```markdown
---
description: Play lofi / late-night coding music. Triggers: lofi, 深夜, 写代码, 低保真, chillhop, late night coding, study beats.
allowed-tools: Bash
argument-hint: ""
---

# Lofi — 深夜写代码

Run immediately — no analysis needed:

```bash
cwb smart_search "lofi hip hop late night coding chill" > /tmp/cwb_lofi_1.txt 2>&1 &
cwb smart_search "lofi jazz rain study instrumental" > /tmp/cwb_lofi_2.txt 2>&1 &
cwb smart_search "chillhop beats lo-fi bedroom producer" > /tmp/cwb_lofi_3.txt 2>&1 &
wait
cat /tmp/cwb_lofi_1.txt
cat /tmp/cwb_lofi_2.txt
cat /tmp/cwb_lofi_3.txt
```

Display results in three groups with labels, renumber globally (1, 2, 3… across all groups):

**🎧 Lofi Hip Hop** · **🌧 Lofi Jazz Rain** · **🛏 Chillhop**

End with: 喜欢哪首？说编号我来播。
```

- [ ] **Step 3: Verify files exist**

```bash
ls codex_skills/cwb-lofi/SKILL.md commands/cwb-lofi.md
```

Expected: both paths printed, no errors.

- [ ] **Step 4: Spot-check search angle works**

```bash
cwb smart_search "lofi hip hop late night coding chill"
```

Expected: numbered track list (may be empty if library is sparse, but no crash).

- [ ] **Step 5: Commit**

```bash
git add codex_skills/cwb-lofi/ commands/cwb-lofi.md
git commit -m "feat: add cwb-lofi scene skill (Codex + Claude Code)"
```

---

## Task 2: cwb-focus + cwb-hype scene skills

**Files:**
- Create: `codex_skills/cwb-focus/SKILL.md`, `commands/cwb-focus.md`
- Create: `codex_skills/cwb-hype/SKILL.md`, `commands/cwb-hype.md`

- [ ] **Step 1: Create cwb-focus Codex skill**

```bash
mkdir -p codex_skills/cwb-focus
```

Write `codex_skills/cwb-focus/SKILL.md`:

```markdown
---
name: cwb-focus
description: Play focus / flow-state music with no vocals. Activate when user mentions 专注, 心流, ambient, 无人声, flow state, deep work, 摸鱼不分心, concentration, or needs distraction-free background music.
metadata:
  short-description: Focus & flow state music
---

# Focus — 专注心流

## Trigger patterns
专注 / 心流 / ambient / 无人声 / flow state / deep work / 摸鱼不分心 / concentration / no vocals

## Action — run immediately in parallel

```bash
cwb smart_search "deep focus ambient instrumental no vocals" > /tmp/cwb_focus_1.txt 2>&1 &
cwb smart_search "flow state drone minimal electronic" > /tmp/cwb_focus_2.txt 2>&1 &
cwb smart_search "study music concentration piano quiet" > /tmp/cwb_focus_3.txt 2>&1 &
wait
```

## Display format

**🧠 Deep Focus Ambient**
(results from angle 1)

**⚡ Flow State**
(results from angle 2)

**📚 Study Piano**
(results from angle 3)

Renumber globally. End with: 喜欢哪首？说编号我来播。
Do NOT auto-play.
```

- [ ] **Step 2: Create cwb-focus Claude Code command**

Write `commands/cwb-focus.md`:

```markdown
---
description: Play focus / flow-state instrumental music. Triggers: 专注, 心流, ambient, 无人声, flow state, deep work, concentration, no vocals.
allowed-tools: Bash
argument-hint: ""
---

# Focus — 专注心流

Run immediately:

```bash
cwb smart_search "deep focus ambient instrumental no vocals" > /tmp/cwb_focus_1.txt 2>&1 &
cwb smart_search "flow state drone minimal electronic" > /tmp/cwb_focus_2.txt 2>&1 &
cwb smart_search "study music concentration piano quiet" > /tmp/cwb_focus_3.txt 2>&1 &
wait
cat /tmp/cwb_focus_1.txt
cat /tmp/cwb_focus_2.txt
cat /tmp/cwb_focus_3.txt
```

Group as **🧠 Deep Focus Ambient** · **⚡ Flow State** · **📚 Study Piano**. Renumber globally. End with: 喜欢哪首？说编号我来播。
```

- [ ] **Step 3: Create cwb-hype Codex skill**

```bash
mkdir -p codex_skills/cwb-hype
```

Write `codex_skills/cwb-hype/SKILL.md`:

```markdown
---
name: cwb-hype
description: Play energetic / high-energy music for workouts, morning wake-up, or motivation. Activate when user mentions 充能, 运动, 高能, 早晨, workout, 跑步, 起床, hype, motivation, or wants music to get pumped up.
metadata:
  short-description: High energy & workout music
---

# Hype — 充能运动

## Trigger patterns
充能 / 运动 / 高能 / 早晨 / workout / 跑步 / 起床 / hype / motivation / pump up / 跑步

## Action — run immediately in parallel

```bash
cwb smart_search "morning energy upbeat pop indie fresh" > /tmp/cwb_hype_1.txt 2>&1 &
cwb smart_search "workout motivation electronic dance" > /tmp/cwb_hype_2.txt 2>&1 &
cwb smart_search "hype rap trap energetic beats pump" > /tmp/cwb_hype_3.txt 2>&1 &
wait
```

## Display format

**☀️ Morning Energy**
(results from angle 1)

**💪 Workout**
(results from angle 2)

**🔥 Hype Beats**
(results from angle 3)

Renumber globally. End with: 喜欢哪首？说编号我来播。
Do NOT auto-play.
```

- [ ] **Step 4: Create cwb-hype Claude Code command**

Write `commands/cwb-hype.md`:

```markdown
---
description: Play high-energy / workout / morning motivation music. Triggers: 充能, 运动, 高能, 早晨, workout, hype, motivation, 跑步, 起床.
allowed-tools: Bash
argument-hint: ""
---

# Hype — 充能运动

Run immediately:

```bash
cwb smart_search "morning energy upbeat pop indie fresh" > /tmp/cwb_hype_1.txt 2>&1 &
cwb smart_search "workout motivation electronic dance" > /tmp/cwb_hype_2.txt 2>&1 &
cwb smart_search "hype rap trap energetic beats pump" > /tmp/cwb_hype_3.txt 2>&1 &
wait
cat /tmp/cwb_hype_1.txt
cat /tmp/cwb_hype_2.txt
cat /tmp/cwb_hype_3.txt
```

Group as **☀️ Morning Energy** · **💪 Workout** · **🔥 Hype Beats**. Renumber globally. End with: 喜欢哪首？说编号我来播。
```

- [ ] **Step 5: Verify files**

```bash
ls codex_skills/cwb-focus/SKILL.md codex_skills/cwb-hype/SKILL.md commands/cwb-focus.md commands/cwb-hype.md
```

Expected: all four paths printed.

- [ ] **Step 6: Commit**

```bash
git add codex_skills/cwb-focus/ codex_skills/cwb-hype/ commands/cwb-focus.md commands/cwb-hype.md
git commit -m "feat: add cwb-focus and cwb-hype scene skills"
```

---

## Task 3: cwb-jazz + cwb-synthwave scene skills

**Files:**
- Create: `codex_skills/cwb-jazz/SKILL.md`, `commands/cwb-jazz.md`
- Create: `codex_skills/cwb-synthwave/SKILL.md`, `commands/cwb-synthwave.md`

- [ ] **Step 1: Create cwb-jazz Codex skill**

```bash
mkdir -p codex_skills/cwb-jazz
```

Write `codex_skills/cwb-jazz/SKILL.md`:

```markdown
---
name: cwb-jazz
description: Play jazz, smooth jazz, or bossa nova music. Activate when user mentions 爵士, jazz, 咖啡馆, smooth, bossa nova, 慵懒, 下午, café music, or relaxed instrumental.
metadata:
  short-description: Jazz & café atmosphere
---

# Jazz — 爵士咖啡馆

## Trigger patterns
爵士 / jazz / 咖啡馆 / smooth / bossa nova / 慵懒 / 下午茶 / café / swing

## Action — run immediately in parallel

```bash
cwb smart_search "smooth jazz cafe background mellow" > /tmp/cwb_jazz_1.txt 2>&1 &
cwb smart_search "jazz trio acoustic bossa nova guitar" > /tmp/cwb_jazz_2.txt 2>&1 &
cwb smart_search "late night jazz piano bar cool relaxed" > /tmp/cwb_jazz_3.txt 2>&1 &
wait
```

## Display format

**☕ Smooth Jazz**
(results from angle 1)

**🎸 Bossa Nova**
(results from angle 2)

**🎹 Jazz Piano Bar**
(results from angle 3)

Renumber globally. End with: 喜欢哪首？说编号我来播。
Do NOT auto-play.
```

- [ ] **Step 2: Create cwb-jazz Claude Code command**

Write `commands/cwb-jazz.md`:

```markdown
---
description: Play jazz / bossa nova / café atmosphere music. Triggers: 爵士, jazz, 咖啡馆, smooth, bossa nova, 慵懒, café.
allowed-tools: Bash
argument-hint: ""
---

# Jazz — 爵士咖啡馆

Run immediately:

```bash
cwb smart_search "smooth jazz cafe background mellow" > /tmp/cwb_jazz_1.txt 2>&1 &
cwb smart_search "jazz trio acoustic bossa nova guitar" > /tmp/cwb_jazz_2.txt 2>&1 &
cwb smart_search "late night jazz piano bar cool relaxed" > /tmp/cwb_jazz_3.txt 2>&1 &
wait
cat /tmp/cwb_jazz_1.txt
cat /tmp/cwb_jazz_2.txt
cat /tmp/cwb_jazz_3.txt
```

Group as **☕ Smooth Jazz** · **🎸 Bossa Nova** · **🎹 Jazz Piano Bar**. Renumber globally. End with: 喜欢哪首？说编号我来播。
```

- [ ] **Step 3: Create cwb-synthwave Codex skill**

```bash
mkdir -p codex_skills/cwb-synthwave
```

Write `codex_skills/cwb-synthwave/SKILL.md`:

```markdown
---
name: cwb-synthwave
description: Play synthwave, cyberpunk, or retro electronic music. Activate when user mentions 赛博, synthwave, 电子, 夜驾, neon, retrowave, 复古, cyberpunk, outrun, or 80s synth vibes.
metadata:
  short-description: Synthwave & cyberpunk electronic
---

# Synthwave — 赛博夜驾

## Trigger patterns
赛博 / synthwave / 电子 / 夜驾 / neon / retrowave / 复古 / cyberpunk / outrun / 80s synth

## Action — run immediately in parallel

```bash
cwb smart_search "synthwave retrowave night drive neon" > /tmp/cwb_synth_1.txt 2>&1 &
cwb smart_search "cyberpunk electronic dark ambient synth" > /tmp/cwb_synth_2.txt 2>&1 &
cwb smart_search "80s retro synth outrun vapor" > /tmp/cwb_synth_3.txt 2>&1 &
wait
```

## Display format

**🌆 Synthwave**
(results from angle 1)

**🤖 Cyberpunk**
(results from angle 2)

**📼 Retro Synth**
(results from angle 3)

Renumber globally. End with: 喜欢哪首？说编号我来播。
Do NOT auto-play.
```

- [ ] **Step 4: Create cwb-synthwave Claude Code command**

Write `commands/cwb-synthwave.md`:

```markdown
---
description: Play synthwave / cyberpunk / retro electronic music. Triggers: 赛博, synthwave, 电子, 夜驾, neon, retrowave, cyberpunk, 复古, outrun.
allowed-tools: Bash
argument-hint: ""
---

# Synthwave — 赛博夜驾

Run immediately:

```bash
cwb smart_search "synthwave retrowave night drive neon" > /tmp/cwb_synth_1.txt 2>&1 &
cwb smart_search "cyberpunk electronic dark ambient synth" > /tmp/cwb_synth_2.txt 2>&1 &
cwb smart_search "80s retro synth outrun vapor" > /tmp/cwb_synth_3.txt 2>&1 &
wait
cat /tmp/cwb_synth_1.txt
cat /tmp/cwb_synth_2.txt
cat /tmp/cwb_synth_3.txt
```

Group as **🌆 Synthwave** · **🤖 Cyberpunk** · **📼 Retro Synth**. Renumber globally. End with: 喜欢哪首？说编号我来播。
```

- [ ] **Step 5: Verify files**

```bash
ls codex_skills/cwb-jazz/SKILL.md codex_skills/cwb-synthwave/SKILL.md commands/cwb-jazz.md commands/cwb-synthwave.md
```

Expected: all four paths printed.

- [ ] **Step 6: Commit**

```bash
git add codex_skills/cwb-jazz/ codex_skills/cwb-synthwave/ commands/cwb-jazz.md commands/cwb-synthwave.md
git commit -m "feat: add cwb-jazz and cwb-synthwave scene skills"
```

---

## Task 4: cwb-relax + cwb-classical scene skills

**Files:**
- Create: `codex_skills/cwb-relax/SKILL.md`, `commands/cwb-relax.md`
- Create: `codex_skills/cwb-classical/SKILL.md`, `commands/cwb-classical.md`

- [ ] **Step 1: Create cwb-relax Codex skill**

```bash
mkdir -p codex_skills/cwb-relax
```

Write `codex_skills/cwb-relax/SKILL.md`:

```markdown
---
name: cwb-relax
description: Play relaxing / unwinding music for after work or evening wind-down. Activate when user mentions 放松, 解压, 下班, 傍晚, unwind, chill out, 休息, 轻松, or wants to decompress.
metadata:
  short-description: Relax & evening wind-down
---

# Relax — 放松解压

## Trigger patterns
放松 / 解压 / 下班 / 傍晚 / unwind / chill out / 休息 / 轻松 / 减压

## Action — run immediately in parallel

```bash
cwb smart_search "relaxing downtempo chill evening unwind" > /tmp/cwb_relax_1.txt 2>&1 &
cwb smart_search "acoustic folk gentle calm soft" > /tmp/cwb_relax_2.txt 2>&1 &
cwb smart_search "nature ambient breeze afternoon easy listening" > /tmp/cwb_relax_3.txt 2>&1 &
wait
```

## Display format

**🌅 Downtempo Chill**
(results from angle 1)

**🎸 Acoustic Folk**
(results from angle 2)

**🌿 Nature Ambient**
(results from angle 3)

Renumber globally. End with: 喜欢哪首？说编号我来播。
Do NOT auto-play.
```

- [ ] **Step 2: Create cwb-relax Claude Code command**

Write `commands/cwb-relax.md`:

```markdown
---
description: Play relaxing / evening wind-down music. Triggers: 放松, 解压, 下班, 傍晚, unwind, chill out, 休息, 轻松.
allowed-tools: Bash
argument-hint: ""
---

# Relax — 放松解压

Run immediately:

```bash
cwb smart_search "relaxing downtempo chill evening unwind" > /tmp/cwb_relax_1.txt 2>&1 &
cwb smart_search "acoustic folk gentle calm soft" > /tmp/cwb_relax_2.txt 2>&1 &
cwb smart_search "nature ambient breeze afternoon easy listening" > /tmp/cwb_relax_3.txt 2>&1 &
wait
cat /tmp/cwb_relax_1.txt
cat /tmp/cwb_relax_2.txt
cat /tmp/cwb_relax_3.txt
```

Group as **🌅 Downtempo Chill** · **🎸 Acoustic Folk** · **🌿 Nature Ambient**. Renumber globally. End with: 喜欢哪首？说编号我来播。
```

- [ ] **Step 3: Create cwb-classical Codex skill**

```bash
mkdir -p codex_skills/cwb-classical
```

Write `codex_skills/cwb-classical/SKILL.md`:

```markdown
---
name: cwb-classical
description: Play classical music including piano, strings, and orchestral pieces. Activate when user mentions 古典, 钢琴, 弦乐, 交响, classical, piano, 管弦乐, 巴赫, 莫扎特, or orchestral music.
metadata:
  short-description: Classical, piano & orchestral
---

# Classical — 古典乐

## Trigger patterns
古典 / 钢琴 / 弦乐 / 交响 / classical / piano / 管弦乐 / 巴赫 / 莫扎特 / 肖邦

## Action — run immediately in parallel

```bash
cwb smart_search "classical piano solo nocturne gentle" > /tmp/cwb_classical_1.txt 2>&1 &
cwb smart_search "string quartet orchestral cinematic calm" > /tmp/cwb_classical_2.txt 2>&1 &
cwb smart_search "bach mozart ambient classical study" > /tmp/cwb_classical_3.txt 2>&1 &
wait
```

## Display format

**🎹 Piano Solo**
(results from angle 1)

**🎻 String Quartet**
(results from angle 2)

**🎼 Baroque & Classical**
(results from angle 3)

Renumber globally. End with: 喜欢哪首？说编号我来播。
Do NOT auto-play.
```

- [ ] **Step 4: Create cwb-classical Claude Code command**

Write `commands/cwb-classical.md`:

```markdown
---
description: Play classical music — piano solos, strings, orchestral. Triggers: 古典, 钢琴, 弦乐, 交响, classical, piano, 巴赫, 莫扎特, orchestral.
allowed-tools: Bash
argument-hint: ""
---

# Classical — 古典乐

Run immediately:

```bash
cwb smart_search "classical piano solo nocturne gentle" > /tmp/cwb_classical_1.txt 2>&1 &
cwb smart_search "string quartet orchestral cinematic calm" > /tmp/cwb_classical_2.txt 2>&1 &
cwb smart_search "bach mozart ambient classical study" > /tmp/cwb_classical_3.txt 2>&1 &
wait
cat /tmp/cwb_classical_1.txt
cat /tmp/cwb_classical_2.txt
cat /tmp/cwb_classical_3.txt
```

Group as **🎹 Piano Solo** · **🎻 String Quartet** · **🎼 Baroque & Classical**. Renumber globally. End with: 喜欢哪首？说编号我来播。
```

- [ ] **Step 5: Verify files**

```bash
ls codex_skills/cwb-relax/SKILL.md codex_skills/cwb-classical/SKILL.md commands/cwb-relax.md commands/cwb-classical.md
```

Expected: all four paths printed.

- [ ] **Step 6: Commit**

```bash
git add codex_skills/cwb-relax/ codex_skills/cwb-classical/ commands/cwb-relax.md commands/cwb-classical.md
git commit -m "feat: add cwb-relax and cwb-classical scene skills"
```

---

## Task 5: cwb-sad + cwb-party scene skills

**Files:**
- Create: `codex_skills/cwb-sad/SKILL.md`, `commands/cwb-sad.md`
- Create: `codex_skills/cwb-party/SKILL.md`, `commands/cwb-party.md`

- [ ] **Step 1: Create cwb-sad Codex skill**

```bash
mkdir -p codex_skills/cwb-sad
```

Write `codex_skills/cwb-sad/SKILL.md`:

```markdown
---
name: cwb-sad
description: Play melancholy / emotional / heartbreak music. Activate when user mentions 伤感, 失落, 难过, melancholy, heartbreak, sad, 情绪, 哭泣, 失恋, emotional, or wants music to match a low mood.
metadata:
  short-description: Melancholy & emotional music
---

# Sad — 伤感情绪

## Trigger patterns
伤感 / 失落 / 难过 / melancholy / heartbreak / sad / 情绪 / 哭泣 / 失恋 / emotional

## Action — run immediately in parallel

```bash
cwb smart_search "melancholy emotional piano sad indie" > /tmp/cwb_sad_1.txt 2>&1 &
cwb smart_search "heartbreak slow ballad rnb rainy" > /tmp/cwb_sad_2.txt 2>&1 &
cwb smart_search "sorrowful strings cinematic emotional" > /tmp/cwb_sad_3.txt 2>&1 &
wait
```

## Display format

**💙 Melancholy**
(results from angle 1)

**🌧 Heartbreak Ballad**
(results from angle 2)

**🎻 Sorrowful Strings**
(results from angle 3)

Renumber globally. End with: 喜欢哪首？说编号我来播。
Do NOT auto-play.
```

- [ ] **Step 2: Create cwb-sad Claude Code command**

Write `commands/cwb-sad.md`:

```markdown
---
description: Play melancholy / emotional / heartbreak music. Triggers: 伤感, 失落, 难过, melancholy, heartbreak, sad, 情绪, 失恋, emotional.
allowed-tools: Bash
argument-hint: ""
---

# Sad — 伤感情绪

Run immediately:

```bash
cwb smart_search "melancholy emotional piano sad indie" > /tmp/cwb_sad_1.txt 2>&1 &
cwb smart_search "heartbreak slow ballad rnb rainy" > /tmp/cwb_sad_2.txt 2>&1 &
cwb smart_search "sorrowful strings cinematic emotional" > /tmp/cwb_sad_3.txt 2>&1 &
wait
cat /tmp/cwb_sad_1.txt
cat /tmp/cwb_sad_2.txt
cat /tmp/cwb_sad_3.txt
```

Group as **💙 Melancholy** · **🌧 Heartbreak Ballad** · **🎻 Sorrowful Strings**. Renumber globally. End with: 喜欢哪首？说编号我来播。
```

- [ ] **Step 3: Create cwb-party Codex skill**

```bash
mkdir -p codex_skills/cwb-party
```

Write `codex_skills/cwb-party/SKILL.md`:

```markdown
---
name: cwb-party
description: Play party / dance / celebratory music. Activate when user mentions 派对, 聚会, 节日, party, dance, 蹦迪, edm, 狂欢, 热闹, or wants music to get a crowd going.
metadata:
  short-description: Party & dance floor music
---

# Party — 派对狂欢

## Trigger patterns
派对 / 聚会 / 节日 / party / dance / 蹦迪 / edm / 狂欢 / 热闹 / celebrate

## Action — run immediately in parallel

```bash
cwb smart_search "party dance pop upbeat celebratory" > /tmp/cwb_party_1.txt 2>&1 &
cwb smart_search "edm festival club electronic banger" > /tmp/cwb_party_2.txt 2>&1 &
cwb smart_search "latin pop reggaeton dance floor" > /tmp/cwb_party_3.txt 2>&1 &
wait
```

## Display format

**🎉 Dance Pop**
(results from angle 1)

**🎛 EDM Festival**
(results from angle 2)

**💃 Latin Dance**
(results from angle 3)

Renumber globally. End with: 喜欢哪首？说编号我来播。
Do NOT auto-play.
```

- [ ] **Step 4: Create cwb-party Claude Code command**

Write `commands/cwb-party.md`:

```markdown
---
description: Play party / dance / EDM music. Triggers: 派对, 聚会, 节日, party, dance, 蹦迪, edm, 狂欢, celebrate.
allowed-tools: Bash
argument-hint: ""
---

# Party — 派对狂欢

Run immediately:

```bash
cwb smart_search "party dance pop upbeat celebratory" > /tmp/cwb_party_1.txt 2>&1 &
cwb smart_search "edm festival club electronic banger" > /tmp/cwb_party_2.txt 2>&1 &
cwb smart_search "latin pop reggaeton dance floor" > /tmp/cwb_party_3.txt 2>&1 &
wait
cat /tmp/cwb_party_1.txt
cat /tmp/cwb_party_2.txt
cat /tmp/cwb_party_3.txt
```

Group as **🎉 Dance Pop** · **🎛 EDM Festival** · **💃 Latin Dance**. Renumber globally. End with: 喜欢哪首？说编号我来播。
```

- [ ] **Step 5: Verify files**

```bash
ls codex_skills/cwb-sad/SKILL.md codex_skills/cwb-party/SKILL.md commands/cwb-sad.md commands/cwb-party.md
```

Expected: all four paths printed.

- [ ] **Step 6: Commit**

```bash
git add codex_skills/cwb-sad/ codex_skills/cwb-party/ commands/cwb-sad.md commands/cwb-party.md
git commit -m "feat: add cwb-sad and cwb-party scene skills"
```

---

## Task 6: cwb-chinese + cwb-sleep scene skills

**Files:**
- Create: `codex_skills/cwb-chinese/SKILL.md`, `commands/cwb-chinese.md`
- Create: `codex_skills/cwb-sleep/SKILL.md`, `commands/cwb-sleep.md`

- [ ] **Step 1: Create cwb-chinese Codex skill**

```bash
mkdir -p codex_skills/cwb-chinese
```

Write `codex_skills/cwb-chinese/SKILL.md`:

```markdown
---
name: cwb-chinese
description: Play Chinese music including 国风, 古风, Mandarin pop, or folk. Activate when user mentions 国风, 中国风, 华语, 民谣, 古风, 国语, guzheng, erhu, 古琴, or Chinese traditional/folk music.
metadata:
  short-description: 国风、华语、古风音乐
---

# Chinese — 国风华语

## Trigger patterns
国风 / 中国风 / 华语 / 民谣 / 古风 / 国语 / guzheng / erhu / 古琴 / 中文歌

## Action — run immediately in parallel

```bash
cwb smart_search "中国风 古风 古琴 传统乐器" > /tmp/cwb_cn_1.txt 2>&1 &
cwb smart_search "华语流行 国语歌 indie 民谣" > /tmp/cwb_cn_2.txt 2>&1 &
cwb smart_search "chinese traditional folk guzheng erhu instrumental" > /tmp/cwb_cn_3.txt 2>&1 &
wait
```

## Display format

**🏮 古风国乐**
(results from angle 1)

**🎤 华语独立**
(results from angle 2)

**🪘 传统器乐**
(results from angle 3)

Renumber globally. End with: 喜欢哪首？说编号我来播。
Do NOT auto-play.
```

- [ ] **Step 2: Create cwb-chinese Claude Code command**

Write `commands/cwb-chinese.md`:

```markdown
---
description: Play Chinese music — 国风, 古风, 华语, 民谣. Triggers: 国风, 中国风, 华语, 民谣, 古风, 国语, guzheng, 古琴, erhu.
allowed-tools: Bash
argument-hint: ""
---

# Chinese — 国风华语

Run immediately:

```bash
cwb smart_search "中国风 古风 古琴 传统乐器" > /tmp/cwb_cn_1.txt 2>&1 &
cwb smart_search "华语流行 国语歌 indie 民谣" > /tmp/cwb_cn_2.txt 2>&1 &
cwb smart_search "chinese traditional folk guzheng erhu instrumental" > /tmp/cwb_cn_3.txt 2>&1 &
wait
cat /tmp/cwb_cn_1.txt
cat /tmp/cwb_cn_2.txt
cat /tmp/cwb_cn_3.txt
```

Group as **🏮 古风国乐** · **🎤 华语独立** · **🪘 传统器乐**. Renumber globally. End with: 喜欢哪首？说编号我来播。
```

- [ ] **Step 3: Create cwb-sleep Codex skill**

```bash
mkdir -p codex_skills/cwb-sleep
```

Write `codex_skills/cwb-sleep/SKILL.md`:

```markdown
---
name: cwb-sleep
description: Play sleep / insomnia / white noise music for falling asleep. Activate when user mentions 助眠, 睡前, 失眠, sleep, white noise, 白噪音, 入睡, or meditation for sleep.
metadata:
  short-description: Sleep, white noise & deep rest
---

# Sleep — 助眠入睡

## Trigger patterns
助眠 / 睡前 / 失眠 / sleep / white noise / 白噪音 / 入睡 / 冥想 / 放空

## Action — run immediately in parallel

```bash
cwb smart_search "sleep music white noise ambient drone" > /tmp/cwb_sleep_1.txt 2>&1 &
cwb smart_search "lullaby soft piano rain sleep calm" > /tmp/cwb_sleep_2.txt 2>&1 &
cwb smart_search "meditation deep sleep binaural delta waves" > /tmp/cwb_sleep_3.txt 2>&1 &
wait
```

## Display format

**🌙 Sleep Ambient**
(results from angle 1)

**💤 Lullaby**
(results from angle 2)

**🧘 Deep Sleep**
(results from angle 3)

Renumber globally. End with: 喜欢哪首？说编号我来播。
Do NOT auto-play.
```

- [ ] **Step 4: Create cwb-sleep Claude Code command**

Write `commands/cwb-sleep.md`:

```markdown
---
description: Play sleep / white noise / insomnia music. Triggers: 助眠, 睡前, 失眠, sleep, white noise, 白噪音, 入睡, meditation.
allowed-tools: Bash
argument-hint: ""
---

# Sleep — 助眠入睡

Run immediately:

```bash
cwb smart_search "sleep music white noise ambient drone" > /tmp/cwb_sleep_1.txt 2>&1 &
cwb smart_search "lullaby soft piano rain sleep calm" > /tmp/cwb_sleep_2.txt 2>&1 &
cwb smart_search "meditation deep sleep binaural delta waves" > /tmp/cwb_sleep_3.txt 2>&1 &
wait
cat /tmp/cwb_sleep_1.txt
cat /tmp/cwb_sleep_2.txt
cat /tmp/cwb_sleep_3.txt
```

Group as **🌙 Sleep Ambient** · **💤 Lullaby** · **🧘 Deep Sleep**. Renumber globally. End with: 喜欢哪首？说编号我来播。
```

- [ ] **Step 5: Verify files**

```bash
ls codex_skills/cwb-chinese/SKILL.md codex_skills/cwb-sleep/SKILL.md commands/cwb-chinese.md commands/cwb-sleep.md
```

Expected: all four paths printed.

- [ ] **Step 6: Commit**

```bash
git add codex_skills/cwb-chinese/ codex_skills/cwb-sleep/ commands/cwb-chinese.md commands/cwb-sleep.md
git commit -m "feat: add cwb-chinese and cwb-sleep scene skills"
```

---

## Task 7: Update commands/cwb.md routing

**File:** Modify `commands/cwb.md`

Replace the entire `## Multi-angle smart search` section (lines 44–54) with a scene dispatch table. The replacement leaves the routing rule line on line 40 intact — only the section content changes.

- [ ] **Step 1: Replace the multi-angle section**

In `commands/cwb.md`, find and replace:

Old text (exact):
```
## Multi-angle smart search

For mood/vibe/scene queries, generate 2–3 distinct keyword translations and run them **in parallel**:

```bash
cwb smart_search "<angle-1-keywords>"
cwb smart_search "<angle-2-keywords>"
cwb smart_search "<angle-3-keywords>"   # optional
```

Display all results **grouped by angle** with a short label per group (e.g. **🎷 Lofi Jazz**, **🌆 Synthwave**). Number tracks globally across groups so the user can say "play 5". End with: "喜欢哪首？说编号我来播。" Do **not** auto-play.
```

New text:
```
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
```

- [ ] **Step 2: Verify the section was replaced**

```bash
grep -n "Scene dispatch" commands/cwb.md
```

Expected: one line printed with the section heading.

```bash
grep -c "generate" commands/cwb.md
```

Expected: `0` (the old "generate keywords" instruction is gone).

- [ ] **Step 3: Commit**

```bash
git add commands/cwb.md
git commit -m "feat: replace cwb routing with scene dispatch table, remove runtime keyword generation"
```

---

## Task 8: Update codex_skills/cwb/SKILL.md routing

**File:** Modify `codex_skills/cwb/SKILL.md`

The Codex skill uses MCP tools instead of CLI commands. Add a scene dispatch section that lists `smart_search(query)` calls per scene.

- [ ] **Step 1: Add scene dispatch section**

In `codex_skills/cwb/SKILL.md`, append the following section after the `## Natural language examples` table (before `## CLI fallback`):

```markdown
## Scene dispatch — mood / vibe / scene requests

Do NOT generate keywords. For any request that isn't a specific song/artist/command, match to a scene and call `smart_search` three times in parallel with the pre-defined angles:

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

Call all three `smart_search(query)` for the matched scene, display results grouped by angle with emoji labels, number globally across groups (1, 2, 3…), end with: 喜欢哪首？说编号我来播。 Do NOT auto-play.
```

- [ ] **Step 2: Verify**

```bash
grep -n "Scene dispatch" codex_skills/cwb/SKILL.md
```

Expected: one line printed with the section heading.

- [ ] **Step 3: Commit**

```bash
git add codex_skills/cwb/SKILL.md
git commit -m "feat: add scene dispatch table to Codex cwb skill"
```

---

## Self-Review Checklist

- [x] All 11 scenes have both Codex (`codex_skills/cwb-*/SKILL.md`) and Claude Code (`commands/cwb-*.md`) files
- [x] Every file has complete content — no "TBD" or "similar to above"
- [x] `commands/cwb.md` routing table covers all 11 scenes with exact Bash commands
- [x] `codex_skills/cwb/SKILL.md` scene dispatch table covers all 11 scenes
- [x] All scene skill files share consistent structure: trigger patterns → parallel commands → grouped display
- [x] Every task ends with a git commit
- [x] No Python code changes required
