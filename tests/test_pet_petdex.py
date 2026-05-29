import json

from PIL import Image

from coding_with_beat.pet.petdex import (
    BUNDLED_PETDEX_DIR,
    DEFAULT_PETDEX_SLUG,
    FRAME_COLUMNS,
    FRAME_ROWS,
    PETDEX_ACTION_ROWS,
    PetdexAnimator,
    PetdexPet,
    default_petdex_slug,
    display_size,
    ensure_petdex_pet,
    frame_size,
    installed_petdex_pets,
    resolve_spritesheet_path,
)


def test_petdex_action_mapping_covers_internal_actions():
    assert PETDEX_ACTION_ROWS["idle"] == 0
    assert PETDEX_ACTION_ROWS["walk"] == 1
    assert PETDEX_ACTION_ROWS["recommend"] == 3
    assert PETDEX_ACTION_ROWS["happy"] == 4
    assert PETDEX_ACTION_ROWS["panic"] == 5
    assert PETDEX_ACTION_ROWS["think"] == 6
    assert PETDEX_ACTION_ROWS["dance"] == 7


def test_petdex_grid_is_eight_columns_by_nine_rows():
    assert FRAME_COLUMNS == 8
    assert FRAME_ROWS == 9


def test_default_petdex_slug_is_codebeat_buddy():
    assert DEFAULT_PETDEX_SLUG == "codebeat-buddy"


def test_default_petdex_slug_migrates_legacy_boba_default():
    assert default_petdex_slug("") == "codebeat-buddy"
    assert default_petdex_slug("boba") == "codebeat-buddy"
    assert default_petdex_slug("mochi") == "mochi"


def test_bundled_codebeat_buddy_is_resolved_without_network():
    pet = ensure_petdex_pet("codebeat-buddy")

    assert pet.slug == "codebeat-buddy"
    assert pet.name == "CodeBeat Buddy"
    assert pet.folder == BUNDLED_PETDEX_DIR / "codebeat-buddy"
    assert resolve_spritesheet_path(pet).exists()


def test_bundled_codebeat_buddy_spritesheet_matches_petdex_grid():
    pet = ensure_petdex_pet("codebeat-buddy")

    with Image.open(resolve_spritesheet_path(pet)) as image:
        assert image.mode == "RGBA"
        assert image.size == (FRAME_COLUMNS * 192, FRAME_ROWS * 208)


def test_bundled_codebeat_buddy_declares_visual_v2():
    data = json.loads((BUNDLED_PETDEX_DIR / "codebeat-buddy" / "pet.json").read_text(encoding="utf-8"))

    assert data["visualVersion"] == 2


def test_bundled_codebeat_buddy_idle_frame_has_cute_head_body_ratio():
    pet = ensure_petdex_pet("codebeat-buddy")

    with Image.open(resolve_spritesheet_path(pet)).convert("RGBA") as image:
        idle = image.crop((0, 0, 192, 208)).getchannel("A")
        head_pixels = _visible_pixels(idle.crop((36, 0, 156, 86)))
        body_pixels = _visible_pixels(idle.crop((36, 86, 156, 168)))

    assert head_pixels >= body_pixels * 0.85


def test_bundled_codebeat_buddy_idle_frame_has_no_translucent_backdrop():
    pet = ensure_petdex_pet("codebeat-buddy")

    with Image.open(resolve_spritesheet_path(pet)).convert("RGBA") as image:
        idle_alpha = image.crop((0, 0, 192, 208)).getchannel("A")

    assert _translucent_pixels(idle_alpha) == 0


def _visible_pixels(alpha_channel: Image.Image) -> int:
    histogram = alpha_channel.histogram()
    return sum(histogram[1:])


def _translucent_pixels(alpha_channel: Image.Image) -> int:
    histogram = alpha_channel.histogram()
    return sum(histogram[1:255])


def test_installed_petdex_pets_includes_bundled_codebeat_buddy():
    pets = installed_petdex_pets()

    assert any(pet.slug == "codebeat-buddy" and pet.name == "CodeBeat Buddy" for pet in pets)


def test_petdex_idle_animator_uses_six_frame_loop():
    animator = PetdexAnimator()
    assert animator.current_cell() == (0, 0)
    for _ in range(6):
        animator.tick()
    assert animator.current_cell() == (0, 0)


def test_petdex_action_uses_its_own_frame_count():
    animator = PetdexAnimator()
    animator.set_action("recommend")
    assert animator.current_cell() == (3, 0)
    for _ in range(4):
        animator.tick()
    assert animator.current_cell() == (3, 0)


def test_frame_size_for_recommended_petdex_sheet():
    assert frame_size(1536, 1872) == (192, 208)


def test_petdex_display_size_matches_desktop_pet_scale():
    assert display_size(192, 208) == (72, 78)


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


def test_installed_petdex_pets_discovers_local_pet_json(tmp_path):
    pet_dir = tmp_path / "boba"
    pet_dir.mkdir()
    (pet_dir / "pet.json").write_text(
        '{"id":"boba","displayName":"Boba","spritesheetPath":"spritesheet.webp"}',
        encoding="utf-8",
    )
    (pet_dir / "spritesheet.webp").write_bytes(b"webp")

    assert installed_petdex_pets([tmp_path]) == [
        PetdexPet(slug="boba", name="Boba", folder=pet_dir, spritesheet_path=pet_dir / "spritesheet.webp")
    ]


def test_installed_petdex_pets_prefers_first_duplicate(tmp_path):
    first = tmp_path / "first" / "boba"
    second = tmp_path / "second" / "boba"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    for pet_dir, name in ((first, "First Boba"), (second, "Second Boba")):
        (pet_dir / "pet.json").write_text(f'{{"id":"boba","displayName":"{name}"}}', encoding="utf-8")
        (pet_dir / "spritesheet.png").write_bytes(b"png")

    assert installed_petdex_pets([tmp_path / "first", tmp_path / "second"])[0].name == "First Boba"
