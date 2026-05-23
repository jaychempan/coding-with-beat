---
name: cwb-focus
description: Play focus / flow-state music with no vocals. Activate when user mentions 专注, 心流, ambient, 无人声, flow state, deep work, 摸鱼不分心, concentration, or needs distraction-free background music.
metadata:
  short-description: Focus & flow state music
---

# Focus — 深度工作 / 心流状态

## Trigger patterns
专注 / 心流 / ambient / 无人声 / flow state / deep work / 摸鱼不分心 / concentration / no vocals

## Action — run immediately in parallel

Run all three at once, collect output:

```bash
cwb smart_search "deep focus ambient instrumental no vocals" > /tmp/cwb_focus_1.txt 2>&1 &
cwb smart_search "flow state drone minimal electronic" > /tmp/cwb_focus_2.txt 2>&1 &
cwb smart_search "study music concentration piano quiet" > /tmp/cwb_focus_3.txt 2>&1 &
wait
```

## Display format

Show three groups. Renumber tracks globally (1, 2, 3… across all groups):

**🧠 Deep Focus Ambient**
(results from angle 1)

**⚡ Flow State**
(results from angle 2)

**📚 Study Piano**
(results from angle 3)

End with: 喜欢哪首？说编号我来播。
Do NOT auto-play.
