---
name: cwb-profile
description: Music profile analysis and listening reports. Activate when user asks for listening history analysis, music profile, periodic report (daily/weekly/monthly/yearly), or personalized recommendations based on history.
metadata:
  short-description: Personal music profile, listening reports, and history-based recommendations
---

# coding-with-beat — Music Profile & Listening Report

You have access to the `generate_profile` MCP tool. Use it to analyse the user's listening history and generate personalised reports and recommendations.

## When to activate

- 听歌报告 · 音乐画像 · 本周报告 · 本月报告 · 年度报告 · 日报告
- music profile · listening report · music report · my music taste
- 分析我的听歌 · 我最近在听什么 · 推荐基于历史
- history profile · what have I been listening to
- 给我推荐基于历史 · 根据我的喜好推荐

## Dispatch logic

1. **Detect period** from the user's message:
   - 今天 / 日 / today / daily → `"daily"`
   - 本周 / 这周 / week / weekly → `"weekly"` (default)
   - 本月 / 这个月 / month / monthly → `"monthly"`
   - 今年 / 年度 / year / yearly → `"yearly"`
   - No mention → default `"weekly"`

2. **Extract context** (optional scene/mood words the user mentions):
   - 写代码 / coding / 跑步 / 放松 / 通勤 etc. → pass as `context`
   - If no scene mentioned → `context = ""`

3. **Call the tool:**
   ```
   generate_profile(period=<detected>, context=<extracted>)
   ```

4. **Display** the returned report in full.

5. **After the report**, present the recommendation queries and ask:
   > "要播放推荐吗？说"播放推荐1"或直接告诉我你想听哪个方向。"

6. **If user agrees to play:**
   - Extract the query strings from the report's recommendation section
   - Call `smart_search(queries=[<those queries>])`
   - Show results and let user pick by number with `play_number(n)`

## Example exchanges

**User:** 帮我生成本周的听歌报告
→ `generate_profile(period="weekly", context="")`

**User:** 我最近都在听什么，帮我分析一下，适合写代码的
→ `generate_profile(period="weekly", context="写代码")`

**User:** 给我出一份年度音乐画像
→ `generate_profile(period="yearly", context="")`

**User:** 今天听了什么
→ `generate_profile(period="daily", context="")`

## Error handling

If the tool returns "不足 5 首", tell the user:
> "还没有足够的听歌记录来生成画像，先多听几首再来吧 🎵"
Do not retry automatically.
