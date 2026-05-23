# Smart Search Skills Architecture

**Date:** 2026-05-24  
**Status:** Approved

## Problem

The current multi-angle smart search is slow and inconsistent:

1. **LLM keyword generation at runtime** — Claude or Codex must "think up" keyword angles each time. This adds latency and produces varying quality.
2. **Subprocess overhead** — each `cwb smart_search` call is a subprocess; 3 parallel calls = 3 forks + Apple Music queries.
3. **Code re-exploration** — Claude Code sometimes re-reads project files before acting on music commands because the routing instruction is too open-ended.

## Solution: Router + Scene Skill files

Two-layer architecture:

```
User intent ("深夜写代码")
    │
    ▼
 cwb Router  (updated commands/cwb.md + codex_skills/cwb/SKILL.md)
    │  pattern-matches intent → scene name, no keyword generation
    ▼
 Scene Skill  (new commands/cwb-lofi.md + codex_skills/cwb-lofi/SKILL.md)
    │  pre-hardcoded angles, immediately runs parallel searches
    ▼
 Grouped results + global numbering → user picks by number
```

**Key principle:** Scene Skill files contain pre-written keyword angles. The system looks up, not thinks up.

## File Structure

22 new files (11 scenes × 2 environments):

```
codex_skills/
  cwb-lofi/SKILL.md
  cwb-focus/SKILL.md
  cwb-hype/SKILL.md
  cwb-jazz/SKILL.md
  cwb-synthwave/SKILL.md
  cwb-relax/SKILL.md
  cwb-classical/SKILL.md
  cwb-sad/SKILL.md
  cwb-party/SKILL.md
  cwb-chinese/SKILL.md
  cwb-sleep/SKILL.md

commands/
  cwb-lofi.md
  cwb-focus.md
  cwb-hype.md
  cwb-jazz.md
  cwb-synthwave.md
  cwb-relax.md
  cwb-classical.md
  cwb-sad.md
  cwb-party.md
  cwb-chinese.md
  cwb-sleep.md
```

Plus updates to existing:
- `codex_skills/cwb/SKILL.md` — routing table replaces "generate keywords" instruction
- `commands/cwb.md` — same routing table update

## Scene Skill File Format

### Codex CLI (`codex_skills/cwb-<scene>/SKILL.md`)

```markdown
---
name: cwb-<scene>
description: <one-line trigger description for auto-activation>
metadata:
  short-description: <scene label>
---

# <Scene Name>

## Trigger patterns
<Chinese and English keywords that indicate this scene>

## Action — run immediately in parallel

\`\`\`bash
cwb smart_search "<angle-1>" &
cwb smart_search "<angle-2>" &
cwb smart_search "<angle-3>" &
wait
\`\`\`

## Display
Group results by angle with emoji label. Number tracks globally (1, 2, 3…
across all groups). End with: 喜欢哪首？说编号我来播。
```

### Claude Code (`commands/cwb-<scene>.md`)

```markdown
---
description: <same trigger description>
disable-model-invocation: true
allowed-tools: Bash
argument-hint: ""
---

# <Scene Name>

Run immediately — no analysis needed:

\`\`\`bash
cwb smart_search "<angle-1>" &
cwb smart_search "<angle-2>" &
cwb smart_search "<angle-3>" &
wait
\`\`\`

Group by angle, number globally, end with: 喜欢哪首？说编号我来播。
```

## Scene Catalog

| Scene | Triggers (sample) | Angle 1 | Angle 2 | Angle 3 |
|---|---|---|---|---|
| `cwb-lofi` | 深夜/写代码/lofi/低保真/熬夜 | `lofi hip hop late night coding chill` | `lofi jazz rain study instrumental` | `chillhop beats lo-fi bedroom producer` |
| `cwb-focus` | 专注/心流/无人声/ambient/摸鱼不分心 | `deep focus ambient instrumental no vocals` | `flow state drone minimal electronic` | `study music concentration piano quiet` |
| `cwb-hype` | 充能/早晨/运动/高能/清醒/跑步 | `morning energy upbeat pop indie fresh` | `workout motivation electronic dance` | `hype rap trap energetic beats pump` |
| `cwb-jazz` | 爵士/jazz/咖啡馆/慵懒/smooth/慵懒 | `smooth jazz cafe background mellow` | `jazz trio acoustic bossa nova guitar` | `late night jazz piano bar cool relaxed` |
| `cwb-synthwave` | 赛博/电子/夜驾/synthwave/复古/neon | `synthwave retrowave night drive neon` | `cyberpunk electronic dark ambient synth` | `80s retro synth outrun vapor` |
| `cwb-relax` | 放松/解压/下班/傍晚/轻松/休息 | `relaxing downtempo chill evening unwind` | `acoustic folk gentle calm soft` | `nature ambient breeze afternoon easy` |
| `cwb-classical` | 古典/钢琴/弦乐/交响/管弦 | `classical piano solo nocturne gentle` | `string quartet orchestral cinematic calm` | `bach mozart ambient classical study` |
| `cwb-sad` | 伤感/失落/难过/情绪/哭泣/heartbreak | `melancholy emotional piano sad indie` | `heartbreak slow ballad rnb rainy` | `sorrowful strings cinematic emotional` |
| `cwb-party` | 派对/聚会/节日/热闹/蹦迪/狂欢 | `party dance pop upbeat celebratory` | `edm festival club electronic banger` | `latin pop reggaeton dance floor` |
| `cwb-chinese` | 国风/中国风/古风/华语/民谣/国语 | `中国风 古风 古琴 传统乐器` | `华语流行 国语歌 indie 民谣` | `chinese traditional folk guzheng erhu` |
| `cwb-sleep` | 助眠/睡前/失眠/白噪音/入睡 | `sleep music white noise ambient drone` | `lullaby soft piano rain sleep calm` | `meditation deep sleep binaural delta` |

## Router Update

In both `commands/cwb.md` and `codex_skills/cwb/SKILL.md`, replace:

> "For mood/vibe/scene queries, generate 2–3 distinct keyword translations..."

With:

> "Match intent to the scene dispatch table below. Do NOT generate keywords.
> Dispatch immediately to the matching scene skill."

Then add the scene dispatch table mapping trigger words → scene skill name.

The router handles only fixed-verb commands (play, pause, next, source, etc.) itself.
Everything else routes to a scene skill.

## Behavior Contract

Each scene skill file must:
1. Run all three `cwb smart_search` calls in parallel (background `&` + `wait`)
2. Label each group with an emoji + scene direction name
3. Number results globally across groups (1, 2, 3…)
4. End output with: `喜欢哪首？说编号我来播。`
5. Never auto-play a track

## Out of Scope

- Changes to `server.py` or `__main__.py` (the `smart_search` MCP tool stays as-is)
- New Python modules or data files
- Changes to the vibe/hook system
