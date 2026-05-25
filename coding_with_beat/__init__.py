"""Coding With Beat: a pixel-art music companion for Claude Code."""

try:
    from importlib.metadata import version as _version

    __version__ = _version("coding-with-beat")
except Exception:
    __version__ = "0.3.7"
