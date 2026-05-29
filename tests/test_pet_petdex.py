from coding_with_beat.pet.petdex import PETDEX_ACTION_ROWS, PetdexAnimator, PetdexPet, resolve_spritesheet_path


def test_petdex_action_mapping_covers_internal_actions():
    assert PETDEX_ACTION_ROWS["idle"] == 0
    assert PETDEX_ACTION_ROWS["recommend"] == 1
    assert PETDEX_ACTION_ROWS["walk"] == 2
    assert PETDEX_ACTION_ROWS["panic"] == 3
    assert PETDEX_ACTION_ROWS["think"] == 4
    assert PETDEX_ACTION_ROWS["happy"] == 5


def test_petdex_animator_cycles_nine_columns():
    animator = PetdexAnimator()
    assert animator.current_cell() == (0, 0)
    for _ in range(9):
        animator.tick()
    assert animator.current_cell() == (0, 0)


def test_resolve_spritesheet_path_prefers_converted_png(tmp_path):
    pet = PetdexPet(slug="boba", name="Boba", folder=tmp_path, spritesheet_path=tmp_path / "spritesheet.webp")
    converted = tmp_path / "spritesheet.png"
    converted.write_bytes(b"png")
    assert resolve_spritesheet_path(pet) == converted


def test_resolve_spritesheet_path_falls_back_to_original(tmp_path):
    original = tmp_path / "spritesheet.webp"
    original.write_bytes(b"webp")
    pet = PetdexPet(slug="boba", name="Boba", folder=tmp_path, spritesheet_path=original)
    assert resolve_spritesheet_path(pet) == original
