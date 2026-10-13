from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import select

from ...cases.registry import list_cases
from ...deps import DB, CurrentUser, View, audit, rate_limit
from ...engine import board as board_svc
from ...engine import game as game_svc
from ...engine import reasoning
from ...engine import timeline as tl
from ...engine.state import load_view
from ...errors import NotFound
from ...models import GameSession, Hypothesis, IdempotencyKey, Report
from ...schemas.requests import (
    AccusationIn,
    BoardItemIn,
    BoardLinkIn,
    BoardMoveIn,
    ContradictionCheckIn,
    HypothesisEvalIn,
    HypothesisIn,
    SessionCreateIn,
    TimelineEntryIn,
)

router = APIRouter(tags=["game"], dependencies=[Depends(rate_limit("api"))])


# ----------------------------------------------------------------------- catalog & sessions
@router.get("/cases")
def cases(user: CurrentUser):
    return [{"id": c.id, "title": c.title, "tagline": c.tagline, "summary": c.summary, "version": c.version}
            for c in list_cases()]


@router.post("/sessions", status_code=201)
def create_session(body: SessionCreateIn, db: DB, user: CurrentUser, request: Request):
    s = game_svc.create_session(db, user, body.case_id, body.mode)
    audit(db, user_id=user.id, session_id=s.id, action="session.create", request=request, case=s.case_id, mode=s.mode)
    return game_svc.overview(load_view(db, s))


@router.get("/sessions")
def my_sessions(db: DB, user: CurrentUser):
    rows = db.scalars(select(GameSession).where(GameSession.user_id == user.id).order_by(GameSession.updated_at.desc()).limit(50))
    out = []
    for s in rows:
        ov = game_svc.overview(load_view(db, s))
        out.append({k: ov[k] for k in ("id", "case_id", "case_title", "mode", "status", "attempts", "progress", "updated_at",
                                       "created_at", "score")})
    return out


@router.get("/sessions/{session_id}")
def session_overview(view: View):
    return game_svc.overview(view)


@router.get("/progress")
def progress(db: DB, user: CurrentUser):
    rows = list(db.scalars(select(GameSession).where(GameSession.user_id == user.id)))
    solved = [s for s in rows if s.status == "solved"]
    return {"sessions": len(rows), "solved": len(solved), "best_score": max((s.score or 0 for s in solved), default=None),
            "total_actions": sum(s.actions for s in rows)}


# ----------------------------------------------------------------------- exploration
@router.get("/sessions/{session_id}/locations")
def locations(view: View):
    return game_svc.locations_view(view)


@router.get("/sessions/{session_id}/locations/{loc_key}")
def location(loc_key: str, view: View):
    return game_svc.location_detail(view, loc_key)


@router.post("/sessions/{session_id}/locations/{loc_key}/hotspots/{hotspot_key}/inspect")
def inspect(loc_key: str, hotspot_key: str, view: View, db: DB):
    return game_svc.inspect_hotspot(db, view, loc_key, hotspot_key)


# ----------------------------------------------------------------------- evidence
@router.get("/sessions/{session_id}/evidence")
def evidence(view: View):
    return game_svc.list_evidence(view)


@router.get("/sessions/{session_id}/evidence/timestamps")
def evidence_timestamps(view: View):
    return {"clock_known": game_svc.clock_known(view.case, view.held), "items": game_svc.evidence_timestamps(view)}


@router.get("/sessions/{session_id}/evidence/{ev_key}")
def evidence_one(ev_key: str, view: View):
    if ev_key not in view.found:
        raise NotFound("evidence")
    return game_svc.evidence_view(view, view.case.ev(ev_key))


@router.post("/sessions/{session_id}/evidence/{ev_key}/examine")
def examine(ev_key: str, view: View, db: DB):
    return game_svc.examine_evidence(db, view, ev_key)


@router.get("/sessions/{session_id}/contradictions")
def contradictions(view: View):
    return game_svc.contradictions_list(view)


@router.post("/sessions/{session_id}/contradictions/check")
def contradiction_check(body: ContradictionCheckIn, view: View, db: DB):
    return game_svc.check_contradiction(db, view, body.a, body.b)


@router.get("/sessions/{session_id}/events")
def events(view: View):
    return game_svc.visible_events(view)


# ----------------------------------------------------------------------- dossiers
@router.get("/sessions/{session_id}/dossiers")
def dossiers(view: View):
    return game_svc.dossier_list(view)


@router.get("/sessions/{session_id}/dossiers/{char_key}")
def dossier(char_key: str, view: View):
    return game_svc.dossier_view(view, char_key)


# ----------------------------------------------------------------------- board
@router.get("/sessions/{session_id}/board")
def board(view: View, db: DB):
    return board_svc.board_view(db, view)


@router.post("/sessions/{session_id}/board/items", status_code=201)
def board_add(body: BoardItemIn, view: View, db: DB):
    it = board_svc.add_item(db, view, kind=body.kind, ref_key=body.ref_key, x=body.x, y=body.y, text=body.text)
    return next(i for i in board_svc.board_view(db, view)["items"] if i["id"] == it.id)


@router.patch("/sessions/{session_id}/board/items/{item_id}")
def board_move(item_id: str, body: BoardMoveIn, view: View, db: DB):
    it = board_svc.move_item(db, view, item_id, body.x, body.y)
    return {"id": it.id, "x": it.x, "y": it.y}


@router.delete("/sessions/{session_id}/board/items/{item_id}", status_code=204)
def board_del(item_id: str, view: View, db: DB):
    board_svc.delete_item(db, view, item_id)


