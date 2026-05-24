---
name: cwb-chinese
description: Play Chinese music including 国风, 古风, Mandarin pop, or folk. Activate when user mentions 国风, 中国风, 华语, 民谣, 古风, 国语, guzheng, erhu, 古琴, or Chinese traditional/folk music.
metadata:
  short-description: 国风、华语、古风音乐
---

# Chinese — 国风 / 华语 / 古风

## Trigger patterns
国风 / 中国风 / 华语 / 民谣 / 古风 / 国语 / guzheng / erhu / 古琴 / 中文歌

## Action — run immediately in parallel

Run all three at once, collect output:

```bash
cwb smart_search "中国风 古风 古琴 传统乐器" > /tmp/cwb_cn_1.txt 2>&1 &
cwb smart_search "华语流行 国语歌 indie 民谣" > /tmp/cwb_cn_2.txt 2>&1 &
cwb smart_search "chinese traditional folk guzheng erhu instrumental" > /tmp/cwb_cn_3.txt 2>&1 &
wait
```

## Display format

Show three groups. Renumber tracks globally (1, 2, 3… across all groups):

**🏮 古风国乐**
(results from angle 1)

**🎤 华语独立**
(results from angle 2)

**🪘 传统器乐**
(results from angle 3)

End with: 喜欢哪首？说编号我来播。
Do NOT auto-play.
