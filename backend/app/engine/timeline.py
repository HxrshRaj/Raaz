"""Player timeline reconstruction + validation against explicit clock and travel rules."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..errors import DomainError, NotFound
from ..models import TimelineEntry
from .clock import clock_known, fmt_seconds, parse_seconds, to_rt_seconds
from .game import bump
from .state import SessionView

MAX_ENTRIES = 60
TOLERANCE_S = 90


def entry_view(view: SessionView, e: TimelineEntry) -> dict[str, Any]:
    known = clock_known(view.case, view.held)
    return {
        "id": e.id, "label": e.label, "time": e.time_hhmm, "clock": e.clock, "actor_key": e.actor_key,
        "location_key": e.location_key, "evidence_keys": list(e.evidence_keys or []),
        "real_time": fmt_seconds(to_rt_seconds(view.case, e.clock, e.time_hhmm), True) if known else None,
    }


def list_entries(db: Session, view: SessionView) -> list[TimelineEntry]:
    return list(db.scalars(select(TimelineEntry).where(TimelineEntry.session_id == view.session.id)
                           .order_by(TimelineEntry.created_at)))


def add_entry(db: Session, view: SessionView, *, label: str, time: str, clock: str, actor_key: str | None,
              location_key: str | None, evidence_keys: list[str]) -> TimelineEntry:
    case = view.case
    try:
        parse_seconds(time)
    except ValueError as e:
        raise DomainError("bad_time", "Use a time like 22:45 or 22:45:10.") from e
    if clock not in ("RT", "ST"):
        raise DomainError("bad_clock", "Clock must be RT (phones, banks) or ST (station clock).")
    if actor_key and actor_key != "adrian" and not any(c.key == actor_key for c in case.characters):
        raise NotFound("character")
    if location_key and not any(loc.key == location_key for loc in case.locations):
        raise NotFound("location")
    if location_key and location_key not in view.unlocked:
        raise DomainError("location_locked", "You haven't been to that place yet.", status=403)
    for k in evidence_keys:
        if k not in view.held:
            raise NotFound("evidence")
    if len(list_entries(db, view)) >= MAX_ENTRIES:
        raise DomainError("too_many_entries", "Your timeline is full. Remove something first.", status=409)
    entry = TimelineEntry(session_id=view.session.id, label=label.strip(), time_hhmm=time, clock=clock,
                          actor_key=actor_key, location_key=location_key, evidence_keys=list(dict.fromkeys(evidence_keys)))
    db.add(entry)
    bump(db, view.session.id, actions=0)
    db.commit()
    return entry


def delete_entry(db: Session, view: SessionView, entry_id: str) -> None:
    e = db.get(TimelineEntry, entry_id)
    if e is None or e.session_id != view.session.id:
        raise NotFound("timeline entry")
    db.delete(e)
    db.commit()


def validate(view: SessionView, entries: list[TimelineEntry]) -> dict[str, Any]:
    case = view.case
    known = clock_known(case, view.held)
    issues: list[dict[str, Any]] = []

    def comparable(clock_a: str, clock_b: str) -> bool:
        return known or clock_a == clock_b

    def secs(clock: str, t: str) -> int:
        return to_rt_seconds(case, clock, t) if known else parse_seconds(t)

    # 1) each entry must agree with the sources it cites
    for e in entries:
        for k in e.evidence_keys or []:
            ev = case.ev(k)
            if not ev.timestamps:
                continue
            ok = False
            comparable_any = False
            for ts in ev.timestamps:
                if comparable(e.clock, ts.clock):
                    comparable_any = True
                    if abs(secs(e.clock, e.time_hhmm) - secs(ts.clock, ts.time)) <= TOLERANCE_S:
                        ok = True
            if not comparable_any:
                issues.append({"type": "clock_unreconciled", "severity": "warning", "entries": [e.id],
                               "message": f"“{e.label}” cites {ev.name}, which keeps a different clock. You can't compare "
                                          "the two until you know how those clocks relate."})
            elif not ok:
                shown = ", ".join(f"{t.time} ({t.clock})" for t in ev.timestamps)
                issues.append({"type": "source_mismatch", "severity": "error", "entries": [e.id],
                               "message": f"“{e.label}” is at {e.time_hhmm} ({e.clock}) but {ev.name} records {shown}."})
    # 2) the same person cannot be in two places too close together
    by_actor: dict[str, list[TimelineEntry]] = {}
    for e in entries:
        if e.actor_key and e.location_key:
            by_actor.setdefault(e.actor_key, []).append(e)
    for actor, es in by_actor.items():
        for i in range(len(es)):
            for j in range(i + 1, len(es)):
                a, b = es[i], es[j]
                if a.location_key == b.location_key:
                    continue
                if not comparable(a.clock, b.clock):
                    issues.append({"type": "mixed_clocks", "severity": "warning", "entries": [a.id, b.id],
                                   "message": "These entries use different clocks, so their order can't be checked yet."})
                    continue
                gap = abs(secs(a.clock, a.time_hhmm) - secs(b.clock, b.time_hhmm))
                need = case.travel(a.location_key, b.location_key) * 60  # type: ignore[arg-type]
                if gap < need:
                    name = "Adrian" if actor == "adrian" else case.char(actor).name
                    issues.append({
                        "type": "impossible_travel", "severity": "error", "entries": [a.id, b.id],
                        "message": f"{name} can't be at {case.loc(a.location_key).name} and "  # type: ignore[arg-type]
                                   f"{case.loc(b.location_key).name} {gap // 60}m{gap % 60:02d}s apart; the walk in this rain "  # type: ignore[arg-type]
                                   f"takes about {need // 60} minutes."})
    return {"clock_known": known, "issues": issues, "ok": not any(i["severity"] == "error" for i in issues)}
