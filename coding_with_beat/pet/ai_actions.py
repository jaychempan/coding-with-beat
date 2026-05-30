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
_CHINESE_TRACK_RE = re.compile(
    r"(?:^\s*\d+[.)、]?\s*)?《([^》]+)》\s*[-—–]\s*([^\n,.;:，。；：]+?)(?=\s+is\b|很|适合|可以|能|是|[\n,.;:，。；：]|$)",
    re.MULTILINE,
)
_ENGLISH_BY_RE = re.compile(
    r"(?:^\s*\d+[.)]?\s*)?([A-Z][^\n]+?)\s+by\s+([A-Z][^\n,.;:，。；：]+?)(?=\s+(?:is|for|while|when|to|if|because)\b|[\n,.;:，。；：]|$)",
    re.MULTILINE,
)


def parse_ai_music_reply(raw: str) -> AiVisibleReply:
    text = (raw or "").strip()
    actions: list[MusicAction] = []
    visible = text
    has_structured_music_actions = False

    for match in _JSON_BLOCK_RE.finditer(text):
        has_music_actions, parsed = _actions_from_json(match.group(1))
        if has_music_actions:
            has_structured_music_actions = True
            visible = visible.replace(match.group(0), "").strip()
        if parsed:
            actions.extend(parsed)

    if not actions and not has_structured_music_actions:
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
    volume = re.match(r"^/?(?:volume|音量)\s+(-?\d+)$", lower)
    if volume:
        percent = max(0, min(100, int(volume.group(1))))
        return MusicAction(MusicActionKind.CONTROL, f"音量 {percent}", f"set_volume:{percent}")
    return None


def _actions_from_json(raw_json: str) -> tuple[bool, list[MusicAction]]:
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        return False, []
    values = data.get("music_actions") if isinstance(data, dict) else None
    if not isinstance(values, list):
        return False, []
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
    return True, actions


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
