"""Typed structures for a case package.

A *case package* is the private, versioned, server-side source of truth for one mystery. Nothing in this
module is ever serialised to a client directly; `app.schemas.public` projects the safe subset.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Timestamp:
    label: str
    clock: str  # "RT" real time | "ST" station clock
    time: str  # HH:MM or HH:MM:SS


@dataclass(frozen=True)
class Bears:
    """How an evidence item bears on suspicion of a character, as visible to the player."""

    character: str
    stance: str  # "points_to" | "clears" | "undermines_claim"
    requires: tuple[str, ...] = ()  # other evidence needed for this reading (e.g. the clock rule)
    note: str = ""
    aspect: str = ""  # motive | presence | meeting | alibi | claim


@dataclass(frozen=True)
class Evidence:
    key: str
    name: str
    category: str  # timeline|financial|access|testimony|physical|digital
    description: str
    examined_detail: str
    source: str
    location: str | None = None
    reliability: str = "unverified"  # verified|unverified|disputed|altered|testimony
    reliability_examined: str | None = None
    related_people: tuple[str, ...] = ()
    events: tuple[str, ...] = ()
    timestamps: tuple[Timestamp, ...] = ()
    unlocks_locations: tuple[str, ...] = ()
    bears_on: tuple[Bears, ...] = ()
    is_testimony: bool = False
    icon: str = "doc"


@dataclass(frozen=True)
class Hotspot:
    key: str
    label: str
    narration: str
    yields: tuple[str, ...]
    x: float  # percentages of the scene
    y: float
    w: float = 10
    h: float = 12
    requires: tuple[str, ...] = ()  # evidence needed before the hotspot can be noticed
    icon: str = "search"


@dataclass(frozen=True)
class Location:
    key: str
    name: str
    description: str
    scene: str
    hotspots: tuple[Hotspot, ...] = ()
    off_site: bool = False
    initially_unlocked: bool = True
    sort: int = 0
    unlock_hint: str = ""


@dataclass(frozen=True)
class Gate:
    trust_min: float = 0
    stress_min: float = 0
    evidence_any: tuple[str, ...] = ()
    need_count: int = 1  # how many distinct evidence from evidence_any must have been presented
    evidence_all: tuple[str, ...] = ()
    requires_revealed: tuple[str, ...] = ()  # fact keys this character already revealed (kind=reveal)
    min_turns: int = 0
    trust_bypass: float = 0  # if >0 and trust >= this, evidence requirements are waived


@dataclass(frozen=True)
class Fact:
    key: str
    text: str  # what the character really knows/believes (never sent to clients)
    topics: tuple[str, ...]  # retrieval vocabulary
    public_line: str | None = None  # stated account while the gate is closed (may be false)
    public_truthful: bool = True
    reveal_line: str | None = None  # said once the gate opens
    gate: Gate | None = None
    kind: str = "firsthand"  # firsthand | hearsay | belief
    grants_statement: str | None = None  # evidence key granted when public_line is voiced
    grants_evidence: str | None = None  # evidence key granted when reveal_line is voiced
    secret: bool = False
    leak_markers: tuple[str, ...] = ()  # lowercase phrases that must not appear before reveal
    volunteer: bool = False  # may be mentioned in an opening statement without being asked


@dataclass(frozen=True)
class Portrait:
    skin: str
    hair: str
    outfit: str
    accent: str
    glasses: bool = False
    beard: bool = False
    hair_style: str = "short"  # short|long|bald|bun|cap
    age: str = "mid"


@dataclass(frozen=True)
class Character:
    key: str
    name: str
    role: str
    age: int
    is_suspect: bool
    personality: str
    style: str  # speech style guidance (given to the LLM and used by fallback)
    relationship_to_victim: str
    public_facts: tuple[str, ...]
    facts: tuple[Fact, ...]
    relationships: dict[str, str]
    greeting: str
    deflections: tuple[str, ...]
    unknown_lines: tuple[str, ...]
    evidence_reactions: dict[str, str]  # generic reaction when shown evidence without a gated fact
    portrait: Portrait
    base_trust: float = 40
    base_stress: float = 10
    defensiveness: float = 1.0  # multiplier on stress gain
    sort: int = 0


@dataclass(frozen=True)
class ContradictionRule:
    key: str
    title: str
    explanation: str
    pairs: tuple[tuple[str, str], ...]  # any held pair triggers the rule
    about: str  # character key
    importance: int = 1


@dataclass(frozen=True)
class AlibiRule:
    key: str
    characters: tuple[str, ...]
    requires: tuple[str, ...]  # all evidence needed to establish the alibi
    statement: str
    window: str = ""


@dataclass(frozen=True)
class Event:
    key: str
    order: int
    rt: str
    title: str
    description: str
    revealed_by_any: tuple[str, ...]


@dataclass(frozen=True)
class Motive:
    key: str
    label: str
    description: str
    subjects: tuple[str, ...] = ()  # characters this motive could plausibly apply to (public reading)
    support: tuple[str, ...] = ()  # evidence that shows the motive exists


@dataclass(frozen=True)
class EvidenceRequirement:
    key: str
    label: str
    any_of: tuple[str, ...]
    weight: float
    need: int = 1


@dataclass(frozen=True)
class AccusationSpec:
    culprit: str
    motive: str
    motive_partial: tuple[str, ...]
    canonical_sequence: tuple[str, ...]  # event keys in true order
    min_sequence: int
    requirements: tuple[EvidenceRequirement, ...]
    key_contradictions: tuple[str, ...]
    closing_threshold: int  # number of requirement groups needed to close the case
    must_have_any_of: tuple[str, ...]  # at least one requirement key that must be satisfied
    max_attempts: int = 3


@dataclass(frozen=True)
class Doc:
    key: str
    title: str
    text: str
    required_evidence: str | None = None


@dataclass(frozen=True)
class ClockSpec:
    st_to_rt_minutes: int
    discovered_by: tuple[str, ...]  # evidence that reveals the offset to the player
    sources_on_st: tuple[str, ...]  # evidence keys whose timestamps are on the station clock


@dataclass(frozen=True)
class CaseSpec:
    id: str
    version: str
    title: str
    tagline: str
    summary: str
    briefing: str
    victim: str
    solution_culprit: str  # PRIVATE
    solution_motive: str  # PRIVATE
    solution_narrative: str  # PRIVATE
    locations: tuple[Location, ...]
    evidence: tuple[Evidence, ...]
    characters: tuple[Character, ...]
    contradictions: tuple[ContradictionRule, ...]
    alibis: tuple[AlibiRule, ...]
    events: tuple[Event, ...]
    motives: tuple[Motive, ...]
    accusation: AccusationSpec
    docs: tuple[Doc, ...]
    clock: ClockSpec
    travel_minutes: dict[tuple[str, str], int] = field(default_factory=dict)
    default_travel: int = 4

    # ---- helpers -----------------------------------------------------------------------------
    def ev(self, key: str) -> Evidence:
        return self._index("ev")[key]

    def has_ev(self, key: str) -> bool:
        return key in self._index("ev")

    def loc(self, key: str) -> Location:
        return self._index("loc")[key]

    def char(self, key: str) -> Character:
        return self._index("char")[key]

    def _index(self, kind: str) -> dict:
        cache = self.__dict__.setdefault("_cache", {})
        if kind not in cache:
            src: tuple[Any, ...] = {"ev": self.evidence, "loc": self.locations, "char": self.characters}[kind]
            cache[kind] = {x.key: x for x in src}
        return cache[kind]

    def travel(self, a: str, b: str) -> int:
        if a == b:
            return 0
        return self.travel_minutes.get((a, b), self.travel_minutes.get((b, a), self.default_travel))

    def content_hash(self) -> str:
        data = asdict(self)
        data["travel_minutes"] = {"|".join(k): v for k, v in self.travel_minutes.items()}
        payload = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()
