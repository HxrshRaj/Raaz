"""SQLAlchemy 2.x models.

Catalog tables (cases, locations, characters, evidence) hold only **player-safe** public columns; the
private canonical specification stays in the server-side case package and is never stored in a table that
a public endpoint reads.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return uuid.uuid4().hex


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# --------------------------------------------------------------------------- users
class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    display_name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_guest: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    profile: Mapped[PlayerProfile] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class PlayerProfile(Base, TimestampMixin):
    __tablename__ = "player_profiles"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    stats: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    user: Mapped[User] = relationship(back_populates="profile")


# --------------------------------------------------------------------------- catalog (public columns only)
class Case(Base, TimestampMixin):
    __tablename__ = "cases"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    tagline: Mapped[str] = mapped_column(String(300), default="")
    summary: Mapped[str] = mapped_column(Text, default="")


class CaseVersion(Base, TimestampMixin):
    __tablename__ = "case_versions"
    __table_args__ = (UniqueConstraint("case_id", "version"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    version: Mapped[str] = mapped_column(String(32))
    content_hash: Mapped[str] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Location(Base):
    __tablename__ = "locations"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True)
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    initially_unlocked: Mapped[bool] = mapped_column(Boolean, default=True)
    off_site: Mapped[bool] = mapped_column(Boolean, default=False)
    sort: Mapped[int] = mapped_column(Integer, default=0)


class Character(Base):
    __tablename__ = "characters"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True)
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(160))
    is_suspect: Mapped[bool] = mapped_column(Boolean, default=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)


class Evidence(Base):
    __tablename__ = "evidence"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True)
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(32))
    location_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_testimony: Mapped[bool] = mapped_column(Boolean, default=False)


# --------------------------------------------------------------------------- sessions & progress
class GameSession(Base, TimestampMixin):
    __tablename__ = "game_sessions"
    __table_args__ = (
        CheckConstraint("attempts >= 0", name="ck_attempts_nonneg"),
        Index("ix_sessions_user", "user_id", "updated_at"),
    )
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    case_version: Mapped[str] = mapped_column(String(32))
    mode: Mapped[str] = mapped_column(String(16), default="standard")  # standard | demo
    status: Mapped[str] = mapped_column(String(24), default="active")  # active|solved|closed_unsolved
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    actions: Mapped[int] = mapped_column(Integer, default=0)
    hints_used: Mapped[int] = mapped_column(Integer, default=0)
    reputation: Mapped[int] = mapped_column(Integer, default=100)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)  # optimistic concurrency token
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UnlockedLocation(Base, TimestampMixin):
    __tablename__ = "unlocked_locations"
    session_id: Mapped[str] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"), primary_key=True)
    location_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    via: Mapped[str] = mapped_column(String(64), default="start")


class EvidenceDiscovery(Base):
    __tablename__ = "evidence_discoveries"
    __table_args__ = (
        ForeignKeyConstraint(["case_id", "evidence_key"], ["evidence.case_id", "evidence.key"]),
        Index("ix_disc_session", "session_id", "discovered_at"),
    )
    session_id: Mapped[str] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"), primary_key=True)
    evidence_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(80))  # hotspot:loc/h | conversation:char | system
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    action_no: Mapped[int] = mapped_column(Integer, default=0)
    examined: Mapped[bool] = mapped_column(Boolean, default=False)
    examined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ContradictionFound(Base):
    __tablename__ = "contradictions_found"
    session_id: Mapped[str] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"), primary_key=True)
    rule_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    via: Mapped[str] = mapped_column(String(64))
    found_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Disclosure(Base):
    """A fact a character has voiced to the player (kind=public: their stated account; kind=reveal: the truth)."""

    __tablename__ = "disclosures"
    session_id: Mapped[str] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"), primary_key=True)
    character_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    fact_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(10), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# --------------------------------------------------------------------------- conversations
class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("session_id", "character_key"),
        ForeignKeyConstraint(["case_id", "character_key"], ["characters.case_id", "characters.key"]),
    )
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"))
    case_id: Mapped[str] = mapped_column(String(64))
    character_key: Mapped[str] = mapped_column(String(64))
    trust: Mapped[float] = mapped_column(Float, default=40.0)
    stress: Mapped[float] = mapped_column(Float, default=10.0)
    mood: Mapped[str] = mapped_column(String(24), default="guarded")
    turns: Mapped[int] = mapped_column(Integer, default=0)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation", order_by="Message.seq", cascade="all, delete-orphan"
    )


class Message(Base, TimestampMixin):
    __tablename__ = "messages"
    __table_args__ = (UniqueConstraint("conversation_id", "seq"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(10))  # player | npc | system
    content: Mapped[str] = mapped_column(Text)
    evidence_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class CharacterMemory(Base, TimestampMixin):
    __tablename__ = "character_memories"
    __table_args__ = (Index("ix_mem_session_char", "session_id", "character_key"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"))
    character_key: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(24))  # evidence_seen | said | summary | belief
    content: Mapped[str] = mapped_column(Text)


class NazarMessage(Base, TimestampMixin):
    __tablename__ = "nazar_messages"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(10))
    content: Mapped[str] = mapped_column(Text)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


# --------------------------------------------------------------------------- RAG
class RagChunk(Base, TimestampMixin):
    __tablename__ = "rag_chunks"
    __table_args__ = (
        Index("ix_rag_case_scope", "case_id", "scope"),
        Index("ix_rag_session", "session_id"),
    )
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    case_id: Mapped[str] = mapped_column(String(64))
    session_id: Mapped[str | None] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"), nullable=True)
    scope: Mapped[str] = mapped_column(String(24))  # case_doc | evidence | character | dialogue | memory
    character_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    required_evidence: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_ref: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(200), default="")
    text: Mapped[str] = mapped_column(Text)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    embedding: Mapped[list[float]] = mapped_column(JSON)


# --------------------------------------------------------------------------- board / timeline / hypotheses
class BoardItem(Base, TimestampMixin):
    __tablename__ = "board_items"
    __table_args__ = (UniqueConstraint("session_id", "kind", "ref_key"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(16))  # evidence | person | location | note
    ref_key: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(200), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    predicted_category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    x: Mapped[float] = mapped_column(Float, default=0.0)
    y: Mapped[float] = mapped_column(Float, default=0.0)


class BoardLink(Base, TimestampMixin):
    __tablename__ = "board_links"
    __table_args__ = (UniqueConstraint("session_id", "from_item", "to_item", "relation"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"), index=True)
    from_item: Mapped[str] = mapped_column(ForeignKey("board_items.id", ondelete="CASCADE"))
    to_item: Mapped[str] = mapped_column(ForeignKey("board_items.id", ondelete="CASCADE"))
    relation: Mapped[str] = mapped_column(String(24))  # related|supports|contradicts|located_at|happened_at
    note: Mapped[str] = mapped_column(Text, default="")
    validated: Mapped[bool] = mapped_column(Boolean, default=False)
    rule_key: Mapped[str | None] = mapped_column(String(64), nullable=True)


class TimelineEntry(Base, TimestampMixin):
    __tablename__ = "timeline_entries"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(300))
    time_hhmm: Mapped[str] = mapped_column(String(8))  # HH:MM or HH:MM:SS
    clock: Mapped[str] = mapped_column(String(4), default="RT")  # RT (real) | ST (station clock)
    actor_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    location_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_keys: Mapped[list[str]] = mapped_column(JSON, default=list)


class Hypothesis(Base, TimestampMixin):
    __tablename__ = "hypotheses"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    culprit_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    motive_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_for: Mapped[list[str]] = mapped_column(JSON, default=list)
    evidence_against: Mapped[list[str]] = mapped_column(JSON, default=list)
    evaluation: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Accusation(Base, TimestampMixin):
    __tablename__ = "accusations"
    __table_args__ = (UniqueConstraint("session_id", "attempt_no"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"), index=True)
    attempt_no: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    score: Mapped[int] = mapped_column(Integer)
    verdict: Mapped[str] = mapped_column(String(24))
    report: Mapped[dict[str, Any]] = mapped_column(JSON)


# --------------------------------------------------------------------------- agents / reports / jobs
class AgentRun(Base, TimestampMixin):
    __tablename__ = "agent_runs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"), index=True)
    question: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="queued")  # queued|running|succeeded|failed|cancelled
    plan: Mapped[list[Any]] = mapped_column(JSON, default=list)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    iterations: Mapped[int] = mapped_column(Integer, default=0)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    steps: Mapped[list[AgentStep]] = relationship(
        back_populates="run", order_by="AgentStep.idx", cascade="all, delete-orphan"
    )


class AgentStep(Base, TimestampMixin):
    __tablename__ = "agent_steps"
    __table_args__ = (UniqueConstraint("run_id", "idx"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True)
    idx: Mapped[int] = mapped_column(Integer)
    node: Mapped[str] = mapped_column(String(40))
    tool: Mapped[str | None] = mapped_column(String(60), nullable=True)
    args: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    summary: Mapped[str] = mapped_column(Text, default="")
    refs: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(12), default="ok")  # ok | denied | error
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    run: Mapped[AgentRun] = relationship(back_populates="steps")


class Report(Base, TimestampMixin):
    __tablename__ = "reports"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(24))  # investigation | final
    content: Mapped[dict[str, Any]] = mapped_column(JSON)


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    kind: Mapped[str] = mapped_column(String(40))
    session_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="queued")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# --------------------------------------------------------------------------- ML tracking, audit, idempotency
class MLExperiment(Base, TimestampMixin):
    __tablename__ = "ml_experiments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120))
    task: Mapped[str] = mapped_column(String(40))
    dataset_version: Mapped[str] = mapped_column(String(40))
    dataset_hash: Mapped[str] = mapped_column(String(64))
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    mlflow_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class ModelVersion(Base, TimestampMixin):
    __tablename__ = "model_versions"
    __table_args__ = (UniqueConstraint("name", "version"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    experiment_id: Mapped[int | None] = mapped_column(ForeignKey("ml_experiments.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(80))
    version: Mapped[str] = mapped_column(String(40))
    framework: Mapped[str] = mapped_column(String(24))
    artifact_path: Mapped[str] = mapped_column(String(300))
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuditEvent(Base, TimestampMixin):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    action: Mapped[str] = mapped_column(String(60))
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)


class IdempotencyKey(Base, TimestampMixin):
    __tablename__ = "idempotency_keys"
    user_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    route: Mapped[str] = mapped_column(String(120), primary_key=True)
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    status_code: Mapped[int] = mapped_column(Integer)
    response: Mapped[dict[str, Any]] = mapped_column(JSON)
