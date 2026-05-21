# Coding With Beat

Claude Code 的像素艺术音乐伴侣。无需离开终端即可听歌，享受响应式复古 UI，让小巧的 DJ Buddy 随你的编码节奏改变氛围。

```
██╗    ██╗██╗████████╗██╗  ██╗    ██████╗ ███████╗ █████╗ ████████╗
██║    ██║██║╚══██╔══╝██║  ██║    ██╔══██╗██╔════╝██╔══██╗╚══██╔══╝
██║ █╗ ██║██║   ██║   ███████║    ██████╔╝█████╗  ███████║   ██║
██║███╗██║██║   ██║   ██╔══██║    ██╔══██╗██╔══╝  ██╔══██║   ██║
╚███╔███╔╝██║   ██║   ██║  ██║    ██████╔╝███████╗██║  ██║   ██║
 ╚══╝╚══╝ ╚═╝   ╚═╝   ╚═╝  ╚═╝    ╚═════╝ ╚══════╝╚═╝  ╚═╝   ╚═╝
              coding · with · beat  —  a pixel companion for vibecoding
```

## 功能介绍

- **MCP 服务器** — 向 Claude Code 暴露 21 个工具，让你可以直接说"播放 lofi"、"跳过这首"、"显示播放器"、"正在播放什么？"等自然语言指令。
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
curl -LsSf https://raw.githubusercontent.com/jaychempan/coding-with-beat/main/bootstrap.sh | sh
```

这会将 coding-with-beat 克隆到 `~/.coding-with-beat/src`，然后运行 `install.sh`。随时重新运行即可更新。

### 手动安装

```bash
git clone https://github.com/jaychempan/coding-with-beat.git
cd coding-with-beat
./install.sh
```

### install.sh 做了什么

1. **Python** — 在 PATH、`/opt/homebrew/bin`、`/usr/local/bin` 或 `~/miniconda3/envs` 等路径下查找 Python ≥3.10。如果都不存在，**自动安装 uv 并用它下载 Python 3.12**（不污染系统，安装在 `~/.local/` 下）。可通过 `CWB_PYTHON=/path/to/python ./install.sh` 覆盖。
2. **venv** — 创建于 `~/.coding-with-beat/venv`（不在仓库目录中，所以移动/删除源码不影响安装）。
3. **`cwb` CLI** — 符号链接到 `~/.local/bin/`，并（幂等地）向 `~/.zshrc`（和 `~/.bashrc`）追加带标记的 `export PATH=…` 块，使命令在任何新 shell 中可用。
4. **`/cwb` 斜杠命令** — 从 `commands/cwb.md` 符号链接到 `~/.claude/commands/` — 仓库是真实来源，所以 `git pull` 即可更新命令，无需重新运行安装脚本。
5. **Claude Code 设置** — 合并条目到 `~/.claude/settings.json`：
   - `mcpServers["coding-with-beat"]`
   - `statusLine`（仅当你没有配置时才添加）
   - `PreToolUse`、`PostToolUse`、`SessionStart`、`Stop` 钩子
   - `/cwb` 的 `UserPromptExpansion` 钩子，用一次性 headless Claude 子会话理解音乐指令，避免污染主上下文
6. **状态目录** `~/.coding-with-beat/` 用于运行时 JSON。

每个条目都标记 `_owner: "coding-with-beat"`，以便 `./uninstall.sh` 只删除我们添加的内容。

启动一个新 shell（让 PATH 生效）和一个新的 Claude Code 会话。你应该能在状态栏看到 `(•_•)` 表情。试着说：

> 显示播放器

……Claude 会调用 `show_player`，在终端内绘制像素边框。或者输入 `/cwb play 周杰伦` 直接驱动。

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
| 播放图标 | `▶` / `▷` (每秒闪烁) / `❚❚` | 播放中每秒在 ▶ ▷ 之间切换；暂停显示 ❚❚ |
| 曲目 | `雨爱 — 杨丞琳  ██████░░░░░░░░` | 曲名 + 艺术家 + 14 格进度条 |
| Vibe | `[build]` `[focus]` 等 | 当前编码氛围，颜色随心情变化 |
| 番茄钟 | `🍅 work 24:15` `☕ break 04:30` | 仅专注模式激活时出现 |
| 律动波纹 | `▁▂▃▄▅` | BPM 由曲目哈希派生，每拍涨落一次；暂停时显示暗色平线 |
| 歌词 / 台词 | `│ ♪ 不忍揭曉的劇情` / `│ ✦ 台词` | 当前 LRC 歌词；收到 DJ 台词时短暂替换为 ✦ 版本 |

终端宽度不足时，歌词自动截断；更窄时波纹和歌词依次隐藏，曲目信息始终可见。

## 项目级配置

在任何项目目录下：

```bash
cwb init
```

……会写入 `.coding-with-beat.toml`，让不同项目可以默认不同的氛围/来源/起始查询。

## 命令行工具

安装后，`cwb` 命令已在 PATH 中。

```
cwb status              # 当前状态
cwb np                  # 单行：标题 — 艺术家
cwb play [query]        # 恢复播放，或搜索并播放
cwb pause               # 暂停
cwb next                # 下一首
cwb prev                # 上一首
cwb like                # 收藏当前曲目
cwb mode <mode>         # 播放模式：shuffle | sequential | repeat | repeat_one
cwb volume <0-100>      # 调整音量（0-100）
cwb seek <t>            # 跳转进度：秒数（90）或 mm:ss（1:30）
cwb player              # 完整像素播放器
cwb watch               # 实时 TUI（支持键盘控制，q 退出）
cwb karaoke             # 全屏卡拉 OK（支持键盘控制，q 退出）
cwb cover [rgb|gameboy] # 仅显示当前封面
cwb lyrics              # 歌词窗口
cwb history [n]         # 显示最近播放的 n 首歌（默认 10）
cwb bar <show|hide|auto> # 状态栏显示模式：show = 始终显示，hide = 隐藏，auto = 仅播放时显示
cwb demo                # 视觉冒烟测试
cwb banner              # 大型横幅
cwb init                # 写入 .coding-with-beat.toml
cwb server              # MCP 服务器（CC 会自动启动）
cwb statusline          # 单帧状态栏（CC 调用）
cwb hook                # CC 钩子接收器（stdin = JSON 事件）
```

### `watch` / `karaoke` 键盘快捷键

进入实时 TUI 后无需退出即可控制播放：

| 按键     | 动作           |
|----------|----------------|
| `Space`  | 播放 / 暂停    |
| `n`      | 下一首         |
| `p`      | 上一首         |
| `l`      | 收藏当前曲目   |
| `q`      | 退出           |

### `cwb play` 搜索行为

Apple Music 搜索是三层级的（优先最便宜的）：

1. **本地库子串匹配** — `every track of library playlist 1 whose name contains "Q" or artist contains "Q"`。快速、精确。
2. **多词 AND 匹配** — `"青花瓷 周杰伦"` → 每个词都匹配 `name` 或 `artist` 的曲目。让自然的"歌曲 艺术家"查询即使没有单个字段包含完整字符串也能工作。
3. **iTunes Search API** — 如果本地无匹配，访问 Apple 公开搜索端点，让 Music.app 打开排名第一的曲目目录 URL（`music://music.apple.com/song/<id>`）。需要有效的 Apple Music 订阅才能实际播放；否则 Music 只会显示页面。

