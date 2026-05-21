# Coding With Beat

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-macOS-000000?style=flat-square&logo=apple&logoColor=white)
![Claude Code](https://img.shields.io/badge/Claude_Code-compatible-c85f41?style=flat-square)
![MCP](https://img.shields.io/badge/MCP-21_tools-7c5cbf?style=flat-square)
![Apple Music](https://img.shields.io/badge/Apple_Music-supported-FC3C44?style=flat-square)
![Version](https://img.shields.io/badge/version-0.1.0-9bbc0f?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)

Claude Code 的像素艺术音乐伴侣。无需离开终端即可听歌，享受响应式复古 UI，让小巧的 DJ Buddy 随你的编码节奏改变氛围。

[English README](README_EN.md)

```
                            ╭─────────────────╮
                            │ ╭─────────────╮ │
                            │ │  ╭───────╮  │ │
                            │ │  │   ◉   │  │ │
                            │ │  ╰───────╯  │ │
                            │ ╰─────────────╯ │
                            ╰─────────────────╯

               (♪‿♪)   a pixel companion for vibecoding   (♪‿♪)

                               C  O  D  I  N  G
 ██╗    ██╗██╗████████╗██╗  ██╗    ██████╗ ███████╗ █████╗ ████████╗
 ██║    ██║██║╚══██╔══╝██║  ██║    ██╔══██╗██╔════╝██╔══██╗╚══██╔══╝
 ██║ █╗ ██║██║   ██║   ███████║    ██████╔╝█████╗  ███████║   ██║
 ██║███╗██║██║   ██║   ██╔══██║    ██╔══██╗██╔══╝  ██╔══██║   ██║
 ╚███╔███╔╝██║   ██║   ██║  ██║    ██████╔╝███████╗██║  ██║   ██║
  ╚══╝╚══╝ ╚═╝   ╚═╝   ╚═╝  ╚═╝    ╚═════╝ ╚══════╝╚═╝  ╚═╝   ╚═╝

 ────────────────────────────────────────────────────────────────────────────
    ✓  MCP server registered                ✓  /cwb command installed
    ✓  CC hooks active                      ✓  statusline ready
 ────────────────────────────────────────────────────────────────────────────

    open Claude Code and say: "play some lofi"  ·  or /cwb play 周杰伦
```

---

## 功能介绍

- **MCP 服务器** — 向 Claude Code 暴露 21 个工具，直接说"放点 lofi"、"跳过这首"、"现在在放什么"就能用。
- **音乐来源** — Apple Music（AppleScript，无需打开 GUI）、本地文件（afplay）、QQ 音乐（搜索 + 试听）。
- **像素 UI** — 专辑封面半格 ANSI 渲染，GameBoy 复古边框，伪频谱均衡器。
- **DJ Buddy** — 戴耳机的像素小人，随你的编码状态换心情。测试挂了它也跟着慌。
- **氛围引擎** — 通过 CC hooks 实时感知你在干什么，自动切换氛围。`git commit` 了？胜利姿势。测试炸了？进入 panic 模式。
- **状态栏** — 一行：表情 + 当前曲目 + 进度条。
- **专注模式** — 内置 25/5 番茄钟，显示在状态栏里。

---

## 安装

```bash
curl -LsSf https://raw.githubusercontent.com/jaychempan/coding-with-beat/main/bootstrap.sh | sh
```

或者手动：

```bash
git clone https://github.com/jaychempan/coding-with-beat.git
cd coding-with-beat
./install.sh
```

打开新 shell 和新的 Claude Code 会话，状态栏出现 `(•_•)` 就好了。

---

## 用法

### 直接跟 Claude 说

装好之后，在 Claude Code 里直接用自然语言控制：

> 放点 lofi  
> 跳过这首  
> 现在在放什么  
> 暂停一下

### `/cwb` 命令

也可以用斜杠命令直接驱动，中英文都支持：

```
/cwb play 周杰伦          # 搜索并播放
/cwb play lofi beats      # 播放 lofi
/cwb next / 下一首
/cwb pause / 暂停
/cwb np                   # 当前播放
/cwb like / 收藏
/cwb volume 70            # 调音量
/cwb watch                # 实时播放器（q 退出）
/cwb karaoke              # 全屏卡拉 OK（q 退出）
/cwb lyrics               # 歌词窗口
/cwb bar auto             # 状态栏：auto / show / hide
```

### `watch` / `karaoke` 快捷键

| 按键 | 动作 |
|------|------|
| `Space` | 播放 / 暂停 |
| `n` | 下一首 |
| `p` | 上一首 |
| `l` | 收藏 |
| `q` | 退出 |

---

## 状态栏解读

装好之后，Claude Code 底部会出现一行状态栏，长这样：

```
(•_•) ⚡  ▶ 雨爱 — 杨丞琳  ██████░░░░░░░░  [build]  ▃▆█▆▃  │ ♪ 不忍揭曉的劇情
```

从左到右：

| 元素 | 示例 | 说明 |
|------|------|------|
| DJ 表情 | `(•_•)` `(^_^)` `(T_T)` | Buddy 当前心情，随编码事件变化 |
| 热度指示 | `⚡` / `·` / _(无)_ | `⚡` = 15 秒内有工具调用；`·` = 90 秒内；空 = 已冷却 |
| 播放图标 | `▶` / `▷` (每秒闪烁) / `❚❚` | 播放中闪烁；暂停显示 ❚❚ |
| 曲目 | `雨爱 — 杨丞琳  ██████░░░░░░░░` | 曲名 + 艺术家 + 进度条 |
| Vibe | `[build]` `[focus]` 等 | 当前编码氛围 |
| 番茄钟 | `🍅 work 24:15` | 仅专注模式激活时出现 |
| 律动波纹 | `▁▂▃▄▅` | 随节拍涨落；暂停时变暗 |
| 歌词 | `│ ♪ 不忍揭曉的劇情` | 当前 LRC 歌词 |

---

## 命令行工具

```
cwb play [query]        # 搜索并播放，或继续播放
cwb pause               # 暂停
cwb next                # 下一首
cwb prev                # 上一首
cwb np                  # 当前播放
cwb like                # 收藏当前曲目
cwb volume <0-100>      # 调整音量
cwb seek <t>            # 跳转进度：秒数（90）或 mm:ss（1:30）
cwb mode <mode>         # 播放模式：shuffle | sequential | repeat | repeat_one
cwb player              # 完整像素播放器
cwb watch               # 实时 TUI（q 退出）
cwb karaoke             # 全屏卡拉 OK（q 退出）
cwb lyrics              # 歌词窗口
cwb history [n]         # 最近播放的 n 首歌
cwb bar <show|hide|auto> # 状态栏显示模式
cwb status              # 当前状态
```

---

## 音源能力矩阵

| 能力 | Apple Music | 本地文件 | QQ 音乐 |
|------|-------------|----------|---------|
| 当前播放信息 | ✓ | ✓ | ⚠ 仅预览时 |
| 播放 / 暂停 | ✓ | ✓ | ✓ |
| 上一首 / 下一首 | ✓ | ✓ | ✓ |
| 进度跳转 | ✓ | ⚠ 重启定位 | ⚠ 仅预览时 |
| 音量控制 | ✓ | ✓ | ⚠ 粗略步进 |
| 收藏 | ✓ | ✗ | ✓ |
| 封面 | ✓ | ✓ | ✓ |
| 完整播放 | ✓ 需订阅 | ✓ | ✗ 仅 30s 试听 |
| 播放模式 | ✓ | ✗ | ✓ |

> QQ 音乐无官方 API，通过公开搜索端点获取元数据 + afplay 播放预览片段；完整曲目需打开 QQ 音乐客户端。

---

## 卸载

```bash
./uninstall.sh           # 移除配置、命令、PATH
./uninstall.sh --purge   # 同上 + 删除 ~/.coding-with-beat/
```
