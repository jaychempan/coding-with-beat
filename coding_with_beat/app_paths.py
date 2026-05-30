"""Filesystem paths for the CodeBeat macOS app."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

APP_SUPPORT_NAME = "CodeBeat"
LEGACY_DATA_NAME = ".coding-with-beat"


@dataclass(frozen=True)
class CodeBeatPaths:
    support_dir: Path
    logs_dir: Path
    settings_file: Path
    service_file: Path
    integrations_file: Path
    legacy_data_dir: Path
    legacy_pet_settings_file: Path
    legacy_mcp_url_file: Path

    @classmethod
    def default(cls) -> "CodeBeatPaths":
        home = Path.home()
        support_dir = home / "Library" / "Application Support" / APP_SUPPORT_NAME
        logs_dir = home / "Library" / "Logs" / APP_SUPPORT_NAME
        legacy_data_dir = home / LEGACY_DATA_NAME
        return cls(
            support_dir=support_dir,
            logs_dir=logs_dir,
            settings_file=support_dir / "settings.json",
            service_file=support_dir / "service.json",
            integrations_file=support_dir / "integrations.json",
            legacy_data_dir=legacy_data_dir,
            legacy_pet_settings_file=legacy_data_dir / "pet.json",
            legacy_mcp_url_file=legacy_data_dir / "mcp-url",
        )

    def ensure(self) -> None:
        self.support_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
