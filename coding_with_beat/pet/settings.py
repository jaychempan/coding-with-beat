"""Persistent settings for the desktop pet."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from coding_with_beat.config import DATA_DIR, ensure_dirs

SETTINGS_FILE = DATA_DIR / "pet.json"


@dataclass
class PetSettings:
    x: int = 80
    y: int = 120
    skin_id: str = "dj"
    petdex_slug: str = "codebeat-buddy"
    scale: int = 5
    show_menu_bar_icon: bool = True
    show_dock_icon: bool = True


def load_settings(path: Path = SETTINGS_FILE) -> PetSettings:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        return PetSettings()
    except json.JSONDecodeError:
        return PetSettings()
    names = {field.name for field in fields(PetSettings)}
    values = {key: value for key, value in raw.items() if key in names}
    return PetSettings(**values)


def save_settings(settings: PetSettings, path: Path = SETTINGS_FILE) -> None:
    if path == SETTINGS_FILE:
        ensure_dirs()
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(settings), ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)
