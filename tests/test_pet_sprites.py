from coding_with_beat.pet.sprites import ACTIONS, BUILTIN_SKINS, get_skin


def test_all_five_skins_exist():
    assert set(BUILTIN_SKINS) == {"dj", "programmer", "sleepwear", "cyber", "chinese"}


def test_every_skin_has_every_action_with_frames():
    for skin in BUILTIN_SKINS.values():
        assert set(skin.actions) == set(ACTIONS)
        for action, frames in skin.actions.items():
            assert frames, f"{skin.id} missing frames for {action}"
            assert all(frame.pixels for frame in frames)


def test_every_action_animates_with_visible_motion():
    for skin in BUILTIN_SKINS.values():
        for action, frames in skin.actions.items():
            assert len(frames) >= 2, f"{skin.id} {action} needs at least 2 frames"
            diffs = [_pixel_diff(a.pixels, b.pixels) for a, b in zip(frames, frames[1:] + frames[:1])]
            assert max(diffs) >= 10, f"{skin.id} {action} motion is too subtle: {diffs}"


def test_skin_idle_silhouettes_are_not_just_recolors():
    silhouettes = {_opaque_signature(skin.actions["idle"][0].pixels) for skin in BUILTIN_SKINS.values()}
    assert len(silhouettes) == len(BUILTIN_SKINS)


def test_get_skin_falls_back_to_dj():
    assert get_skin("missing").id == "dj"


def _pixel_diff(left, right):
    return sum(c1 != c2 for row1, row2 in zip(left, right) for c1, c2 in zip(row1, row2))


def _opaque_signature(pixels):
    return tuple((x, y) for y, row in enumerate(pixels) for x, ch in enumerate(row) if ch != ".")
