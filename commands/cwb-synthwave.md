---
description: Play synthwave / cyberpunk / retro electronic music. Triggers: 赛博, synthwave, 电子, 夜驾, neon, retrowave, cyberpunk, 复古, outrun.
allowed-tools: Bash
argument-hint: ""
---

# Synthwave — 赛博 / 电子 / 夜驾

Run immediately — no analysis needed:

```bash
cwb smart_search "synthwave retrowave night drive neon" > /tmp/cwb_synth_1.txt 2>&1 &
cwb smart_search "cyberpunk electronic dark ambient synth" > /tmp/cwb_synth_2.txt 2>&1 &
cwb smart_search "80s retro synth outrun vapor" > /tmp/cwb_synth_3.txt 2>&1 &
wait
cat /tmp/cwb_synth_1.txt
cat /tmp/cwb_synth_2.txt
cat /tmp/cwb_synth_3.txt
```

Display results in three groups with labels, renumber globally (1, 2, 3… across all groups):

**🌆 Synthwave**
(results from angle 1)

**🤖 Cyberpunk**
(results from angle 2)

**📼 Retro Synth**
(results from angle 3)

End with: 喜欢哪首？说编号我来播。

Do NOT auto-play.
