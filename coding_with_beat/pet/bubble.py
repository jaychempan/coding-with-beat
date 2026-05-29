"""Compact text cards for desktop pet bubbles."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_NUMBERED_LINE = re.compile(r"^\s*(\d+)\s*[.)、]\s*(.+?)\s*$")
_MAX_RECOMMENDATIONS = 5
_MAX_ERROR_TEXT = 170


@dataclass(frozen=True)
class PetResultItem:
    number: int
    label: str


@dataclass(frozen=True)
class PetBubbleCard:
    kind: str
    text: str
    action: str = "idle"
    items: list[PetResultItem] = field(default_factory=list)


class PetBubbleView:
    def recommendations(self, title: str, message: str, raw_results: str) -> PetBubbleCard:
        return self.results(
            title,
            message,
            raw_results,
            empty_text="没有找到合适结果。可以换一组，或者说一个更具体的心情。",
        )

    def results(
        self,
        title: str,
        message: str,
        raw_results: str,
        *,
        empty_text: str = "没有找到结果。可以换个关键词，或者说得更具体一点。",
        max_items: int = _MAX_RECOMMENDATIONS,
    ) -> PetBubbleCard:
        items = _parse_numbered_items(raw_results, max_items=max_items)
        if not items:
            return PetBubbleCard(
                kind="empty",
                text=f"{title}\n{empty_text}",
                action="sad",
            )

        lines = [f"{item.number}. {item.label}" for item in items]
        text = f"{title}\n{message}\n\n" + "\n".join(lines) + "\n\n点编号播放 · 🎲 换一组"
        return PetBubbleCard(kind="recommendations", text=text, action="recommend", items=items)

    def status(self, title: str, detail: str, action: str = "idle") -> PetBubbleCard:
        return PetBubbleCard(kind="status", text=f"{title}\n{_one_line(detail)}", action=action)

    def confirmation(self, title: str, detail: str, action: str = "dance") -> PetBubbleCard:
        return PetBubbleCard(
            kind="confirmation",
            text=f"{title}\n{_one_line(detail)}\n\n下一首 · 🎲 换一组",
            action=action,
        )

    def error(self, title: str, detail: str) -> PetBubbleCard:
        text = f"{title}\n{_one_line(detail)}"
        return PetBubbleCard(kind="error", text=_trim_text(text, _MAX_ERROR_TEXT), action="sad")


def _parse_numbered_items(raw_results: str, *, max_items: int = _MAX_RECOMMENDATIONS) -> list[PetResultItem]:
    items: list[PetResultItem] = []
    for line in (raw_results or "").splitlines():
        match = _NUMBERED_LINE.match(line)
        if not match:
            continue
        label = match.group(2).strip()
        if not label:
            continue
        items.append(PetResultItem(int(match.group(1)), label))
        if len(items) >= max_items:
            break
    return items


def _one_line(text: str) -> str:
    return " ".join((text or "").split())


def _trim_text(text: str, max_length: int) -> str:
    clean = text.strip()
    if len(clean) <= max_length:
        return clean
    if max_length <= 3:
        return clean[:max_length]
    return clean[: max_length - 3].rstrip() + "..."
