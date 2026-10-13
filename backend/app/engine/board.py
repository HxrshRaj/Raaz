"""Investigation board: pinned items and meaningful, server-validated connections."""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from ..errors import Conflict, DomainError, NotFound
from ..models import BoardItem, BoardLink
from .game import bearing_for, matching_rule, record_contradiction
from .state import SessionView, bump

KINDS = ("evidence", "person", "location", "note")
RELATIONS = ("related", "supports", "contradicts", "implicates", "clears", "located_at", "happened_at")
MAX_ITEMS = 80
MAX_LINKS = 200


def classify_note(text: str) -> str | None:
    """Best-effort ML clue category for a free-text note (see app.ml). Never required for gameplay."""
    try:
        from ..ml.service import predict_category

        return predict_category(text)
    except Exception:  # noqa: BLE001 - model may not be trained/available; board must keep working
        return None


def _label(view: SessionView, kind: str, ref: str) -> str:
    case = view.case
    if kind == "evidence":
        return case.ev(ref).name
    if kind == "person":
        return "Adrian Vale" if ref == "adrian" else case.char(ref).name
    if kind == "location":
        return case.loc(ref).name
    return ref


def board_view(db: Session, view: SessionView) -> dict[str, Any]:
    sid = view.session.id
    items = list(db.scalars(select(BoardItem).where(BoardItem.session_id == sid).order_by(BoardItem.created_at)))
    links = list(db.scalars(select(BoardLink).where(BoardLink.session_id == sid).order_by(BoardLink.created_at)))
    return {
        "items": [{"id": i.id, "kind": i.kind, "ref_key": i.ref_key, "label": i.label or _label(view, i.kind, i.ref_key)
                   if i.kind != "note" else i.label, "note": i.note, "x": i.x, "y": i.y,
                   "predicted_category": i.predicted_category} for i in items],
        "links": [{"id": link.id, "from": link.from_item, "to": link.to_item, "relation": link.relation,
                   "note": link.note, "validated": link.validated, "rule_key": link.rule_key} for link in links],
        "relations": list(RELATIONS),
    }


def add_item(db: Session, view: SessionView, *, kind: str, ref_key: str, x: float, y: float, text: str = "") -> BoardItem:
    case = view.case
    if kind not in KINDS:
        raise DomainError("bad_kind", "Unknown board item type.")
    count = len(list(db.scalars(select(BoardItem.id).where(BoardItem.session_id == view.session.id))))
    if count >= MAX_ITEMS:
        raise Conflict("board_full", "Your board is full.")
    label = ""
    predicted = None
    if kind == "evidence":
        if ref_key not in view.held:
            raise NotFound("evidence")
    elif kind == "person":
        if ref_key != "adrian" and not any(c.key == ref_key for c in case.characters):
            raise NotFound("character")
    elif kind == "location":
        if not any(loc.key == ref_key for loc in case.locations):
            raise NotFound("location")
        if ref_key not in view.unlocked:
            raise NotFound("location")
    else:  # note
        text = text.strip()
        if not text:
            raise DomainError("empty_note", "A note needs some text.")
        label = text[:200]
        ref_key = f"note-{count + 1}-{abs(hash(text)) % 10**6}"
        predicted = classify_note(text)
    existing = db.scalar(select(BoardItem).where(BoardItem.session_id == view.session.id, BoardItem.kind == kind,
                                                 BoardItem.ref_key == ref_key))
    if existing:
        return existing
    it = BoardItem(session_id=view.session.id, kind=kind, ref_key=ref_key, label=label, x=x, y=y,
                   predicted_category=predicted)
    db.add(it)
    bump(db, view.session.id, actions=0)
    db.commit()
    return it


def move_item(db: Session, view: SessionView, item_id: str, x: float, y: float) -> BoardItem:
    it = db.get(BoardItem, item_id)
    if it is None or it.session_id != view.session.id:
        raise NotFound("board item")
    it.x, it.y = x, y
    db.commit()
    return it


def delete_item(db: Session, view: SessionView, item_id: str) -> None:
    it = db.get(BoardItem, item_id)
    if it is None or it.session_id != view.session.id:
        raise NotFound("board item")
    db.execute(delete(BoardLink).where(BoardLink.session_id == view.session.id,
                                       or_(BoardLink.from_item == item_id, BoardLink.to_item == item_id)))
    db.delete(it)
    db.commit()


