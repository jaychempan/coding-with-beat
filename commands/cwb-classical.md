---
description: Play classical music — piano solos, strings, orchestral. Triggers: 古典, 钢琴, 弦乐, 交响, classical, piano, 巴赫, 莫扎特, orchestral.
allowed-tools: Bash
argument-hint: ""
---

# Classical — 古典 / 钢琴 / 交响

Run immediately — no analysis needed:

```bash
cwb smart_search "classical piano solo nocturne gentle" > /tmp/cwb_classical_1.txt 2>&1 &
cwb smart_search "string quartet orchestral cinematic calm" > /tmp/cwb_classical_2.txt 2>&1 &
cwb smart_search "bach mozart ambient classical study" > /tmp/cwb_classical_3.txt 2>&1 &
wait
cat /tmp/cwb_classical_1.txt
cat /tmp/cwb_classical_2.txt
cat /tmp/cwb_classical_3.txt
```

Display results in three groups with labels, renumber globally (1, 2, 3… across all groups):

**🎹 Piano Solo**
(results from angle 1)

**🎻 String Quartet**
(results from angle 2)

**🎼 Baroque & Classical**
(results from angle 3)

End with: 喜欢哪首？说编号我来播。

Do NOT auto-play.
