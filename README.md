# CC-Jukebox

> **你上一次 vibecoding 的时候又唱又跳是什么时候？**
>
> 对。你已经不记得了。

```
 ██████╗ ██████╗     ██╗██╗   ██╗██╗  ██╗███████╗██████╗  ██████╗ ██╗  ██╗
██╔════╝██╔════╝     ██║██║   ██║██║ ██╔╝██╔════╝██╔══██╗██╔═══██╗╚██╗██╔╝
██║     ██║          ██║██║   ██║█████╔╝ █████╗  ██████╔╝██║   ██║ ╚███╔╝
██║     ██║     ██   ██║██║   ██║██╔═██╗ ██╔══╝  ██╔══██╗██║   ██║ ██╔██╗
╚██████╗╚██████╗╚█████╔╝╚██████╔╝██║  ██╗███████╗██████╔╝╚██████╔╝██╔╝ ██╗
 ╚═════╝ ╚═════╝ ╚════╝  ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═════╝  ╚═════╝ ╚═╝  ╚═╝
                   a pixel companion for vibecoding
```

你只是在敲代码。Claude 在旁边静静地看着。终端里除了光标在闪，什么声音都没有。
这个工具的存在，就是为了终结这种悲剧。

**CC-Jukebox** 是一个住在 Claude Code 里的像素风 DJ 小伙伴。
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
curl -LsSf https://raw.githubusercontent.com/jaychempan/cc-jukebox/main/bootstrap.sh | sh
```

克隆到 `~/.cc-jukebox/src`，然后自动跑 `install.sh`。想更新？再跑一次。

### 手动装

```bash
git clone https://github.com/jaychempan/cc-jukebox.git
cd cc-jukebox
./install.sh
```

### `install.sh` 背后在干什么

1. **找 Python** — 按顺序找 PATH 上的、Homebrew 的、conda 环境里的 Python ≥3.10。一个都没有？自动装 uv，再用 uv 下 Python 3.12。你的系统不会多出任何垃圾。想指定路径就 `CC_JUKEBOX_PYTHON=/path/to/python ./install.sh`。
2. **建 venv** — 放在 `~/.cc-jukebox/venv`，不在项目目录里，删了源码也不影响。
3. **`cc-jukebox` 命令** — symlink 进 `~/.local/bin/`，顺便往 `~/.zshrc` / `~/.bashrc` 写一条 `export PATH`。
4. **`/juke` slash command** — symlink 进 `~/.claude/commands/`，指向仓库里的文件，`git pull` 自动更新。
5. **Claude Code 配置** — 合并写入 `~/.claude/settings.json`：MCP server、状态栏、vibe hooks，以及 `/juke` 的 UserPromptExpansion hook。
6. **状态目录** — `~/.cc-jukebox/` 存运行时 JSON。

每项配置都打上 `_owner: "cc-jukebox"` 标签，卸载时精准清除，不动你自己的配置。

装完开个新 shell、新 Claude Code 会话，状态栏里出现 `(•_•)` 就成了。然后试试：

> 帮我打开播放器

Claude 会调 `show_player`，把像素播放器画在终端里。或者直接 `/juke play 周杰伦`。

---

## 项目级配置

在任意项目目录：

```bash
cc-jukebox init
```

生成 `.cc-jukebox.toml`，可以给不同项目设不同的默认氛围、音源、启动歌单。
写 Python 时放 lo-fi，写 Makefile 时放 city pop，完全合理。

---

## SSH 远端 Claude Code

如果 Claude Code 跑在服务器上，而 Apple Music 跑在本机 Mac，可以用 relay 模式。远端 `cc-jukebox` 只接 Claude Code 的 MCP、hooks、statusline 和 `/juke` 请求，真正的音乐控制仍回到本机执行。

推荐的 SSH attach 模式：

```bash
# 本机 Mac：正常安装
./install.sh

# 服务器：安装并把 Claude Code 配到远端 request socket
./install.sh --relay-socket ~/.cc-jukebox/run/agent-request.sock

# 服务器：启动远端 relay agent
cc-jukebox relay agent-service

# 本机 Mac：建立长期 SSH attach
cc-jukebox relay attach user@server
```

之后在服务器上的 Claude Code 里，MCP 工具、状态栏、hooks 和 `/juke` 都会穿过 relay 回到本机 Mac 执行。
如果服务器上的 `cc-jukebox` 不在默认 `$HOME/.local/bin/cc-jukebox`，给 attach 加 `--remote-bin /path/to/cc-jukebox`。

HTTP + SSH 反向端口转发也可以：

```bash
# 本机 Mac
cc-jukebox relay serve --host 127.0.0.1 --port 8765
ssh -R 127.0.0.1:8765:127.0.0.1:8765 user@server

# 服务器
./install.sh --relay-url http://127.0.0.1:8765
```

---

## 命令行

```
cc-jukebox status              # 当前状态
cc-jukebox np                  # 一行：曲名 — 艺术家
cc-jukebox play [query]        # 继续播放，或搜索并播
cc-jukebox pause               # 暂停
cc-jukebox next                # 下一首
cc-jukebox prev                # 上一首
cc-jukebox player              # 完整像素播放器
cc-jukebox watch               # TUI 实时模式（Ctrl-C 退出）
cc-jukebox cover [rgb|gameboy] # 只显示封面
cc-jukebox lyrics              # 卡拉 OK 歌词窗口
cc-jukebox demo                # 视觉测试
cc-jukebox banner              # 大横幅
cc-jukebox init                # 生成 .cc-jukebox.toml
cc-jukebox server              # MCP server（CC 会自动启动）
cc-jukebox relay               # SSH/HTTP 远端 relay
cc-jukebox statusline          # 输出一帧状态栏（CC 调用）
cc-jukebox hook                # CC hook 接收器（stdin = JSON 事件）
```

### `play` 搜索逻辑

Apple Music 搜索三段走，从快到慢：

1. **本地库子串匹配** — `name` 或 `artist` 包含关键词，秒出。
2. **多词 AND 匹配** — `"青花瓷 周杰伦"` → 每个词分别命中 `name` 或 `artist`，自然语言查询也能用。
3. **iTunes Search API** — 本地找不到？走苹果公开搜索 API，拿到 catalog URL 让 Music.app 打开。需要有效的 Apple Music 订阅才能真正播放。

### `/juke` slash command

装完之后在 Claude Code 里直接用：

```
/juke status
/juke play 稻香 周杰伦
/juke next
/juke pause
/juke np
```

中英文自由输入，`下一首`、`暂停`、`在放什么` 都行。默认情况下 `/juke` 会先被 UserPromptExpansion hook 接住，启动一个一次性的 headless Claude 子会话来理解你的意图，再执行经过校验的 `cc-jukebox` 命令；主会话只看到短结果，不会把点歌过程塞进当前上下文。

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
cc_jukebox/
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
./uninstall.sh           # 移除 settings.json 条目、cc-jukebox 命令、/juke 命令、PATH 块
./uninstall.sh --purge   # 同上，另外删除 ~/.cc-jukebox/（venv + 状态文件）
```
