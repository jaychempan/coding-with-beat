---
name: cwb-synthwave
description: Play synthwave, cyberpunk, or retro electronic music. Activate when user mentions 赛博, synthwave, 电子, 夜驾, neon, retrowave, 复古, cyberpunk, outrun, or 80s synth vibes.
metadata:
  short-description: Synthwave & cyberpunk electronic
---

# Synthwave — 赛博 / 电子 / 夜驾

## Trigger patterns
赛博 / synthwave / 电子 / 夜驾 / neon / retrowave / 复古 / cyberpunk / outrun / 80s synth

## Action — run immediately in parallel

Run all three at once, collect output:

```bash
cwb smart_search "synthwave retrowave night drive neon" > /tmp/cwb_synth_1.txt 2>&1 &
cwb smart_search "cyberpunk electronic dark ambient synth" > /tmp/cwb_synth_2.txt 2>&1 &
cwb smart_search "80s retro synth outrun vapor" > /tmp/cwb_synth_3.txt 2>&1 &
wait
```

## Display format

Show three groups. Renumber tracks globally (1, 2, 3… across all groups):

**🌆 Synthwave**
(results from angle 1)

**🤖 Cyberpunk**
(results from angle 2)

**📼 Retro Synth**
(results from angle 3)

End with: 喜欢哪首？说编号我来播。
Do NOT auto-play.
