"""Deterministic core of the game: catalog seeding, sessions, exploration, evidence, contradictions, dossiers.

Nothing in this module calls an LLM. Everything here is reproducible from (case package, session state).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..cases.base import CaseSpec, ContradictionRule, Evidence
from ..cases.registry import get_case, list_cases
from ..errors import Conflict, Forbidden, NotFound
from ..models import (
    Case,
    CaseVersion,
    ContradictionFound,
    EvidenceDiscovery,
    GameSession,
    UnlockedLocation,
    User,
)
from ..models import Character as CharRow
from ..models import Evidence as EvRow
from ..models import Location as LocRow
from .clock import clock_known, effective_held, fmt_seconds, to_rt_seconds
from .state import SessionView, bump, insert_ignore, load_view

CLOCK_LABEL = {"RT": "Real time (phones, banks, wearables)", "ST": "Station clock"}


# --------------------------------------------------------------------------- catalog
def ensure_catalog(db: Session) -> None:
    """Idempotently mirror the *public* columns of every case package into the catalog tables."""
    for c in list_cases():
        row = db.get(Case, c.id)
        if row is None:
            db.add(Case(id=c.id, title=c.title, tagline=c.tagline, summary=c.summary))
        else:
            row.title, row.tagline, row.summary = c.title, c.tagline, c.summary
        h = c.content_hash()
        ver = db.scalar(select(CaseVersion).where(CaseVersion.case_id == c.id, CaseVersion.version == c.version))
        if ver is None:
            db.add(CaseVersion(case_id=c.id, version=c.version, content_hash=h, is_active=True))
        elif ver.content_hash != h:
            ver.content_hash = h
        db.flush()
        for loc in c.locations:
            lrow = db.get(LocRow, (c.id, loc.key))
            vals = dict(name=loc.name, description=loc.description, initially_unlocked=loc.initially_unlocked,
                        off_site=loc.off_site, sort=loc.sort)
            if lrow is None:
                db.add(LocRow(case_id=c.id, key=loc.key, **vals))
            else:
                for k, v in vals.items():
                    setattr(lrow, k, v)
        for ch in c.characters:
            crow = db.get(CharRow, (c.id, ch.key))
            vals = dict(name=ch.name, role=ch.role, is_suspect=ch.is_suspect, sort=ch.sort)
            if crow is None:
                db.add(CharRow(case_id=c.id, key=ch.key, **vals))
            else:
                for k, v in vals.items():
                    setattr(crow, k, v)
        for ev in c.evidence:
            erow = db.get(EvRow, (c.id, ev.key))
            vals = dict(name=ev.name, category=ev.category, location_key=ev.location, is_testimony=ev.is_testimony)
            if erow is None:
                db.add(EvRow(case_id=c.id, key=ev.key, **vals))
            else:
                for k, v in vals.items():
                    setattr(erow, k, v)
    db.commit()


# --------------------------------------------------------------------------- sessions
def create_session(db: Session, user: User, case_id: str, mode: str = "standard") -> GameSession:
    try:
        case = get_case(case_id)
    except KeyError as e:
        raise NotFound("case") from e
    s = GameSession(user_id=user.id, case_id=case.id, case_version=case.version, mode=mode)
    db.add(s)
    db.flush()
    for loc in case.locations:
        if loc.initially_unlocked:
            db.add(UnlockedLocation(session_id=s.id, location_key=loc.key, via="start"))
    db.commit()
    return s


def view_of(db: Session, session: GameSession) -> SessionView:
    return load_view(db, session)


# --------------------------------------------------------------------------- projections
def _people(case: CaseSpec, keys: tuple[str, ...]) -> list[dict[str, str]]:
    out = []
    for k in keys:
        if k == "adrian":
            out.append({"key": "adrian", "name": "Adrian Vale"})
        else:
            try:
                out.append({"key": k, "name": case.char(k).name})
            except KeyError:
                continue
    return out


def bearing_for(view: SessionView, ev: Evidence) -> list[dict[str, str]]:
    """How this evidence bears on suspicion of each character, given what the player actually holds."""
    held = effective_held(view.case, view.held)
    out = []
    for b in ev.bears_on:
        if all(r in held for r in b.requires):
            out.append({"character": b.character, "name": view.case.char(b.character).name, "stance": b.stance,
                        "aspect": b.aspect, "note": b.note})
    return out


def evidence_view(view: SessionView, ev: Evidence) -> dict[str, Any]:
    disc = view.found[ev.key]
    case = view.case
    known = clock_known(case, view.held)
    ts = []
    for t in ev.timestamps:
        item: dict[str, Any] = {"label": t.label, "clock": t.clock, "clock_label": CLOCK_LABEL[t.clock], "time": t.time}
        if known:
            item["real_time"] = fmt_seconds(to_rt_seconds(case, t.clock, t.time), with_seconds=t.time.count(":") == 2)
        ts.append(item)
    loc_name = case.loc(ev.location).name if ev.location else None
    reliability = ev.reliability_examined if (disc.examined and ev.reliability_examined) else ev.reliability
    found_rules = [r.key for r in case.contradictions
                   if r.key in view.contradictions and any(ev.key in p for p in r.pairs)]
    events = [{"key": e.key, "title": e.title} for e in case.events if e.key in ev.events]
    return {
        "key": ev.key, "name": ev.name, "category": ev.category, "description": ev.description,
        "examined_detail": ev.examined_detail if disc.examined else None,
        "source": ev.source, "location_key": ev.location, "location_name": loc_name,
        "discovered_at": disc.discovered_at.isoformat() if disc.discovered_at else None,
        "discovered_via": disc.source, "action_no": disc.action_no,
        "examined": disc.examined, "reliability": reliability,
        "related_people": _people(case, ev.related_people), "related_events": events,
        "timestamps": ts, "bearing": bearing_for(view, ev), "is_testimony": ev.is_testimony,
        "icon": ev.icon, "contradiction_rules": found_rules,
    }


def list_evidence(view: SessionView) -> list[dict[str, Any]]:
    rows = sorted(view.found.values(), key=lambda d: (d.action_no, d.discovered_at or datetime.min.replace(tzinfo=UTC)))
    return [evidence_view(view, view.case.ev(d.evidence_key)) for d in rows]


def contradiction_view(view: SessionView, rule: ContradictionRule, pair: tuple[str, str] | None = None) -> dict[str, Any]:
    found = view.contradictions.get(rule.key)
    pair = pair or next((p for p in rule.pairs if p[0] in view.held and p[1] in view.held), rule.pairs[0])
    return {
        "key": rule.key, "title": rule.title, "explanation": rule.explanation,
        "about": rule.about, "about_name": view.case.char(rule.about).name, "importance": rule.importance,
        "evidence": list(pair), "found_via": found.via if found else None,
        "found_at": found.found_at.isoformat() if found and found.found_at else None,
    }


def contradictions_list(view: SessionView) -> list[dict[str, Any]]:
    return [contradiction_view(view, r) for r in view.case.contradictions if r.key in view.contradictions]


# --------------------------------------------------------------------------- locations
def _hotspot_visible(view: SessionView, h) -> bool:
    return all(r in view.held for r in h.requires)


def locations_view(view: SessionView) -> list[dict[str, Any]]:
    out = []
    for loc in sorted(view.case.locations, key=lambda x: x.sort):
        unlocked = loc.key in view.unlocked
        vis = [h for h in loc.hotspots if _hotspot_visible(view, h)]
        searched = sum(1 for h in vis if all(y in view.held for y in h.yields))
        out.append({
            "key": loc.key, "name": loc.name, "scene": loc.scene, "off_site": loc.off_site,
            "locked": not unlocked, "unlock_hint": loc.unlock_hint if not unlocked else "",
            "description": loc.description if unlocked else "",
            "visible_hotspots": len(vis) if unlocked else 0, "searched_hotspots": searched if unlocked else 0,
        })
    return out


def location_detail(view: SessionView, loc_key: str) -> dict[str, Any]:
    try:
        loc = view.case.loc(loc_key)
    except KeyError as e:
        raise NotFound("location") from e
    if loc.key not in view.unlocked:
        raise Forbidden("location_locked", "You have no reason to go there yet.")
    spots = []
    for h in loc.hotspots:
        if not _hotspot_visible(view, h):
            continue
        spots.append({
            "key": h.key, "label": h.label, "x": h.x, "y": h.y, "w": h.w, "h": h.h, "icon": h.icon,
            "searched": all(y in view.held for y in h.yields),
        })
    return {"key": loc.key, "name": loc.name, "description": loc.description, "scene": loc.scene,
            "off_site": loc.off_site, "hotspots": spots}


def inspect_hotspot(db: Session, view: SessionView, loc_key: str, hotspot_key: str) -> dict[str, Any]:
    case = view.case
    if view.session.status == "solved":
        raise Conflict("case_closed", "This case is closed. You can still review your notes.")
    try:
        loc = case.loc(loc_key)
    except KeyError as e:
        raise NotFound("location") from e
    if loc.key not in view.unlocked:
        raise Forbidden("location_locked", "You have no reason to go there yet.")
    hs = next((h for h in loc.hotspots if h.key == hotspot_key), None)
    if hs is None or not _hotspot_visible(view, hs):
        raise NotFound("hotspot")
    new_keys: list[str] = []
    already: list[str] = []
    next_action = view.session.actions + 1
    for ev_key in hs.yields:
        if _discover(db, view, ev_key, f"hotspot:{loc.key}/{hs.key}", next_action):
            new_keys.append(ev_key)
        else:
            already.append(ev_key)
    unlocked_now = _apply_unlocks(db, view, new_keys)
    bump(db, view.session.id)
    db.commit()
    return {
        "narration": hs.narration, "new_evidence": [evidence_view(view, case.ev(k)) for k in new_keys],
        "already_found": already, "unlocked_locations": unlocked_now,
    }


def _discover(db: Session, view: SessionView, ev_key: str, source: str, action_no: int) -> bool:
    if ev_key in view.found:
        return False
    ok = insert_ignore(db, EvidenceDiscovery, {
        "session_id": view.session.id, "evidence_key": ev_key, "case_id": view.case.id, "source": source,
        "discovered_at": datetime.now(UTC), "action_no": action_no, "examined": False,
    })
    if ok:
        row = db.get(EvidenceDiscovery, (view.session.id, ev_key))
        view.found[ev_key] = row  # type: ignore[assignment]
    else:  # another request won the race: refresh our view
        row = db.get(EvidenceDiscovery, (view.session.id, ev_key))
        if row is not None:
            view.found[ev_key] = row
    return ok


def grant_evidence(db: Session, view: SessionView, ev_key: str, source: str) -> bool:
    """Used by the NPC engine to hand over statements/testimony. Does not commit."""
    ok = _discover(db, view, ev_key, source, view.session.actions + 1)
    if ok:
        _apply_unlocks(db, view, [ev_key])
    return ok


def _apply_unlocks(db: Session, view: SessionView, ev_keys: list[str]) -> list[dict[str, str]]:
    out = []
    for k in ev_keys:
        for loc_key in view.case.ev(k).unlocks_locations:
            if loc_key in view.unlocked:
                continue
            if insert_ignore(db, UnlockedLocation, {"session_id": view.session.id, "location_key": loc_key, "via": k,
                                                    "created_at": datetime.now(UTC)}):
                row = db.get(UnlockedLocation, (view.session.id, loc_key))
                view.unlocked[loc_key] = row  # type: ignore[assignment]
                out.append({"key": loc_key, "name": view.case.loc(loc_key).name, "via": k})
    return out


def examine_evidence(db: Session, view: SessionView, ev_key: str) -> dict[str, Any]:
    if ev_key not in view.found:
        # identical response whether the key is invalid or simply not yours: no oracle for hidden evidence
        raise NotFound("evidence")
    res = db.execute(
        update(EvidenceDiscovery)
        .where(EvidenceDiscovery.session_id == view.session.id, EvidenceDiscovery.evidence_key == ev_key,
               EvidenceDiscovery.examined.is_(False))
        .values(examined=True, examined_at=datetime.now(UTC))
    )
    first = (res.rowcount or 0) > 0
    if first:
        bump(db, view.session.id)
    db.commit()
    row = db.get(EvidenceDiscovery, (view.session.id, ev_key))
    view.found[ev_key] = row  # type: ignore[assignment]
    return {"first_examination": first, "evidence": evidence_view(view, view.case.ev(ev_key))}


# --------------------------------------------------------------------------- contradictions
def matching_rule(case: CaseSpec, a: str, b: str) -> tuple[ContradictionRule, tuple[str, str]] | None:
    for r in case.contradictions:
        for p in r.pairs:
            if (a, b) == p or (b, a) == p:
                return r, p
    return None


def record_contradiction(db: Session, view: SessionView, rule: ContradictionRule, via: str) -> bool:
    ok = insert_ignore(db, ContradictionFound, {"session_id": view.session.id, "rule_key": rule.key, "via": via,
                                                "found_at": datetime.now(UTC)})
    if ok:
        view.contradictions[rule.key] = db.get(ContradictionFound, (view.session.id, rule.key))  # type: ignore[assignment]
    return ok


def check_contradiction(db: Session, view: SessionView, a: str, b: str) -> dict[str, Any]:
    if a not in view.held or b not in view.held or a == b:
        raise NotFound("evidence")
    m = matching_rule(view.case, a, b)
    if m is None:
        return {"established": False, "newly_found": False, "contradiction": None,
                "message": "Those two items don't conflict in any way you can establish from the record."}
    rule, pair = m
    new = record_contradiction(db, view, rule, "player_check")
    if new:
        bump(db, view.session.id)
    db.commit()
    return {"established": True, "newly_found": new, "contradiction": contradiction_view(view, rule, pair),
            "message": "Contradiction established."}


def triggered_by_presentation(db: Session, view: SessionView, presented: str, char_key: str) -> list[ContradictionRule]:
    """Contradictions that become established because `presented` was shown to the person it is about."""
    out = []
    for r in view.case.contradictions:
        if r.about != char_key:
            continue
        for a, b in r.pairs:
            if presented in (a, b):
                other = b if presented == a else a
                if other in view.held:
                    if record_contradiction(db, view, r, f"presentation:{char_key}") or r.key in view.contradictions:
                        out.append(r)
                    break
    return out


# --------------------------------------------------------------------------- events, timeline sources
def visible_events(view: SessionView) -> list[dict[str, Any]]:
    """Events the player's evidence has revealed. Deliberately listed alphabetically by title — never in true order,
    so the list itself can't leak the sequence the player is asked to reconstruct."""
    out = []
    for e in sorted(view.case.events, key=lambda x: x.title):
        basis = [k for k in e.revealed_by_any if k in view.held]
        if basis:
            out.append({"key": e.key, "title": e.title, "description": e.description, "basis": basis})
    return out


