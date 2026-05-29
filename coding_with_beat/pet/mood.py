"""Map short mood prompts to smart_search query angles."""

from __future__ import annotations

_BUCKETS: tuple[tuple[tuple[str, ...], tuple[str, str, str]], ...] = (
    (
        ("顺利", "开心", "成功", "胜利", "搞定", "happy", "success", "win", "good"),
        (
            "victory feel good indie pop",
            "celebration upbeat bright positive",
            "happy dance pop fresh energy",
        ),
    ),
    (
        ("累", "疲惫", "解压", "放松", "tired", "relax", "unwind", "calm"),
        (
            "relaxing downtempo chill evening unwind",
            "soft acoustic gentle calm",
            "calm piano breathe stress relief",
        ),
    ),
    (
        ("难过", "伤感", "低落", "失落", "sad", "heartbreak", "melancholy"),
        (
            "melancholy emotional piano sad indie",
            "heartbreak slow ballad rainy",
            "sorrowful strings cinematic emotional",
        ),
    ),
    (
        ("专注", "心流", "写代码", "coding", "focus", "flow", "debug"),
        (
            "deep focus ambient instrumental no vocals",
            "flow state minimal electronic coding",
            "lofi hip hop late night coding chill",
        ),
    ),
    (
        ("睡", "困", "助眠", "晚安", "sleep", "insomnia", "white noise"),
        (
            "sleep music white noise ambient drone",
            "lullaby soft piano rain sleep calm",
            "meditation deep sleep binaural delta waves",
        ),
    ),
    (
        ("派对", "蹦迪", "party", "edm", "dance"),
        (
            "party dance pop upbeat celebratory",
            "edm festival club electronic banger",
            "latin pop reggaeton dance floor",
        ),
    ),
    (
        ("爵士", "咖啡", "jazz", "bossa", "cafe"),
        (
            "smooth jazz cafe background mellow",
            "jazz trio acoustic bossa nova guitar",
            "late night jazz piano bar cool relaxed",
        ),
    ),
    (
        ("赛博", "电子", "夜驾", "synthwave", "cyber", "neon"),
        (
            "synthwave retrowave night drive neon",
            "cyberpunk electronic dark ambient synth",
            "80s retro synth outrun vapor",
        ),
    ),
    (
        ("国风", "中国风", "华语", "民谣", "古风", "古琴", "chinese"),
        (
            "中国风 古风 古琴 传统乐器",
            "华语流行 国语歌 indie 民谣",
            "chinese traditional folk guzheng erhu instrumental",
        ),
    ),
)

_FALLBACK = (
    "background lofi focus no distraction",
    "ambient flow state instrumental",
    "study chill rain cafe cozy",
)


def queries_for_mood(text: str) -> list[str]:
    """Return three smart_search query angles for a short mood prompt."""
    normalized = (text or "").strip().lower()
    for keywords, queries in _BUCKETS:
        if any(keyword in normalized for keyword in keywords):
            return list(queries)
    return list(_FALLBACK)