@router.post("/sessions/{session_id}/board/links", status_code=201)
def board_link(body: BoardLinkIn, view: View, db: DB):
    return board_svc.add_link(db, view, from_id=body.from_item, to_id=body.to_item, relation=body.relation, note=body.note)


@router.delete("/sessions/{session_id}/board/links/{link_id}", status_code=204)
def board_link_del(link_id: str, view: View, db: DB):
    board_svc.delete_link(db, view, link_id)


# ----------------------------------------------------------------------- timeline
@router.get("/sessions/{session_id}/timeline")
def timeline(view: View, db: DB):
    entries = tl.list_entries(db, view)
    return {"entries": [tl.entry_view(view, e) for e in entries], "validation": tl.validate(view, entries)}


@router.post("/sessions/{session_id}/timeline", status_code=201)
def timeline_add(body: TimelineEntryIn, view: View, db: DB):
    e = tl.add_entry(db, view, label=body.label, time=body.time, clock=body.clock, actor_key=body.actor_key,
                     location_key=body.location_key, evidence_keys=body.evidence_keys)
    entries = tl.list_entries(db, view)
    return {"entry": tl.entry_view(view, e), "validation": tl.validate(view, entries)}


@router.delete("/sessions/{session_id}/timeline/{entry_id}", status_code=204)
def timeline_del(entry_id: str, view: View, db: DB):
    tl.delete_entry(db, view, entry_id)


# ----------------------------------------------------------------------- hypotheses
@router.get("/sessions/{session_id}/hypotheses")
def hypotheses(view: View, db: DB):
    rows = db.scalars(select(Hypothesis).where(Hypothesis.session_id == view.session.id).order_by(Hypothesis.created_at))
    return [reasoning.hypothesis_view(h) for h in rows]


@router.post("/sessions/{session_id}/hypotheses/evaluate")
def hypothesis_eval(body: HypothesisEvalIn, view: View):
    return reasoning.evaluate(view, body.culprit_key, body.motive_key)


@router.post("/sessions/{session_id}/hypotheses", status_code=201)
def hypothesis_create(body: HypothesisIn, view: View, db: DB):
    h = reasoning.save_hypothesis(db, view, title=body.title, culprit_key=body.culprit_key, motive_key=body.motive_key,
                                  evidence_for=body.evidence_for, evidence_against=body.evidence_against)
    return reasoning.hypothesis_view(h)


@router.put("/sessions/{session_id}/hypotheses/{hid}")
def hypothesis_update(hid: str, body: HypothesisIn, view: View, db: DB):
    h = reasoning.save_hypothesis(db, view, title=body.title, culprit_key=body.culprit_key, motive_key=body.motive_key,
                                  evidence_for=body.evidence_for, evidence_against=body.evidence_against, hypothesis_id=hid)
    return reasoning.hypothesis_view(h)


@router.delete("/sessions/{session_id}/hypotheses/{hid}", status_code=204)
def hypothesis_delete(hid: str, view: View, db: DB):
    reasoning.delete_hypothesis(db, view, hid)


# ----------------------------------------------------------------------- accusation
@router.get("/sessions/{session_id}/accusation/options")
def accusation_options(view: View):
    case = view.case
    return {
        "suspects": [{"key": c.key, "name": c.name, "role": c.role} for c in sorted(case.characters, key=lambda x: x.sort)
                     if c.is_suspect],
        "motives": [{"key": m.key, "label": m.label, "description": m.description} for m in case.motives],
        "events": game_svc.visible_events(view),
        "evidence": [e for e in game_svc.list_evidence(view)],
        "contradictions": game_svc.contradictions_list(view),
        "attempts": view.session.attempts, "max_attempts": case.accusation.max_attempts, "status": view.session.status,
        "rubric": [{"key": r.key, "label": r.label, "weight": r.weight} for r in case.accusation.requirements]
                  + [{"key": "culprit", "label": "The accused", "weight": 35}, {"key": "motive", "label": "Motive", "weight": 15},
                     {"key": "sequence", "label": "Reconstructed sequence", "weight": 15},
                     {"key": "contradictions", "label": "Contradictions explained", "weight": 10}],
    }


@router.post("/sessions/{session_id}/accusation")
def accuse(body: AccusationIn, view: View, db: DB, user: CurrentUser, request: Request,
           idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=80)):
    route = f"accuse:{view.session.id}"
    if idempotency_key:
        prev = db.get(IdempotencyKey, (user.id, route, idempotency_key))
        if prev is not None:
            return prev.response
    result = reasoning.accuse(db, view, body.model_dump())
    audit(db, user_id=user.id, session_id=view.session.id, action="accusation.submit", request=request,
          accused=body.culprit, verdict=result["verdict"], score=result["score"])
    if idempotency_key:
        db.add(IdempotencyKey(user_id=user.id, route=route, key=idempotency_key, status_code=200, response=result))
        db.commit()
    return result


@router.get("/sessions/{session_id}/accusation/history")
def accusation_history(view: View, db: DB):
    return reasoning.history(db, view.session.id)


@router.post("/sessions/{session_id}/reopen")
def reopen(view: View, db: DB, user: CurrentUser, request: Request):
    reasoning.reopen(db, view)
    audit(db, user_id=user.id, session_id=view.session.id, action="session.reopen", request=request)
    db.refresh(view.session)
    return game_svc.overview(load_view(db, view.session))


@router.get("/sessions/{session_id}/reports")
def reports(view: View, db: DB):
    rows = db.scalars(select(Report).where(Report.session_id == view.session.id).order_by(Report.created_at.desc()).limit(30))
    return [{"id": r.id, "kind": r.kind, "created_at": r.created_at.isoformat(), "content": r.content} for r in rows]
