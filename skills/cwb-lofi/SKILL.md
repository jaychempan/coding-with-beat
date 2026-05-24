---
name: cwb-lofi
description: Play lofi / chill background music. Activate when the user mentions lofi, 深夜, 写代码, 低保真, chillhop, 熬夜, late night coding, or asks for background beats for coding or studying.
metadata:
  short-description: Lofi & chill for coding
---

# Lofi — 深夜写代码

## Trigger patterns
深夜 / 写代码 / lofi / 低保真 / chillhop / 熬夜 / late night / coding music / study beats

## Action — run immediately in parallel

Run all three at once, collect output:

```bash
cwb smart_search "lofi hip hop late night coding chill" > /tmp/cwb_lofi_1.txt 2>&1 &
cwb smart_search "lofi jazz rain study instrumental" > /tmp/cwb_lofi_2.txt 2>&1 &
cwb smart_search "chillhop beats lo-fi bedroom producer" > /tmp/cwb_lofi_3.txt 2>&1 &
wait
```

## Display format

Show three groups. Renumber tracks globally (1, 2, 3… across all groups):

**🎧 Lofi Hip Hop**
(results from angle 1)

**🌧 Lofi Jazz Rain**
(results from angle 2)

**🛏 Chillhop**
(results from angle 3)

End with: 喜欢哪首？说编号我来播。
Do NOT auto-play.