def _assess(view: SessionView, a: BoardItem, b: BoardItem, relation: str) -> tuple[bool, str | None, str]:
    """Is this connection backed by the record? Returns (validated, contradiction_rule_key, message)."""
    case = view.case
    kinds = {a.kind, b.kind}
    if a.kind == "note" or b.kind == "note":
        return False, None, "A note is your own theory; it can't be validated against the record."
    if relation == "contradicts":
        if a.kind == b.kind == "evidence":
            m = matching_rule(case, a.ref_key, b.ref_key)
            if m:
                return True, m[0].key, "Contradiction established."
        return False, None, "That conflict can't be established from the record (yet)."
    ev_item = a if a.kind == "evidence" else b if b.kind == "evidence" else None
    other = b if ev_item is a else a
    if ev_item is None:
        return False, None, "Connections between places and people are only theory unless evidence ties them."
    ev = case.ev(ev_item.ref_key)
    if other.kind == "person" and relation in ("implicates", "supports", "clears", "related"):
        bearing = [x for x in bearing_for(view, ev) if x["character"] == other.ref_key]
        if relation == "clears":
            return any(x["stance"] == "clears" for x in bearing), None, "Checked against what the evidence shows."
        if relation in ("implicates", "supports"):
            return any(x["stance"] in ("points_to", "undermines_claim") for x in bearing), None, \
                "Checked against what the evidence shows."
        return other.ref_key in ev.related_people or bool(bearing), None, "Checked against the record."
    if other.kind == "location" and relation in ("located_at", "related"):
        return ev.location == other.ref_key, None, "Checked against where the evidence was found."
    if other.kind == "evidence":
        if relation not in ("related", "supports"):
            return False, None, "That kind of connection doesn't apply between two items of evidence."
        e2 = case.ev(other.ref_key)
        shared = set(ev.related_people) & set(e2.related_people) or set(ev.events) & set(e2.events)
        return bool(shared), None, "Checked against shared people and events."
    if kinds == {"evidence"}:
        return False, None, "No link established."
    return False, None, "No link established."


def add_link(db: Session, view: SessionView, *, from_id: str, to_id: str, relation: str, note: str = "") -> dict[str, Any]:
    if relation not in RELATIONS:
        raise DomainError("bad_relation", "Unknown connection type.")
    if from_id == to_id:
        raise DomainError("self_link", "Pick two different items.")
    a, b = db.get(BoardItem, from_id), db.get(BoardItem, to_id)
    if not a or not b or a.session_id != view.session.id or b.session_id != view.session.id:
        raise NotFound("board item")
    n = len(list(db.scalars(select(BoardLink.id).where(BoardLink.session_id == view.session.id))))
    if n >= MAX_LINKS:
        raise Conflict("board_full", "Too many connections.")
    existing = db.scalar(select(BoardLink).where(BoardLink.session_id == view.session.id, BoardLink.from_item == from_id,
                                                 BoardLink.to_item == to_id, BoardLink.relation == relation))
    validated, rule_key, message = _assess(view, a, b, relation)
    newly = False
    contradiction = None
    if validated and rule_key:
        rule = next(r for r in view.case.contradictions if r.key == rule_key)
        newly = record_contradiction(db, view, rule, "board")
        from .game import contradiction_view

        contradiction = contradiction_view(view, rule)
    if existing:
        link = existing
        link.validated, link.rule_key, link.note = validated, rule_key, note[:300]
    else:
        link = BoardLink(session_id=view.session.id, from_item=from_id, to_item=to_id, relation=relation,
                         note=note[:300], validated=validated, rule_key=rule_key)
        db.add(link)
    bump(db, view.session.id, actions=0)
    db.commit()
    return {"link": {"id": link.id, "from": link.from_item, "to": link.to_item, "relation": link.relation,
                     "note": link.note, "validated": link.validated, "rule_key": link.rule_key},
            "message": message, "newly_found_contradiction": newly, "contradiction": contradiction}


def delete_link(db: Session, view: SessionView, link_id: str) -> None:
    link = db.get(BoardLink, link_id)
    if link is None or link.session_id != view.session.id:
        raise NotFound("connection")
    db.delete(link)
    db.commit()
