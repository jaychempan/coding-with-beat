# Pet DJ AI Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the DJ panel AI chat into an AI-first conversation where AI-recommended songs and commands become one-click music actions.

**Architecture:** Keep `coding_with_beat/pet/ai_chat.py` focused on child AI process execution. Add a small `coding_with_beat/pet/ai_actions.py` parser for structured `music_actions` JSON and conservative text fallback extraction. Refactor `CodeBeatDjPanel` so the existing main scroll area becomes the unified conversation timeline and action cards route through existing `PetMusicSession` / CWB control commands.

**Tech Stack:** Python, PySide6, QProcess, pytest, ruff.

---

## File Structure

- Create `coding_with_beat/pet/ai_actions.py`: dataclasses and parsers for AI-visible text plus music action extraction.
- Create `tests/test_pet_ai_actions.py`: unit tests for structured action JSON, fallback parsing, and local command detection.
- Modify `coding_with_beat/pet/ai_chat.py`: wrap prompts with the music action contract before sending them to Codex / Claude Code.
- Modify `tests/test_pet_ai_chat.py`: assert AI prompts include the contract while preserving command construction and runner behavior.
- Modify `coding_with_beat/pet/dj_panel.py`: remove the separate `AiChatPanel`, use the main transcript as the unified AI/DJ timeline, render action buttons inline, and route clicks to existing music APIs.
- Modify `tests/test_pet_dj_panel.py`: replace standalone AI panel assertions with unified prompt/timeline/action tests.

### Task 1: Music Action Parser

**Files:**
- Create: `coding_with_beat/pet/ai_actions.py`
- Create: `tests/test_pet_ai_actions.py`

- [ ] **Step 1: Write failing parser tests**

Create `tests/test_pet_ai_actions.py`:

````python
from coding_with_beat.pet.ai_actions import (
    AiVisibleReply,
    MusicAction,
    MusicActionKind,
    detect_local_command_action,
    parse_ai_music_reply,
)


def test_parse_structured_music_actions_hides_json_block():
    raw = """我会先放两种选择。

```json
{
  "music_actions": [
    {"kind": "play_track", "query": "周杰伦 晴天", "label": "晴天 - 周杰伦"},
    {"kind": "search_music", "query": "lofi hip hop coding focus", "label": "Coding lofi"}
  ]
}
```
"""

    reply = parse_ai_music_reply(raw)

    assert reply == AiVisibleReply(
        text="我会先放两种选择。",
        actions=[
            MusicAction(MusicActionKind.PLAY_TRACK, "晴天 - 周杰伦", "周杰伦 晴天"),
            MusicAction(MusicActionKind.SEARCH_MUSIC, "Coding lofi", "lofi hip hop coding focus"),
        ],
    )


def test_parse_structured_music_actions_keeps_text_when_json_is_invalid():
    raw = "推荐《晴天》- 周杰伦\n```json\n{\"music_actions\": [\n```"

    reply = parse_ai_music_reply(raw)

    assert reply.text.startswith("推荐《晴天》")
    assert reply.actions == [MusicAction(MusicActionKind.PLAY_TRACK, "晴天 - 周杰伦", "晴天 周杰伦")]


def test_fallback_extracts_chinese_and_english_recommendation_lines():
    raw = "1. 《晴天》- 周杰伦\n2. Anti-Hero by Taylor Swift\n这两首都适合继续写代码。"

    reply = parse_ai_music_reply(raw)

    assert reply.text == raw
    assert reply.actions == [
        MusicAction(MusicActionKind.PLAY_TRACK, "晴天 - 周杰伦", "晴天 周杰伦"),
        MusicAction(MusicActionKind.PLAY_TRACK, "Anti-Hero - Taylor Swift", "Anti-Hero Taylor Swift"),
    ]


def test_local_command_detection_maps_fast_transport_controls():
    assert detect_local_command_action("/next") == MusicAction(MusicActionKind.CONTROL, "下一首", "next_track")
    assert detect_local_command_action("下一首") == MusicAction(MusicActionKind.CONTROL, "下一首", "next_track")
    assert detect_local_command_action("暂停") == MusicAction(MusicActionKind.CONTROL, "暂停/继续", "toggle")
    assert detect_local_command_action("音量 70") == MusicAction(MusicActionKind.CONTROL, "音量 70", "set_volume:70")
    assert detect_local_command_action("解释这个项目") is None
