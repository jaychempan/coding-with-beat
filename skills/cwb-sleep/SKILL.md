---
name: cwb-sleep
description: Play sleep / insomnia / white noise music for falling asleep. Activate when user mentions 助眠, 睡前, 失眠, sleep, white noise, 白噪音, 入睡, or meditation for sleep.
metadata:
  short-description: Sleep, white noise & deep rest
---

# Sleep — 助眠 / 睡眠 / 白噪音

## Trigger patterns
助眠 / 睡前 / 失眠 / sleep / white noise / 白噪音 / 入睡 / 冥想 / 放空

## Action — run immediately in parallel

Run all three at once, collect output:

```bash
cwb smart_search "sleep music white noise ambient drone" > /tmp/cwb_sleep_1.txt 2>&1 &
cwb smart_search "lullaby soft piano rain sleep calm" > /tmp/cwb_sleep_2.txt 2>&1 &
cwb smart_search "meditation deep sleep binaural delta waves" > /tmp/cwb_sleep_3.txt 2>&1 &
wait
```

## Display format

Show three groups. Renumber tracks globally (1, 2, 3… across all groups):

**🌙 Sleep Ambient**
(results from angle 1)

**💤 Lullaby**
(results from angle 2)

**🧘 Deep Sleep**
(results from angle 3)

End with: 喜欢哪首？说编号我来播。
Do NOT auto-play.
