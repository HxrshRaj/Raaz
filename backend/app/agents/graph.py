"""Explicit state-machine workflow for multi-step investigations (LangGraph-style, dependency-free).

    planner -> evidence_analyst -> timeline_analyst -> witness_analyst -> research -> contradiction_verifier -> report

* Nodes share one typed `AgentState` and call only the permissioned tools in `tools.py`.
* Hard limits: max iterations, wall-clock deadline, cancellation checked between nodes.
* Every node execution and tool call is persisted (`agent_steps`) with a concise reasoning *summary* — never raw
  chain-of-thought.
* Agents only observe and propose. Establishing a contradiction or accusing someone remains an explicit player action.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import func, select

from .. import db as dbmod
from .. import metrics
from ..config import get_settings
from ..engine.state import SessionView, load_view
from ..logging_setup import get_logger
from ..models import AgentRun, AgentStep, GameSession, Report
from .tools import ToolContext, ToolDenied, ToolError

log = get_logger("raaz.agents")

TASKS = ("evidence", "timeline", "witness", "research", "hypothesis")


class AgentState(BaseModel):
    question: str
    tasks: list[str] = Field(default_factory=list)
    focus_people: list[str] = Field(default_factory=list)
    findings: list[dict[str, Any]] = Field(default_factory=list)
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    witness: dict[str, Any] = Field(default_factory=dict)
    documents: list[dict[str, Any]] = Field(default_factory=list)
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    verified: list[dict[str, Any]] = Field(default_factory=list)
    hypotheses: list[dict[str, Any]] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    report: dict[str, Any] | None = None


class Cancelled(Exception):
    pass


class Runner:
    def __init__(self, run_id: str, view: SessionView, ctx: ToolContext, max_iter: int) -> None:
        self.run_id, self.view, self.ctx, self.max_iter = run_id, view, ctx, max_iter
        self.idx = 0
        self.iterations = 0

    # persistence of steps uses its own short transactions so pollers see progress
    def record(self, node: str, tool: str | None, args: dict, summary: str, refs: list[str], status: str, ms: int) -> None:
        with dbmod.SessionLocal() as db:
            db.add(AgentStep(run_id=self.run_id, idx=self.idx, node=node, tool=tool, args=args, summary=summary[:600],
                             refs=refs[:12], status=status, duration_ms=ms))
            db.commit()
        self.idx += 1

    def check_cancel(self) -> None:
        with dbmod.SessionLocal() as db:
            r = db.get(AgentRun, self.run_id)
            if r is not None and r.cancel_requested:
                raise Cancelled()

    def tool(self, node: str, name: str, args: dict | None = None) -> dict[str, Any] | None:
        args = args or {}
        t0 = time.perf_counter()
        try:
            res = self.ctx.call(name, args)
            self.record(node, name, args, _summ(name, res), _refs(res), "ok", int((time.perf_counter() - t0) * 1000))
            return res
        except ToolDenied as e:
            self.record(node, name, args, f"denied: {e}", [], "denied", int((time.perf_counter() - t0) * 1000))
            metrics.inc("raaz_agent_tool_denied_total", tool=name)
            return None
        except ToolError as e:
            self.record(node, name, args, f"error: {e}", [], "error", int((time.perf_counter() - t0) * 1000))
            return None


def _refs(res: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for key in ("results", "candidates", "statements", "documents", "items"):
        for r in res.get(key, [])[:8]:
            for k in ("key", "rule", "ref", "evidence_key"):
                if isinstance(r, dict) and r.get(k):
                    refs.append(str(r[k]))
    return refs


def _summ(name: str, res: dict[str, Any]) -> str:
    if name == "search_evidence":
        return f"found {len(res['results'])} relevant item(s)"
    if name == "candidate_contradictions":
        n = sum(1 for c in res["candidates"] if not c["established"])
        return f"{len(res['candidates'])} conflicting pair(s) among held items; {n} not yet established"
    if name == "clock_status":
        return "clocks in use: " + ",".join(res["clocks_in_use"]) + ("; offset known" if res["offset_known"] else "; offset unknown")
    if name == "list_timestamps":
        return f"{len(res['items'])} timestamped record(s)"
    if name == "read_statements":
        return f"{len(res['statements'])} statement(s) on record for {res['character']}"
    if name == "retrieve_documents":
        return f"{len(res['documents'])} document excerpt(s) retrieved"
    if name == "alibi_status":
        return "alibi status: " + ", ".join(f"{k}={v}" for k, v in res["alibis"].items())
    return "ok"


# --------------------------------------------------------------------------- nodes
def n_planner(r: Runner, s: AgentState) -> str:
    q = s.question.lower()
    tasks = []
    if any(w in q for w in ("time", "when", "clock", "timeline", "sequence", "late", "train", "alibi", "where")):
        tasks.append("timeline")
    if any(w in q for w in ("said", "statement", "claim", "lie", "lied", "witness", "alibi", "story", "account", "contradict", "consistent")):
        tasks.append("witness")
    if any(w in q for w in ("evidence", "item", "clue", "found", "ticket", "register", "key", "log", "camera")):
        tasks.append("evidence")
    if any(w in q for w in ("rule", "document", "policy", "procedure", "allowed", "what is", "how does")):
        tasks.append("research")
    if any(w in q for w in ("suspect", "who", "theory", "hypothesis", "culprit", "motive")):
        tasks.append("hypothesis")
    if not tasks:
        tasks = ["evidence", "timeline", "witness"]
    s.tasks = list(dict.fromkeys(tasks))[:5]
    for c in r.view.case.characters:
        if c.key in q or c.name.split()[0].lower() in q:
            s.focus_people.append(c.key)
    r.record("planner", None, {}, f"Plan: {', '.join(s.tasks)}" + (f"; focusing on {', '.join(s.focus_people)}" if s.focus_people else ""),
             [], "ok", 0)
    return "evidence_analyst"


def n_evidence(r: Runner, s: AgentState) -> str:
    if "evidence" in s.tasks or not s.tasks:
        res = r.tool("evidence_analyst", "search_evidence", {"query": s.question, "limit": 6})
        for it in (res or {}).get("results", []):
            s.findings.append({"kind": "observed", "text": f"{it['name']} ({it['category']})" + ("" if it["examined"] else " — not yet examined"),
                               "refs": [it["key"]]})
            if not it["examined"]:
                s.caveats.append(f"“{it['name']}” has not been examined; there may be detail you haven't read.")
    return "timeline_analyst"


def n_timeline(r: Runner, s: AgentState) -> str:
    if "timeline" in s.tasks:
        clock = r.tool("timeline_analyst", "clock_status")
        ts = r.tool("timeline_analyst", "list_timestamps")
        if clock and clock["mixed"] and not clock["offset_known"]:
            s.findings.append({"kind": "interpretation", "text": "Your records mix the station clock and real time and you have not "
                               "yet established how they relate; sequences that span both are unreliable.", "refs": []})
        elif clock and clock["offset_known"]:
            s.findings.append({"kind": "observed", "text": f"Station time + {clock['offset_minutes']} min = real time.", "refs": []})
        s.timeline = (ts or {}).get("items", [])
        al = r.tool("timeline_analyst", "alibi_status")
        if al:
            for ck, st in al["alibis"].items():
                if st == "cleared_for_window":
                    s.findings.append({"kind": "observed", "text": f"{r.view.case.char(ck).name} is established elsewhere at the moment of death.",
                                       "refs": []})
            open_ = [r.view.case.char(ck).name for ck, st in al["alibis"].items() if st != "cleared_for_window"]
            if open_:
                s.findings.append({"kind": "interpretation", "text": "Not yet accounted for at the moment of death: " + ", ".join(open_) +
                                   ". That is a gap in the record, not a sign of guilt.", "refs": []})
    return "witness_analyst"


def n_witness(r: Runner, s: AgentState) -> str:
    if "witness" in s.tasks:
        people = s.focus_people or [c.key for c in r.view.case.characters]
        for ck in people[:6]:
            res = r.tool("witness_analyst", "read_statements", {"character": ck})
            if res:
                s.witness[ck] = [x["name"] for x in res["statements"]]
    return "research"


def n_research(r: Runner, s: AgentState) -> str:
    if "research" in s.tasks or "evidence" in s.tasks:
        res = r.tool("research_agent", "retrieve_documents", {"query": s.question, "k": 3})
        s.documents = (res or {}).get("documents", [])
    return "contradiction_verifier"


def n_verify(r: Runner, s: AgentState) -> str:
    res = r.tool("contradiction_verifier", "candidate_contradictions")
    for c in (res or {}).get("candidates", []):
        if s.focus_people and c["about"] not in s.focus_people:
            continue
        # Provenance check: both pieces must really be held and the pair must be a known rule pair.
        ok = all(k in r.view.held for k in c["evidence"])
        s.candidates.append(c)
        if ok:
            s.verified.append({**c, "provenance": "both items are in the player's possession; pair matches a case rule",
                               "needs_player_action": not c["established"]})
    if "hypothesis" in s.tasks:
        for ck in s.focus_people or [c.key for c in r.view.case.characters if c.is_suspect][:5]:
            if not r.view.case.char(ck).is_suspect:
                continue
            res2 = r.tool("contradiction_verifier", "evaluate_hypothesis", {"culprit": ck})
            if res2:
                s.hypotheses.append({"suspect": ck, **res2})
    return "report_generator"


def n_report(r: Runner, s: AgentState) -> str | None:
    case = r.view.case
    unconfirmed = [v for v in s.verified if v["needs_player_action"]]
    key_findings = [f for f in s.findings if f["kind"] == "observed"][:6]
    interp = [f for f in s.findings if f["kind"] == "interpretation"][:5]
    actions = [{"action": "check_contradiction", "a": v["evidence"][0], "b": v["evidence"][1],
                "why": f"{v['title']} (confirm it yourself to record it)"} for v in unconfirmed][:4]
    s.report = {
        "question": s.question, "plan": s.tasks,
        "observed": key_findings, "interpretations": interp,
        "contradictions": [{"rule": v["rule"], "title": v["title"], "established": v["established"],
                            "evidence": [{"key": k, "name": case.ev(k).name} for k in v["evidence"]],
                            "provenance": v["provenance"]} for v in s.verified],
        "witness_statements": {case.char(k).name: v for k, v in s.witness.items() if v},
        "timeline": s.timeline[:16],
        "documents": s.documents,
        "hypotheses": [{"suspect": case.char(h["suspect"]).name, "strength": h["strength"], "supporting": h["supporting"],
                        "opposing": h["opposing"], "open_questions": h["open_questions"]} for h in s.hypotheses],
        "suggested_player_actions": actions,
        "caveats": list(dict.fromkeys(s.caveats))[:5] + [
            "Generated by an automated analysis of the evidence you hold. It proposes; you decide. "
            "Nothing here is canonical until you establish it."],
    }
    r.record("report_generator", None, {}, f"Report ready: {len(s.verified)} verified conflict(s), {len(s.findings)} finding(s)", [], "ok", 0)
    return None


NODES: dict[str, Callable[[Runner, AgentState], str | None]] = {
    "planner": n_planner, "evidence_analyst": n_evidence, "timeline_analyst": n_timeline, "witness_analyst": n_witness,
    "research": n_research, "contradiction_verifier": n_verify, "report_generator": n_report,
}


# --------------------------------------------------------------------------- run orchestration
def create_run(db, view: SessionView, question: str) -> AgentRun:
    s = get_settings()
    from ..errors import Conflict, TooManyRequests

    active = db.scalar(select(func.count()).select_from(AgentRun).where(AgentRun.session_id == view.session.id,
                                                                        AgentRun.status.in_(("queued", "running"))))
    if active:
        raise Conflict("agent_busy", "An investigation is already running. Wait for it or cancel it.")
    recent = db.scalar(select(func.count()).select_from(AgentRun).where(
        AgentRun.session_id == view.session.id, AgentRun.created_at > datetime.now(UTC).replace(microsecond=0) - _hour()))
    if (recent or 0) >= s.agent_runs_per_hour:
        raise TooManyRequests("Investigation limit reached for this hour.", retry_after=600)
    run = AgentRun(session_id=view.session.id, question=question.strip(), status="queued")
    db.add(run)
    db.commit()
    return run


def _hour():
    from datetime import timedelta

    return timedelta(hours=1)


def execute(run_id: str) -> dict[str, Any]:
    """Job body: runs the graph with limits. Raises nothing; outcome is persisted."""
    s = get_settings()
    with dbmod.SessionLocal() as db:
        run = db.get(AgentRun, run_id)
        assert run is not None
        run.status = "running"
        db.commit()
        sess = db.get(GameSession, run.session_id)
        view = load_view(db, sess)  # type: ignore[arg-type]
        question = run.question
        ctx = ToolContext(db=db, view=view, deadline=time.monotonic() + s.agent_timeout_s)
        runner = Runner(run_id, view, ctx, s.agent_max_iterations)
        state = AgentState(question=question)
        node: str | None = "planner"
        status, error = "succeeded", None
        t0 = time.perf_counter()
        try:
            while node is not None:
                runner.iterations += 1
                if runner.iterations > runner.max_iter:
                    raise RuntimeError("iteration limit reached")
                runner.check_cancel()
                if time.monotonic() > ctx.deadline:
                    raise TimeoutError("investigation timed out")
                node = NODES[node](runner, state)
        except Cancelled:
            status = "cancelled"
        except Exception as e:  # noqa: BLE001
            status, error = "failed", f"{type(e).__name__}: {e}"[:300]
            log.warning("agent run failed", extra={"run": run_id, "error": error})
        finally:
            with dbmod.SessionLocal() as db2:
                r2 = db2.get(AgentRun, run_id)
                r2.status, r2.error, r2.iterations = status, error, runner.iterations  # type: ignore[union-attr]
                r2.plan = state.tasks  # type: ignore[union-attr]
                r2.result = state.report if status == "succeeded" else None  # type: ignore[union-attr]
                r2.finished_at = datetime.now(UTC)  # type: ignore[union-attr]
                if status == "succeeded" and state.report:
                    db2.add(Report(session_id=r2.session_id, kind="investigation",  # type: ignore[union-attr]
                                   content={"question": question, **state.report}))
                db2.commit()
            metrics.inc("raaz_agent_runs_total", status=status)
            metrics.observe("raaz_agent_run_seconds", time.perf_counter() - t0)
    return {"status": status}


def run_view(db, run: AgentRun, with_steps: bool = True) -> dict[str, Any]:
    out = {"id": run.id, "question": run.question, "status": run.status, "plan": run.plan, "iterations": run.iterations,
           "error": run.error, "result": run.result, "created_at": run.created_at.isoformat(),
           "finished_at": run.finished_at.isoformat() if run.finished_at else None}
    if with_steps:
        steps = db.scalars(select(AgentStep).where(AgentStep.run_id == run.id).order_by(AgentStep.idx))
        out["steps"] = [{"idx": s.idx, "node": s.node, "tool": s.tool, "args": s.args, "summary": s.summary, "refs": s.refs,
                         "status": s.status, "duration_ms": s.duration_ms} for s in steps]
    return out
