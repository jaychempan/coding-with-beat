from .base import MusicSource, NowPlaying
from .apple_music import AppleMusic
from .local import LocalFiles
from .qq_music import QQMusic


def get_source(name: str) -> MusicSource:
    name = (name or "apple_music").lower()
    if name in ("apple", "apple_music", "applemusic", "am"):
        return AppleMusic()
    if name in ("local", "files"):
        return LocalFiles()
    if name in ("qq", "qq_music", "qqmusic"):
        return QQMusic()
    raise ValueError(f"unknown source: {name}")


__all__ = ["MusicSource", "NowPlaying", "get_source", "AppleMusic", "LocalFiles", "QQMusic"]
