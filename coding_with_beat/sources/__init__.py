from .apple_music import AppleMusic
from .base import MusicSource, NowPlaying
from .local import LocalFiles
from .qq_music import QQMusic


def get_source(name: str) -> MusicSource:
    name = (name or "apple_music").strip().lower()
    if name in ("apple", "apple_music", "applemusic", "am", "苹果", "苹果音乐"):
        return AppleMusic()
    if name in ("local", "files", "本地", "本地文件"):
        return LocalFiles()
    if name in ("qq", "qq_music", "qqmusic", "qq音乐"):
        return QQMusic()
    raise ValueError(f"unknown source: {name}")


__all__ = ["MusicSource", "NowPlaying", "get_source", "AppleMusic", "LocalFiles", "QQMusic"]