### `/cwb` 斜杠命令

安装于 `~/.claude/commands/cwb.md`（符号链接到此仓库）。在 Claude Code 内：

```
/cwb status
/cwb play 稻香 周杰伦
/cwb next
/cwb 下一首
/cwb pause
/cwb 暂停
/cwb np
/cwb volume 70
/cwb seek 1:30
/cwb like
/cwb 收藏
/cwb bar show           # 始终显示状态栏
/cwb bar hide           # 隐藏状态栏
/cwb bar auto           # 仅播放时显示（有歌才出现）
/cwb 隐藏状态栏
/cwb 显示状态栏
```

接受自由格式的中文或英文意图（`下一首`、`暂停`、`在放什么`、`收藏`）。

**快速路径**：常见命令（pause、next、prev、np、like、volume、seek 等）本地直接匹配，无需启动 Claude 子进程，响应从 ~5s 降到 <0.1s。只有模糊的自然语言搜索才走 headless Claude 子会话，主会话只收到短结果，不污染当前上下文。

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
| `Edit` / `Write` 测试文件（`test_*.py`、`*.spec.ts` 等） | focus | debug |
| `Edit` / `Write` / `MultiEdit`            | focus      | 根据扩展名（py/ts → build，sql → focus，md → review） |
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
coding_with_beat/
├── __main__.py            # CLI 分发器
├── server.py              # MCP 服务器（21 个工具）
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
./uninstall.sh           # 删除 settings.json 条目、cwb bin
                         # 符号链接、/cwb 命令，以及 ~/.zshrc / ~/.bashrc
                         # 中的 PATH 块。
./uninstall.sh --purge   # 同时删除 ~/.coding-with-beat/（venv + 状态）。
```