def evidence_timestamps(view: SessionView) -> list[dict[str, Any]]:
    case = view.case
    known = clock_known(case, view.held)
    rows = []
    for k in view.held:
        ev = case.ev(k)
        for t in ev.timestamps:
            rows.append({"evidence_key": k, "evidence_name": ev.name, "label": t.label, "clock": t.clock,
                         "clock_label": CLOCK_LABEL[t.clock], "time": t.time,
                         "real_time": fmt_seconds(to_rt_seconds(case, t.clock, t.time), True) if known else None,
                         "_sort": to_rt_seconds(case, t.clock, t.time) if known else to_rt_seconds(case, "RT", t.time)})
    rows.sort(key=lambda r: (r["_sort"], r["evidence_key"]))
    for r in rows:
        r.pop("_sort")
    return rows


# --------------------------------------------------------------------------- dossier / overview
def alibi_status(view: SessionView, char_key: str) -> dict[str, Any]:
    held = effective_held(view.case, view.held)
    for a in view.case.alibis:
        if char_key in a.characters and all(r in held for r in a.requires):
            return {"status": "cleared_for_window", "statement": a.statement, "window": a.window}
    found_about = [r for r in view.case.contradictions if r.about == char_key and r.key in view.contradictions]
    if found_about:
        return {"status": "claims_contradicted", "statement": "At least one of their statements has been contradicted.",
                "window": ""}
    return {"status": "unverified", "statement": "Their whereabouts at the time of death are not yet established.",
            "window": ""}


