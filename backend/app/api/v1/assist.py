from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select

from ...agents import graph as agents
from ...config import get_settings
from ...deps import DB, CurrentUser, View, audit, rate_limit
from ...errors import NotFound
from ...jobs import submit
from ...models import AgentRun
from ...nazar import service as nazar
from ...schemas.requests import InvestigationIn, NazarIn

router = APIRouter(tags=["assistant"])


@router.post("/sessions/{session_id}/nazar",
             dependencies=[Depends(rate_limit("nazar", lambda: get_settings().llm_rate_limit_per_min))])
def ask_nazar(body: NazarIn, view: View, db: DB):
    return nazar.ask(db, view, body.question, body.hint_level)


@router.get("/sessions/{session_id}/nazar", dependencies=[Depends(rate_limit("api"))])
def nazar_history(view: View, db: DB):
    return nazar.history(db, view.session.id)


@router.post("/sessions/{session_id}/investigations", status_code=202,
             dependencies=[Depends(rate_limit("agents", lambda: 12))])
def start_investigation(body: InvestigationIn, view: View, db: DB, user: CurrentUser, request: Request, response: Response):
    run = agents.create_run(db, view, body.question)
    job_id = submit("agent_run", lambda: agents.execute(run.id), session_id=view.session.id, max_attempts=1)
    audit(db, user_id=user.id, session_id=view.session.id, action="agent.start", request=request, run=run.id)
    response.headers["Location"] = f"/api/v1/sessions/{view.session.id}/investigations/{run.id}"
    return {"id": run.id, "status": "queued", "job_id": job_id}


@router.get("/sessions/{session_id}/investigations", dependencies=[Depends(rate_limit("api"))])
def list_investigations(view: View, db: DB):
    rows = db.scalars(select(AgentRun).where(AgentRun.session_id == view.session.id).order_by(AgentRun.created_at.desc()).limit(20))
    return [agents.run_view(db, r, with_steps=False) for r in rows]


def _run(db, view, run_id: str) -> AgentRun:
    run = db.get(AgentRun, run_id)
    if run is None or run.session_id != view.session.id:
        raise NotFound("investigation")
    return run


@router.get("/sessions/{session_id}/investigations/{run_id}", dependencies=[Depends(rate_limit("poll", lambda: 600))])
def get_investigation(run_id: str, view: View, db: DB):
    return agents.run_view(db, _run(db, view, run_id))


@router.post("/sessions/{session_id}/investigations/{run_id}/cancel")
def cancel_investigation(run_id: str, view: View, db: DB):
    run = _run(db, view, run_id)
    if run.status in ("queued", "running"):
        run.cancel_requested = True
        db.commit()
    return {"id": run.id, "status": run.status, "cancel_requested": run.cancel_requested}
