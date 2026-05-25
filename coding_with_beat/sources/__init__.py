from .apple_music import AppleMusic
from .base import MusicSource, NowPlaying
from .local import LocalFiles
from .qq_music import QQMusic

_CACHE: dict[str, MusicSource] = {}


def get_source(name: str) -> MusicSource:
    name = (name or "apple_music").strip().lower()
    if name in ("apple", "apple_music", "applemusic", "am", "苹果", "苹果音乐"):
        key = "apple_music"
        cls = AppleMusic
    elif name in ("local", "files", "本地", "本地文件"):
        key = "local"
        cls = LocalFiles
    elif name in ("qq", "qq_music", "qqmusic", "qq音乐"):
        key = "qq_music"
        cls = QQMusic
    else:
        raise ValueError(f"unknown source: {name}")
    if key not in _CACHE:
        _CACHE[key] = cls()
    return _CACHE[key]


__all__ = ["MusicSource", "NowPlaying", "get_source", "AppleMusic", "LocalFiles", "QQMusic"]
