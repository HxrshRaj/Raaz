"""Static integrity checks for a case package (used by tests and `python -m app.cases.validate`)."""

from __future__ import annotations

from .base import CaseSpec


def validate_case(c: CaseSpec) -> list[str]:
    errs: list[str] = []
    evs = {e.key for e in c.evidence}
    locs = {loc.key for loc in c.locations}
    chars = {ch.key for ch in c.characters}
    if len(evs) != len(c.evidence):
        errs.append("duplicate evidence keys")

    def need(key: str | None, ctx: str) -> None:
        if key and key not in evs:
            errs.append(f"{ctx}: unknown evidence {key}")

    obtainable: set[str] = set()
    for loc in c.locations:
        for h in loc.hotspots:
            for y in h.yields:
                need(y, f"hotspot {h.key}")
                obtainable.add(y)
            for r in h.requires:
                need(r, f"hotspot {h.key}.requires")
    for ch in c.characters:
        fkeys = [f.key for f in ch.facts]
        if len(set(fkeys)) != len(fkeys):
            errs.append(f"{ch.key}: duplicate fact keys")
        for f in ch.facts:
            for k in (f.grants_statement, f.grants_evidence):
                need(k, f"fact {f.key}")
                if k:
                    obtainable.add(k)
            if f.gate:
                for k in (*f.gate.evidence_any, *f.gate.evidence_all):
                    need(k, f"gate {f.key}")
                for r in f.gate.requires_revealed:
                    if r not in {x.key for x in ch.facts}:
                        errs.append(f"gate {f.key}: unknown fact {r}")
            if f.gate is not None and f.reveal_line is None and f.public_line is None:
                errs.append(f"fact {f.key}: gated but no line to say")
        for k in ch.evidence_reactions:
            need(k, f"reaction {ch.key}")
    for rule in c.contradictions:
        if rule.about not in chars:
            errs.append(f"rule {rule.key}: unknown character")
        for a, b in rule.pairs:
            need(a, rule.key)
            need(b, rule.key)
    for event in c.events:
        for k in event.revealed_by_any:
            need(k, f"event {event.key}")
    for e in c.evidence:
        if e.location and e.location not in locs:
            errs.append(f"evidence {e.key}: unknown location {e.location}")
        for u in e.unlocks_locations:
            if u not in locs:
                errs.append(f"evidence {e.key}: unknown unlock {u}")
        for bear in e.bears_on:
            if bear.character not in chars:
                errs.append(f"evidence {e.key}: bears_on unknown character")
            for k in bear.requires:
                need(k, f"bears_on {e.key}")
        for ev in e.events:
            if ev not in {x.key for x in c.events}:
                errs.append(f"evidence {e.key}: unknown event {ev}")
    for req in c.accusation.requirements:
        for k in req.any_of:
            need(k, f"requirement {req.key}")
    for alibi in c.alibis:
        for k in alibi.requires:
            need(k, f"alibi {alibi.key}")
    if c.accusation.culprit not in chars:
        errs.append("unknown culprit")
    if c.accusation.motive not in {m.key for m in c.motives}:
        errs.append("unknown motive")
    for k in c.accusation.canonical_sequence:
        if k not in {e.key for e in c.events}:
            errs.append(f"unknown event in canonical sequence {k}")
    unobtainable = evs - obtainable
    if unobtainable:
        errs.append(f"unobtainable evidence: {sorted(unobtainable)}")
    return errs


if __name__ == "__main__":  # pragma: no cover
    from .registry import list_cases

    for case in list_cases():
        problems = validate_case(case)
        print(case.id, "OK" if not problems else problems)
