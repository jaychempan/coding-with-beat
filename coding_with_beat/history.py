# coding_with_beat/history.py
"""Play history: write (non-AM sources) and analyse (all sources)."""
from __future__ import annotations

import datetime
from collections import Counter

from .config import DATA_DIR, ensure_dirs

_LOG_FILE = DATA_DIR / "history.log"

_STYLE_KEYWORDS: dict[str, list[str]] = {
    "lofi": ["lofi", "lo-fi", "chillhop"],
    "jazz": ["jazz", "bossa", "blues", "swing"],
    "classical": ["classical", "piano", "nocturne", "symphony",
                  "beethoven", "mozart", "bach", "chopin", "satie"],
    "ambient": ["ambient", "drone"],
    "electronic": ["electronic", "电子", "synth", "edm"],
    "华语": ["华语", "国语", "粤语", "中文"],
    "民谣": ["民谣", "folk", "acoustic"],
    "synthwave": ["synthwave", "retrowave", "outrun"],
    "rnb": ["r&b", "rnb", "soul", "funk"],
    "hip-hop": ["hip hop", "hip-hop", "rap", "trap"],
}


def write(title: str, artist: str, album: str) -> None:
    """Append one play record to history.log (non-Apple Music sources only)."""
    if not title:
        return
    ensure_dirs()
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"{ts} | {title} | {artist or '?'} | {album or '?'}\n"
    try:
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def read(limit: int = 100) -> list[dict]:
    """Read the most recent `limit` entries from history.log, most-recent first.
    Each entry: {title, artist, album, ts (datetime)}."""
    try:
        lines = _LOG_FILE.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    result: list[dict] = []
    for line in reversed(lines):
        parts = line.split(" | ", 3)
        if len(parts) < 4:
            continue
        ts_str, title, artist, album = parts
        try:
            ts = datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        result.append({"title": title, "artist": artist, "album": album, "ts": ts})
        if len(result) >= limit:
            break
    return result


def summarize(tracks: list[dict], window_days: int = 14) -> dict:
    """Analyse a flat list of track dicts.

    Each dict must have 'title', 'artist', 'album', and a 'ts' key
    (datetime object). Apple Music dicts from play_history() also work
    because play_history() stores a datetime in 'ts'.

    Returns:
        top_artists: list of (artist, count) sorted by frequency, recent window only
        style_tags: list of style tag strings matched from album/artist text
        unheard_candidates: tracks whose artist hasn't appeared in the recent window
    """
    cutoff = datetime.datetime.now() - datetime.timedelta(days=window_days)

    recent: list[dict] = []
    older: list[dict] = []
    for t in tracks:
        ts = t.get("ts")
        if isinstance(ts, str):
            try:
                ts = datetime.datetime.strptime(ts[:19], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                ts = None
        if ts is None or ts >= cutoff:
            recent.append(t)
        else:
            older.append(t)

    # top artists (recent window)
    artist_counter: Counter = Counter()
    for t in recent:
        a = (t.get("artist") or "").strip()
        if a and a != "?":
            artist_counter[a] += 1
    top_artists = artist_counter.most_common(5)

    # style tags (keyword scan on album + artist of recent tracks)
    tag_counter: Counter = Counter()
    for t in recent:
        text = f"{t.get('artist', '')} {t.get('album', '')}".lower()
        for tag, keywords in _STYLE_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                tag_counter[tag] += 1
    style_tags = [tag for tag, _ in tag_counter.most_common(3)]

    # unheard candidates: artists in older not seen in recent, deduplicated by artist
    recent_artists_lower = {(t.get("artist") or "").strip().lower() for t in recent}
    recent_titles_lower = {(t.get("title") or "").strip().lower() for t in recent}
    seen_unheard: set[str] = set()
    unheard_candidates: list[dict] = []
    for t in older:
        a_lower = (t.get("artist") or "").strip().lower()
        title_lower = (t.get("title") or "").strip().lower()
        if a_lower in recent_artists_lower:
            continue
        if title_lower in recent_titles_lower:
            continue
        if a_lower in seen_unheard:
            continue
        seen_unheard.add(a_lower)
        unheard_candidates.append(t)
        if len(unheard_candidates) >= 5:
            break

    return {
        "top_artists": top_artists,
        "style_tags": style_tags,
        "unheard_candidates": unheard_candidates,
    }
