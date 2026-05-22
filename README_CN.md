# Coding With Beat

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-macOS-000000?style=flat-square&logo=apple&logoColor=white)
![Claude Code](https://img.shields.io/badge/Claude_Code-compatible-c85f41?style=flat-square)
![MCP](https://img.shields.io/badge/MCP-21_tools-7c5cbf?style=flat-square)
![Apple Music](https://img.shields.io/badge/Apple_Music-supported-FC3C44?style=flat-square)
![Version](https://img.shields.io/badge/version-0.1.0-9bbc0f?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
[![Website](https://img.shields.io/badge/website-codebeat.top-9bbc0f?style=flat-square)](https://codebeat.top)

> **你上一次 vibecoding 的时候又唱又跳是什么时候？**
>
> 对，你已经不记得了。

![](assets/welcome_log.png)

一个住在 Claude Code 里的像素风 DJ 小伙伴。它帮你放音乐、看歌词、在 commit 成功时庆祝，在测试挂掉时跟你一起崩溃。

[English](README.md) ／ [日本語](README_JP.md)

---

## 功能

- **MCP 服务器** — 向 Claude Code 暴露 21 个工具，直接说"放点 lofi"、"跳过这首"、"现在在放什么"就能用。
- **音乐源** — Apple Music（AppleScript 驱动，不用开 GUI）、本地文件（afplay）、QQ 音乐（搜索 + 预览）。
- **像素 UI** — 专辑封面用半格 ANSI 字符渲染，支持 GameBoy 复古边框和伪频谱。
- **DJ Buddy** — 一个戴耳机的像素小人，会根据你的工作状态换表情。
- **Vibe 引擎** — 通过 Claude Code hooks 实时感知你在做什么，自动切换氛围。
- **状态栏** — 一行小脸 + 当前曲目 + 进度条 + 歌词。
- **专注模式** — 内置 25/5 番茄钟，显示在状态栏里。

---

## 安装

```bash
curl -LsSf https://raw.githubusercontent.com/jaychempan/coding-with-beat/main/bootstrap.sh | sh
```

手动安装：

```bash
git clone https://github.com/jaychempan/coding-with-beat.git
cd coding-with-beat
./install.sh
```

安装脚本会把 Claude Code 配成 HTTP MCP endpoint：`http://127.0.0.1:8765/mcp`，把 URL 写到 `~/.coding-with-beat/mcp-url`，并在 macOS 上安装/启动一个用户级 LaunchAgent。调试时也可以手动跑：

```bash
cwb server --host 127.0.0.1 --port 8765 --path /mcp
```

开一个新 shell 和新的 Claude Code 会话，状态栏里出现 `(•_•)` 就好了。

---

## 用法

### 直接跟 Claude 说

```
play some lofi
skip this track
what's playing
pause
```

### `/cwb` 命令

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

中文也可以：`下一首`、`暂停`、`在放什么`、`收藏` 都能识别。

### `watch` / `karaoke` 快捷键

| 按键 | 动作 |
|------|------|
| `Space` | 播放 / 暂停 |
| `n` | 下一首 |
| `p` | 上一首 |
| `l` | 收藏 |
| `q` | 退出 |

---

## 状态栏

安装后，Claude Code 底部会出现一行状态栏：

```
(•_•) ⚡  ▶ 雨爱 — 杨丞琳  ██████░░░░░░░░  [build]  ▃▆█▆▃  │ ♪ 不忍揭曉的劇情
```

| 元素 | 示例 | 说明 |
|------|------|------|
| DJ 表情 | `(•_•)` `(^_^)` `(T_T)` | 跟随 coding 状态变化 |
| 活跃度 | `⚡` / `·` / 空 | 最近工具调用热度 |
| 播放状态 | `▶` / `▷` / `❚❚` | 播放时闪烁，暂停时显示 ❚❚ |
| 曲目 | `雨爱 — 杨丞琳  ██████░░░░░░░░` | 歌名、歌手、进度条 |
| 氛围 | `[build]` `[focus]` 等 | 当前 coding vibe |
| 番茄钟 | `🍅 work 24:15` | 专注模式开启时显示 |
| Beat wave | `▁▂▃▄▅` | 随节拍起伏，暂停时变暗 |
| 歌词 | `│ ♪ lyrics here` | 当前 LRC 歌词行 |

---

## SSH 远端 Claude Code

如果 Claude Code 跑在服务器上，而 Apple Music 跑在本机 Mac，推荐把 streamable HTTP MCP server 跑在 Mac 上，再用 SSH 反向端口转发给服务器：

```bash
# 本机 Mac：安装并启动 HTTP MCP LaunchAgent
./install.sh

# 本机 Mac：把服务暴露到服务器的 127.0.0.1:8765
ssh -N -R 127.0.0.1:8765:127.0.0.1:8765 user@server

# 服务器：安装 hooks/statusline，并指向转发后的 endpoint
./install.sh --mcp-url http://127.0.0.1:8765/mcp
```

远端 Claude Code、`/cwb`、statusline、hooks 和 `cwb` 命令行都会使用同一个 HTTP MCP URL。只要 SSH 隧道还在，`cwb play`、`cwb np`、`cwb next`、`cwb player`、`cwb karaoke` 就会控制 Mac 上的音乐客户端。

---

## 命令行

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
cwb server              # MCP streamable HTTP 服务器
```

---

## 音源能力矩阵

| 功能 | Apple Music | 本地文件 | QQ 音乐 |
|------|-------------|----------|---------|
| 当前曲目 | ✓ | ✓ | ⚠ 预览 |
| 播放 / 暂停 | ✓ | ✓ | ✓ |
| 下一首 / 上一首 | ✓ | ✓ | ✓ |
| 跳转进度 | ✓ | ⚠ 重启播放实现 | ⚠ 预览 |
| 音量 | ✓ | ✓ | ⚠ 粗略调整 |
| 收藏 | ✓ | ✗ | ✓ |
| 封面 | ✓ | ✓ | ✓ |
| 完整播放 | ✓ 需要订阅 | ✓ | ✗ 30 秒预览 |
| 播放模式 | ✓ | ✗ | ✓ |

> QQ 音乐没有官方 API。搜索元数据来自公开 endpoint，音频通过 afplay 播放 30 秒预览。完整曲目需要 QQ 音乐桌面端。

---

## 卸载

```bash
./uninstall.sh           # 移除配置、命令、PATH
./uninstall.sh --purge   # 同上 + 删除 ~/.coding-with-beat/
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.
