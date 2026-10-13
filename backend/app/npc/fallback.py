"""Deterministic scripted dialogue — the clearly-labelled fallback when no LLM is available or its output is rejected.

It never pretends to be generative: it only voices authored lines chosen by the same game-engine plan that would
constrain an LLM.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from ..cases.base import Character


@dataclass
class Beat:
    kind: str  # reveal | public | deflect | unknown | reaction | caught
    text: str
    fact_key: str | None = None
    truthful: bool = True


_OPENERS = {
    "open": ("", "", "Of course. "),
    "cooperative": ("", "Happy to help. ", ""),
    "guarded": ("", "Hm. ", ""),
    "anxious": ("Well... ", "", "Um — "),
    "defensive": ("Look, ", "I've already said — ", ""),
    "cornered": ("...", "You're twisting this. ", "No — "),
    "hostile": ("I don't owe you answers. But fine — ", "", "Tch. "),
}

_CAUGHT = (
    "That... is not how I remember it. I may have the details wrong.",
    "I don't see how that fits what I said, and I'd rather not guess.",
    "Give me a moment. That is not what I expected you to put on the table.",
)


def _pick(options: tuple[str, ...], seed: str) -> str:
    h = int(hashlib.sha1(seed.encode()).hexdigest()[:8], 16)
    return options[h % len(options)]


def caught_line(ch: Character, turn: int) -> str:
    return _pick(_CAUGHT, f"{ch.key}:{turn}")


def deflect_line(ch: Character, turn: int) -> str:
    return _pick(ch.deflections, f"{ch.key}:d:{turn}")


def unknown_line(ch: Character, turn: int) -> str:
    return _pick(ch.unknown_lines, f"{ch.key}:u:{turn}")


def compose(ch: Character, beats: list[Beat], mood: str, turn: int) -> str:
    if not beats:
        return deflect_line(ch, turn)
    opener = _pick(_OPENERS.get(mood, ("",)), f"{ch.key}:o:{turn}")
    body = " ".join(b.text.strip() for b in beats[:3])
    text = f"{opener}{body}".strip()
    if opener and body:
        text = f"{opener}{body[0].upper()}{body[1:]}" if opener.endswith(". ") else f"{opener}{body}"
    return text[:900]
