---
description: Play party / dance / EDM music. Triggers: 派对, 聚会, 节日, party, dance, 蹦迪, edm, 狂欢, celebrate.
allowed-tools: Bash
argument-hint: ""
---

# Party — 派对 / 聚会 / 舞蹈

Run immediately — no analysis needed:

```bash
cwb smart_search "party dance pop upbeat celebratory" > /tmp/cwb_party_1.txt 2>&1 &
cwb smart_search "edm festival club electronic banger" > /tmp/cwb_party_2.txt 2>&1 &
cwb smart_search "latin pop reggaeton dance floor" > /tmp/cwb_party_3.txt 2>&1 &
wait
cat /tmp/cwb_party_1.txt
cat /tmp/cwb_party_2.txt
cat /tmp/cwb_party_3.txt
```

Display results in three groups with labels, renumber globally (1, 2, 3… across all groups):

**🎉 Dance Pop**
(results from angle 1)

**🎛 EDM Festival**
(results from angle 2)

**💃 Latin Dance**
(results from angle 3)

End with: 喜欢哪首？说编号我来播。

Do NOT auto-play.
