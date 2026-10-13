"""Access-controlled hybrid retrieval over `rag_chunks`.

ACL is applied **before** ranking and re-checked after: a chunk is returned only if it belongs to the case, the
requested scopes, the calling session (or is global), the requested character (for character-scoped knowledge),
and its `required_evidence` has been discovered by the player.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..models import RagChunk
from .embed import get_embedder, tokenize
from .lexical import BM25

RRF_K = 30


@dataclass
class Hit:
    chunk_id: str
    score: float
    text: str
    title: str
    scope: str
    source_ref: str
    character_key: str | None
    meta: dict[str, Any] = field(default_factory=dict)
    dense: float = 0.0
    lexical: float = 0.0

    def citation(self) -> dict[str, str]:
        return {"ref": self.source_ref, "title": self.title, "scope": self.scope}


def _allowed(row: RagChunk, *, session_id: str | None, character_key: str | None, held: frozenset[str],
             examined: frozenset[str]) -> bool:
    if row.session_id is not None and row.session_id != session_id:
        return False
    if row.scope == "character" and (character_key is None or row.character_key != character_key):
        return False
    if row.scope in ("dialogue", "memory") and (row.session_id != session_id or row.character_key != character_key):
        return False
    if row.required_evidence is not None and row.required_evidence not in held:
        return False
    if row.meta.get("requires_examined") and row.required_evidence not in examined:
        return False
    return True


def retrieve(db: Session, *, case_id: str, query: str, scopes: tuple[str, ...], session_id: str | None = None,
             character_key: str | None = None, held: frozenset[str] = frozenset(), examined: frozenset[str] = frozenset(),
             k: int = 5, min_score: float = 0.0, rerank: bool = True) -> list[Hit]:
    stmt = select(RagChunk).where(RagChunk.case_id == case_id, RagChunk.scope.in_(scopes))
    stmt = stmt.where(or_(RagChunk.session_id.is_(None), RagChunk.session_id == session_id))
    if character_key is None:
        stmt = stmt.where(RagChunk.scope != "character")
    else:
        stmt = stmt.where(or_(RagChunk.character_key.is_(None), RagChunk.character_key == character_key))
    rows = [r for r in db.scalars(stmt)
            if _allowed(r, session_id=session_id, character_key=character_key, held=held, examined=examined)]
    if not rows or not query.strip():
        return []
    emb = get_embedder()
    qv = emb.embed([query])[0]
    mat = np.asarray([r.embedding for r in rows], dtype=np.float32)
    dense = mat @ qv
    bm = BM25([f"{r.title} {r.text}" for r in rows])
    lex = np.asarray(bm.scores(query), dtype=np.float32)
    d_rank = {i: rank for rank, i in enumerate(np.argsort(-dense))}
    l_rank = {i: rank for rank, i in enumerate(np.argsort(-lex))}
    fused = []
    for i in range(len(rows)):
        s = 1.0 / (RRF_K + d_rank[i]) + (1.0 / (RRF_K + l_rank[i]) if lex[i] > 0 else 0.0)
        fused.append(s)
    order = sorted(range(len(rows)), key=lambda i: -fused[i])[: max(k * 3, k)]
    q_terms = set(tokenize(query))
    hits: list[Hit] = []
    for i in order:
        r = rows[i]
        score = fused[i]
        if rerank and q_terms:
            cover = len(q_terms & set(tokenize(r.title + " " + r.text))) / len(q_terms)
            score = score * (1 + cover)
        hits.append(Hit(r.id, float(score), r.text, r.title, r.scope, r.source_ref, r.character_key, dict(r.meta),
                        float(dense[i]), float(lex[i])))
    hits.sort(key=lambda h: -h.score)
    hits = [h for h in hits if h.dense >= min_score or h.lexical > 0][:k]
    return hits
