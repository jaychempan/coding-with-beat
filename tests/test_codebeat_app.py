from unittest import mock

from coding_with_beat import app


def test_codebeat_app_keeps_dock_icon_visible():
    with (
        mock.patch("coding_with_beat.app.load_settings") as load_settings,
        mock.patch("coding_with_beat.app.run_pet_app", return_value=0) as run_pet_app,
    ):
        load_settings.return_value.petdex_slug = "codebeat-buddy"
        assert app.run() == 0

    run_pet_app.assert_called_once_with(petdex_slug="codebeat-buddy", hide_dock=False, show_control=False)


def test_codebeat_app_defaults_to_codebeat_buddy_when_saved_pet_is_empty():
    with (
        mock.patch("coding_with_beat.app.load_settings") as load_settings,
        mock.patch("coding_with_beat.app.run_pet_app", return_value=0) as run_pet_app,
    ):
        load_settings.return_value.petdex_slug = ""
        assert app.run() == 0

    run_pet_app.assert_called_once_with(petdex_slug="codebeat-buddy", hide_dock=False, show_control=False)
