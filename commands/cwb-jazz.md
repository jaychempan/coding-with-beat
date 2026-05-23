---
description: Play jazz / bossa nova / café atmosphere music. Triggers: 爵士, jazz, 咖啡馆, smooth, bossa nova, 慵懒, café.
allowed-tools: Bash
argument-hint: ""
---

# Jazz — 爵士 / 咖啡馆

Run immediately — no analysis needed:

```bash
cwb smart_search "smooth jazz cafe background mellow" > /tmp/cwb_jazz_1.txt 2>&1 &
cwb smart_search "jazz trio acoustic bossa nova guitar" > /tmp/cwb_jazz_2.txt 2>&1 &
cwb smart_search "late night jazz piano bar cool relaxed" > /tmp/cwb_jazz_3.txt 2>&1 &
wait
cat /tmp/cwb_jazz_1.txt
cat /tmp/cwb_jazz_2.txt
cat /tmp/cwb_jazz_3.txt
```

Display results in three groups with labels, renumber globally (1, 2, 3… across all groups):

**☕ Smooth Jazz**
(results from angle 1)

**🎸 Bossa Nova**
(results from angle 2)

**🎹 Jazz Piano Bar**
(results from angle 3)

End with: 喜欢哪首？说编号我来播。

Do NOT auto-play.
