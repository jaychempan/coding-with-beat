---
description: Play relaxing / evening wind-down music. Triggers: 放松, 解压, 下班, 傍晚, unwind, chill out, 休息, 轻松.
allowed-tools: Bash
argument-hint: ""
---

# Relax — 放松 / 解压 / 下班

Run immediately — no analysis needed:

```bash
cwb smart_search "relaxing downtempo chill evening unwind" > /tmp/cwb_relax_1.txt 2>&1 &
cwb smart_search "acoustic folk gentle calm soft" > /tmp/cwb_relax_2.txt 2>&1 &
cwb smart_search "nature ambient breeze afternoon easy listening" > /tmp/cwb_relax_3.txt 2>&1 &
wait
cat /tmp/cwb_relax_1.txt
cat /tmp/cwb_relax_2.txt
cat /tmp/cwb_relax_3.txt
```

Display results in three groups with labels, renumber globally (1, 2, 3… across all groups):

**🌅 Downtempo Chill**
(results from angle 1)

**🎸 Acoustic Folk**
(results from angle 2)

**🌿 Nature Ambient**
(results from angle 3)

End with: 喜欢哪首？说编号我来播。

Do NOT auto-play.
