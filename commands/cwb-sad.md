---
description: Play melancholy / emotional / heartbreak music. Triggers: 伤感, 失落, 难过, melancholy, heartbreak, sad, 情绪, 失恋, emotional.
allowed-tools: Bash
argument-hint: ""
---

# Sad — 伤感 / 失落 / 情绪

Run immediately — no analysis needed:

```bash
cwb smart_search "melancholy emotional piano sad indie" > /tmp/cwb_sad_1.txt 2>&1 &
cwb smart_search "heartbreak slow ballad rnb rainy" > /tmp/cwb_sad_2.txt 2>&1 &
cwb smart_search "sorrowful strings cinematic emotional" > /tmp/cwb_sad_3.txt 2>&1 &
wait
cat /tmp/cwb_sad_1.txt
cat /tmp/cwb_sad_2.txt
cat /tmp/cwb_sad_3.txt
```

Display results in three groups with labels, renumber globally (1, 2, 3… across all groups):

**💙 Melancholy**
(results from angle 1)

**🌧 Heartbreak Ballad**
(results from angle 2)

**🎻 Sorrowful Strings**
(results from angle 3)

End with: 喜欢哪首？说编号我来播。

Do NOT auto-play.
