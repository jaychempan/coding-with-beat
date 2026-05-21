# Coding With Beat

> **你上一次 vibecoding 的时候又唱又跳是什么时候？**
>
> 对。你已经不记得了。

```
██╗    ██╗██╗████████╗██╗  ██╗    ██████╗ ███████╗ █████╗ ████████╗
██║    ██║██║╚══██╔══╝██║  ██║    ██╔══██╗██╔════╝██╔══██╗╚══██╔══╝
██║ █╗ ██║██║   ██║   ███████║    ██████╔╝█████╗  ███████║   ██║
██║███╗██║██║   ██║   ██╔══██║    ██╔══██╗██╔══╝  ██╔══██║   ██║
╚███╔███╔╝██║   ██║   ██║  ██║    ██████╔╝███████╗██║  ██║   ██║
 ╚══╝╚══╝ ╚═╝   ╚═╝   ╚═╝  ╚═╝    ╚═════╝ ╚══════╝╚═╝  ╚═╝   ╚═╝
              coding · with · beat  —  a pixel companion for vibecoding
```

你只是在敲代码。Claude 在旁边静静地看着。终端里除了光标在闪，什么声音都没有。
这个工具的存在，就是为了终结这种悲剧。

**Coding With Beat** 是一个住在 Claude Code 里的像素风 DJ 小伙伴。
它帮你放音乐、看歌词、在你 commit 成功的时候庆祝，在测试挂掉的时候跟你一起崩溃。

---

## 它能干什么

