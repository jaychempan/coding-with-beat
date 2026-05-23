---
description: Play Chinese music — 国风, 古风, 华语, 民谣. Triggers: 国风, 中国风, 华语, 民谣, 古风, 国语, guzheng, 古琴, erhu.
allowed-tools: Bash
argument-hint: ""
---

# Chinese — 国风 / 华语 / 古风

Run immediately — no analysis needed:

```bash
cwb smart_search "中国风 古风 古琴 传统乐器" > /tmp/cwb_cn_1.txt 2>&1 &
cwb smart_search "华语流行 国语歌 indie 民谣" > /tmp/cwb_cn_2.txt 2>&1 &
cwb smart_search "chinese traditional folk guzheng erhu instrumental" > /tmp/cwb_cn_3.txt 2>&1 &
wait
cat /tmp/cwb_cn_1.txt
cat /tmp/cwb_cn_2.txt
cat /tmp/cwb_cn_3.txt
```

Display results in three groups with labels, renumber globally (1, 2, 3… across all groups):

**🏮 古风国乐**
(results from angle 1)

**🎤 华语独立**
(results from angle 2)

**🪘 传统器乐**
(results from angle 3)

End with: 喜欢哪首？说编号我来播。

Do NOT auto-play.
