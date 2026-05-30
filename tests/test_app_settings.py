import json

from coding_with_beat.app_paths import CodeBeatPaths
from coding_with_beat.app_settings import (
    AppSettings,
    IntegrationSettings,
    PetAppSettings,
    ServiceSettings,
    load_settings,
    mirror_mcp_url,
    save_settings,
)


def _paths(tmp_path):
    return CodeBeatPaths(
        support_dir=tmp_path / "support",
        logs_dir=tmp_path / "logs",
        settings_file=tmp_path / "support" / "settings.json",
        service_file=tmp_path / "support" / "service.json",
        integrations_file=tmp_path / "support" / "integrations.json",
        legacy_data_dir=tmp_path / "legacy",
        legacy_pet_settings_file=tmp_path / "legacy" / "pet.json",
        legacy_mcp_url_file=tmp_path / "legacy" / "mcp-url",
    )


def test_load_settings_returns_defaults_when_no_files_exist(tmp_path):
    settings = load_settings(_paths(tmp_path))

    assert settings.version == 1
    assert settings.source == "apple_music"
    assert settings.pet.slug == "codebeat-buddy"
    assert settings.pet.show_dock_icon is True
    assert settings.pet.show_menu_bar_icon is True
    assert settings.service.mcp_url == "http://127.0.0.1:8765/mcp"
    assert settings.service.start_on_launch is True
    assert settings.service.restart_on_crash is True
    assert settings.integrations["claude"].enabled is False
    assert settings.integrations["codex"].enabled is False


def test_load_settings_migrates_legacy_pet_and_mcp_url(tmp_path):
    paths = _paths(tmp_path)
    paths.legacy_data_dir.mkdir()
    paths.legacy_pet_settings_file.write_text(
        json.dumps(
            {
                "petdex_slug": "boba",
                "show_dock_icon": False,
                "show_menu_bar_icon": False,
            }
        ),
        encoding="utf-8",
    )
    paths.legacy_mcp_url_file.write_text("http://127.0.0.1:9876/mcp\n", encoding="utf-8")

    settings = load_settings(paths)

    assert settings.pet.slug == "boba"
    assert settings.pet.show_dock_icon is False
    assert settings.pet.show_menu_bar_icon is False
    assert settings.service.mcp_url == "http://127.0.0.1:9876/mcp"
    assert paths.legacy_pet_settings_file.exists()
    assert paths.legacy_mcp_url_file.exists()


def test_save_settings_writes_camel_case_json(tmp_path):
    paths = _paths(tmp_path)
    settings = AppSettings(
        version=1,
        source="local",
        pet=PetAppSettings(slug="codebeat-buddy", show_dock_icon=False, show_menu_bar_icon=True),
        service=ServiceSettings(
            mcp_url="http://127.0.0.1:9999/mcp",
            start_on_launch=False,
            restart_on_crash=True,
        ),
        integrations={
            "claude": IntegrationSettings(enabled=True),
            "codex": IntegrationSettings(enabled=False),
        },
    )

    save_settings(settings, paths)

    raw = json.loads(paths.settings_file.read_text(encoding="utf-8"))
    assert raw["version"] == 1
    assert raw["source"] == "local"
    assert raw["pet"]["slug"] == "codebeat-buddy"
    assert raw["pet"]["showDockIcon"] is False
    assert raw["service"]["mcpUrl"] == "http://127.0.0.1:9999/mcp"
    assert raw["service"]["startOnLaunch"] is False
    assert raw["integrations"]["claude"]["enabled"] is True


def test_mirror_mcp_url_writes_legacy_mcp_url(tmp_path):
    paths = _paths(tmp_path)
    settings = AppSettings(
        service=ServiceSettings(mcp_url="http://127.0.0.1:9999/mcp"),
    )

    mirror_mcp_url(settings, paths)

    assert paths.legacy_data_dir.is_dir()
    assert paths.legacy_mcp_url_file.read_text(encoding="utf-8") == "http://127.0.0.1:9999/mcp\n"


def test_load_settings_preserves_existing_app_settings_over_legacy(tmp_path):
    paths = _paths(tmp_path)
    paths.support_dir.mkdir()
    paths.settings_file.write_text(
        json.dumps(
            {
                "version": 1,
                "source": "qq_music",
                "pet": {
                    "slug": "codebeat-buddy",
                    "showDockIcon": True,
                    "showMenuBarIcon": False,
                },
                "service": {
                    "mcpUrl": "http://127.0.0.1:8765/mcp",
                    "startOnLaunch": False,
                    "restartOnCrash": False,
                },
                "integrations": {
                    "claude": {"enabled": True},
                    "codex": {"enabled": False},
                },
            }
        ),
        encoding="utf-8",
    )
    paths.legacy_data_dir.mkdir()
    paths.legacy_mcp_url_file.write_text("http://127.0.0.1:9876/mcp\n", encoding="utf-8")

    settings = load_settings(paths)

    assert settings.source == "qq_music"
    assert settings.service.mcp_url == "http://127.0.0.1:8765/mcp"
    assert settings.service.start_on_launch is False


def test_load_settings_defaults_malformed_integration_entries(tmp_path):
    paths = _paths(tmp_path)
    paths.support_dir.mkdir()
    paths.settings_file.write_text(
        json.dumps(
            {
                "integrations": {
                    "claude": True,
                    "codex": "enabled",
                },
            }
        ),
        encoding="utf-8",
    )

    settings = load_settings(paths)

    assert settings.integrations["claude"].enabled is False
    assert settings.integrations["codex"].enabled is False


def test_load_settings_defaults_malformed_version(tmp_path):
    paths = _paths(tmp_path)
    paths.support_dir.mkdir()
    paths.settings_file.write_text(json.dumps({"version": "bad"}), encoding="utf-8")

    settings = load_settings(paths)

    assert settings.version == 1


def test_load_settings_defaults_infinite_versions(tmp_path):
    for version in ("Infinity", "-Infinity"):
        paths = _paths(tmp_path / version)
        paths.support_dir.mkdir(parents=True)
        paths.settings_file.write_text(f'{{"version": {version}}}', encoding="utf-8")

        settings = load_settings(paths)

        assert settings.version == 1
