---
description: Play lofi / late-night coding music. Triggers: lofi, 深夜, 写代码, 低保真, chillhop, late night coding, study beats.
allowed-tools: Bash
argument-hint: ""
---

# Lofi — 深夜写代码

Run immediately — no analysis needed:

```bash
cwb smart_search "lofi hip hop late night coding chill" > /tmp/cwb_lofi_1.txt 2>&1 &
cwb smart_search "lofi jazz rain study instrumental" > /tmp/cwb_lofi_2.txt 2>&1 &
cwb smart_search "chillhop beats lo-fi bedroom producer" > /tmp/cwb_lofi_3.txt 2>&1 &
wait
cat /tmp/cwb_lofi_1.txt
cat /tmp/cwb_lofi_2.txt
cat /tmp/cwb_lofi_3.txt
```

Display results in three groups with labels, renumber globally (1, 2, 3… across all groups):

**🎧 Lofi Hip Hop** · **🌧 Lofi Jazz Rain** · **🛏 Chillhop**

End with: 喜欢哪首？说编号我来播。
