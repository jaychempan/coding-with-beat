from coding_with_beat.pet.petdex import (
    FRAME_COLUMNS,
    FRAME_ROWS,
    PETDEX_ACTION_ROWS,
    PetdexAnimator,
    PetdexPet,
    frame_size,
    resolve_spritesheet_path,
)


def test_petdex_action_mapping_covers_internal_actions():
    assert PETDEX_ACTION_ROWS["idle"] == 0
    assert PETDEX_ACTION_ROWS["recommend"] == 1
    assert PETDEX_ACTION_ROWS["walk"] == 2
    assert PETDEX_ACTION_ROWS["panic"] == 3
    assert PETDEX_ACTION_ROWS["think"] == 4
    assert PETDEX_ACTION_ROWS["happy"] == 5


def test_petdex_grid_is_eight_columns_by_nine_rows():
    assert FRAME_COLUMNS == 8
    assert FRAME_ROWS == 9


def test_petdex_animator_cycles_eight_columns():
    animator = PetdexAnimator()
    assert animator.current_cell() == (0, 0)
    for _ in range(8):
        animator.tick()
    assert animator.current_cell() == (0, 0)


def test_frame_size_for_recommended_petdex_sheet():
    assert frame_size(1536, 1872) == (192, 208)


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