- **MCP server** — 接入 21 个工具，让你直接跟 Claude 说「放点 lofi」「跳过这首」「现在在放啥」，全都好使。
- **音乐源** — Apple Music（AppleScript 驱动，不用开 GUI）、本地文件（afplay）、QQ 音乐（搜索 + 预览）。
- **像素 UI** — 专辑封面用半格 ANSI 字符渲染，支持 GameBoy 四色模式，复古边框，加一个「看起来很像真的」频谱均衡器。
- **DJ Buddy** — 一个 5 行高的像素小人，会根据你的工作状态换表情。测试挂了它也跟着慌。
- **Vibe 引擎** — 通过 CC hooks（PreToolUse / PostToolUse / SessionStart / Stop）实时感知你在干什么，自动切换氛围。`git commit` 了？胜利音效。测试炸了？小人开始 panic。
- **状态栏** — 一行小脸 + 当前曲目 + 进度条，随时知道放到哪了。
- **专注模式** — 内置 25/5 番茄钟，显示在状态栏里，让你假装自己很自律。
- **一键安装** — `bootstrap.sh` / `install.sh` 全局搞定，不需要手动配置任何东西。没有 Python？自动用 [uv](https://docs.astral.sh/uv/) 帮你下一个。

---

## 装上它

### 一行搞定（推荐）

```bash
curl -LsSf https://raw.githubusercontent.com/jaychempan/coding-with-beat/main/bootstrap.sh | sh
```

克隆到 `~/.coding-with-beat/src`，然后自动跑 `install.sh`。想更新？再跑一次。

### 手动装

```bash
git clone https://github.com/jaychempan/coding-with-beat.git
cd coding-with-beat
./install.sh
```

### `install.sh` 背后在干什么

1. **找 Python** — 按顺序找 PATH 上的、Homebrew 的、conda 环境里的 Python ≥3.10。一个都没有？自动装 uv，再用 uv 下 Python 3.12。你的系统不会多出任何垃圾。想指定路径就 `CWB_PYTHON=/path/to/python ./install.sh`。
2. **建 venv** — 放在 `~/.coding-with-beat/venv`，不在项目目录里，删了源码也不影响。
3. **`cwb` 命令** — symlink 进 `~/.local/bin/`，顺便往 `~/.zshrc` / `~/.bashrc` 写一条 `export PATH`。
4. **`/juke` slash command** — symlink 进 `~/.claude/commands/`，指向仓库里的文件，`git pull` 自动更新。
5. **Claude Code 配置** — 合并写入 `~/.claude/settings.json`：MCP server、状态栏、vibe hooks，以及 `/juke` 的 UserPromptExpansion hook。
6. **状态目录** — `~/.coding-with-beat/` 存运行时 JSON。

每项配置都打上 `_owner: "coding-with-beat"` 标签，卸载时精准清除，不动你自己的配置。

装完开个新 shell、新 Claude Code 会话，状态栏里出现 `(•_•)` 就成了。然后试试：

> 帮我打开播放器

Claude 会调 `show_player`，把像素播放器画在终端里。或者直接 `/cwb play 周杰伦`。

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
| 播放图标 | `▶` / `▷` (每秒闪烁) / `❚❚` | 播放中每秒在 ▶ ▷ 之间切换；暂停显示 ❚❚ |
| 曲目 | `雨爱 — 杨丞琳  ██████░░░░░░░░` | 曲名 + 艺术家 + 14 格进度条 |
| Vibe | `[build]` `[focus]` 等 | 当前编码氛围，颜色随心情变化 |
| 番茄钟 | `🍅 work 24:15` `☕ break 04:30` | 仅专注模式激活时出现 |
| 律动波纹 | `▁▂▃▄▅` | BPM 由曲目哈希派生，每拍涨落一次；暂停时显示暗色平线 |
| 歌词 / 台词 | `│ ♪ 不忍揭曉的劇情` / `│ ✦ 台词` | 当前 LRC 歌词；收到 DJ 台词时短暂替换为 ✦ 版本 |

终端宽度不足时，歌词自动截断；更窄时波纹和歌词依次隐藏，曲目信息始终可见。

---

## 项目级配置

在任意项目目录：

```bash
cwb init
```

生成 `.coding-with-beat.toml`，可以给不同项目设不同的默认氛围、音源、启动歌单。
写 Python 时放 lo-fi，写 Makefile 时放 city pop，完全合理。

---

## 命令行

```
cwb status              # 当前状态
cwb np                  # 一行：曲名 — 艺术家
cwb play [query]        # 继续播放，或搜索并播
cwb pause               # 暂停
cwb next                # 下一首
cwb prev                # 上一首
cwb like                # 收藏当前曲目
cwb mode <mode>         # 播放模式：shuffle | sequential | repeat | repeat_one
cwb volume <0-100>      # 调整音量（0-100）
cwb seek <t>            # 跳转进度：秒数（90）或 mm:ss（1:30）
cwb player              # 完整像素播放器
cwb watch               # TUI 实时模式（支持键盘控制，q 退出）
cwb karaoke             # 全屏卡拉 OK 模式（支持键盘控制，q 退出）
cwb cover [rgb|gameboy] # 只显示封面
cwb lyrics              # 歌词窗口
cwb history [n]         # 显示最近播放的 n 首歌（默认 10）
cwb bar <show|hide|auto> # 状态栏显示模式：show = 始终显示，hide = 隐藏，auto = 仅播放时显示
cwb demo                # 视觉测试
cwb banner              # 大横幅
cwb init                # 生成 .coding-with-beat.toml
cwb server              # MCP server（CC 会自动启动）
cwb statusline          # 输出一帧状态栏（CC 调用）
cwb hook                # CC hook 接收器（stdin = JSON 事件）
```

### `watch` / `karaoke` 键盘快捷键

进入实时 TUI 模式后，无需退出就能控制播放：

| 按键     | 动作           |
|----------|----------------|
| `Space`  | 播放 / 暂停    |
| `n`      | 下一首         |
| `p`      | 上一首         |
| `l`      | 收藏当前曲目   |
| `q`      | 退出           |

### `play` 搜索逻辑

Apple Music 搜索三段走，从快到慢：

1. **本地库子串匹配** — `name` 或 `artist` 包含关键词，秒出。
2. **多词 AND 匹配** — `"青花瓷 周杰伦"` → 每个词分别命中 `name` 或 `artist`，自然语言查询也能用。
3. **iTunes Search API** — 本地找不到？走苹果公开搜索 API，拿到 catalog URL 让 Music.app 打开。需要有效的 Apple Music 订阅才能真正播放。

### `/cwb` slash command

装完之后在 Claude Code 里直接用：

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

中英文自由输入，`下一首`、`暂停`、`在放什么`、`收藏` 都行。

**快速路径**：常见命令（pause、next、prev、np、like、volume、seek 等）直接在本地匹配，无需启动 Claude 子进程，响应时间从 ~5s 降到 <0.1s。只有模糊的自然语言搜索（"播放一首 city pop"）才会走 headless Claude 子会话。主会话只看到短结果，不会把点歌过程塞进当前上下文。

---

## 音源能力矩阵

| 音源         | 当前曲目 | 播放/暂停 | 跳曲 | 进度 | 搜索        | 完整播放          | 封面 |
|--------------|----------|-----------|------|------|-------------|-------------------|------|
| apple_music  | ✓        | ✓         | ✓    | ✓    | ✓（本地库） | ✓                 | ✓    |
| local        | ✓        | ✓         | ✓    | ⚠    | ✓（文件名） | ✓                 | ✓    |
| qq_music     | 部分     | ✓（预览） | —    | —    | ✓（HTTP）   | ⚠ 仅 30 秒预览   | ✓    |

QQ 音乐没有 AppleScript 接口，也没有公开 API，用的是非官方搜索接口配合 30 秒预览。想完整播放还是得开 QQ 音乐客户端，这不是我们能驱动的范围。

---

## Vibe 规则（默认）

| 事件                                      | 心情     | 氛围     |
|-------------------------------------------|----------|----------|
| `SessionStart`                            | happy    | focus    |
| `Edit` / `Write` 测试文件（`test_*.py`、`*.spec.ts` 等） | focus | debug |
| `Edit` / `Write` / `MultiEdit`            | focus    | 根据扩展名（py/ts → build，sql → focus，md → review） |
| `Read` / `Grep` / `Glob`                  | thinking | review   |
| `Bash` 含 `pytest` / `npm test` 等        | victory 或 sad | victory 或 fail |
| `Bash` 含 `git commit`                    | victory  | victory  |
| `Stop`                                    | sleep    | idle     |

随时可以覆盖：

> 切换到 debug 模式
> DJ 说点鼓励的话

这会触发 `vibe_set` 和 `dj_say` 工具。

---

## 文件结构

```
coding_with_beat/
├── __main__.py            # CLI 入口
├── server.py              # MCP server（21 个工具）
├── statusline.py          # 单帧状态栏
├── vibe.py                # hook 接收器 + 分类器
├── focus.py               # 番茄钟
├── dj.py                  # DJ Buddy（表情、精灵、台词）
├── state.py               # JSON 状态存取
├── config.py              # 路径、调色板、vibe 映射
├── sources/
│   ├── apple_music.py     # AppleScript
│   ├── local.py           # afplay + mutagen 标签
│   └── qq_music.py        # HTTP 搜索 + 预览
└── ui/
    ├── pixel_cover.py     # 图片 → 半格 ANSI
    ├── progress.py        # 进度条 + 伪频谱
    ├── frame.py           # 复古像素边框 + 横幅
    └── lyrics.py          # 卡拉 OK 窗口
```

---

## 已知局限

- **仅限 macOS。** Apple Music 和 afplay 都是 macOS 独有的。Linux / Windows 需要换后端，目前没有计划。
- **频谱是假的。** 终端里没法捕获系统音频，所以均衡器的柱子是根据播放进度用确定性算法生成的动画。好看，但不是真 FFT，不要误会。
- **DJ Buddy 不会主动打扰你。** 它只在 CC 调用 `dj_say` 时说话，hooks 只更新状态，不会突然弹出来。

---

## 卸载

```bash
./uninstall.sh           # 移除 settings.json 条目、cwb 命令、/cwb 命令、PATH 块
./uninstall.sh --purge   # 同上，另外删除 ~/.coding-with-beat/（venv + 状态文件）
```
