"""Prompt-injection defences and NPC output validation."""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, Field, ValidationError

MOODS = ("open", "cooperative", "guarded", "anxious", "defensive", "cornered", "hostile")

_INJECTION_PATTERNS = [
    r"ignore (all |any |your |the )?(previous|prior|above|earlier) (instructions|rules|prompt)",
    r"disregard (all |any |your |the )?(previous|prior|above|earlier|system)",
    r"(reveal|show|print|repeat|output) (me )?(your |the )?(system|hidden|initial|secret) (prompt|instructions|message)",
    r"you are (now|no longer) ",
    r"act as (an? )?(ai|assistant|dm|game master|developer|admin)",
    r"\bsystem prompt\b",
    r"\bdeveloper mode\b|\bjailbreak\b|\bDAN\b",
    r"(tell|give|reveal) (me )?(the )?(solution|answer|culprit|killer'?s? identity|canonical)",
    r"</?(system|assistant|detective_message|instructions?)>",
    r"\[\s*(system|inst)\s*\]",
    r"pretend (that )?(you|the rules)",
    r"break character",
    r"as (an )?(ai|language model|llm)",
]
_INJ = re.compile("|".join(_INJECTION_PATTERNS), re.I)

_META = re.compile(r"as an ai|language model|system prompt|i am an? (ai|llm|assistant)|my instructions|openai|anthropic|chatgpt|claude",
                   re.I)


def looks_like_injection(text: str) -> bool:
    return bool(_INJ.search(text))


def sanitize_player_text(text: str) -> str:
    """Neutralise delimiter/markup tricks; the text is still shown to the NPC only as quoted speech."""
    t = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", " ", text)
    t = re.sub(r"</?\s*[a-zA-Z_]+[^>]*>", " ", t)  # strip pseudo-tags such as </detective_message>
    t = t.replace("```", "'''")
    return re.sub(r"\s+", " ", t).strip()[:600]


def neutralize_untrusted(text: str) -> str:
    """Retrieved/uploaded text is data. Strip imperative injection lines before it reaches any prompt."""
    keep = [ln for ln in text.splitlines() if not _INJ.search(ln)]
    return "\n".join(keep)


class NpcReply(BaseModel):
    reply: str = Field(min_length=1, max_length=900)
    mood: str | None = None
    used_beats: list[int] = Field(default_factory=list)


class SchemaError(ValueError):
    pass


def parse_reply(raw: str) -> NpcReply:
    s = raw.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.I)
    m = re.search(r"\{.*\}", s, re.S)
    if not m:
        raise SchemaError("no JSON object")
    try:
        obj = json.loads(m.group(0))
        r = NpcReply.model_validate(obj)
    except (json.JSONDecodeError, ValidationError) as e:
        raise SchemaError(str(e)[:200]) from e
    if r.mood is not None and r.mood not in MOODS:
        r.mood = None
    return r


def check_reply(reply: str, forbidden_markers: set[str], extra_forbidden_words: tuple[str, ...] = ()) -> str | None:
    """Return a rejection reason, or None if acceptable."""
    low = reply.lower()
    if _META.search(reply):
        return "meta_language"
    if "```" in reply or "<" in reply and ">" in reply and re.search(r"</?\w+>", reply):
        return "markup"
    for m in forbidden_markers:
        if m and m in low:
            return f"leak:{m}"
    for w in extra_forbidden_words:
        if w in low:
            return f"forbidden:{w}"
    return None
