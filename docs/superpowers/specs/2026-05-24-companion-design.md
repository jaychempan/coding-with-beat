# Companion Mode — Design Spec

**Date:** 2026-05-24  
**Status:** Approved  
**Feature:** DJ Buddy 音乐陪伴系统 — 主动关心 + 情境音乐推荐

---

## 1. 目标

将 coding-with-beat 从"被动音乐控制器"升级为"编程陪伴"：
在关键编程时刻主动出现，用 DJ Buddy 的语气关心用户状态，并推荐当下最合适的音乐。
核心原则：**有温度但不打扰**（15 分钟冷却、条件门控、静默跳过）。

---

## 2. 触发时机与交付路径

| 触发 | 条件 | 谁感知 | 怎么送达 |
|---|---|---|---|
| Session 开始 | 每次 CC 启动 | SessionStart hook | hook stdout 轻量问候 + Claude 第一条回复调 `companion_check` |
| Debug 挣扎 | 连续**测试命令**失败 ≥ 3 次 | Claude 看到错误 | Claude 调 `companion_check("debug_struggle")` |
| 胜利时刻 | git commit 成功 / 测试全绿 | Claude 看到输出 | Claude 调 `companion_check("victory")` |
| 静默签到 | 工具调用 ≥ 20 次 且 ≥ 25 分钟无音乐推荐 | Claude 自判 | Claude 调 `companion_check("idle_checkin")` |
| Session 结束 | 用户说"收工/bye"等 或 Stop hook + 会话 ≥ 5 分钟 | Claude / Stop hook | Claude 调 `companion_check("session_end")` / hook stdout 告别卡 |

---

## 3. 架构概览

```
用户编程
  │
  ├─ SessionStart hook → vibe.py
  │     ├─ 初始化 companion 状态字段
  │     └─ stdout: 轻量问候卡
  │
  ├─ PostToolUse hook → vibe.py
  │     └─ 累积 failure_streak / tool_count → AppState
  │
  ├─ Claude 感知触发事件
  │     └─ companion_check(trigger) [MCP tool]
  │                 │
  │           companion.py
  │                 ├─ can_trigger(): 冷却 + 条件检查
  │                 ├─ get_message(): 从消息池随机取
  │                 ├─ get_queries(): 返回 smart_search 查询词
  │                 └─ 组装陪伴卡（DJ Buddy sprite + 话语 + 推荐列表）
  │
  └─ Stop hook → vibe.py
        └─ stdout: 告别卡（会话 ≥ 5 分钟）
```

---

## 4. 文件改动清单

| 文件 | 操作 |
|---|---|
| `coding_with_beat/companion.py` | 新建 — 核心逻辑 |
| `coding_with_beat/state.py` | 修改 — AppState 加 4 个字段 |
| `coding_with_beat/server.py` | 修改 — 新增 `companion_check()` MCP 工具 |
| `coding_with_beat/vibe.py` | 修改 — SessionStart / PostToolUse / Stop 增强 |
| `skills/cwb-companion/SKILL.md` | 新建 — Claude 触发规则 + 呈现方式 |
| `install.sh` | 修改 — 注入 cwb-companion 到 `~/.claude/CLAUDE.md` |

---

## 5. State 变更（`state.py`）

`AppState` 新增字段：

```python
companion_last_at: float = 0.0        # 上次陪伴消息时间戳（冷却基准）
companion_session_start: float = 0.0  # 本 session 启动时间
companion_failure_streak: int = 0     # 连续测试/命令失败次数
companion_tool_count: int = 0         # 本 session 累计工具调用次数
```

SessionStart hook 重置全部四个字段（`companion_last_at` 也重置为 0，新 session 不受上个 session 冷却影响）。

---

## 6. `companion.py` 模块

### 常量

```python
COOLDOWN_SECS = 900        # 15 分钟冷却
FAILURE_THRESHOLD = 3      # 连续失败触发阈值
IDLE_TOOLS_THRESHOLD = 20  # 静默签到工具调用阈值
MIN_SESSION_SECS = 300     # session_end 最短会话时长
```

### 函数接口

```python
def can_trigger(st: AppState, trigger: str) -> bool
    # 统一冷却检查 + 各 trigger 专属条件

def get_message(trigger: str, st: AppState) -> str
    # 从 MESSAGES[trigger] 随机取一条

def get_queries(trigger: str) -> list[str]
    # 返回 2-3 条 smart_search 查询词
```

