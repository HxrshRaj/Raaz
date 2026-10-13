from __future__ import annotations

from ..base import CaseSpec
from .characters import CHARACTERS
from .evidence import EVIDENCE
from .rules import ACCUSATION, ALIBIS, CONTRADICTIONS, SOLUTION_NARRATIVE
from .world import BRIEFING, CLOCK, DOCS, EVENTS, LOCATIONS, MOTIVES, TRAVEL


def build() -> CaseSpec:
    return CaseSpec(
        id="aakhri_gaadi",
        version="1.0.0",
        title="Aakhri Gaadi — The Last Train",
        tagline="Har raaz ke peeche ek kahaani hai.",
        summary="Devgarh Junction, a monsoon night. A tech founder is dead in a locked private carriage, five people "
        "had reasons to be there, and the station clock is lying.",
        briefing=BRIEFING,
        victim="Adrian Vale",
        solution_culprit=ACCUSATION.culprit,
        solution_motive=ACCUSATION.motive,
        solution_narrative=SOLUTION_NARRATIVE,
        locations=LOCATIONS,
        evidence=EVIDENCE,
        characters=CHARACTERS,
        contradictions=CONTRADICTIONS,
        alibis=ALIBIS,
        events=EVENTS,
        motives=MOTIVES,
        accusation=ACCUSATION,
        docs=DOCS,
        clock=CLOCK,
        travel_minutes=TRAVEL,
    )
