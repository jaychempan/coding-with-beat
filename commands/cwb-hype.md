---
description: Play high-energy / workout / morning motivation music. Triggers: 充能, 运动, 高能, 早晨, workout, hype, motivation, 跑步, 起床.
allowed-tools: Bash
argument-hint: ""
---

# Hype — 充能 / 运动 / 高能

Run immediately — no analysis needed:

```bash
cwb smart_search "morning energy upbeat pop indie fresh" > /tmp/cwb_hype_1.txt 2>&1 &
cwb smart_search "workout motivation electronic dance" > /tmp/cwb_hype_2.txt 2>&1 &
cwb smart_search "hype rap trap energetic beats pump" > /tmp/cwb_hype_3.txt 2>&1 &
wait
cat /tmp/cwb_hype_1.txt
cat /tmp/cwb_hype_2.txt
cat /tmp/cwb_hype_3.txt
```

Display results in three groups with labels, renumber globally (1, 2, 3… across all groups):

**☀️ Morning Energy**
(results from angle 1)

**💪 Workout**
(results from angle 2)

**🔥 Hype Beats**
(results from angle 3)

End with: 喜欢哪首？说编号我来播。
