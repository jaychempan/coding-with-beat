---
name: cwb-sad
description: Play melancholy / emotional / heartbreak music. Activate when user mentions 伤感, 失落, 难过, melancholy, heartbreak, sad, 情绪, 哭泣, 失恋, emotional, or wants music to match a low mood.
metadata:
  short-description: Melancholy & emotional music
---

# Sad — 伤感 / 失落 / 情绪

## Trigger patterns
伤感 / 失落 / 难过 / melancholy / heartbreak / sad / 情绪 / 哭泣 / 失恋 / emotional

## Action — run immediately in parallel

Run all three at once, collect output:

```bash
cwb smart_search "melancholy emotional piano sad indie" > /tmp/cwb_sad_1.txt 2>&1 &
cwb smart_search "heartbreak slow ballad rnb rainy" > /tmp/cwb_sad_2.txt 2>&1 &
cwb smart_search "sorrowful strings cinematic emotional" > /tmp/cwb_sad_3.txt 2>&1 &
wait
```

## Display format

Show three groups. Renumber tracks globally (1, 2, 3… across all groups):

**💙 Melancholy**
(results from angle 1)

**🌧 Heartbreak Ballad**
(results from angle 2)

**🎻 Sorrowful Strings**
(results from angle 3)

End with: 喜欢哪首？说编号我来播。
Do NOT auto-play.
