---
name: cwb-hype
description: Play energetic / high-energy music for workouts, morning wake-up, or motivation. Activate when user mentions 充能, 运动, 高能, 早晨, workout, 跑步, 起床, hype, motivation, or wants music to get pumped up.
metadata:
  short-description: High energy & workout music
---

# Hype — 充能 / 运动 / 高能

## Trigger patterns
充能 / 运动 / 高能 / 早晨 / workout / 跑步 / 起床 / hype / motivation / pump up

## Action — run immediately in parallel

Run all three at once, collect output:

```bash
cwb smart_search "morning energy upbeat pop indie fresh" > /tmp/cwb_hype_1.txt 2>&1 &
cwb smart_search "workout motivation electronic dance" > /tmp/cwb_hype_2.txt 2>&1 &
cwb smart_search "hype rap trap energetic beats pump" > /tmp/cwb_hype_3.txt 2>&1 &
wait
```

## Display format

Show three groups. Renumber tracks globally (1, 2, 3… across all groups):

**☀️ Morning Energy**
(results from angle 1)

**💪 Workout**
(results from angle 2)

**🔥 Hype Beats**
(results from angle 3)

End with: 喜欢哪首？说编号我来播。
Do NOT auto-play.
