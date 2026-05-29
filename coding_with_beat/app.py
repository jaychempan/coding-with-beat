"""CodeBeat macOS app control-center entrypoint."""

from __future__ import annotations

from .pet.app import run as run_pet_app
from .pet.settings import load_settings


def run() -> int:
    petdex_slug = load_settings().petdex_slug or "boba"
    return run_pet_app(petdex_slug=petdex_slug, hide_dock=False, show_control=False)