def unresolved_questions(view: SessionView, char_key: str) -> list[str]:
    case = view.case
    ch = case.char(char_key)
    qs: list[str] = []
    conv = view.conversations.get(char_key)
    if conv is None or conv.turns == 0:
        qs.append(f"You have not yet interviewed {ch.name.split()[0]}.")
    for ev_key in sorted(view.held):
        ev = case.ev(ev_key)
        if ev.is_testimony and char_key in ev.related_people and ev_key.startswith("ev_stmt_"):
            checked = any(r.key in view.contradictions and any(ev_key in p for p in r.pairs) for r in case.contradictions)
            if not checked:
                qs.append(f"Their statement “{ev.name.split(': ', 1)[-1]}” has not been checked against any record.")
    if alibi_status(view, char_key)["status"] == "unverified" and ch.is_suspect:
        qs.append("Where were they at the exact moment of death?")
    return qs[:6]


def dossier_view(view: SessionView, char_key: str) -> dict[str, Any]:
    case = view.case
    try:
        ch = case.char(char_key)
    except KeyError as e:
        raise NotFound("character") from e
    conv = view.conversations.get(char_key)
    stmts = [evidence_view(view, case.ev(k)) for k in sorted(view.held)
             if case.ev(k).is_testimony and char_key in case.ev(k).related_people]
    connections = []
    for k in sorted(view.held):
        ev = case.ev(k)
        if ev.is_testimony:
            continue
        bearing = [b for b in bearing_for(view, ev) if b["character"] == char_key]
        if char_key in ev.related_people or bearing:
            connections.append({"key": k, "name": ev.name, "stance": bearing[0]["stance"] if bearing else "related",
                                "note": bearing[0]["note"] if bearing else ""})
    return {
        "key": ch.key, "name": ch.name, "role": ch.role, "age": ch.age, "is_suspect": ch.is_suspect,
        "relationship_to_victim": ch.relationship_to_victim, "public_facts": list(ch.public_facts),
        "relationships": ch.relationships,
        "portrait": ch.portrait.__dict__,
        "interview": {"turns": conv.turns if conv else 0, "mood": conv.mood if conv else "unmet"},
        "statements": stmts, "evidence_connections": connections,
        "alibi": alibi_status(view, char_key), "unresolved_questions": unresolved_questions(view, char_key),
    }


