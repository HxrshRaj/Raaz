"""Typed, permissioned tools available to investigation agents.

Rules enforced here (not trusted to the agents):
  * every tool takes a pydantic-validated argument model and returns a plain dict;
  * every tool is scoped to one session and can only see what the *player* holds (collected evidence, voiced
    statements, established contradictions) — the canonical solution service is not reachable from here;
  * there is no shell, no SQL, no network, and no write-path to game state (agents propose; the player decides).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session

from .. import metrics
from ..engine import game as game_svc
from ..engine import reasoning
from ..engine.clock import clock_known, fmt_seconds, to_rt_seconds
from ..engine.state import SessionView
from ..rag.embed import tokenize
from ..rag.store import retrieve


class ToolDenied(Exception):
    pass


class ToolError(Exception):
    pass


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SearchEvidenceArgs(_Args):
    query: str = Field(min_length=1, max_length=200)
    limit: int = Field(default=5, ge=1, le=8)


class GetEvidenceArgs(_Args):
    key: str = Field(max_length=64)


class StatementsArgs(_Args):
    character: str = Field(max_length=64)


class CompareArgs(_Args):
    a: str = Field(max_length=64)
    b: str = Field(max_length=64)


class NoArgs(_Args):
    pass


class DocsArgs(_Args):
    query: str = Field(min_length=1, max_length=200)
    k: int = Field(default=3, ge=1, le=4)


class TravelArgs(_Args):
    a: str = Field(max_length=64)
    b: str = Field(max_length=64)


class HypothesisArgs(_Args):
    culprit: str = Field(max_length=64)
    motive: str | None = Field(default=None, max_length=64)


@dataclass
class ToolContext:
    db: Session
    view: SessionView
    deadline: float  # monotonic

    # ------------------------------------------------------------------ dispatch
    def call(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        spec = TOOLS.get(name)
        if spec is None:
            raise ToolDenied(f"unknown tool {name!r}")
        if time.monotonic() > self.deadline:
            raise TimeoutError("agent deadline exceeded")
        try:
            parsed = spec[0].model_validate(args)
        except ValidationError as e:
            raise ToolError(f"invalid arguments: {str(e)[:160]}") from e
        t0 = time.perf_counter()
        try:
            return spec[1](self, parsed)
        finally:
            metrics.observe("raaz_agent_tool_seconds", time.perf_counter() - t0, tool=name)

    # ------------------------------------------------------------------ helpers
    def held_ev(self, key: str):
        if key not in self.view.held:
            raise ToolDenied(f"evidence {key!r} is not in the player's possession")
        return self.view.case.ev(key)


# --------------------------------------------------------------------------- tool implementations
def _ev_brief(ctx: ToolContext, k: str) -> dict[str, Any]:
    ev = ctx.view.case.ev(k)
    d = ctx.view.found[k]
    return {"key": k, "name": ev.name, "category": ev.category, "examined": d.examined,
            "people": [p for p in ev.related_people if p != "adrian"]}


def t_search_evidence(ctx: ToolContext, a: SearchEvidenceArgs) -> dict[str, Any]:
    q = set(tokenize(a.query))
    scored = []
    for k in ctx.view.held:
        ev = ctx.view.case.ev(k)
        text = f"{ev.name} {ev.description} {ev.examined_detail if ctx.view.found[k].examined else ''}"
        sc = len(q & set(tokenize(text)))
        if sc:
            scored.append((sc, k))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return {"results": [{**_ev_brief(ctx, k), "score": sc} for sc, k in scored[: a.limit]]}


def t_get_evidence(ctx: ToolContext, a: GetEvidenceArgs) -> dict[str, Any]:
    ev = ctx.held_ev(a.key)
    d = ctx.view.found[a.key]
    return {"key": a.key, "name": ev.name, "description": ev.description,
            "examined_detail": ev.examined_detail if d.examined else None,
            "timestamps": [{"label": t.label, "clock": t.clock, "time": t.time} for t in ev.timestamps]}


def t_read_statements(ctx: ToolContext, a: StatementsArgs) -> dict[str, Any]:
    case = ctx.view.case
    if not any(c.key == a.character for c in case.characters):
        raise ToolError("unknown character")
    out = []
    for k in sorted(ctx.view.held):
        ev = case.ev(k)
        if ev.is_testimony and a.character in ev.related_people:
            out.append({"key": k, "name": ev.name, "text": ev.description})
    return {"character": a.character, "statements": out}


def t_compare_timestamps(ctx: ToolContext, a: CompareArgs) -> dict[str, Any]:
    ea, eb = ctx.held_ev(a.a), ctx.held_ev(a.b)
    if not ea.timestamps or not eb.timestamps:
        raise ToolError("both items need timestamps")
    case = ctx.view.case
    known = clock_known(case, ctx.view.held)
    ta, tb = ea.timestamps[0], eb.timestamps[0]
    if ta.clock != tb.clock and not known:
        return {"comparable": False, "reason": "different clocks and the offset has not been established",
                "a": {"time": ta.time, "clock": ta.clock}, "b": {"time": tb.time, "clock": tb.clock}}
    sa = to_rt_seconds(case, ta.clock, ta.time) if known else int(ta.time.split(":")[0]) * 3600 + int(ta.time.split(":")[1]) * 60
    sb = to_rt_seconds(case, tb.clock, tb.time) if known else int(tb.time.split(":")[0]) * 3600 + int(tb.time.split(":")[1]) * 60
    return {"comparable": True, "a_real": fmt_seconds(sa, True), "b_real": fmt_seconds(sb, True), "gap_seconds": abs(sa - sb),
            "earlier": a.a if sa <= sb else a.b}


def t_clock_status(ctx: ToolContext, _a: NoArgs) -> dict[str, Any]:
    case = ctx.view.case
    clocks = sorted({t.clock for k in ctx.view.held for t in case.ev(k).timestamps})
    known = clock_known(case, ctx.view.held)
    return {"clocks_in_use": clocks, "mixed": len(clocks) > 1, "offset_known": known,
            "offset_minutes": case.clock.st_to_rt_minutes if known else None}


def t_timestamps(ctx: ToolContext, _a: NoArgs) -> dict[str, Any]:
    return {"items": game_svc.evidence_timestamps(ctx.view)}


def t_travel_time(ctx: ToolContext, a: TravelArgs) -> dict[str, Any]:
    case = ctx.view.case
    for k in (a.a, a.b):
        if not any(loc.key == k for loc in case.locations):
            raise ToolError("unknown location")
        if k not in ctx.view.unlocked:
            raise ToolDenied(f"location {k!r} has not been visited")
    return {"minutes": case.travel(a.a, a.b)}


def t_candidate_contradictions(ctx: ToolContext, _a: NoArgs) -> dict[str, Any]:
    v = ctx.view
    out = []
    for r in v.case.contradictions:
        pair = next((p for p in r.pairs if p[0] in v.held and p[1] in v.held), None)
        if pair:
            out.append({"rule": r.key, "title": r.title, "evidence": list(pair), "established": r.key in v.contradictions,
                        "about": r.about, "explanation": r.explanation if r.key in v.contradictions else None})
    return {"candidates": out}


def t_alibis(ctx: ToolContext, _a: NoArgs) -> dict[str, Any]:
    out = {}
    for c in ctx.view.case.characters:
        if c.is_suspect:
            out[c.key] = game_svc.alibi_status(ctx.view, c.key)["status"]
    return {"alibis": out}


def t_documents(ctx: ToolContext, a: DocsArgs) -> dict[str, Any]:
    v = ctx.view
    hits = retrieve(ctx.db, case_id=v.case.id, query=a.query, scopes=("case_doc", "evidence"), session_id=v.session.id,
                    held=frozenset(v.held), examined=frozenset(k for k, d in v.found.items() if d.examined), k=a.k)
    return {"documents": [{"ref": h.source_ref, "title": h.title, "excerpt": h.text[:220]} for h in hits if h.lexical > 0]}


def t_evaluate_hypothesis(ctx: ToolContext, a: HypothesisArgs) -> dict[str, Any]:
    ev = reasoning.evaluate(ctx.view, a.culprit, a.motive)
    return {"strength": ev["strength"], "supporting": [x["name"] for x in ev["supporting"]],
            "opposing": [x["name"] for x in ev["opposing"]], "open_questions": ev["open_questions"]}


TOOLS: dict[str, tuple[type[BaseModel], Callable[[ToolContext, Any], dict[str, Any]]]] = {
    "search_evidence": (SearchEvidenceArgs, t_search_evidence),
    "get_evidence": (GetEvidenceArgs, t_get_evidence),
    "read_statements": (StatementsArgs, t_read_statements),
    "compare_timestamps": (CompareArgs, t_compare_timestamps),
    "clock_status": (NoArgs, t_clock_status),
    "list_timestamps": (NoArgs, t_timestamps),
    "travel_time": (TravelArgs, t_travel_time),
    "candidate_contradictions": (NoArgs, t_candidate_contradictions),
    "alibi_status": (NoArgs, t_alibis),
    "retrieve_documents": (DocsArgs, t_documents),
    "evaluate_hypothesis": (HypothesisArgs, t_evaluate_hypothesis),
}

