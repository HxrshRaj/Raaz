"""Document ingestion: chunking, metadata, embeddings. Idempotent per case content hash."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..cases.base import CaseSpec
from ..cases.registry import list_cases
from ..models import RagChunk
from .embed import get_embedder


def chunk_text(text: str, max_chars: int = 480, overlap: int = 60) -> list[str]:
    """Sentence-aware chunking with a small character overlap."""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_chars:
        return [text] if text else []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    cur = ""
    for s in sentences:
        if cur and len(cur) + len(s) + 1 > max_chars:
            chunks.append(cur)
            cur = (cur[-overlap:] + " " + s).strip() if overlap else s
        else:
            cur = (cur + " " + s).strip()
    if cur:
        chunks.append(cur)
    return chunks


def ingest_document(db: Session, *, case_id: str, scope: str, source_ref: str, title: str, text: str,
                    session_id: str | None = None, character_key: str | None = None,
                    required_evidence: str | None = None, meta: dict[str, Any] | None = None, commit: bool = True) -> int:
    parts = chunk_text(text)
    if not parts:
        return 0
    vecs = get_embedder().embed([f"{title}. {p}" for p in parts])
    for i, (p, v) in enumerate(zip(parts, vecs, strict=True)):
        db.add(RagChunk(case_id=case_id, session_id=session_id, scope=scope, character_key=character_key,
                        required_evidence=required_evidence, source_ref=source_ref if len(parts) == 1 else f"{source_ref}#{i}",
                        title=title, text=p, meta={**(meta or {}), "part": i, "parts": len(parts)},
                        embedding=[round(float(x), 5) for x in v]))
    if commit:
        db.commit()
    return len(parts)


def _ingest_case(db: Session, c: CaseSpec) -> int:
    n = 0
    for d in c.docs:
        n += ingest_document(db, case_id=c.id, scope="case_doc", source_ref=f"doc:{d.key}", title=d.title, text=d.text,
                             required_evidence=d.required_evidence, commit=False)
    for e in c.evidence:
        n += ingest_document(db, case_id=c.id, scope="evidence", source_ref=f"ev:{e.key}", title=e.name,
                             text=e.description, required_evidence=e.key, meta={"evidence": e.key}, commit=False)
        n += ingest_document(db, case_id=c.id, scope="evidence", source_ref=f"evx:{e.key}", title=f"{e.name} (examined)",
                             text=e.examined_detail, required_evidence=e.key,
                             meta={"evidence": e.key, "requires_examined": True}, commit=False)
    for ch in c.characters:
        prof = f"{ch.name}, {ch.role}. {ch.relationship_to_victim} " + " ".join(ch.public_facts)
        n += ingest_document(db, case_id=c.id, scope="character", source_ref=f"char:{ch.key}:profile", title=f"{ch.name} profile",
                             text=prof, character_key=ch.key, commit=False)
        for f in ch.facts:
            n += ingest_document(db, case_id=c.id, scope="character", source_ref=f"fact:{ch.key}:{f.key}", title=f.key,
                                 text=f"{' '.join(f.topics)}. {f.text}", character_key=ch.key,
                                 meta={"fact_key": f.key, "secret": f.secret}, commit=False)
    db.flush()
    return n


def ensure_case_corpus(db: Session) -> None:
    """(Re)build the shared, session-independent corpus whenever a case package changes."""
    for c in list_cases():
        marker = f"{c.id}:{c.content_hash()}:{get_embedder().name}"
        existing = db.scalar(select(RagChunk).where(RagChunk.case_id == c.id, RagChunk.scope == "meta"))
        if existing is not None and existing.source_ref == marker:
            continue
        db.execute(delete(RagChunk).where(RagChunk.case_id == c.id, RagChunk.session_id.is_(None)))
        _ingest_case(db, c)
        db.add(RagChunk(case_id=c.id, scope="meta", source_ref=marker, title="corpus marker", text="marker",
                        embedding=[0.0]))
        db.commit()


def add_dialogue_chunk(db: Session, *, case_id: str, session_id: str, character_key: str, text: str, ref: str,
                       scope: str = "dialogue", meta: dict[str, Any] | None = None) -> None:
    ingest_document(db, case_id=case_id, scope=scope, source_ref=ref, title=f"{scope} with {character_key}", text=text,
                    session_id=session_id, character_key=character_key, meta=meta, commit=False)
