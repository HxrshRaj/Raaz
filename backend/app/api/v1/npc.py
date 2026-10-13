from __future__ import annotations

from fastapi import APIRouter, Depends

from ...config import get_settings
from ...deps import DB, CurrentUser, View, rate_limit
from ...npc import dialogue
from ...schemas.requests import MessageIn

router = APIRouter(tags=["npc"])


@router.get("/system/info")
def system_info(user: CurrentUser):
    s = get_settings()
    return {"llm": dialogue.llm_status(), "env": s.env, "version": "0.1.0",
            "ml_workbench": s.workbench_on,
            "notes": "Without an LLM provider, NPCs use clearly labelled scripted dialogue. The deterministic game "
                     "engine, evidence, contradictions, timeline, board and scoring are unaffected."}


@router.get("/sessions/{session_id}/conversations", dependencies=[Depends(rate_limit("api"))])
def conversations(view: View):
    return [{"character": k, "turns": c.turns, "mood": c.mood} for k, c in view.conversations.items()]


@router.get("/sessions/{session_id}/conversations/{char_key}", dependencies=[Depends(rate_limit("api"))])
def conversation(char_key: str, view: View, db: DB):
    conv = dialogue.open_conversation(db, view, char_key)
    return dialogue.conversation_view(db, view, conv)


@router.post("/sessions/{session_id}/conversations/{char_key}/messages",
             dependencies=[Depends(rate_limit("llm", lambda: get_settings().llm_rate_limit_per_min))])
def send_message(char_key: str, body: MessageIn, view: View, db: DB):
    return dialogue.converse(db, view, char_key, dialogue.assert_text(body.text), body.evidence_key)
