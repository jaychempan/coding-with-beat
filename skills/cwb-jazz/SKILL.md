---
name: cwb-jazz
description: Play jazz, smooth jazz, or bossa nova music. Activate when user mentions 爵士, jazz, 咖啡馆, smooth, bossa nova, 慵懒, 下午, café music, or relaxed instrumental.
metadata:
  short-description: Jazz & café atmosphere
---

# Jazz — 爵士 / 咖啡馆

## Trigger patterns
爵士 / jazz / 咖啡馆 / smooth / bossa nova / 慵懒 / 下午茶 / café / swing

## Action — run immediately in parallel

Run all three at once, collect output:

```bash
cwb smart_search "smooth jazz cafe background mellow" > /tmp/cwb_jazz_1.txt 2>&1 &
cwb smart_search "jazz trio acoustic bossa nova guitar" > /tmp/cwb_jazz_2.txt 2>&1 &
cwb smart_search "late night jazz piano bar cool relaxed" > /tmp/cwb_jazz_3.txt 2>&1 &
wait
```

## Display format

Show three groups. Renumber tracks globally (1, 2, 3… across all groups):

**☕ Smooth Jazz**
(results from angle 1)

**🎸 Bossa Nova**
(results from angle 2)

**🎹 Jazz Piano Bar**
(results from angle 3)

End with: 喜欢哪首？说编号我来播。
Do NOT auto-play.
