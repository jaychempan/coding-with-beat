<div align="center">
  <img src="assets/logo_icon.png" width="128" alt="Coding with Beat"/>
  <h1>Coding with Beat</h1>
  <p>将音乐搬进AI终端 · 打造Coding专属智能DJ · 听歌新范式 · 交互式音乐</p>
</div>

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-macOS-000000?style=flat-square&logo=apple&logoColor=white)
![Claude Code](https://img.shields.io/badge/Claude_Code-compatible-c85f41?style=flat-square)
![Codex CLI](https://img.shields.io/badge/Codex_CLI-compatible-10a37f?style=flat-square)
![MCP](https://img.shields.io/badge/MCP-28_tools-7c5cbf?style=flat-square)
![Apple Music](https://img.shields.io/badge/Apple_Music-supported-FC3C44?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
[![Website](https://img.shields.io/badge/website-codebeat.top-9bbc0f?style=flat-square)](https://codebeat.top)

> **你上一次 vibecoding 的时候又唱又跳是什么时候？**
>
> 对，你已经不记得了。

![](assets/welcome_log.png)

**编程伴奏，搬进 AI 终端。** 智能感知你的编码状态，自动切换音乐情绪，打造属于程序员的专属智能 DJ 与选歌平台 — 为 Claude Code & Codex CLI 而生。

一个支持 Claude Code / Codex CLI / 终端 的复古像素 DJ 小伙伴。它帮你放音乐、看歌词、在 commit 成功时庆祝，在测试挂掉时跟你一起崩溃。

[English](README.md) ／ [日本語](README_JP.md)

---

## 功能

- **MCP 服务器** — 暴露 28 个工具给你的 AI 助手，直接说"放点 lofi"、"跳过这首"、"现在在放什么"就能用。
- **音乐源** — Apple Music（AppleScript 驱动，不用开 GUI）、本地文件（afplay）、QQ 音乐（搜索 + 预览）。
- **像素 UI** — 专辑封面用半格 ANSI 字符渲染，支持 GameBoy 复古边框和伪频谱。
- **DJ Buddy** — 一个戴耳机的像素小人，会根据你的工作状态换表情。
- **Vibe 引擎** — 通过 Claude Code hooks 实时感知你在做什么，自动切换氛围。
- **状态栏** — 一行小脸 + 当前曲目 + 进度条 + 歌词。
- **专注模式** — 内置 25/5 番茄钟，显示在状态栏里。

---

## 安装

> [!NOTE]
> 想提前体验最新功能？前往 **[dev 分支](https://github.com/jaychempan/coding-with-beat/blob/dev/README_CN.md)** 查看最新进展。

### Claude Code

```bash
curl -LsSf https://raw.githubusercontent.com/jaychempan/coding-with-beat/main/bootstrap.sh | sh
```

手动安装：

```bash
git clone https://github.com/jaychempan/coding-with-beat.git
cd coding-with-beat
./install.sh
```

安装脚本会把 Claude Code 配成 HTTP MCP endpoint：`http://127.0.0.1:8765/mcp`，把 URL 写到 `~/.coding-with-beat/mcp-url`，并在 macOS 上安装/启动一个用户级 LaunchAgent。

开一个新 shell 和新的 Claude Code 会话，状态栏里出现 `(•_•)` 就好了。

### Codex CLI

```bash
curl -LsSf https://raw.githubusercontent.com/jaychempan/coding-with-beat/main/bootstrap_codex.sh | sh
```

手动安装：

```bash
git clone https://github.com/jaychempan/coding-with-beat.git
cd coding-with-beat
./install_codex.sh
```

没有 Codex CLI 会自动通过 npm 安装，并配置好 `~/.codex/config.toml`、hooks 和 `cwb` skill，让 Codex 直接识别音乐指令。代理自动检测。重复运行安全，已完成的步骤会自动跳过。

Codex 集成完整说明（hooks、代理、情绪通知、状态栏替代方案）见 **[README_CODEX.md](README_CODEX.md)**。

---

## 用法

> [!TIP]
> **不知道能说什么？** 直接问——`DJ 能做什么`——DJ Buddy 会列出所有可以对它说的话。
>
> **实时播放器：** 在另一个终端运行 `cwb watch`，实时查看正在播放的歌曲、歌词和进度条。
>
> **Apple Music：** 首次播放目录曲目会弹窗，点击**加入资料库**后再重复播放指令即可。

### 直接跟 AI 说

```
play some lofi
skip this track
what's playing
pause
基于我的历史推荐一些歌曲    # history_search — 分析你的收听习惯，推荐新歌
show my recently played tracks  # list_history — 读取 Apple Music 原生播放记录
```

`history_search` 会分析你最常听的歌手、收听风格以及很久没听的歌曲，然后做多角度智能搜索。选一个编号即可播放。

### `/cwb` 命令

```
/cwb play 周杰伦          # 搜索并播放
/cwb play lofi beats      # 播放 lofi
/cwb search 周杰伦        # 搜索资料库 + Apple Music，显示编号列表
/cwb play 2               # 播放搜索或列表结果中的第 2 首
/cwb list                 # 列出资料库所有歌曲
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
| `0-9` | 输入曲目编号 + `Enter` 直接跳转 |
| `q` | 退出 |

---

## 状态栏

安装后，AI CLI 底部会出现一行状态栏：

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

<details>
<summary>小彩蛋：把状态栏显示到别的地方</summary>

`cwb statusline` 就是 Claude Code 状态栏使用的同一个渲染器。它会从 stdin 读取可选 JSON，把 `columns` 当作宽度提示，然后向 stdout 输出一行紧凑状态栏。

```bash
printf '{"columns":120}' | cwb statusline
```

所以它也可以接到其他状态栏里。比如在 tmux 右侧状态栏显示 CWB：

#### tmux status-right

```tmux
set -g status-right-length 180
set -g status-interval 1
set -g status-right '#(printf "{\"columns\":170}" | cwb statusline | perl -pe "s/\e\[[0-9;]*m//g")'
```

`cwb statusline` 现在输出的是带 ANSI 颜色的终端文本。这里的 `perl` 用来去掉 ANSI escape code，因为 tmux 状态栏使用自己的样式语法。想让歌词显示更长，就调大 `columns` 和 `status-right-length`；想短一点就调小。

#### Neovim statusline

Neovim 也可以把 CWB 显示在 statusline 里。建议异步刷新，让编辑器绘制状态栏时只读取缓存文本，不等待外部命令：

```lua
local cwb = { text = "", running = false }

local function strip_ansi(text)
  return text:gsub("\27%[[0-9;]*m", "")
end

local function refresh()
  if cwb.running or vim.fn.executable("cwb") == 0 then
    return
  end
  cwb.running = true
  vim.system({ "cwb", "statusline" }, {
    text = true,
    stdin = vim.json.encode({ columns = 90 }),
  }, function(result)
    vim.schedule(function()
      cwb.running = false
      if result.code == 0 and result.stdout then
        cwb.text = vim.trim(strip_ansi(result.stdout)):gsub("%%", "%%%%")
        vim.cmd.redrawstatus()
      end
    end)
  end)
end

_G.cwb = cwb
vim.fn.timer_start(1000, refresh, { ["repeat"] = -1 })
refresh()
vim.o.statusline = "%f %m%r %= %{v:lua.cwb.text}"
```

</details>

---

## SSH 远端（服务器上的 Claude Code / Codex CLI）

如果你的 AI CLI 跑在服务器上，而 Apple Music 跑在本机 Mac，推荐把 streamable HTTP MCP server 跑在 Mac 上，再用 SSH 反向端口转发给服务器：

```bash
# 本机 Mac：安装并启动 HTTP MCP LaunchAgent
./install.sh          # Claude Code
./install_codex.sh    # Codex CLI

# 本机 Mac：把服务暴露到服务器的 127.0.0.1:8765
ssh -N -R 127.0.0.1:8765:127.0.0.1:8765 user@server

# 服务器：安装 hooks/statusline，并指向转发后的 endpoint
./install.sh --mcp-url http://127.0.0.1:8765/mcp          # Claude Code
./install_codex.sh --mcp-url http://127.0.0.1:8765/mcp    # Codex CLI
```

远端会话、`/cwb`、statusline、hooks 和 `cwb` 命令行都会使用同一个 HTTP MCP URL。只要 SSH 隧道还在，`cwb play`、`cwb np`、`cwb next`、`cwb player`、`cwb karaoke` 就会控制 Mac 上的音乐客户端。

---

## 命令行

```
cwb play [query]        # 搜索并播放，或继续播放
cwb play <n>            # 播放上次搜索或列表结果中的第 n 首
cwb search <query>      # 搜索资料库 + Apple Music 目录（带编号列表）
cwb list [n]            # 列出资料库所有歌曲（默认100首）
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
cwb statusline          # 渲染一行紧凑状态栏
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
# Claude Code
./uninstall.sh           # 移除配置、命令、PATH
./uninstall.sh --purge   # 同上 + 删除 ~/.coding-with-beat/

# Codex CLI
./uninstall_codex.sh           # 移除 Codex 配置、skill、LaunchAgent
./uninstall_codex.sh --purge   # 同上 + 删除 ~/.coding-with-beat/
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.
