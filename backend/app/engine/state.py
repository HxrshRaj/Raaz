from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import Session

from ..cases.base import CaseSpec
from ..cases.registry import get_case
from ..errors import NotFound
from ..models import (
    ContradictionFound,
    Conversation,
    Disclosure,
    EvidenceDiscovery,
    GameSession,
    UnlockedLocation,
)


@dataclass
class SessionView:
    session: GameSession
    case: CaseSpec
    found: dict[str, EvidenceDiscovery] = field(default_factory=dict)
    unlocked: dict[str, UnlockedLocation] = field(default_factory=dict)
    contradictions: dict[str, ContradictionFound] = field(default_factory=dict)
    disclosures: set[tuple[str, str, str]] = field(default_factory=set)
    conversations: dict[str, Conversation] = field(default_factory=dict)

    @property
    def held(self) -> set[str]:
        return set(self.found)

    def revealed(self, char: str) -> set[str]:
        return {f for (c, f, k) in self.disclosures if c == char and k == "reveal"}

    def said(self, char: str) -> set[str]:
        return {f for (c, f, _k) in self.disclosures if c == char}


def get_owned_session(db: Session, user_id: str, session_id: str) -> GameSession:
    s = db.get(GameSession, session_id)
    # Same 404 for "missing" and "someone else's": no existence oracle for other players' sessions.
    if s is None or s.user_id != user_id:
        raise NotFound("investigation")
    return s


def load_view(db: Session, session: GameSession) -> SessionView:
    case = get_case(session.case_id)
    sid = session.id
    found = {r.evidence_key: r for r in db.scalars(select(EvidenceDiscovery).where(EvidenceDiscovery.session_id == sid))}
    unlocked = {r.location_key: r for r in db.scalars(select(UnlockedLocation).where(UnlockedLocation.session_id == sid))}
    contras = {r.rule_key: r for r in db.scalars(select(ContradictionFound).where(ContradictionFound.session_id == sid))}
    disc = {(r.character_key, r.fact_key, r.kind) for r in db.scalars(select(Disclosure).where(Disclosure.session_id == sid))}
    convs = {r.character_key: r for r in db.scalars(select(Conversation).where(Conversation.session_id == sid))}
    return SessionView(session, case, found, unlocked, contras, disc, convs)


def insert_ignore(db: Session, model, values: dict) -> bool:
    """Atomic `INSERT ... ON CONFLICT DO NOTHING`; returns True only for the request that actually inserted.

    This is what makes one-time discoveries race-safe: two simultaneous requests cannot both succeed.
    """
    dialect = db.get_bind().dialect.name
    stmt: Any
    if dialect == "sqlite":
        stmt = sqlite.insert(model).values(**values).on_conflict_do_nothing()
    elif dialect == "postgresql":
        stmt = postgresql.insert(model).values(**values).on_conflict_do_nothing()
    else:  # pragma: no cover
        raise RuntimeError(f"unsupported dialect {dialect}")
    # RETURNING (not rowcount): drivers report rowcount unreliably (-1) for INSERT .. ON CONFLICT on PostgreSQL.
    pk_col = next(iter(model.__table__.primary_key.columns))
    return db.execute(stmt.returning(pk_col)).first() is not None


def bump(db: Session, session_id: str, *, actions: int = 1) -> None:
    """Atomic counter/version bump (no read-modify-write, so concurrent requests can't lose updates)."""
    db.execute(
        update(GameSession)
        .where(GameSession.id == session_id)
        .values(actions=GameSession.actions + actions, version=GameSession.version + 1)
    )
