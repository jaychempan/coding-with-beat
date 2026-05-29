from unittest import mock

from coding_with_beat import app


def test_codebeat_app_keeps_dock_icon_visible():
    with mock.patch("coding_with_beat.app.run_pet_app", return_value=0) as run_pet_app:
        assert app.run() == 0

    run_pet_app.assert_called_once_with(petdex_slug=None, hide_dock=False, show_control=True)
