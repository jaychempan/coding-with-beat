from coding_with_beat.pet.animator import PetAnimator


def test_animator_starts_on_default_skin_idle():
    animator = PetAnimator()
    assert animator.skin.id == "dj"
    assert animator.action == "idle"
    assert animator.current_frame().action == "idle"


def test_set_action_resets_frame_index():
    animator = PetAnimator()
    animator.tick()
    animator.set_action("dance")
    assert animator.action == "dance"
    assert animator.frame_index == 0


def test_invalid_skin_and_action_fall_back():
    animator = PetAnimator(skin_id="missing")
    assert animator.skin.id == "dj"
    animator.set_action("unknown")
    assert animator.action == "idle"
