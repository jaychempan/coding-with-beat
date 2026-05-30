from unittest import mock

from coding_with_beat import app
from coding_with_beat.app_settings import AppSettings, PetAppSettings, ServiceSettings


def test_codebeat_app_keeps_dock_icon_visible():
    settings = AppSettings(
        pet=PetAppSettings(slug="codebeat-buddy", show_dock_icon=True, show_menu_bar_icon=True),
        service=ServiceSettings(start_on_launch=False),
    )
    with (
        mock.patch("coding_with_beat.app.load_app_settings", return_value=settings),
        mock.patch("coding_with_beat.app.save_app_settings") as save_settings,
        mock.patch("coding_with_beat.app.mirror_mcp_url") as mirror_mcp_url,
        mock.patch("coding_with_beat.app.run_pet_app", return_value=0) as run_pet_app,
    ):
        assert app.run() == 0

    save_settings.assert_called_once()
    mirror_mcp_url.assert_called_once_with(settings, mock.ANY)
    run_pet_app.assert_called_once_with(
        petdex_slug="codebeat-buddy",
        hide_dock=False,
        show_control=False,
        show_menu_bar=True,
    )


def test_codebeat_app_defaults_to_codebeat_buddy_when_saved_pet_is_empty():
    settings = AppSettings(
        pet=PetAppSettings(slug="", show_dock_icon=True, show_menu_bar_icon=True),
        service=ServiceSettings(start_on_launch=False),
    )
    with (
        mock.patch("coding_with_beat.app.load_app_settings", return_value=settings),
        mock.patch("coding_with_beat.app.save_app_settings"),
        mock.patch("coding_with_beat.app.mirror_mcp_url"),
        mock.patch("coding_with_beat.app.run_pet_app", return_value=0) as run_pet_app,
    ):
        assert app.run() == 0

    run_pet_app.assert_called_once_with(
        petdex_slug="codebeat-buddy",
        hide_dock=False,
        show_control=False,
        show_menu_bar=True,
    )


def test_codebeat_app_uses_saved_chrome_visibility():
    settings = AppSettings(
        pet=PetAppSettings(slug="codebeat-buddy", show_dock_icon=False, show_menu_bar_icon=False),
        service=ServiceSettings(start_on_launch=False),
    )
    with (
        mock.patch("coding_with_beat.app.load_app_settings", return_value=settings),
        mock.patch("coding_with_beat.app.save_app_settings"),
        mock.patch("coding_with_beat.app.mirror_mcp_url"),
        mock.patch("coding_with_beat.app.run_pet_app", return_value=0) as run_pet_app,
    ):
        assert app.run() == 0

    run_pet_app.assert_called_once_with(
        petdex_slug="codebeat-buddy",
        hide_dock=True,
        show_control=False,
        show_menu_bar=False,
    )


def test_codebeat_app_starts_service_when_enabled():
    settings = AppSettings(service=ServiceSettings(mcp_url="http://127.0.0.1:8765/mcp", start_on_launch=True))
    manager = mock.Mock()

    with (
        mock.patch("coding_with_beat.app.load_app_settings", return_value=settings),
        mock.patch("coding_with_beat.app.save_app_settings"),
        mock.patch("coding_with_beat.app.mirror_mcp_url"),
        mock.patch("coding_with_beat.app.ServiceManager", return_value=manager) as service_manager,
        mock.patch("coding_with_beat.app.run_pet_app", return_value=0),
    ):
        assert app.run() == 0

    service_manager.assert_called_once_with(paths=mock.ANY, mcp_url="http://127.0.0.1:8765/mcp")
    manager.start.assert_called_once_with()


def test_codebeat_app_does_not_start_service_when_disabled():
    settings = AppSettings(service=ServiceSettings(start_on_launch=False))

    with (
        mock.patch("coding_with_beat.app.load_app_settings", return_value=settings),
        mock.patch("coding_with_beat.app.save_app_settings"),
        mock.patch("coding_with_beat.app.mirror_mcp_url"),
        mock.patch("coding_with_beat.app.ServiceManager") as service_manager,
        mock.patch("coding_with_beat.app.run_pet_app", return_value=0),
    ):
        assert app.run() == 0

    service_manager.assert_not_called()
