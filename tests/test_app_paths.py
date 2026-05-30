from pathlib import Path
from unittest import mock

from coding_with_beat import app_paths


def test_app_paths_use_macos_application_locations():
    with mock.patch.object(app_paths.Path, "home", return_value=Path("/Users/alice")):
        paths = app_paths.CodeBeatPaths.default()

    assert paths.support_dir == Path("/Users/alice/Library/Application Support/CodeBeat")
    assert paths.logs_dir == Path("/Users/alice/Library/Logs/CodeBeat")
    assert paths.settings_file == paths.support_dir / "settings.json"
    assert paths.service_file == paths.support_dir / "service.json"
    assert paths.integrations_file == paths.support_dir / "integrations.json"
    assert paths.legacy_data_dir == Path("/Users/alice/.coding-with-beat")
    assert paths.legacy_mcp_url_file == Path("/Users/alice/.coding-with-beat/mcp-url")


def test_ensure_creates_app_owned_directories(tmp_path):
    paths = app_paths.CodeBeatPaths(
        support_dir=tmp_path / "support",
        logs_dir=tmp_path / "logs",
        settings_file=tmp_path / "support" / "settings.json",
        service_file=tmp_path / "support" / "service.json",
        integrations_file=tmp_path / "support" / "integrations.json",
        legacy_data_dir=tmp_path / "legacy",
        legacy_pet_settings_file=tmp_path / "legacy" / "pet.json",
        legacy_mcp_url_file=tmp_path / "legacy" / "mcp-url",
    )

    paths.ensure()

    assert paths.support_dir.is_dir()
    assert paths.logs_dir.is_dir()
