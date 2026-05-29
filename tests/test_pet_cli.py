from unittest import mock

from coding_with_beat.__main__ import COMMANDS, cmd_pet


def test_pet_command_registered():
    assert COMMANDS["pet"] is cmd_pet


def test_cmd_pet_prints_install_hint_when_pyside_missing(capsys):
    with mock.patch("coding_with_beat.pet.app.run", side_effect=RuntimeError("PySide6 is required")):
        rc = cmd_pet()
    assert rc == 1
    assert "pip install" in capsys.readouterr().err


def test_cmd_pet_passes_petdex_slug(monkeypatch):
    called = {}

    def fake_run(*, petdex_slug=None):
        called["petdex_slug"] = petdex_slug
        return 0

    monkeypatch.setattr("sys.argv", ["cwb", "pet", "--petdex", "boba"])
    with mock.patch("coding_with_beat.pet.app.run", side_effect=fake_run):
        assert cmd_pet() == 0
    assert called["petdex_slug"] == "boba"
