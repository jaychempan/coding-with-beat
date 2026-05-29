"""Session orchestration for desktop pet music recommendations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable

from coding_with_beat import state as state_mod

from .bubble import PetBubbleCard, PetBubbleView
from .dj_brain import DjIntent, DjQuerySet, PetDjBrain
from .music import MusicResult, PetMusicClient

_LIBRARY_TRIGGERS = (
    "从资料库找",
    "资料库里有没有",
    "资料库里找",
    "本地库里",
    "in my library",
    "library only",
    "from my library",
)
_LIBRARY_LIST_TRIGGERS = ("资料库", "打开资料库", "列出资料库", "library")
_LOVED_SEARCH_TRIGGERS = ("从喜欢里找", "收藏里找", "收藏里搜", "我喜欢的", "心动歌单", "search loved")
_LOVED_LIST_TRIGGERS = (
    "列出收藏",
    "我的喜欢",
    "我喜欢的",
    "心动歌单",
    "喜欢列表",
    "收藏列表",
    "list loved",
    "show liked",
)
_PLAYLIST_LIST_TRIGGERS = ("我的歌单", "有哪些歌单", "歌单列表", "list playlists", "show playlists")
_PLAYLIST_PLAY_TRIGGERS = ("播放歌单", "播歌单", "play playlist")
_MOOD_KEYWORDS = (
    "lofi",
    "低保真",
    "深夜",
    "写代码",
    "专注",
    "心流",
    "ambient",
    "无人声",
    "充能",
    "运动",
    "高能",
    "workout",
    "爵士",
    "jazz",
    "咖啡馆",
    "bossa",
    "赛博",
    "synthwave",
    "电子",
    "夜驾",
    "放松",
    "解压",
    "下班",
    "relax",
    "古典",
    "钢琴",
    "弦乐",
    "classical",
    "伤感",
    "失落",
    "难过",
    "sad",
    "派对",
    "party",
    "edm",
    "国风",
    "华语",
    "民谣",
    "古风",
    "助眠",
    "睡前",
    "sleep",
    "白噪音",
)


@dataclass(frozen=True)
class PetSessionResult:
    ok: bool
    action: str
    card: PetBubbleCard


class PetMusicSession:
    def __init__(
        self,
        music: PetMusicClient | None = None,
        brain: PetDjBrain | None = None,
        bubble: PetBubbleView | None = None,
        load_state: Callable[[], object] = state_mod.load,
    ) -> None:
        self.music = music if music is not None else PetMusicClient()
        self.brain = brain if brain is not None else PetDjBrain()
        self.bubble = bubble if bubble is not None else PetBubbleView()
        self.load_state = load_state
        self.current_intent: DjIntent | None = None
        self.current_query_set: DjQuerySet | None = None
        self.current_card: PetBubbleCard | None = None
        self.last_result: PetSessionResult | None = None
        self.reroll_count = 0

    def recommend_from_context(self) -> PetSessionResult:
        self.current_intent = self.brain.intent_from_state(self.load_state())
        self.reroll_count = 0
        return self._recommend_current()

    def recommend_from_text(self, text: str) -> PetSessionResult:
        st = self.load_state()
        self.current_intent = self.brain.intent_from_text(text, st)
        self.reroll_count = 0
        return self._recommend_current()

    def handle_prompt(self, text: str) -> PetSessionResult:
        query = text.strip()
        if not query:
            return PetSessionResult(False, "sad", self.bubble.error("音乐请求为空", "请输入歌手、歌名、歌单或心情。"))
        playlist_name = _extract_prefixed_query(query, _PLAYLIST_PLAY_TRIGGERS)
        if playlist_name:
            return self.play_playlist(playlist_name)
        library_query = _extract_prefixed_query(query, _LIBRARY_TRIGGERS)
        if library_query:
            return self.search_library(library_query)
        loved_query = _extract_prefixed_query(query, _LOVED_SEARCH_TRIGGERS)
        if loved_query:
            return self.search_loved(loved_query)
        if _matches_exact(query, _LIBRARY_LIST_TRIGGERS):
            return self.list_library()
        if _matches_exact(query, _LOVED_LIST_TRIGGERS):
            return self.list_loved()
        if _matches_exact(query, _PLAYLIST_LIST_TRIGGERS) or ("歌单" in query and len(query) <= 6):
            return self.list_playlists()
        if _looks_like_mood_request(query):
            return self.recommend_from_text(query)
        return self.search(query)

    def search(self, query: str) -> PetSessionResult:
        music_result = self.music.search(query)
        return self._results_from_music("搜索", query, music_result)

    def search_library(self, query: str) -> PetSessionResult:
        music_result = self.music.search(query)
        if not music_result.ok:
            card = self.bubble.error("资料库搜索失败", music_result.text)
            return self._remember(PetSessionResult(False, "sad", card))
        filtered = _filter_library_lines(music_result.text)
        card = self.bubble.results(
            f"资料库：{query}",
            "只显示资料库里的结果",
            filtered,
            empty_text="资料库里没找到，要不要搜一下线上？",
        )
        self.current_card = card
        return self._remember(PetSessionResult(bool(card.items), card.action, card))

    def list_library(self, limit: int = 40) -> PetSessionResult:
        music_result = self.music.list_library(limit)
        return self._results_from_music("资料库", "", music_result)

    def list_loved(self, limit: int = 40) -> PetSessionResult:
        music_result = self.music.list_loved(limit)
        return self._results_from_music("喜欢", "", music_result)

    def search_loved(self, query: str) -> PetSessionResult:
        music_result = self.music.search_loved(query)
        return self._results_from_music("喜欢", query, music_result)

    def list_playlists(self) -> PetSessionResult:
        music_result = self.music.list_playlists()
        return self._results_from_music("歌单", "", music_result)

    def play_playlist(self, name: str) -> PetSessionResult:
        music_result = self.music.play_playlist(name)
        if not _music_result_ok(music_result):
            card = self.bubble.error("歌单播放失败", music_result.text)
            return self._remember(PetSessionResult(False, "sad", card))
        card = self.bubble.confirmation("播放歌单", music_result.text, action="dance")
        return self._remember(PetSessionResult(True, "dance", card))

    def reroll(self) -> PetSessionResult:
        if self.current_intent is None:
            self.current_intent = self.brain.intent_from_state(self.load_state())
            self.reroll_count = 0
        else:
            self.reroll_count += 1
        return self._recommend_current()

    def play_number(self, number: int) -> PetSessionResult:
        music_result = self.music.play_number(number)
        if not _music_result_ok(music_result):
            card = self.bubble.error("播放失败", music_result.text)
            return self._remember(PetSessionResult(False, "sad", card))
        card = self.bubble.confirmation("已开播", music_result.text, action="dance")
        return self._remember(PetSessionResult(True, "dance", card))

    def auto_play_from_context(self) -> PetSessionResult:
        recommendation = self.recommend_from_context()
        if not recommendation.ok:
            return recommendation

        music_result = self.music.play_number(1)
        if not _music_result_ok(music_result):
            card = self.bubble.error("自动开播失败", music_result.text)
            return self._remember(PetSessionResult(False, "sad", card))

        title = self.current_intent.title if self.current_intent is not None else ""
        card = self.bubble.confirmation(f"已按 {title} 开播", music_result.text, action="dance")
        return self._remember(PetSessionResult(True, "dance", card))

    def now_playing(self) -> PetSessionResult:
        music_result = self.music.now_playing()
        if not _music_result_ok(music_result):
            card = self.bubble.error("当前播放读取失败", music_result.text)
            return self._remember(PetSessionResult(False, "sad", card))
        card = self.bubble.status("当前播放", music_result.text)
        return self._remember(PetSessionResult(True, card.action, card))

    def live_now_playing(self) -> PetSessionResult:
        music_result = self.music.now_playing_snapshot("")
        if not music_result.ok:
            return PetSessionResult(False, "idle", PetBubbleCard("live", "当前播放\n未播放", action="idle"))
        try:
            data = json.loads(music_result.text or "{}")
        except json.JSONDecodeError:
            return PetSessionResult(False, "idle", PetBubbleCard("live", "当前播放\n未播放", action="idle"))

        title = str(data.get("title") or "").strip()
        artist = str(data.get("artist") or "").strip()
        playing = bool(data.get("playing"))
        if not title and not artist:
            return PetSessionResult(False, "idle", PetBubbleCard("live", "当前播放\n未播放", action="idle"))

        marker = "▶" if playing else "▷"
        label = f"{title} — {artist}" if title and artist else title or artist
        action = "dance" if playing else "idle"
        return PetSessionResult(True, action, PetBubbleCard("live", f"当前播放\n{marker} {label}", action=action))

    def _recommend_current(self) -> PetSessionResult:
        if self.current_intent is None:
            self.current_intent = self.brain.intent_from_state(self.load_state())

        query_set = self.brain.queries_for_intent(self.current_intent, self.reroll_count)
        self.current_query_set = query_set
        music_result = self.music.recommend(query_set.queries)
        if not music_result.ok:
            card = self.bubble.error("推荐失败", music_result.text)
            return self._remember(PetSessionResult(False, "sad", card))

        card = self.bubble.recommendations(query_set.title, query_set.message, music_result.text)
        self.current_card = card
        if card.kind == "empty":
            return self._remember(PetSessionResult(False, card.action, card))
        return self._remember(PetSessionResult(True, card.action, card))

    def _results_from_music(self, title: str, query: str, music_result: MusicResult) -> PetSessionResult:
        label = f"{title}：{query}" if query else title
        if not music_result.ok:
            card = self.bubble.error(f"{title}失败", music_result.text)
            return self._remember(PetSessionResult(False, "sad", card))
        card = self.bubble.results(label, "点 ▶ 或输入编号播放", music_result.text)
        self.current_card = card
        return self._remember(PetSessionResult(bool(card.items), card.action, card))

    def _remember(self, result: PetSessionResult) -> PetSessionResult:
        self.last_result = result
        return result


def _music_result_ok(result: MusicResult) -> bool:
    if not result.ok:
        return False
    return not _textual_failure(result.text)


def _textual_failure(text: str) -> bool:
    clean = (text or "").strip().lower()
    return clean.startswith("(unsupported") or clean.startswith("(no match") or "full playback did not start" in clean


def _extract_prefixed_query(text: str, prefixes: tuple[str, ...]) -> str:
    clean = text.strip()
    lowered = clean.lower()
    for prefix in prefixes:
        lower_prefix = prefix.lower()
        if lowered.startswith(lower_prefix):
            return clean[len(prefix) :].strip(" ：:，,")
        if lower_prefix in lowered:
            before, _, after = clean.partition(prefix)
            if not before.strip():
                return after.strip(" ：:，,")
    return ""


def _matches_exact(text: str, triggers: tuple[str, ...]) -> bool:
    lowered = text.strip().lower()
    return any(lowered == trigger.lower() for trigger in triggers)


def _looks_like_mood_request(text: str) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in _MOOD_KEYWORDS)


def _filter_library_lines(text: str) -> str:
    lines = []
    for line in (text or "").splitlines():
        lowered = line.lower()
        if "[library]" in lowered or "[资料库]" in lowered:
            lines.append(line)
    return "\n".join(lines)
