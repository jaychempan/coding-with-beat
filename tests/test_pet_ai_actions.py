from coding_with_beat.pet.ai_actions import (
    AiVisibleReply,
    MusicAction,
    MusicActionKind,
    detect_local_command_action,
    parse_ai_music_reply,
)


def test_parse_structured_music_actions_hides_json_block():
    raw = """我会先放两种选择。

```json
{
  "music_actions": [
    {"kind": "play_track", "query": "周杰伦 晴天", "label": "晴天 - 周杰伦"},
    {"kind": "search_music", "query": "lofi hip hop coding focus", "label": "Coding lofi"}
  ]
}
```
"""

    reply = parse_ai_music_reply(raw)

    assert reply == AiVisibleReply(
        text="我会先放两种选择。",
        actions=[
            MusicAction(MusicActionKind.PLAY_TRACK, "晴天 - 周杰伦", "周杰伦 晴天"),
            MusicAction(MusicActionKind.SEARCH_MUSIC, "Coding lofi", "lofi hip hop coding focus"),
        ],
    )


def test_parse_structured_music_actions_keeps_text_when_json_is_invalid():
    raw = '推荐《晴天》- 周杰伦\n```json\n{"music_actions": [\n```'

    reply = parse_ai_music_reply(raw)

    assert reply.text.startswith("推荐《晴天》")
    assert reply.actions == [MusicAction(MusicActionKind.PLAY_TRACK, "晴天 - 周杰伦", "晴天 周杰伦")]


def test_fallback_extracts_chinese_and_english_recommendation_lines():
    raw = "1. 《晴天》- 周杰伦\n2. Anti-Hero by Taylor Swift\n这两首都适合继续写代码。"

    reply = parse_ai_music_reply(raw)

    assert reply.text == raw
    assert reply.actions == [
        MusicAction(MusicActionKind.PLAY_TRACK, "晴天 - 周杰伦", "晴天 周杰伦"),
        MusicAction(MusicActionKind.PLAY_TRACK, "Anti-Hero - Taylor Swift", "Anti-Hero Taylor Swift"),
    ]


def test_local_command_detection_maps_fast_transport_controls():
    assert detect_local_command_action("/next") == MusicAction(MusicActionKind.CONTROL, "下一首", "next_track")
    assert detect_local_command_action("下一首") == MusicAction(MusicActionKind.CONTROL, "下一首", "next_track")
    assert detect_local_command_action("暂停") == MusicAction(MusicActionKind.CONTROL, "暂停/继续", "toggle")
    assert detect_local_command_action("音量 70") == MusicAction(MusicActionKind.CONTROL, "音量 70", "set_volume:70")
    assert detect_local_command_action("解释这个项目") is None