````

- [ ] **Step 2: Run parser tests to verify they fail**

Run:

```bash
pytest tests/test_pet_ai_actions.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'coding_with_beat.pet.ai_actions'`.

- [ ] **Step 3: Implement the parser module**

Create `coding_with_beat/pet/ai_actions.py`:

````python
"""Parse AI DJ replies into visible chat text and playable music actions."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum


class MusicActionKind(str, Enum):
    PLAY_TRACK = "play_track"
    SEARCH_MUSIC = "search_music"
    PLAY_NUMBER = "play_number"
    CONTROL = "control"
    PLAYLIST = "playlist"


@dataclass(frozen=True)
class MusicAction:
    kind: MusicActionKind
    label: str
    query: str


@dataclass(frozen=True)
class AiVisibleReply:
    text: str
    actions: list[MusicAction]


_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)
_CHINESE_TRACK_RE = re.compile(r"(?:^\s*\d+[.)、]?\s*)?《([^》]+)》\s*[-—–]\s*([^\n，。]+)", re.MULTILINE)
_ENGLISH_BY_RE = re.compile(r"(?:^\s*\d+[.)]?\s*)?([A-Z][^\n]+?)\s+by\s+([A-Z][^\n]+)", re.MULTILINE)


def parse_ai_music_reply(raw: str) -> AiVisibleReply:
    text = (raw or "").strip()
    actions: list[MusicAction] = []
    visible = text

    for match in _JSON_BLOCK_RE.finditer(text):
        parsed = _actions_from_json(match.group(1))
        if parsed:
            actions.extend(parsed)
            visible = visible.replace(match.group(0), "").strip()

    if not actions:
        actions.extend(_fallback_actions(text))

    return AiVisibleReply(_normalize_visible_text(visible), _dedupe_actions(actions))


def detect_local_command_action(text: str) -> MusicAction | None:
    value = (text or "").strip()
    lower = value.lower()
    if lower in {"/next", "next", "下一首"}:
        return MusicAction(MusicActionKind.CONTROL, "下一首", "next_track")
    if lower in {"/prev", "/previous", "prev", "previous", "上一首"}:
        return MusicAction(MusicActionKind.CONTROL, "上一首", "prev_track")
    if lower in {"/pause", "/toggle", "pause", "toggle", "暂停", "继续"}:
        return MusicAction(MusicActionKind.CONTROL, "暂停/继续", "toggle")
    if lower in {"/like", "like", "喜欢这首"}:
        return MusicAction(MusicActionKind.CONTROL, "喜欢当前歌曲", "like_current")
    volume = re.match(r"^/?(?:volume|音量)\s+(\d{1,3})$", lower)
    if volume:
        percent = max(0, min(100, int(volume.group(1))))
        return MusicAction(MusicActionKind.CONTROL, f"音量 {percent}", f"set_volume:{percent}")
    return None


def _actions_from_json(raw_json: str) -> list[MusicAction]:
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        return []
    values = data.get("music_actions") if isinstance(data, dict) else None
    if not isinstance(values, list):
        return []
    actions: list[MusicAction] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        try:
            kind = MusicActionKind(str(item.get("kind") or ""))
        except ValueError:
            continue
        query = str(item.get("query") or "").strip()
        label = str(item.get("label") or query).strip()
        if query and label:
            actions.append(MusicAction(kind, label, query))
    return actions


def _fallback_actions(text: str) -> list[MusicAction]:
    actions: list[MusicAction] = []
    for title, artist in _CHINESE_TRACK_RE.findall(text):
        title = title.strip()
        artist = artist.strip()
        actions.append(MusicAction(MusicActionKind.PLAY_TRACK, f"{title} - {artist}", f"{title} {artist}"))
    for title, artist in _ENGLISH_BY_RE.findall(text):
        title = title.strip(" -:").strip()
        artist = artist.strip(" -:").strip()
        if title and artist:
            actions.append(MusicAction(MusicActionKind.PLAY_TRACK, f"{title} - {artist}", f"{title} {artist}"))
    return actions


def _dedupe_actions(actions: list[MusicAction]) -> list[MusicAction]:
    seen: set[tuple[MusicActionKind, str]] = set()
    deduped: list[MusicAction] = []
    for action in actions:
        key = (action.kind, action.query.lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(action)
    return deduped


def _normalize_visible_text(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(lines).strip()
````

- [ ] **Step 4: Run parser tests to verify they pass**

Run:

```bash
pytest tests/test_pet_ai_actions.py -q
```

Expected: PASS, all parser tests pass.

- [ ] **Step 5: Commit parser work**

Run:

```bash
git add coding_with_beat/pet/ai_actions.py tests/test_pet_ai_actions.py
git commit -m "feat(pet): parse ai music actions"
```

Expected: commit succeeds.

### Task 2: AI Prompt Contract

**Files:**
- Modify: `coding_with_beat/pet/ai_chat.py`
- Modify: `tests/test_pet_ai_chat.py`

- [ ] **Step 1: Write failing prompt-wrapper test**

Append this test to `tests/test_pet_ai_chat.py`:

````python
def test_ai_chat_session_wraps_prompt_with_music_action_contract(tmp_path):
    session = AiChatSession(provider=AiProvider.CODEX, cwd=tmp_path)

    command = session.build_command("推荐几首适合写代码的歌", AiPermissionMode.READ_ONLY)

    assert "music_actions" in command.stdin
    assert "play_track" in command.stdin
    assert "search_music" in command.stdin
    assert "推荐几首适合写代码的歌" in command.stdin
````

- [ ] **Step 2: Run prompt-wrapper test to verify it fails**

Run:

```bash
pytest tests/test_pet_ai_chat.py::test_ai_chat_session_wraps_prompt_with_music_action_contract -q
```

Expected: FAIL because `command.stdin` is still the raw prompt.

- [ ] **Step 3: Add the prompt contract to `ai_chat.py`**

In `coding_with_beat/pet/ai_chat.py`, add this constant near the top after `AiPermissionMode`:

````python
_MUSIC_ACTION_CONTRACT = """You are inside CodeBeat DJ, an AI-first music companion.

