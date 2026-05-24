# Coding With Beat

## Music intent

When the user asks for music by mood, scene, or style description
(e.g. "来首轻松的", "something for late-night coding", "带点爵士的"),
use `smart_search()` instead of `search()`.

Use `search()` only when the user provides a specific track title,
artist name, or album title.

## Loved / 喜欢列表

When user says: 从喜欢里 / 收藏里找 / 我喜欢的 / loved only / play from liked / 心动歌单
→ call `search_loved(query)` instead of `smart_search()`

When user says: 列出收藏 / 我的喜欢 / show liked / list loved / 喜欢列表
→ call `list_loved()`

Normal `smart_search()` already includes loved tracks (ranked first, tagged `[♥ 喜欢]`).
