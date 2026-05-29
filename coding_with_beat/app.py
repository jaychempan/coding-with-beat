"""CodeBeat macOS app control-center entrypoint."""

from __future__ import annotations

from .pet.app import run as run_pet_app


def run() -> int:
    return run_pet_app(petdex_slug=None, hide_dock=True)
