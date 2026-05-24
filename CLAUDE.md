# Coding With Beat

## Music intent

When the user asks for music by mood, scene, or style description
(e.g. "来首轻松的", "something for late-night coding", "带点爵士的"),
use `smart_search()` instead of `search()`.

Use `search()` only when the user provides a specific track title,
artist name, or album title.

## Smart search: multi-angle display

When handling a mood/vibe/scene music request, call `smart_search()` **once** with
the `queries` parameter containing 2–3 keyword angles. Do NOT call `smart_search()`
multiple times — each call overwrites the queue, so `play_number()` will index into
the wrong results.

Example for "深夜写代码":

```python
smart_search(queries=[
    "lofi hip hop late night coding instrumental",
    "lofi jazz late night rain cozy",
    "synthwave retrowave night drive electronic",
])
```

The tool returns globally numbered results grouped by direction with emoji labels.
Ask the user to pick by number and call `play_number(N)`. Do NOT auto-play.
