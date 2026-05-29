from coding_with_beat.pet.mood import queries_for_mood


def test_successful_mood_maps_to_upbeat_queries():
    queries = queries_for_mood("今天很顺利 开心")
    assert len(queries) == 3
    assert any("victory" in q or "feel good" in q for q in queries)


def test_chinese_style_maps_to_chinese_queries():
    queries = queries_for_mood("想听国风古风")
    assert len(queries) == 3
    assert any("中国风" in q or "古风" in q for q in queries)


def test_unknown_text_uses_focus_fallback():
    queries = queries_for_mood("random text")
    assert len(queries) == 3
    assert any("focus" in q or "lofi" in q for q in queries)
