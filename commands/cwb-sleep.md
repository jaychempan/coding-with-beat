---
description: Play sleep / white noise / insomnia music. Triggers: 助眠, 睡前, 失眠, sleep, white noise, 白噪音, 入睡, meditation.
allowed-tools: Bash
argument-hint: ""
---

# Sleep — 助眠 / 睡眠 / 白噪音

Run immediately — no analysis needed:

```bash
cwb smart_search "sleep music white noise ambient drone" > /tmp/cwb_sleep_1.txt 2>&1 &
cwb smart_search "lullaby soft piano rain sleep calm" > /tmp/cwb_sleep_2.txt 2>&1 &
cwb smart_search "meditation deep sleep binaural delta waves" > /tmp/cwb_sleep_3.txt 2>&1 &
wait
cat /tmp/cwb_sleep_1.txt
cat /tmp/cwb_sleep_2.txt
cat /tmp/cwb_sleep_3.txt
```

Display results in three groups with labels, renumber globally (1, 2, 3… across all groups):

**🌙 Sleep Ambient**
(results from angle 1)

**💤 Lullaby**
(results from angle 2)

**🧘 Deep Sleep**
(results from angle 3)

End with: 喜欢哪首？说编号我来播。

Do NOT auto-play.
