from coding_with_beat.pet.settings import PetSettings, load_settings, save_settings


def test_missing_settings_returns_defaults(tmp_path):
    settings = load_settings(tmp_path / "pet.json")
    assert settings.skin_id == "dj"
    assert settings.scale == 5


def test_save_and_load_round_trip(tmp_path):
    path = tmp_path / "pet.json"
    save_settings(PetSettings(x=12, y=34, skin_id="cyber", scale=4), path)
    loaded = load_settings(path)
    assert loaded.x == 12
    assert loaded.y == 34
    assert loaded.skin_id == "cyber"
    assert loaded.scale == 4
