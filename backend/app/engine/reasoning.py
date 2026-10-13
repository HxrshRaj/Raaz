"""Hypothesis evaluation and the final accusation — deterministic, transparent, evidence-based.

The rubric (`AccusationSpec.requirements`) is scored against evidence the player *actually holds*; no LLM
participates in scoring.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..errors import Conflict, DomainError, Forbidden, NotFound
from ..models import Accusation, Conversation, GameSession, Hypothesis, Report
from .game import alibi_status, bearing_for, contradiction_view, visible_events
from .state import SessionView, load_view

MAX_HYPOTHESES = 12


# --------------------------------------------------------------------------- hypotheses
def evaluate(view: SessionView, culprit_key: str | None, motive_key: str | None) -> dict[str, Any]:
    case = view.case
    if culprit_key is None:
        return {"strength": 0, "supporting": [], "opposing": [], "undermined_claims": [], "contradictions": [],
                "alibi": None, "open_questions": ["Pick a suspect to evaluate."], "motive_fit": None}
    if not any(c.key == culprit_key for c in case.characters if c.is_suspect):
        raise NotFound("suspect")
    supporting, opposing, undermined = [], [], []
    aspects: set[str] = set()
    for k in sorted(view.held):
        ev = case.ev(k)
        for b in bearing_for(view, ev):
            if b["character"] != culprit_key:
                continue
            row = {"key": k, "name": ev.name, "note": b["note"], "aspect": b["aspect"]}
            if b["stance"] == "points_to":
                supporting.append(row)
                aspects.add(b["aspect"])
            elif b["stance"] == "clears":
                opposing.append(row)
            else:
                undermined.append(row)
                aspects.add("claim")
    contradictions = [contradiction_view(view, r) for r in case.contradictions
                      if r.about == culprit_key and r.key in view.contradictions]
    alibi = alibi_status(view, culprit_key)
    open_q: list[str] = []
    name = case.char(culprit_key).name
    if "motive" not in aspects:
        open_q.append(f"Nothing in your evidence establishes a motive for {name}.")
    if "presence" not in aspects and "meeting" not in aspects:
        open_q.append(f"Nothing yet places {name} at the saloon or the siding.")
    if alibi["status"] == "cleared_for_window":
        open_q.append(alibi["statement"])
    elif not undermined and not contradictions:
        open_q.append(f"{name}'s account of the evening has not been broken by any record.")
    motive_fit = None
    if motive_key:
        m = next((x for x in case.motives if x.key == motive_key), None)
        if m is None:
            raise NotFound("motive")
        held_support = [k for k in m.support if k in view.held]
        motive_fit = {
            "label": m.label, "applies_to_suspect": (culprit_key in m.subjects) if m.subjects else False,
            "supporting_evidence": [{"key": k, "name": case.ev(k).name} for k in held_support],
        }
        if not held_support:
            open_q.append("You hold no evidence for the motive you chose.")
    strength = 0
    strength += 20 if "motive" in aspects else 0
    strength += 25 if "presence" in aspects else 0
    strength += 15 if "meeting" in aspects else 0
    strength += 20 if ("claim" in aspects or contradictions) else 0
    strength += 20 if alibi["status"] != "cleared_for_window" else -40
    strength = max(0, min(100, strength))
    return {"strength": strength, "supporting": supporting, "opposing": opposing, "undermined_claims": undermined,
            "contradictions": contradictions, "alibi": alibi, "open_questions": open_q, "motive_fit": motive_fit}


def hypothesis_view(h: Hypothesis) -> dict[str, Any]:
    return {"id": h.id, "title": h.title, "culprit_key": h.culprit_key, "motive_key": h.motive_key,
            "evidence_for": h.evidence_for, "evidence_against": h.evidence_against, "evaluation": h.evaluation,
            "created_at": h.created_at.isoformat()}


def save_hypothesis(db: Session, view: SessionView, *, title: str, culprit_key: str | None, motive_key: str | None,
                    evidence_for: list[str], evidence_against: list[str], hypothesis_id: str | None = None) -> Hypothesis:
    for k in [*evidence_for, *evidence_against]:
        if k not in view.held:
            raise NotFound("evidence")
    ev = evaluate(view, culprit_key, motive_key)
    if hypothesis_id:
        h = db.get(Hypothesis, hypothesis_id)
        if h is None or h.session_id != view.session.id:
            raise NotFound("hypothesis")
    else:
        n = len(list(db.scalars(select(Hypothesis.id).where(Hypothesis.session_id == view.session.id))))
        if n >= MAX_HYPOTHESES:
            raise Conflict("too_many_hypotheses", "Retire an old theory first.")
        h = Hypothesis(session_id=view.session.id)
        db.add(h)
    h.title, h.culprit_key, h.motive_key = title.strip()[:200], culprit_key, motive_key
    h.evidence_for, h.evidence_against, h.evaluation = evidence_for, evidence_against, ev
    db.commit()
    return h


def delete_hypothesis(db: Session, view: SessionView, hid: str) -> None:
    h = db.get(Hypothesis, hid)
    if h is None or h.session_id != view.session.id:
        raise NotFound("hypothesis")
    db.delete(h)
    db.commit()


# --------------------------------------------------------------------------- accusation
def _lcs(a: list[str], b: list[str]) -> int:
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a)):
        for j in range(len(b)):
            dp[i + 1][j + 1] = dp[i][j] + 1 if a[i] == b[j] else max(dp[i][j + 1], dp[i + 1][j])
    return dp[-1][-1]


def score(view: SessionView, payload: dict[str, Any]) -> dict[str, Any]:
    """Pure function: (session view, validated payload) -> report. No side effects."""
    case = view.case
    spec = case.accusation
    held = view.held
    culprit = payload["culprit"]
    right_culprit = culprit == spec.culprit
    criteria: list[dict[str, Any]] = []
    name = case.char(culprit).name

    # evidence annotations relative to the accused
    annotations = []
    for k in payload["evidence"]:
        ev = case.ev(k)
        bears = [b for b in bearing_for(view, ev) if b["character"] == culprit]
        role = "neutral"
        note = "Does not bear directly on this suspect."
        if any(b["stance"] == "clears" for b in bears):
            role, note = "contradicts", next(b["note"] for b in bears if b["stance"] == "clears")
        elif bears:
            role, note = "supports", bears[0]["note"]
        elif right_culprit and any(k in r.any_of for r in spec.requirements):
            role, note = "supports", "Bears on the case against the accused."
        annotations.append({"key": k, "name": ev.name, "role": role, "note": note})

    # --- suspect
    if right_culprit:
        criteria.append({"key": "culprit", "label": "The accused", "status": "supported", "points": 35, "max": 35,
                         "message": f"The evidence you hold is consistent with {name} being responsible."})
    else:
        ev_alibi = alibi_status(view, culprit)
        msg = (ev_alibi["statement"] if ev_alibi["status"] == "cleared_for_window"
               else f"Nothing you submitted places {name} in the saloon at the time of death.")
        criteria.append({"key": "culprit", "label": "The accused",
                         "status": "contradicted" if ev_alibi["status"] == "cleared_for_window" else "unsupported",
                         "points": 0, "max": 35, "message": msg})

    # --- motive
    mk = payload["motive"]
    if right_culprit and mk == spec.motive:
        mp, mst, mmsg = 15, "supported", "The motive you named fits the record."
    elif right_culprit and mk in spec.motive_partial:
        mp, mst, mmsg = 7, "partial", "Part of the picture, but it misses the sharper grievance behind it."
    else:
        mp, mst, mmsg = 0, "unsupported", "That motive is not supported for this suspect."
    criteria.append({"key": "motive", "label": "Motive", "status": mst, "points": mp, "max": 15, "message": mmsg})

    # --- sequence
    seq = [e for e in dict.fromkeys(payload["event_sequence"])]
    canon = [e for e in seq if e in spec.canonical_sequence]
    sp = 0
    if right_culprit and len(canon) >= spec.min_sequence:
        order = [e for e in spec.canonical_sequence if e in canon]
        lcs = _lcs(canon, order)
        sp = round(15 * (lcs / len(canon)) * min(1.0, lcs / 6))
        smsg = f"{lcs} of {len(canon)} events are in the right order."
        sst = "supported" if lcs == len(canon) and len(canon) >= 6 else "partial" if sp else "unsupported"
    elif right_culprit:
        smsg, sst = f"Arrange at least {spec.min_sequence} events of the night in order.", "unsupported"
    else:
        smsg, sst = "A sequence can't support an accusation of the wrong person.", "unsupported"
    criteria.append({"key": "sequence", "label": "Reconstructed sequence", "status": sst, "points": sp, "max": 15,
                     "message": smsg})

    # --- evidence rubric
    submitted = set(payload["evidence"])
    ep = 0.0
    satisfied: list[str] = []
    ev_rows: list[dict[str, Any]] = []
    for req in spec.requirements:
        got = [k for k in req.any_of if k in submitted and k in held]
        if right_culprit and len(got) >= req.need:
            pts, st, sat = req.weight, "supported", True
        elif right_culprit and got:
            pts, st, sat = req.weight / 2, "partial", False
        else:
            pts, st, sat = 0.0, "unsupported", False
        if sat:
            satisfied.append(req.key)
        ep += pts
        ev_rows.append({"key": req.key, "label": req.label, "status": st, "points": round(pts, 1), "max": req.weight,
                        "evidence": [{"key": k, "name": case.ev(k).name} for k in got]})
    ep_i = round(ep)
    criteria.append({"key": "evidence", "label": "Supporting evidence", "status":
                     "supported" if len(satisfied) >= spec.closing_threshold else "partial" if ep_i else "unsupported",
                     "points": ep_i, "max": 25, "message": f"{len(satisfied)} of {len(spec.requirements)} evidence "
                     "requirements met.", "rows": ev_rows})

    # --- contradictions
    explained = [k for k in payload["contradictions"] if k in spec.key_contradictions and k in view.contradictions]
    cp = round(10 * len(explained) / len(spec.key_contradictions)) if right_culprit else 0
    criteria.append({"key": "contradictions", "label": "Contradictions explained",
                     "status": "supported" if cp >= 8 else "partial" if cp else "unsupported", "points": cp, "max": 10,
                     "message": f"{len(explained)} of the {len(spec.key_contradictions)} decisive contradictions explained.",
                     "explained": [contradiction_view(view, next(r for r in case.contradictions if r.key == k))
                                   for k in explained]})

    total = sum(c["points"] for c in criteria)
    must = any(k in satisfied for k in spec.must_have_any_of)
    closed = (right_culprit and len(satisfied) >= spec.closing_threshold and must and mst in ("supported", "partial"))
    if closed:
        verdict = "case_closed"
    elif right_culprit:
        verdict = "insufficient_evidence"
    else:
        verdict = "wrong_suspect"

    next_steps: list[str] = []
    if verdict == "insufficient_evidence":
        for row in ev_rows:
            if row["status"] != "supported":
                next_steps.append(f"Establish: {row['label'].lower()}.")
        if mst != "supported":
            next_steps.append("Reconsider your stated motive.")
    elif verdict == "wrong_suspect":
        next_steps.append("Re-examine who could physically have been in the saloon at 22:58:41 real time.")
        next_steps.append("Compare each statement you have collected with the records.")
    return {"verdict": verdict, "score": total, "right_culprit": right_culprit if verdict == "case_closed" else None,
            "criteria": criteria, "evidence_annotations": annotations, "next_steps": next_steps,
            "closed": closed, "accused": culprit}


def validate_payload(view: SessionView, p: dict[str, Any]) -> dict[str, Any]:
    case = view.case
    if not any(c.key == p["culprit"] and c.is_suspect for c in case.characters):
        raise NotFound("suspect")
    if p["motive"] not in {m.key for m in case.motives}:
        raise NotFound("motive")
    vis = {e["key"] for e in visible_events(view)}
    for e in p["event_sequence"]:
        if e not in vis:
            raise DomainError("unknown_event", "One of the events in your sequence is not part of your investigation yet.")
    for k in p["evidence"]:
        if k not in view.held:
            raise NotFound("evidence")
    for k in p["contradictions"]:
        if k not in view.contradictions:
            raise DomainError("unknown_contradiction", "You haven't established that contradiction.")
    if len(p["evidence"]) > 80 or len(p["event_sequence"]) > 12:
        raise DomainError("too_large", "Too many items submitted.")
    return {**p, "evidence": list(dict.fromkeys(p["evidence"])), "contradictions": list(dict.fromkeys(p["contradictions"]))}


def accuse(db: Session, view: SessionView, payload: dict[str, Any]) -> dict[str, Any]:
    s = view.session
    spec = view.case.accusation
    if s.status == "solved":
        raise Conflict("case_closed", "This case is already closed.")
    if s.status == "closed_unsolved" or s.attempts >= spec.max_attempts:
        raise Conflict("case_cold", "The case has gone cold. Reopen it to try again.")
    p = validate_payload(view, payload)
    result = score(view, p)
    expected = s.attempts
    new_status = "solved" if result["closed"] else ("closed_unsolved" if expected + 1 >= spec.max_attempts else "active")
    rep_delta = 0 if result["closed"] else (-15 if result["verdict"] == "wrong_suspect" else -5)
    # Conditional update: two concurrent submissions can't both consume the same attempt.
    res = db.execute(
        update(GameSession)
        .where(GameSession.id == s.id, GameSession.attempts == expected, GameSession.status == "active")
        .values(attempts=expected + 1, status=new_status, reputation=GameSession.reputation + rep_delta,
                version=GameSession.version + 1,
                score=result["score"] if result["closed"] else GameSession.score,
                completed_at=datetime.now(UTC) if result["closed"] else None)
    )
    if (res.rowcount or 0) != 1:
        db.rollback()
        raise Conflict("concurrent_accusation", "Another accusation was processed first. Reload and try again.")
    result["attempt"] = expected + 1
    result["attempts_left"] = max(0, spec.max_attempts - (expected + 1))
    result["status"] = new_status
    result["reputation_delta"] = rep_delta
    if result["closed"]:
        result["solution"] = view.case.solution_narrative
    elif result["verdict"] == "wrong_suspect":
        # in-game consequence: the accused lawyers up
        conv = db.scalar(select(Conversation).where(Conversation.session_id == s.id, Conversation.character_key == p["culprit"]))
        if conv:
            conv.trust = max(0.0, conv.trust - 30)
            conv.mood = "hostile"
        result["consequence"] = (f"{view.case.char(p['culprit']).name} is released and speaks to a lawyer. "
                                 "Trust across the station drops.")
    db.add(Accusation(session_id=s.id, attempt_no=expected + 1, payload=p, score=result["score"], verdict=result["verdict"],
                      report=result))
    db.add(Report(session_id=s.id, kind="final", content=result))
    db.commit()
    return result


def reopen(db: Session, view: SessionView) -> None:
    s = view.session
    if s.status == "solved":
        raise Forbidden("case_closed", "A closed case stays closed.")
    db.execute(update(GameSession).where(GameSession.id == s.id).values(status="active", attempts=0,
                                                                         version=GameSession.version + 1))
    db.commit()


def history(db: Session, session_id: str) -> list[dict[str, Any]]:
    rows = db.scalars(select(Accusation).where(Accusation.session_id == session_id).order_by(Accusation.attempt_no))
    return [{"attempt": r.attempt_no, "verdict": r.verdict, "score": r.score, "accused": r.payload.get("culprit"),
             "report": r.report, "created_at": r.created_at.isoformat()} for r in rows]


def refreshed(db: Session, session: GameSession) -> SessionView:
    db.refresh(session)
    return load_view(db, session)

