from unittest import mock

from coding_with_beat.__main__ import COMMANDS, cmd_app, cmd_pet
from coding_with_beat.pet.settings import PetSettings


def test_pet_command_registered():
    assert COMMANDS["pet"] is cmd_pet


def test_app_command_registered():
    assert COMMANDS["app"] is cmd_app


def test_cmd_pet_prints_install_hint_when_pyside_missing(capsys):
    with mock.patch("coding_with_beat.pet.app.run", side_effect=RuntimeError("PySide6 is required")):
        rc = cmd_pet()
    assert rc == 1
    assert "pip install" in capsys.readouterr().err


def test_cmd_pet_defaults_to_curated_petdex_pet(monkeypatch):
    called = {}

    def fake_run(*, petdex_slug=None, hide_dock=True, show_control=False):
        called["petdex_slug"] = petdex_slug
        called["hide_dock"] = hide_dock
        return 0

    monkeypatch.setattr("sys.argv", ["cwb", "pet"])
    with mock.patch("coding_with_beat.pet.app.run", side_effect=fake_run):
        assert cmd_pet() == 0
    assert called["petdex_slug"] == "boba"
    assert called["hide_dock"] is True


def test_cmd_pet_uses_saved_petdex_pet(monkeypatch):
    called = {}

    def fake_run(*, petdex_slug=None, hide_dock=True, show_control=False):
        called["petdex_slug"] = petdex_slug
        called["hide_dock"] = hide_dock
        return 0

    monkeypatch.setattr("sys.argv", ["cwb", "pet"])
    with (
        mock.patch("coding_with_beat.pet.settings.load_settings", return_value=PetSettings(petdex_slug="mochi")),
        mock.patch("coding_with_beat.pet.app.run", side_effect=fake_run),
    ):
        assert cmd_pet() == 0
    assert called["petdex_slug"] == "mochi"
    assert called["hide_dock"] is True


def test_cmd_pet_passes_petdex_slug(monkeypatch):
    called = {}

    def fake_run(*, petdex_slug=None, hide_dock=True, show_control=False):
        called["petdex_slug"] = petdex_slug
        called["hide_dock"] = hide_dock
        return 0

    monkeypatch.setattr("sys.argv", ["cwb", "pet", "--petdex", "boba"])
    with mock.patch("coding_with_beat.pet.app.run", side_effect=fake_run):
        assert cmd_pet() == 0
    assert called["petdex_slug"] == "boba"
    assert called["hide_dock"] is True


def test_cmd_pet_builtin_disables_petdex_default(monkeypatch):
    called = {}

    def fake_run(*, petdex_slug=None, hide_dock=True, show_control=False):
        called["petdex_slug"] = petdex_slug
        called["hide_dock"] = hide_dock
        return 0

    monkeypatch.setattr("sys.argv", ["cwb", "pet", "--builtin"])
    with mock.patch("coding_with_beat.pet.app.run", side_effect=fake_run):
        assert cmd_pet() == 0
    assert called["petdex_slug"] is None
    assert called["hide_dock"] is True


def test_cmd_pet_show_dock_disables_dock_hiding(monkeypatch):
    called = {}

    def fake_run(*, petdex_slug=None, hide_dock=True, show_control=False):
        called["petdex_slug"] = petdex_slug
        called["hide_dock"] = hide_dock
        return 0

    monkeypatch.setattr("sys.argv", ["cwb", "pet", "--show-dock"])
    with mock.patch("coding_with_beat.pet.app.run", side_effect=fake_run):
        assert cmd_pet() == 0
    assert called["petdex_slug"] == "boba"
    assert called["hide_dock"] is False