When your response recommends music, mentions playable songs, suggests a playlist,
or proposes playback controls, include a fenced JSON block at the end:

```json
{
  "music_actions": [
    {"kind": "play_track", "query": "song artist", "label": "Song - Artist"},
    {"kind": "search_music", "query": "mood genre scene", "label": "Readable label"}
  ]
}
```

Use these action kinds only: play_track, search_music, play_number, control, playlist.
Keep the natural-language reply useful even when the JSON is hidden from the user.
If no music action is relevant, do not include JSON.
"""
````

Then add this helper near `_codex_args`:

```python
def _wrap_user_prompt(prompt: str) -> str:
    return f"{_MUSIC_ACTION_CONTRACT}\n\nUser request:\n{prompt.strip()}"
```

Update `AiChatSession.build_command()` so both providers pass wrapped stdin:

```python
    def build_command(self, prompt: str, mode: AiPermissionMode) -> AiChatCommand:
        mode = AiPermissionMode(mode)
        stdin = _wrap_user_prompt(prompt)
        if self.provider == AiProvider.CODEX:
            return AiChatCommand(_codex_args(self.cwd, mode, self.started), stdin, self.cwd)
        return AiChatCommand(_claude_args(mode, self.session_id or str(uuid4())), stdin, self.cwd)
```

- [ ] **Step 4: Update existing stdin assertions**

In `tests/test_pet_ai_chat.py`, replace assertions that require exact stdin equality:

```python
assert command.stdin == "explain this repo"
```

with contains assertions:

```python
assert "explain this repo" in command.stdin
assert "music_actions" in command.stdin
```

Make the same change for other exact prompt assertions such as `"continue"` and `"hello"`.

- [ ] **Step 5: Run AI chat tests**

Run:

```bash
pytest tests/test_pet_ai_chat.py -q
```

Expected: PASS, all AI chat tests pass.

- [ ] **Step 6: Commit prompt contract work**

Run:

```bash
git add coding_with_beat/pet/ai_chat.py tests/test_pet_ai_chat.py
git commit -m "feat(pet): request structured dj actions from ai"
```

Expected: commit succeeds.

### Task 3: Unified DJ Timeline UI

**Files:**
- Modify: `coding_with_beat/pet/dj_panel.py`
- Modify: `tests/test_pet_dj_panel.py`

- [ ] **Step 1: Replace standalone AI panel tests with unified timeline tests**

In `tests/test_pet_dj_panel.py`, remove tests that assert `AiChatPanel`, `AiPromptInput`, `AiSendButton`, `AiStopButton`, `AiNewSessionButton`, and `AiClearButton` exist.

Add these tests:

```python
def test_dj_panel_uses_unified_ai_prompt_without_standalone_ai_panel():
    app = QApplication.instance() or QApplication([])
    panel = CodeBeatDjPanel(FakeHost())

    assert app is not None
    assert panel.findChild(QLineEdit, "DjPromptInput") is panel.prompt_input
    assert panel.findChild(QLabel, "AiChatTitle") is None
    assert panel.findChild(QPushButton, "AiSendButton") is None
    assert panel.findChild(QComboBox, "AiProviderSelect") is not None
    assert panel.findChild(QComboBox, "AiModeSelect") is not None


def test_dj_panel_ai_prompt_uses_main_timeline_and_runner():
    app = QApplication.instance() or QApplication([])
    panel = CodeBeatDjPanel(FakeHost())
    fake_runner = FakeAiRunner()
    panel.ai_runner = fake_runner

    panel.prompt_input.setText("推荐几首适合写代码的歌")
    panel.submit_prompt()

    assert app is not None
    assert fake_runner.sent == [("推荐几首适合写代码的歌", AiProvider.CODEX, AiPermissionMode.READ_ONLY)]
    assert "You: 推荐几首适合写代码的歌" in panel.transcript_text()
    assert panel.prompt_input.text() == ""


def test_dj_panel_ai_result_renders_playable_music_actions():
    app = QApplication.instance() or QApplication([])
    host = FakeHost()
    panel = CodeBeatDjPanel(host)

    panel.handle_ai_result(
        AiChatResult(
            True,
            '可以，先试试这个。\n```json\n{"music_actions":[{"kind":"play_track","query":"周杰伦 晴天","label":"晴天 - 周杰伦"}]}\n```',
        )
    )
    action_button = next(
        button for button in panel.findChildren(QPushButton) if button.objectName() == "MusicActionButton"
    )
    action_button.click()

    assert app is not None
    assert "Agent: 可以，先试试这个。" in panel.transcript_text()
    assert "music_actions" not in panel.transcript_text()
    assert action_button.text() == "▶ 晴天 - 周杰伦"
    assert host.pending[-1] == "正在处理音乐请求..."
    assert host.calls[-1].card.text == "handled:周杰伦 晴天"


def test_dj_panel_direct_local_command_from_main_prompt_skips_ai_runner():
    app = QApplication.instance() or QApplication([])
    host = FakeHost()
    panel = CodeBeatDjPanel(host)
    fake_runner = FakeAiRunner()
    panel.ai_runner = fake_runner

    panel.prompt_input.setText("下一首")
    panel.submit_prompt()

    assert app is not None
    assert fake_runner.sent == []
    assert host.music_session.music.controls == [("next_track", {})]
```

- [ ] **Step 2: Run unified panel tests to verify they fail**

Run:

```bash
pytest tests/test_pet_dj_panel.py::test_dj_panel_uses_unified_ai_prompt_without_standalone_ai_panel tests/test_pet_dj_panel.py::test_dj_panel_ai_prompt_uses_main_timeline_and_runner tests/test_pet_dj_panel.py::test_dj_panel_ai_result_renders_playable_music_actions tests/test_pet_dj_panel.py::test_dj_panel_direct_local_command_from_main_prompt_skips_ai_runner -q
```

Expected: FAIL because the panel still has a separate AI section and music prompts bypass AI.

- [ ] **Step 3: Import the action parser**

In `coding_with_beat/pet/dj_panel.py`, replace the AI import block:

```python
from .ai_chat import AiChatResult, AiChatRunner, AiPermissionMode, AiProvider
```

with:

```python
from .ai_actions import MusicAction, MusicActionKind, detect_local_command_action, parse_ai_music_reply
from .ai_chat import AiChatResult, AiChatRunner, AiPermissionMode, AiProvider
```

- [ ] **Step 4: Move provider and mode controls into the main input area**

In `CodeBeatDjPanel.__init__`, after `self.prompt_input.returnPressed.connect(self.submit_prompt)`, keep the existing `send_button` but change its text:

```python
        send_button = QPushButton("发送")
        send_button.setObjectName("ActionChip")
        send_button.clicked.connect(self.submit_prompt)
```

Create provider and mode selectors before `input_row`:

```python
        self.ai_provider_select = QComboBox()
        self.ai_provider_select.setObjectName("AiProviderSelect")
        self.ai_provider_select.addItem("Codex", AiProvider.CODEX)
        self.ai_provider_select.addItem("Claude", AiProvider.CLAUDE)
        self.ai_mode_select = QComboBox()
        self.ai_mode_select.setObjectName("AiModeSelect")
        self.ai_mode_select.addItem("Read only", AiPermissionMode.READ_ONLY)
        self.ai_mode_select.addItem("Write", AiPermissionMode.WORKSPACE_WRITE)
```

Update `input_row` to include these controls:

```python
        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.setSpacing(6)
        input_row.addWidget(self.ai_provider_select)
        input_row.addWidget(self.ai_mode_select)
        input_row.addWidget(self.prompt_input, 1)
        input_row.addWidget(send_button)
```

- [ ] **Step 5: Remove the standalone AI panel from layout**

In `CodeBeatDjPanel.__init__`, delete this line:

```python
        layout.addWidget(self._build_ai_chat_panel())
```

Delete the entire `_build_ai_chat_panel()` method.

Keep `stop_ai_chat()`, `new_ai_session()`, and `clear_ai_transcript()` only if they are still wired to compact controls in a later task. For this first pass, delete those methods and the `_append_ai_row()` method because the unified timeline uses `_append_text()`.

- [ ] **Step 6: Route the main prompt through local command detection or AI**

Replace `submit_prompt()` with:

```python
    def submit_prompt(self) -> None:
        text = self.prompt_input.text().strip()
        if not text:
            return
        self.prompt_input.clear()
        command_action = detect_local_command_action(text)
        if command_action is not None:
            self._execute_music_action(command_action)
            return
        self.submit_ai_prompt_text(text)
```

Add this method near `submit_prompt()`:

```python
    def submit_ai_prompt_text(self, text: str) -> None:
        provider = self.ai_provider_select.currentData() or AiProvider.CODEX
        mode = self.ai_mode_select.currentData() or AiPermissionMode.READ_ONLY
        self._append_text(f"You: {text}")
        accepted = self.ai_runner.send(text, provider, mode)
        if not accepted:
            self._append_text("Status: AI chat is already running or could not start.")
```

Delete `recommend_from_text()` only if it is no longer used by `submit_prompt()`. Keep button methods like `recommend_from_context()` unchanged.

- [ ] **Step 7: Render AI replies and action buttons into the main timeline**

Replace `handle_ai_result()` with:

```python
    def handle_ai_result(self, result: AiChatResult) -> None:
        if not result.ok:
            self._append_text(f"Error: {result.text}")
            return
        reply = parse_ai_music_reply(result.text)
        self._append_text(f"Agent: {reply.text or '(empty response)'}")
        for action in reply.actions:
            self._append_music_action(action)
```

Add these methods near `_append_result_item()`:

```python
    def _append_music_action(self, action: MusicAction) -> None:
        button = QPushButton(_music_action_button_text(action))
        button.setObjectName("MusicActionButton")
        button.clicked.connect(lambda _checked=False, selected=action: self._execute_music_action(selected))
        self._insert_widget(button)
        self._transcript.append(button.text())

    def _execute_music_action(self, action: MusicAction) -> None:
        if action.kind in {MusicActionKind.PLAY_TRACK, MusicActionKind.SEARCH_MUSIC, MusicActionKind.PLAYLIST}:
            self._run(lambda: self.host.music_session.handle_prompt(action.query), "正在处理音乐请求...")
            return
        if action.kind == MusicActionKind.PLAY_NUMBER:
            self._play_number(int(action.query))
            return
        if action.kind == MusicActionKind.CONTROL:
            self._execute_control_action(action.query)

    def _execute_control_action(self, query: str) -> None:
        if query.startswith("set_volume:"):
            self._run_cwb_command("set_volume", {"percent": int(query.split(":", 1)[1])})
            return
        self._run_cwb_command(query, {})
```

Add this helper near `_mmss()`:

```python
def _music_action_button_text(action: MusicAction) -> str:
    if action.kind == MusicActionKind.CONTROL:
        return f"⚡ {action.label}"
    if action.kind == MusicActionKind.SEARCH_MUSIC:
        return f"🔍 {action.label}"
    return f"▶ {action.label}"
```

- [ ] **Step 8: Run unified panel tests**

Run:

```bash
pytest tests/test_pet_dj_panel.py::test_dj_panel_uses_unified_ai_prompt_without_standalone_ai_panel tests/test_pet_dj_panel.py::test_dj_panel_ai_prompt_uses_main_timeline_and_runner tests/test_pet_dj_panel.py::test_dj_panel_ai_result_renders_playable_music_actions tests/test_pet_dj_panel.py::test_dj_panel_direct_local_command_from_main_prompt_skips_ai_runner -q
```

Expected: PASS, the new unified timeline tests pass.

- [ ] **Step 9: Run all DJ panel tests and fix old assumptions**

Run:

```bash
pytest tests/test_pet_dj_panel.py -q
```

Expected: PASS. If old tests still expect plain text prompts like `周杰伦` to call `handle_prompt()` directly, update those tests to assert the AI-first behavior instead:

```python
def test_dj_panel_plain_artist_prompt_goes_to_ai_first():
    app = QApplication.instance() or QApplication([])
    panel = CodeBeatDjPanel(FakeHost())
    fake_runner = FakeAiRunner()
    panel.ai_runner = fake_runner

    panel.prompt_input.setText("周杰伦")
    panel.submit_prompt()

    assert app is not None
    assert fake_runner.sent == [("周杰伦", AiProvider.CODEX, AiPermissionMode.READ_ONLY)]
```

- [ ] **Step 10: Commit unified panel work**

Run:

```bash
git add coding_with_beat/pet/dj_panel.py tests/test_pet_dj_panel.py
git commit -m "feat(pet): unify ai chat and dj action timeline"
```

Expected: commit succeeds.

### Task 4: Verification and Documentation Touch-Up

**Files:**
- Modify: `README.md`
- Modify: `README_CN.md`

- [ ] **Step 1: Update English desktop pet documentation**

In `README.md`, replace the desktop pet paragraph that describes the DJ prompt as only a music command box with:

```markdown
- The DJ prompt is now an AI-first conversation box. Ask the DJ to explain, recommend, or help choose music; when the AI reply includes songs, moods, playlists, or playback controls, the panel turns them into one-click playable actions. Fast commands such as `/next`, `/pause`, `/volume 70`, `下一首`, and `喜欢这首` still execute immediately.
```

- [ ] **Step 2: Update Chinese desktop pet documentation**

In `README_CN.md`, add or replace the matching desktop pet bullet with:

```markdown
- DJ 输入框现在是 AI 优先的对话框。你可以让 DJ 解释、推荐、帮你挑歌；当 AI 回复里出现歌曲、风格、歌单或播放控制时，面板会把它们变成可一键播放/搜索/控制的动作。`/next`、`/pause`、`/volume 70`、`下一首`、`喜欢这首` 这类快速命令仍然会立即执行。
```

- [ ] **Step 3: Run focused tests**

Run:

```bash
pytest tests/test_pet_ai_actions.py tests/test_pet_ai_chat.py tests/test_pet_dj_panel.py -q
```

Expected: PASS, all focused tests pass.

- [ ] **Step 4: Run style checks**

Run:

```bash
ruff check coding_with_beat/pet/ai_actions.py coding_with_beat/pet/ai_chat.py coding_with_beat/pet/dj_panel.py tests/test_pet_ai_actions.py tests/test_pet_ai_chat.py tests/test_pet_dj_panel.py
```

Expected: PASS, no lint errors.

- [ ] **Step 5: Run pre-existing broader pet tests**

Run:

```bash
pytest tests/test_pet_ai_actions.py tests/test_pet_ai_chat.py tests/test_pet_dj_panel.py tests/test_pet_window_actions.py tests/test_pet_session.py -q
```

Expected: PASS. These cover the new action parser plus nearby pet music session and window behavior.

- [ ] **Step 6: Commit docs and verification fixes**

Run:

```bash
git add README.md README_CN.md
git commit -m "docs(pet): describe ai-first dj actions"
```

Expected: commit succeeds.

## Plan Self-Review

- Spec coverage: parser, structured `music_actions`, fallback parsing, local command priority, AI prompt wrapping, unified prompt/timeline, one-click action routing, provider behavior preservation, error handling, and focused tests are all covered.
- Placeholder scan: no TBD/TODO/fill-in steps are present.
- Type consistency: `MusicAction`, `MusicActionKind`, `AiVisibleReply`, `parse_ai_music_reply()`, and `detect_local_command_action()` are introduced in Task 1 before later tasks use them.
