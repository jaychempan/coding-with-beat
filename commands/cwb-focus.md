---
description: Play focus / flow-state instrumental music. Triggers: 专注, 心流, ambient, 无人声, flow state, deep work, concentration, no vocals.
allowed-tools: Bash
argument-hint: ""
---

# Focus — 深度工作 / 心流状态

Run immediately — no analysis needed:

```bash
cwb smart_search "deep focus ambient instrumental no vocals" > /tmp/cwb_focus_1.txt 2>&1 &
cwb smart_search "flow state drone minimal electronic" > /tmp/cwb_focus_2.txt 2>&1 &
cwb smart_search "study music concentration piano quiet" > /tmp/cwb_focus_3.txt 2>&1 &
wait
cat /tmp/cwb_focus_1.txt
cat /tmp/cwb_focus_2.txt
cat /tmp/cwb_focus_3.txt
```

Display results in three groups with labels, renumber globally (1, 2, 3… across all groups):

**🧠 Deep Focus Ambient**
(results from angle 1)

**⚡ Flow State**
(results from angle 2)

**📚 Study Piano**
(results from angle 3)

End with: 喜欢哪首？说编号我来播。

Do NOT auto-play.
