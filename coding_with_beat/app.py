"""CodeBeat macOS app control-center entrypoint."""

from __future__ import annotations

from .pet.app import run as run_pet_app
from .pet.petdex import default_petdex_slug
from .pet.settings import load_settings


def run() -> int:
    settings = load_settings()
    petdex_slug = default_petdex_slug(settings.petdex_slug)
    return run_pet_app(
        petdex_slug=petdex_slug,
        hide_dock=not settings.show_dock_icon,
        show_control=False,
        show_menu_bar=settings.show_menu_bar_icon,
    )