def dossier_list(view: SessionView) -> list[dict[str, Any]]:
    out = []
    for ch in sorted(view.case.characters, key=lambda c: c.sort):
        conv = view.conversations.get(ch.key)
        out.append({"key": ch.key, "name": ch.name, "role": ch.role, "is_suspect": ch.is_suspect,
                    "portrait": ch.portrait.__dict__, "turns": conv.turns if conv else 0,
                    "mood": conv.mood if conv else "unmet", "alibi_status": alibi_status(view, ch.key)["status"]})
    return out


def overview(view: SessionView) -> dict[str, Any]:
    s = view.session
    case = view.case
    vis_total = sum(1 for loc in case.locations if loc.key in view.unlocked
                    for h in loc.hotspots if _hotspot_visible(view, h))
    searched = sum(1 for loc in case.locations if loc.key in view.unlocked
                   for h in loc.hotspots if _hotspot_visible(view, h) and all(y in view.held for y in h.yields))
    suspects = [c for c in case.characters]
    interviewed = sum(1 for c in suspects if (view.conversations.get(c.key) and view.conversations[c.key].turns > 0))
    examined = sum(1 for d in view.found.values() if d.examined)
    explore_ratio = searched / vis_total if vis_total else 0.0
    interview_ratio = interviewed / len(suspects)
    exam_ratio = examined / len(view.found) if view.found else 0.0
    progress = round(100 * (0.5 * explore_ratio + 0.3 * interview_ratio + 0.2 * exam_ratio))
    recent = sorted(view.found.values(), key=lambda d: d.action_no, reverse=True)[:5]
    return {
        "id": s.id, "case_id": s.case_id, "case_title": case.title, "tagline": case.tagline, "mode": s.mode,
        "status": s.status, "attempts": s.attempts, "max_attempts": case.accusation.max_attempts,
        "reputation": s.reputation, "hints_used": s.hints_used, "actions": s.actions, "version": s.version,
        "score": s.score, "created_at": s.created_at.isoformat(), "updated_at": s.updated_at.isoformat(),
        "briefing": case.briefing,
        "progress": {"percent": progress, "evidence": len(view.found), "examined": examined,
                     "contradictions": len(view.contradictions), "interviewed": interviewed,
                     "suspects": len(suspects), "places_searched": searched, "places_visible": vis_total},
        "unreviewed_evidence": [{"key": k, "name": case.ev(k).name} for k, d in view.found.items() if not d.examined][:8],
        "recent_discoveries": [{"key": d.evidence_key, "name": case.ev(d.evidence_key).name} for d in recent],
        "suspect_updates": [
            {"key": c.key, "name": c.name, "mood": view.conversations[c.key].mood, "turns": view.conversations[c.key].turns}
            for c in suspects if c.key in view.conversations and view.conversations[c.key].turns > 0
        ],
        "locations": locations_view(view),
        "clock_known": clock_known(case, view.held),
    }


def assert_active(view: SessionView) -> None:
    if view.session.status == "solved":
        raise Conflict("case_closed", "This case is closed.")
