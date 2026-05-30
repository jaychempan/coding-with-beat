"""App-level settings for CodeBeat.app."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from .app_paths import CodeBeatPaths
from .mcp_client import DEFAULT_MCP_URL


@dataclass
class PetAppSettings:
    slug: str = "codebeat-buddy"
    show_dock_icon: bool = True
    show_menu_bar_icon: bool = True


@dataclass
class ServiceSettings:
    mcp_url: str = DEFAULT_MCP_URL
    start_on_launch: bool = True
    restart_on_crash: bool = True


@dataclass
class IntegrationSettings:
    enabled: bool = False


@dataclass
class AppSettings:
    version: int = 1
    source: str = "apple_music"
    pet: PetAppSettings = field(default_factory=PetAppSettings)
    service: ServiceSettings = field(default_factory=ServiceSettings)
    integrations: dict[str, IntegrationSettings] = field(
        default_factory=lambda: {
            "claude": IntegrationSettings(),
            "codex": IntegrationSettings(),
        }
    )


def load_settings(paths: CodeBeatPaths | None = None) -> AppSettings:
    paths = paths or CodeBeatPaths.default()
    raw = _read_json(paths.settings_file)
    if isinstance(raw, dict):
        return _settings_from_json(raw)
    return _settings_from_legacy(paths)


def save_settings(settings: AppSettings, paths: CodeBeatPaths | None = None) -> None:
    paths = paths or CodeBeatPaths.default()
    paths.ensure()
    tmp = paths.settings_file.with_suffix(".tmp")
    tmp.write_text(json.dumps(_settings_to_json(settings), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, paths.settings_file)


def mirror_mcp_url(settings: AppSettings, paths: CodeBeatPaths | None = None) -> None:
    paths = paths or CodeBeatPaths.default()
    paths.legacy_data_dir.mkdir(parents=True, exist_ok=True)
    tmp = paths.legacy_mcp_url_file.with_suffix(".tmp")
    tmp.write_text(settings.service.mcp_url + "\n", encoding="utf-8")
    os.replace(tmp, paths.legacy_mcp_url_file)


def _settings_from_legacy(paths: CodeBeatPaths) -> AppSettings:
    settings = AppSettings()
    pet_raw = _read_json(paths.legacy_pet_settings_file)
    if isinstance(pet_raw, dict):
        settings.pet.slug = str(pet_raw.get("petdex_slug") or settings.pet.slug)
        settings.pet.show_dock_icon = bool(pet_raw.get("show_dock_icon", settings.pet.show_dock_icon))
        settings.pet.show_menu_bar_icon = bool(pet_raw.get("show_menu_bar_icon", settings.pet.show_menu_bar_icon))
    try:
        legacy_url = paths.legacy_mcp_url_file.read_text(encoding="utf-8").strip()
    except OSError:
        legacy_url = ""
    if legacy_url:
        settings.service.mcp_url = legacy_url
    return settings


def _settings_from_json(raw: dict) -> AppSettings:
    pet = raw.get("pet") if isinstance(raw.get("pet"), dict) else {}
    service = raw.get("service") if isinstance(raw.get("service"), dict) else {}
    integrations_raw = raw.get("integrations") if isinstance(raw.get("integrations"), dict) else {}
    integrations = {
        "claude": _integration_from_json(integrations_raw.get("claude")),
        "codex": _integration_from_json(integrations_raw.get("codex")),
    }
    return AppSettings(
        version=_version_from_json(raw.get("version")),
        source=str(raw.get("source") or "apple_music"),
        pet=PetAppSettings(
            slug=str(pet.get("slug") or "codebeat-buddy"),
            show_dock_icon=bool(pet.get("showDockIcon", True)),
            show_menu_bar_icon=bool(pet.get("showMenuBarIcon", True)),
        ),
        service=ServiceSettings(
            mcp_url=str(service.get("mcpUrl") or DEFAULT_MCP_URL),
            start_on_launch=bool(service.get("startOnLaunch", True)),
            restart_on_crash=bool(service.get("restartOnCrash", True)),
        ),
        integrations=integrations,
    )


def _version_from_json(value: object) -> int:
    try:
        return int(value or 1)
    except (TypeError, ValueError):
        return 1


def _integration_from_json(value: object) -> IntegrationSettings:
    if not isinstance(value, dict):
        return IntegrationSettings()
    return IntegrationSettings(enabled=bool(value.get("enabled", False)))


def _settings_to_json(settings: AppSettings) -> dict:
    integrations = settings.integrations or {}
    return {
        "version": settings.version,
        "source": settings.source,
        "pet": {
            "slug": settings.pet.slug,
            "showDockIcon": settings.pet.show_dock_icon,
            "showMenuBarIcon": settings.pet.show_menu_bar_icon,
        },
        "service": {
            "mcpUrl": settings.service.mcp_url,
            "startOnLaunch": settings.service.start_on_launch,
            "restartOnCrash": settings.service.restart_on_crash,
        },
        "integrations": {
            "claude": {"enabled": integrations.get("claude", IntegrationSettings()).enabled},
            "codex": {"enabled": integrations.get("codex", IntegrationSettings()).enabled},
        },
    }


def _read_json(path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
