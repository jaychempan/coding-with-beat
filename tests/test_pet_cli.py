from unittest import mock

from coding_with_beat.__main__ import COMMANDS, cmd_pet


def test_pet_command_registered():
    assert COMMANDS["pet"] is cmd_pet


def test_cmd_pet_prints_install_hint_when_pyside_missing(capsys):
    with mock.patch("coding_with_beat.pet.app.run", side_effect=RuntimeError("PySide6 is required")):
        rc = cmd_pet()
    assert rc == 1
    assert "pip install" in capsys.readouterr().err
