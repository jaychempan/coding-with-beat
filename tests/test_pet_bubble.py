from coding_with_beat.pet.bubble import PetBubbleView


def test_recommendation_card_extracts_numbered_results():
    raw = """1. Night Owl - Luna
2. Rain Debug - Soft Keys
3. Calm Compile - Build Room"""

    card = PetBubbleView().recommendations("Debug flow", "给你找低干扰的专注音乐。", raw)

    assert card.kind == "recommendations"
    assert card.action == "recommend"
    assert card.items[0].number == 1
    assert card.items[0].label == "Night Owl - Luna"
    assert (
        card.text == "Debug flow\n给你找低干扰的专注音乐。"
        "\n\n1. Night Owl - Luna\n2. Rain Debug - Soft Keys\n3. Calm Compile - Build Room"
        "\n\n点编号播放 · 🎲 换一组"
    )


def test_recommendation_card_caps_at_five_results():
    raw = "\n".join(f"{number}. Track {number}" for number in range(1, 8))

    card = PetBubbleView().recommendations("Title", "Message", raw)

    assert [item.number for item in card.items] == [1, 2, 3, 4, 5]
    assert "6. Track 6" not in card.text


def test_recommendation_card_handles_no_results():
    card = PetBubbleView().recommendations(
        "Debug flow",
        "给你找低干扰的专注音乐。",
        "nothing useful",
    )

    assert card.kind == "empty"
    assert card.action == "sad"
    assert card.text == "Debug flow\n没有找到合适结果。可以换一组，或者说一个更具体的心情。"


def test_status_card_is_short():
    card = PetBubbleView().status("Working", "  searching\nfor   tracks  ")

    assert card.kind == "status"
    assert card.action == "idle"
    assert card.text == "Working\nsearching for tracks"


def test_error_card_trims_long_output():
    detail = "failure " * 80

    card = PetBubbleView().error("Search failed", detail)

    assert card.kind == "error"
    assert card.action == "sad"
    assert len(card.text) <= 170
