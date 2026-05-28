# HTML 听歌报告 v2 — 数据仪表盘设计文档

**日期:** 2026-05-27  
**状态:** 已审批  
**范围:** `profile.py` 新增数据字段 + `build_html_report()` 全面重写

---

## 目标

将现有的叙事滚动式报告升级为数据仪表盘，展示全部 8 个模块，采用"主次分明"布局（人格 + 每日图为主舞台，其余模块按重要性分组）。页面宽度从 720px 提升到 860px。

---

## 页面布局（从上到下）

```
┌─────────────────────────────────────────────┐
│  [Header]  人格 emoji + 名称 + 一句描述       │
│            居中显示，视觉重心                  │
├────────┬────────┬────────┬───────────────────┤
│ 总播放  │ 独立艺手│ 估算时长│    峰值时段        │  ← 数字摘要栏（4 格）
├─────────────────────────────────────────────┤
│  📅  每日播放柱状图（全宽）                    │
│  周报：Mon–Sun 7 柱；月报：按日历日期           │
├──────────────────────┬──────────────────────┤
│  🎤 Top 艺手（带钻取）│  🎵 Top 曲风（带钻取）  │  ← 两列
│  前三显示 🥇🥈🥉        │  前三显示 🥇🥈🥉        │
├──────────────────────┬──────────────────────┤
│  🕐 时段热力图        │  🔍 热搜词云           │  ← 两列
│  4 色块 深浅=活跃度   │  字号按频次缩放        │
├───────────┬──────────┬──────────────────────┤
│  🌐 语言  │  ♥ 收藏  │  📈 偏好趋势           │  ← 三列
│  donut图  │  艺手墙  │  ↑↓带百分比变化值      │
├─────────────────────────────────────────────┤
│  🎧 音乐人格（SVG 五边形雷达图 + 5 维度）      │  ← 全宽
├─────────────────────────────────────────────┤
│  💬 AI 总结（自然语言叙述）                    │
└─────────────────────────────────────────────┘
```

---

## 数据层变动：`build_profile()` 新增字段

| 新字段 | 类型 | 计算方式 | 用于 |
|--------|------|---------|------|
| `unique_artist_count` | `int` | `len(artist_counter)` | 摘要栏 |
| `estimated_hours` | `float` | `play_count * 3.5 / 60`，保留一位小数 | 摘要栏 |
| `peak_band` | `str` | `band_genres` 中总计数最多的时段 key | 摘要栏 |
| `daily_plays` | `dict[str, int]` | key 格式按 period 变化（见下） | 每日柱状图 |
| `personality_scores` | `dict[str, int]` | 见下方 `_personality_scores()` | 雷达图 |

**`daily_plays` key 格式：**
- `daily`：`"HH"`（小时字符串 00–23），展示当日 24 小时播放分布
- `weekly`：`"YYYY-MM-DD"`（7 个日期）
- `monthly`：`"YYYY-MM-DD"`（最多 30 个日期）
- `yearly`：`"YYYY-MM"`（12 个月份）

`daily_plays` 按 key 字典序排序后传入 HTML，`title` 属性显示具体数值，JS 渲染柱状图。

---

## 新 Helper：`_personality_scores(profile)`

返回 `dict[str, int]`，每个维度值域 0–100，由 `build_profile()` 调用后写入 profile。

| 维度 key | 中文名 | 算法 |
|----------|--------|------|
| `focus` | 专注力 | `instrumental_ratio * 60 + genre_concentration * 40`（`instrumental_ratio` = `language_pref["instrumental"]`；`genre_concentration` = `_genre_counter(period_tracks)` 前2曲风计数之和 / 所有曲风计数之和） |
| `explore` | 探索欲 | `min(100, unique_artist_count / max(play_count, 1) * 500)` |
| `mood` | 情绪起伏 | 曲风多样性：`min(100, len(top_genres) / 5 * 100)`（top_genres 越多越高） |
| `night_owl` | 夜猫指数 | `night_plays / max(total_plays, 1) * 100`，`night_plays` 来自 `band_genres["night"]` 总计数 |
| `loyalty` | 忠诚度 | `top3_artist_plays / max(play_count, 1) * 100`（前三艺手播放量之和占比） |

