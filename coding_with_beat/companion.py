"""Companion mode: proactive check-ins and context-aware music suggestions."""

from __future__ import annotations

import random
import time
from datetime import datetime as _dt
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .state import JukeboxState

COOLDOWN_SECS = 900
FAILURE_THRESHOLD = 3
IDLE_TOOLS_THRESHOLD = 20
MIN_SESSION_SECS = 300

MESSAGES: dict[str, list[str]] = {
    "session_start_morning": [
        "早！今天想专注什么？我先挑首暖场的",
        "早安——先把节奏拉起来？",
        "新的一天，来首有劲的开场",
    ],
    "session_start_evening": [
        "又到深夜了——来首 lofi 陪你",
        "晚上好，今天还要鏖战？给你挑首夜间编程的",
        "深夜模式启动——来点节奏感的",
    ],
    "debug_struggle": [
        "调了挺久了，先歇口气——换首轻松的？",
        "bug 有点难缠。先让耳朵放个假？",
        "连续在 debug……先听首舒缓的，思路说不定就来了",
    ],
    "victory": [
        "✓ 成了！该庆祝一下",
        "搞定了！来首应景的庆功曲",
        "测试全绿，今天不错——来点带劲的",
    ],
    "idle_checkin": [
        "你还好吧？忙了一阵了——音乐还合适吗",
        "一直在专注——要不要换个曲风换换脑子？",
        "工作了好一会儿了，我给你找首新的？",
    ],
    "session_end": [
        "收工了，辛苦了——来首舒缓的慢慢降落",
        "今天到这里了，来首放松的结个尾",
        "下班！来首解压的——你赢得了它",
    ],
}

QUERIES: dict[str, list[str]] = {
    "session_start_morning": [
        "morning fresh indie pop upbeat",
        "coffee acoustic gentle start of day",
        "morning motivation energy focus",
    ],
    "session_start_evening": [
        "lofi late night coding chill",
        "night session ambient focus instrumental",
        "synthwave night drive electronic",
    ],
    "debug_struggle": [
        "calm piano breathe relax stress relief",
        "lofi chill gentle decompress",
        "acoustic soft peaceful unwind",
    ],
    "victory": [
        "celebration feel good indie pop",
        "victory upbeat dance energetic",
        "achievement summer bright positive",
    ],
    "idle_checkin": [
        "background lofi focus no distraction",
        "ambient flow state instrumental",
        "study chill rain cafe cozy",
    ],
    "session_end": [
        "wind down gentle piano evening",
        "soft acoustic relax unwind peaceful",
        "end of day calm slow",
    ],
}


def _trigger_key(trigger: str) -> str:
    if trigger == "session_start":
        return "session_start_morning" if 6 <= _dt.now().hour < 18 else "session_start_evening"
    return trigger


def can_trigger(st: "JukeboxState", trigger: str) -> bool:
    now = time.time()
    if now - st.companion_last_at < COOLDOWN_SECS:
        return False
    if trigger == "debug_struggle":
        return st.companion_failure_streak >= FAILURE_THRESHOLD
    if trigger == "idle_checkin":
        return st.companion_tool_count >= IDLE_TOOLS_THRESHOLD
    if trigger == "session_end":
        return (now - st.companion_session_start) >= MIN_SESSION_SECS
    return True


def get_message(trigger: str) -> str:
    key = _trigger_key(trigger)
    pool = MESSAGES.get(key, MESSAGES["idle_checkin"])
    return random.choice(pool)


def get_queries(trigger: str) -> list[str]:
    key = _trigger_key(trigger)
    return QUERIES.get(key, QUERIES["idle_checkin"])
