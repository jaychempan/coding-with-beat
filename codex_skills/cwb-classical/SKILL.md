---
name: cwb-classical
description: Play classical music including piano, strings, and orchestral pieces. Activate when user mentions 古典, 钢琴, 弦乐, 交响, classical, piano, 管弦乐, 巴赫, 莫扎特, or orchestral music.
metadata:
  short-description: Classical, piano & orchestral
---

# Classical — 古典 / 钢琴 / 交响

## Trigger patterns
古典 / 钢琴 / 弦乐 / 交响 / classical / piano / 管弦乐 / 巴赫 / 莫扎特 / 肖邦

## Action — run immediately in parallel

Run all three at once, collect output:

```bash
cwb smart_search "classical piano solo nocturne gentle" > /tmp/cwb_classical_1.txt 2>&1 &
cwb smart_search "string quartet orchestral cinematic calm" > /tmp/cwb_classical_2.txt 2>&1 &
cwb smart_search "bach mozart ambient classical study" > /tmp/cwb_classical_3.txt 2>&1 &
wait
```

## Display format

Show three groups. Renumber tracks globally (1, 2, 3… across all groups):

**🎹 Piano Solo**
(results from angle 1)

**🎻 String Quartet**
(results from angle 2)

**🎼 Baroque & Classical**
(results from angle 3)

End with: 喜欢哪首？说编号我来播。
Do NOT auto-play.
