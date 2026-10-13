"""Request bodies. Strict lengths/enums everywhere: all player input is untrusted."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RegisterIn(Strict):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    display_name: str = Field(min_length=1, max_length=60)


class LoginIn(Strict):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class GuestIn(Strict):
    display_name: str = Field(default="Inspector", min_length=1, max_length=60)


class SessionCreateIn(Strict):
    case_id: str = Field(default="aakhri_gaadi", max_length=64)
    mode: Literal["standard", "demo"] = "standard"


class ContradictionCheckIn(Strict):
    a: str = Field(max_length=64)
    b: str = Field(max_length=64)


class MessageIn(Strict):
    text: str = Field(min_length=1, max_length=600)
    evidence_key: str | None = Field(default=None, max_length=64)


class BoardItemIn(Strict):
    kind: Literal["evidence", "person", "location", "note"]
    ref_key: str = Field(default="", max_length=64)
    text: str = Field(default="", max_length=300)
    x: float = Field(default=0, ge=-5000, le=5000)
    y: float = Field(default=0, ge=-5000, le=5000)


class BoardMoveIn(Strict):
    x: float = Field(ge=-5000, le=5000)
    y: float = Field(ge=-5000, le=5000)


class BoardLinkIn(Strict):
    from_item: str = Field(max_length=40)
    to_item: str = Field(max_length=40)
    relation: str = Field(max_length=24)
    note: str = Field(default="", max_length=300)


class TimelineEntryIn(Strict):
    label: str = Field(min_length=1, max_length=300)
    time: str = Field(min_length=4, max_length=8, pattern=r"^\d{1,2}:\d{2}(:\d{2})?$")
    clock: Literal["RT", "ST"] = "RT"
    actor_key: str | None = Field(default=None, max_length=64)
    location_key: str | None = Field(default=None, max_length=64)
    evidence_keys: list[str] = Field(default_factory=list, max_length=6)


class HypothesisIn(Strict):
    title: str = Field(min_length=1, max_length=200)
    culprit_key: str | None = Field(default=None, max_length=64)
    motive_key: str | None = Field(default=None, max_length=64)
    evidence_for: list[str] = Field(default_factory=list, max_length=30)
    evidence_against: list[str] = Field(default_factory=list, max_length=30)


class HypothesisEvalIn(Strict):
    culprit_key: str | None = Field(default=None, max_length=64)
    motive_key: str | None = Field(default=None, max_length=64)


class AccusationIn(Strict):
    culprit: str = Field(max_length=64)
    motive: str = Field(max_length=64)
    event_sequence: list[str] = Field(default_factory=list, max_length=12)
    evidence: list[str] = Field(default_factory=list, max_length=80)
    contradictions: list[str] = Field(default_factory=list, max_length=12)


class NazarIn(Strict):
    question: str = Field(default="", max_length=500)
    hint_level: Literal[1, 2, 3] = 1

    @field_validator("question")
    @classmethod
    def _q(cls, v: str) -> str:
        return v.strip()


class InvestigationIn(Strict):
    question: str = Field(min_length=3, max_length=400)
