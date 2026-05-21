# CC-Jukebox

Claude Code 的像素艺术音乐伴侣。无需离开终端即可听歌，享受响应式复古 UI，让小巧的 DJ Buddy 随你的编码节奏改变氛围。

```
 ██████╗ ██████╗     ██╗██╗   ██╗██╗  ██╗███████╗██████╗  ██████╗ ██╗  ██╗
██╔════╝██╔════╝     ██║██║   ██║██║ ██╔╝██╔════╝██╔══██╗██╔═══██╗╚██╗██╔╝
██║     ██║          ██║██║   ██║█████╔╝ █████╗  ██████╔╝██║   ██║ ╚███╔╝
██║     ██║     ██   ██║██║   ██║██╔═██╗ ██╔══╝  ██╔══██╗██║   ██║ ██╔██╗
╚██████╗╚██████╗╚█████╔╝╚██████╔╝██║  ██╗███████╗██████╔╝╚██████╔╝██╔╝ ██╗
 ╚═════╝ ╚═════╝ ╚════╝  ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═════╝  ╚═════╝ ╚═╝  ╚═╝
                   a pixel companion for vibecoding
```

## 功能介绍

- **MCP 服务器** — 向 Claude Code 暴露 20+ 个工具，让你可以直接说"播放 lofi"、"跳过这首"、"显示播放器"、"正在播放什么？"等自然语言指令。
- **音乐来源** — Apple Music（通过 AppleScript，无需 GUI）、本地文件（afplay）、QQ音乐（通过公开 API 搜索 + 试听）。
- **像素 UI** — 专辑封面以半块 ANSI 字符渲染，GameBoy 4 色调模式，复古边框，响应式（基于播放位置确定性生成）频谱。
- **DJ Buddy** — 一个 5 行像素角色，随你的工作状态改变心情。
- **氛围引擎** — CC 钩子（PreToolUse/PostToolUse/SessionStart/Stop）监听你的活动并实时更新心情/氛围。测试失败 → Buddy 惊慌。提交成功 → 跳胜利舞。
- **状态栏** — 紧凑的单行显示：表情 + 当前曲目 + 进度条。
- **专注循环** — 25/5 番茄钟，显示在状态栏中。
- **一键安装** — `bootstrap.sh` / `install.sh` 全局配置一切（venv、PATH、斜杠命令、MCP 服务器、钩子）。无需系统 Python — 如果机器没有 Python ≥3.10，会自动使用 [uv](https://docs.astral.sh/uv/) 下载一个。

## 安装

### 一行命令安装（推荐）

```bash
curl -LsSf https://raw.githubusercontent.com/jaychempan/cc-jukebox/main/bootstrap.sh | sh
```

这会将 cc-jukebox 克隆到 `~/.cc-jukebox/src`，然后运行 `install.sh`。随时重新运行即可更新。

### 手动安装

```bash
git clone https://github.com/jaychempan/cc-jukebox.git
cd cc-jukebox
./install.sh
```

安装脚本默认把 Claude Code 配成 HTTP MCP，并在 macOS 上安装/启动一个 LaunchAgent：

```bash
./install.sh
```

MCP 地址是 `http://127.0.0.1:8765/mcp`。调试时也可以手动跑：

```bash
cc-jukebox server --host 127.0.0.1 --port 8765 --path /mcp
```

### install.sh 做了什么

1. **Python** — 在 PATH、`/opt/homebrew/bin`、`/usr/local/bin` 或 `~/miniconda3/envs` 等路径下查找 Python ≥3.10。如果都不存在，**自动安装 uv 并用它下载 Python 3.12**（不污染系统，安装在 `~/.local/` 下）。可通过 `CC_JUKEBOX_PYTHON=/path/to/python ./install.sh` 覆盖。
2. **venv** — 创建于 `~/.cc-jukebox/venv`（不在仓库目录中，所以移动/删除源码不影响安装）。
3. **`cc-jukebox` CLI** — 符号链接到 `~/.local/bin/`，并（幂等地）向 `~/.zshrc`（和 `~/.bashrc`）追加带标记的 `export PATH=…` 块，使命令在任何新 shell 中可用。
4. **`/juke` 斜杠命令** — 从 `commands/juke.md` 符号链接到 `~/.claude/commands/` — 仓库是真实来源，所以 `git pull` 即可更新命令，无需重新运行安装脚本。
5. **Claude Code 设置** — 合并条目到 `~/.claude/settings.json`：
   - `mcpServers["cc-jukebox"]`
   - `statusLine`（仅当你没有配置时才添加）
   - `PreToolUse`、`PostToolUse`、`SessionStart`、`Stop` 钩子
   - `/juke` 的 `UserPromptExpansion` 钩子，用一次性 headless Claude 子会话理解音乐指令，避免污染主上下文
6. **状态目录** `~/.cc-jukebox/` 用于运行时 JSON。

每个条目都标记 `_owner: "cc-jukebox"`，以便 `./uninstall.sh` 只删除我们添加的内容。

启动一个新 shell（让 PATH 生效）和一个新的 Claude Code 会话。你应该能在状态栏看到 `(•_•)` 表情。试着说：

> 显示播放器

……Claude 会调用 `show_player`，在终端内绘制像素边框。或者输入 `/juke play 周杰伦` 直接驱动。

## 项目级配置

在任何项目目录下：

```bash
cc-jukebox init
```

……会写入 `.cc-jukebox.toml`，让不同项目可以默认不同的氛围/来源/起始查询。

## SSH 远端 Claude Code

如果 Claude Code 在服务器上运行，而 Apple Music 在本机 Mac 上运行，MCP 工具推荐使用 streamable HTTP：MCP 服务器直接跑在本机 Mac 上，服务器上的 Claude Code 通过 SSH 反向端口转发访问它。

MCP-over-HTTP 模式：

```bash
# 本机 Mac：安装会启动 HTTP MCP LaunchAgent
./install.sh

# 本机 Mac：另一个终端，暴露到服务器的 127.0.0.1:8765
ssh -N -R 127.0.0.1:8765:127.0.0.1:8765 user@server

# 服务器：安装远端 hooks/statusline，并把 MCP 配成 HTTP URL
./install.sh --mcp-url http://127.0.0.1:8765/mcp
```

之后服务器上的 Claude Code 会通过 HTTP MCP 直接调用本机 Mac 的 cc-jukebox tools。远端的 `cc-jukebox np/play/pause/next/prev/like/mode/source/status/cover/lyrics/player/banner` 也会走同一个 MCP URL，所以只要 SSH 反向端口还在，它们就像本地命令一样控制 Mac 上的音乐客户端。

statusline、hooks、`/juke` 和命令行都会使用同一个 HTTP MCP endpoint。`./install.sh --mcp-url ...` 会把这个 URL 同时写入 Claude Code 设置和 `~/.cc-jukebox/mcp-url`，供命令行使用。

## 命令行工具

安装后，`cc-jukebox` 命令已在 PATH 中。

```
cc-jukebox status              # 当前状态
cc-jukebox np                  # 单行：标题 — 艺术家
cc-jukebox play [query]        # 恢复播放，或搜索并播放（见下文）
cc-jukebox pause               # 暂停
cc-jukebox next                # 下一首
cc-jukebox prev                # 上一首
cc-jukebox player              # 完整像素播放器边框
cc-jukebox watch               # 滚动 TUI（Ctrl-C 退出）
cc-jukebox cover [rgb|gameboy] # 仅显示当前封面
cc-jukebox lyrics              # 卡拉OK窗口
cc-jukebox karaoke             # 全屏歌词窗口
cc-jukebox demo                # 视觉冒烟测试
cc-jukebox banner              # 大型横幅
cc-jukebox init                # 写入 .cc-jukebox.toml
cc-jukebox server              # MCP streamable HTTP 服务器
cc-jukebox statusline          # 单帧状态栏（CC 调用）
cc-jukebox hook                # CC 钩子接收器（stdin = JSON 事件）
```

### `cc-jukebox play` 搜索行为

Apple Music 搜索是三层级的（优先最便宜的）：

1. **本地库子串匹配** — `every track of library playlist 1 whose name contains "Q" or artist contains "Q"`。快速、精确。
2. **多词 AND 匹配** — `"青花瓷 周杰伦"` → 每个词都匹配 `name` 或 `artist` 的曲目。让自然的"歌曲 艺术家"查询即使没有单个字段包含完整字符串也能工作。
3. **iTunes Search API** — 如果本地无匹配，访问 Apple 公开搜索端点，让 Music.app 打开排名第一的曲目目录 URL（`music://music.apple.com/song/<id>`）。需要有效的 Apple Music 订阅才能实际播放；否则 Music 只会显示页面。

### `/juke` 斜杠命令

安装于 `~/.claude/commands/juke.md`（符号链接到此仓库）。在 Claude Code 内：

```
/juke status
/juke play 稻香 周杰伦
/juke next
/juke pause
/juke np
```

接受自由格式的中文或英文意图（`下一首`、`暂停`、`在放什么`）。

默认情况下，`/juke` 会先由 `UserPromptExpansion` hook 拦截：它启动一个不持久化历史的 headless Claude 子会话来理解你的自然语言意图，然后只执行经过校验的 `cc-jukebox` 命令。主会话只收到短结果，不会吃掉当前上下文。

## 音乐来源能力矩阵

| 来源         | now_playing | play/pause | skip | seek | search       | full playback | cover art |
|--------------|-------------|------------|------|------|--------------|---------------|-----------|
| apple_music  | ✓ (osascript) | ✓          | ✓    | ✓    | ✓ (library)  | ✓             | ✓         |
| local        | ✓ (PID + clock) | ✓ (kill/respawn) | ✓ (next file) | ⚠ 尽力而为 | ✓ (filename) | ✓        | ✓ (id3)   |
| qq_music     | partial       | ✓ (仅试听) | —    | —    | ✓ (HTTP API) | ⚠ 仅 30s 试听 | ✓ |

QQ音乐没有 AppleScript 钩子也没有官方公开 API。我们使用非官方搜索端点获取元数据，并尝试播放 30 秒试听。完整付费曲目播放需要 QQ 音乐桌面应用，无法在无头模式下驱动。

## 氛围规则（默认）

| 事件                                       | Mood       | Vibe     |
|-------------------------------------------|------------|----------|
| `SessionStart`                            | happy      | focus    |
| `Edit` / `Write` / `MultiEdit`            | focus      | from ext (py/ts → build, sql → focus, md → review) |
| `Read` / `Grep` / `Glob`                  | thinking   | review   |
| `Bash` 包含 `pytest`/`npm test`/etc       | victory 或 sad | victory 或 fail |
| `Bash` 包含 `git commit`                  | victory    | victory  |
| `Stop`                                    | sleep      | idle     |

随时覆盖：

> 设置氛围为 debug
> DJ 说点开心的

（这些触发 `vibe_set` 和 `dj_say` MCP 工具。）

## 文件结构

```
cc_jukebox/
├── __main__.py            # CLI 分发器
├── server.py              # MCP 服务器（20+ 个工具）
├── statusline.py          # 单帧状态栏
├── vibe.py                # 钩子接收器 + 分类器
├── focus.py               # 番茄钟循环
├── dj.py                  # DJ Buddy 角色（表情、精灵图、台词）
├── state.py               # JSON 后端共享状态
├── config.py              # 路径 + 调色板 + 氛围映射
├── sources/
│   ├── apple_music.py     # AppleScript
│   ├── local.py           # afplay + mutagen 标签
│   └── qq_music.py        # HTTP 搜索 + 试听
└── ui/
    ├── pixel_cover.py     # 图像 → 半块 ANSI
    ├── progress.py        # 进度条 + 伪频谱
    ├── frame.py           # 复古像素边框 + 横幅
    └── lyrics.py          # 卡拉OK风格窗口
```

## 注意事项

- **仅支持 macOS。** Apple Music + afplay 是 macOS 特有的。Linux/Windows 需要替换后端。
- **"频谱"是假的。** 我们无法从终端捕获系统音频，所以条形图从 `position` 确定性动画。看起来有活力，但不是真正的 FFT。
- **DJ Buddy 不会自己闭嘴。** 它只在 CC 调用 `dj_say` 时说话。钩子只是更新状态。

## 卸载

```bash
./uninstall.sh           # 删除 settings.json 条目、cc-jukebox bin
                         # 符号链接、/juke 命令，以及 ~/.zshrc / ~/.bashrc
                         # 中的 PATH 块。
./uninstall.sh --purge   # 同时删除 ~/.cc-jukebox/（venv + 状态）。
```
