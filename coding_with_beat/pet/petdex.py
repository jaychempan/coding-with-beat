"""Petdex-compatible spritesheet loading.

Petdex pets are not bundled with coding-with-beat. This module downloads a
user-selected public pet to the local cache and renders it from there.
"""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from coding_with_beat.config import DATA_DIR, ensure_dirs

MANIFEST_URL = "https://petdex.crafter.run/api/manifest"
PETDEX_CACHE_DIR = DATA_DIR / "petdex"
USER_AGENT = "coding-with-beat-pet/1.0"
PETDEX_ACTION_ROWS = {
    "idle": 0,
    "recommend": 1,
    "walk": 2,
    "dance": 2,
    "sad": 3,
    "panic": 3,
    "think": 4,
    "happy": 5,
    "sleep": 7,
}
FRAME_COLUMNS = 9
FRAME_ROWS = 8


@dataclass(frozen=True)
class PetdexPet:
    slug: str
    name: str
    folder: Path
    spritesheet_path: Path


@dataclass
class PetdexAnimator:
    action: str = "idle"
    frame_index: int = 0

    def set_action(self, action: str) -> None:
        next_action = action if action in PETDEX_ACTION_ROWS else "idle"
        if next_action != self.action:
            self.action = next_action
            self.frame_index = 0

    def tick(self) -> tuple[int, int]:
        self.frame_index = (self.frame_index + 1) % FRAME_COLUMNS
        return self.current_cell()

    def current_cell(self) -> tuple[int, int]:
        return PETDEX_ACTION_ROWS.get(self.action, 0), self.frame_index % FRAME_COLUMNS


def ensure_petdex_pet(slug: str, cache_dir: Path = PETDEX_CACHE_DIR) -> PetdexPet:
    """Download and cache a public Petdex pet by slug."""
    normalized = slug.strip().lower()
    if not normalized:
        raise ValueError("Petdex slug is required")
    manifest = _json_get(MANIFEST_URL)
    pets = manifest.get("pets") or []
    entry = next((pet for pet in pets if pet.get("slug") == normalized), None)
    if entry is None:
        raise ValueError(f"Petdex pet not found: {slug}")

    folder = cache_dir / normalized
    folder.mkdir(parents=True, exist_ok=True)
    pet_json_path = folder / "pet.json"
    spritesheet_source = folder / "spritesheet.webp"
    pet_json = _json_get(entry["petJsonUrl"])
    pet_json_path.write_text(json.dumps(pet_json, ensure_ascii=False, indent=2), encoding="utf-8")
    _download(entry["spritesheetUrl"], spritesheet_source)
    spritesheet_path = _convert_to_png(spritesheet_source)
    return PetdexPet(
        slug=normalized,
        name=pet_json.get("displayName") or entry.get("displayName") or normalized,
        folder=folder,
        spritesheet_path=spritesheet_path,
    )


def resolve_spritesheet_path(pet: PetdexPet) -> Path:
    converted = pet.folder / "spritesheet.png"
    if converted.exists():
        return converted
    return pet.spritesheet_path


def _json_get(url: str) -> dict:
    raw = _bytes_get(url)
    return json.loads(raw.decode("utf-8"))


def _download(url: str, path: Path) -> None:
    raw = _bytes_get(url)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(raw)
    os.replace(tmp, path)


def _bytes_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()


def _convert_to_png(path: Path) -> Path:
    target = path.with_suffix(".png")
    with Image.open(path) as image:
        image.save(target)
    return target


def petdex_cache_dir() -> Path:
    ensure_dirs()
    PETDEX_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return PETDEX_CACHE_DIR
