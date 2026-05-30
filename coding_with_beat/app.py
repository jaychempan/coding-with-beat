"""CodeBeat macOS app control-center entrypoint."""

from __future__ import annotations

from .app_paths import CodeBeatPaths
from .app_settings import load_settings as load_app_settings
from .app_settings import mirror_mcp_url
from .app_settings import save_settings as save_app_settings
from .mcp_client import call_tool
from .pet.app import run as run_pet_app
from .pet.petdex import default_petdex_slug
from .service_manager import ServiceManager


def _service_reachable(url: str) -> bool:
    try:
        call_tool("status", url=url, timeout=1.0)
    except Exception:
        return False
    return True


def run() -> int:
    paths = CodeBeatPaths.default()
    paths.ensure()

    settings = load_app_settings(paths)
    save_app_settings(settings, paths)
    mirror_mcp_url(settings, paths)

    if settings.service.start_on_launch and not _service_reachable(settings.service.mcp_url):
        ServiceManager(paths=paths, mcp_url=settings.service.mcp_url).start()

    petdex_slug = default_petdex_slug(settings.pet.slug)
    return run_pet_app(
        petdex_slug=petdex_slug,
        hide_dock=not settings.pet.show_dock_icon,
        show_control=False,
        show_menu_bar=settings.pet.show_menu_bar_icon,
    )
