from coding_with_beat.pet.bubble import PetBubbleCard, PetBubbleView
from coding_with_beat.pet.interactions import PetInteractionController
from coding_with_beat.pet.session import PetSessionResult


class FakeSession:
    def __init__(self):
        self.calls = []

    def now_playing(self):
        self.calls.append("now_playing")
        return PetSessionResult(True, "idle", PetBubbleCard("status", "当前播放\nTrack"))

    def recommend_from_context(self):
        self.calls.append("recommend_from_context")
        return PetSessionResult(True, "recommend", PetBubbleCard("recommendations", "推荐\n1. Track"))

    def auto_play_from_context(self):
        self.calls.append("auto_play_from_context")
        return PetSessionResult(True, "dance", PetBubbleCard("confirmation", "已开播\nTrack", action="dance"))

    def reroll(self):
        self.calls.append("reroll")
        return PetSessionResult(True, "recommend", PetBubbleCard("recommendations", "换一组\n1. Track"))


def test_single_click_shows_status_bubble():
    session = FakeSession()
    controller = PetInteractionController(session=session)

    result = controller.single_click()

    assert result.card.kind == "status"
    assert session.calls == ["now_playing"]


def test_double_click_recommends_from_context():
    session = FakeSession()
    controller = PetInteractionController(session=session)

    result = controller.double_click()

    assert result.card.kind == "recommendations"
    assert session.calls == ["recommend_from_context"]


def test_long_press_auto_plays_from_context():
    session = FakeSession()
    controller = PetInteractionController(session=session)

    result = controller.long_press()

    assert result.card.kind == "confirmation"
    assert session.calls == ["auto_play_from_context"]


def test_quick_action_reroll():
    session = FakeSession()
    controller = PetInteractionController(session=session)

    result = controller.quick_action("reroll")

    assert result.card.kind == "recommendations"
    assert session.calls == ["reroll"]


def test_quick_action_now_calls_now_playing():
    session = FakeSession()
    controller = PetInteractionController(session=session)

    result = controller.quick_action("now")

    assert result.card.kind == "status"
    assert session.calls == ["now_playing"]


def test_quick_action_recommend_calls_recommend_from_context():
    session = FakeSession()
    controller = PetInteractionController(session=session)

    result = controller.quick_action("recommend")

    assert result.card.kind == "recommendations"
    assert session.calls == ["recommend_from_context"]


def test_unknown_quick_action_returns_error_card():
    session = FakeSession()
    controller = PetInteractionController(session=session, bubble=PetBubbleView())

    result = controller.quick_action("skip")

    assert result.ok is False
    assert result.action == "sad"
    assert result.card.kind == "error"
    assert session.calls == []