所有维度都用 `int(min(100, max(0, value)))` 箝位。

---

## HTML 报告重写：各模块规格

### 数字摘要栏（4 格）

```
总播放 | 独立艺手 | 估算时长 | 峰值时段
147    |   23    |  8.6h   |  🌙 深夜
```

- 4 等宽卡片，横排
- 峰值时段用 emoji + 中文：`{"morning":"🌅 早晨","afternoon":"☀️ 下午","evening":"🌆 傍晚","night":"🌙 深夜"}`

### 每日播放柱状图

- 全宽 SVG 柱状图，或 HTML `div` 模拟（与现有 bar chart 风格一致）
- 数据来自 `daily_plays`，自动按日期排序
- 周期为 `daily`：显示 24 小时分布；`weekly`：7 天；`monthly`：最近 30 天；`yearly`：12 个月聚合
- Hover（`title` 属性）显示具体数值
- 零播放日显示 1px 占位条，不隐藏

### Top 艺手 / Top 曲风

- 每列最多显示 5 条，前三加 🥇🥈🥉 emoji
- 保留现有的点击钻取 modal（`handleBarClick`）
- 条形图相对宽度与播放次数成比例

### 时段热力图

- 4 个色块横排：早晨 / 下午 / 傍晚 / 深夜
- 色块高度固定，透明度 = 该时段播放量 / 最高时段播放量
- 每个色块下方显示前 2 个曲风 tag（点击可钻取）

### 热搜词云

- 数据来自 `top_search_terms`（已在 `build_profile()` 计算）
- 最多 8 个词，字号范围 11px–18px，按频次线性缩放
- 颜色：按频次深浅使用紫色系（`rgba(139,92,246, 0.3~1.0)`）
- 全部无点击行为（只是展示）

### 语言偏好

- 保留现有的 donut SVG，但图例格式对齐其他卡片风格

### 收藏艺手墙

- 数据来自 `loved_artists`（已在 `build_profile()` 获取）
- 每个艺手显示名字 + 实际播放次数（从 `top_artists` 交叉查询）
- 若某收藏艺手本期播放为 0，显示"0 次"并以灰色表示

### 偏好趋势

- 保留 ↑ 新增 / → 稳定 / ↓ 下降 三栏
- 每个 genre 旁加变化幅度（如 `+34%`）：`abs(second - first) / max(first, 1) * 100`
- `first == 0` 的新增项显示 `NEW`

### 音乐人格雷达图

- 全宽卡片，内含 SVG 五边形雷达图（160×160）
- 纯 `math` 计算五顶点坐标，两层多边形（背景网格 + 数据填充）
- 5 个顶点标签：专注力 / 探索欲 / 情绪起伏 / 夜猫指数 / 忠诚度
- 填充色：`rgba(139,92,246,0.3)`，描边：`#8b5cf6`
- 人格 emoji + 标题 + 描述居右侧（与雷达图并排）

### AI 总结

- 保留现有 `summary` 逻辑，放在最底部
- 背景 `rgba(139,92,246,.08)`，微边框

---

## 交互保留

- 点击艺手/曲风条 → modal 弹出歌曲列表（现有 `handleBarClick` / `handlePillClick`）
- 保存为图片按钮（现有 `saveAsImage` + html2canvas）
- ESC 关闭 modal

---

## 文件变动清单

| 文件 | 变更 |
|------|------|
| `coding_with_beat/profile.py` | `build_profile()` 追加 6 个新字段；新增 `_personality_scores()`；`build_html_report()` 全面重写 |
| `tests/test_profile.py` | 新增针对 6 个新字段的单元测试；新增 `build_html_report()` 各模块测试 |

不新增文件，不改动 `__main__.py`（`--html` 入口不变）。

---

## 不在范围内

- 移动端响应式（现有报告已有基础，不做专项优化）
- 多语言国际化
- 历史对比（跨期对比），只展示当期数据
- 实时刷新