### 消息池 & 查询词

| trigger | 示例话语 | 查询词方向 |
|---|---|---|
| `session_start`（6-17时） | "早！今天想专注什么？我先挑首暖场的" | morning fresh indie / coffee acoustic / start of day motivation |
| `session_start`（18-5时） | "又到深夜了——来首 lofi 陪你" | lofi late night coding / night ambient focus / synthwave night drive |
| `debug_struggle` | "调了挺久了，先歇口气——换首轻松的？" | calm piano breathe / lofi stress relief / gentle acoustic decompress |
| `victory` | "✓ 成了！该庆祝一下" | celebration feel good indie / victory upbeat pop / achievement energetic |
| `idle_checkin` | "你还好吧？忙了一阵了——音乐还合适吗" | background lofi focus / ambient flow state / study chill rain cafe |
| `session_end` | "收工了，辛苦了——来首舒缓的慢慢降落" | wind down gentle piano / soft acoustic unwind / peaceful end of day |

每个 trigger 至少 3 条不同话语，`get_message()` 随机选取。

---

## 7. `companion_check()` MCP 工具（`server.py`）

```python
@mcp.tool()
async def companion_check(trigger: str) -> str:
    """
    DJ Buddy 陪伴检查。
    trigger ∈ {session_start, debug_struggle, victory, idle_checkin, session_end}
    内部处理冷却 + 条件判断。返回陪伴卡或 "(not needed right now)"。
    """
    from . import companion
    st = state.load()
    if not companion.can_trigger(st, trigger):
        return "(not needed right now)"
    queries = companion.get_queries(trigger)
    music_results = await _multi_angle_search(queries, limit_per_query=4)
    st.companion_last_at = time.time()
    state.save(st)
    message = companion.get_message(trigger, st)
    return _companion_card(message, music_results)
```

`_companion_card(message, music_results)` 复用 `_buddy_card()` 渲染：DJ Buddy 像素人在左，话语 + 推荐列表在右。

---

## 8. `vibe.py` Hook 增强

### SessionStart

```python
st.companion_session_start = time.time()
st.companion_failure_streak = 0
st.companion_tool_count = 0
st.companion_last_at = 0.0
state.save(st)
print(_build_session_greeting(st))  # 轻量问候，无 smart_search
```

### PostToolUse

```python
if tool == "bash" and _is_test_command(cmd):
    if not success:
        st.companion_failure_streak += 1
    else:
        st.companion_failure_streak = 0
st.companion_tool_count += 1
state.save(st)
```

### Stop

```python
duration = time.time() - st.companion_session_start
if duration >= MIN_SESSION_SECS:
    print(_build_session_farewell(st))  # 轻量告别，无 smart_search
```

hook stdout 的问候/告别卡**不调用 smart_search**（避免 hook 里做异步网络请求）。
仅含 DJ Buddy sprite + 一句话 + "说想听什么我来找"提示。

---

## 9. `cwb-companion` Skill

**触发规则（告知 Claude）：**

| 时机 | 调用 |
|---|---|
| Session 开始后第一条回复 | `companion_check("session_start")` |
| 连续看到 ≥3 次**测试命令**失败 | `companion_check("debug_struggle")` |
| git commit 成功 / 测试全绿 | `companion_check("victory")` |
| 本 session ≥20 工具调用 且 ≥25 分钟无音乐推荐 | `companion_check("idle_checkin")` |
| 用户说"收工/下班/bye/晚安" | `companion_check("session_end")` |

**呈现规则：**
- 返回 `(not needed right now)` → 静默，不对用户提及
- 返回陪伴卡 → 完整输出，卡片前可加一句过渡语（"对了——"），卡片后不追加解释
- 等用户说编号后调用 `play_number()`

**语气基调：** 简短、有温度、不说废话。

---

## 10. install.sh 注入

在现有 `# >>> coding-with-beat >>>` 块附近，追加 `# >>> cwb-companion >>>` 块到 `~/.claude/CLAUDE.md`，内容：加载 `cwb-companion` skill 的触发条件摘要（一段简短的路由规则）。

---

## 11. 范围边界（不做的事）

- **不做**语音/系统通知
- **不做**自定义冷却时长配置（硬编码 15 分钟，够用）
- **不做**历史陪伴记录持久化
- **不做** companion_check 的测试框架外 E2E 测试（hook stdout 行为随 CC 版本变化）
