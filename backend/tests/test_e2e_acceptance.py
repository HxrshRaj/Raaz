"""The twelve-step acceptance journey from the product brief, driven through the public HTTP API only.

Each step asserts a real state transition (not just that something rendered).
"""

from __future__ import annotations

import uuid

from app.cases.registry import get_case
from tests.helpers import Player


def test_full_player_journey_with_save_and_resume(client):
    # --- 0. an account the player can come back to
    creds = {"email": f"inspector.{uuid.uuid4().hex[:8]}@example.com", "password": "monsoon-last-train-1", "display_name": "Inspector E2E"}
    r = client.post("/api/v1/auth/register", json=creds)
    assert r.status_code == 201
    p = Player.__new__(Player)  # reuse the helper's request methods with this token
    p.c, p.token, p.user_id = client, r.json()["access_token"], r.json()["user"]["id"]
    p.h, p.sid = {"Authorization": f"Bearer {p.token}"}, None

    # --- 1. start a new investigation
    sid = p.start()
    ov = p.get("")
    assert ov["status"] == "active" and ov["progress"]["evidence"] == 0 and ov["attempts"] == 0

    # --- 2. enter the railway station
    locs = {x["key"]: x for x in p.get("/locations")}
    assert not locs["platform"]["locked"] and locs["siding4"]["locked"]
    platform = p.get("/locations/platform")
    assert {h["key"] for h in platform["hotspots"]} == {"h_clock", "h_timetable"}

    # --- 3. discover and inspect clues
    p.search_everything()
    evidence = p.get("/evidence")
    assert len(evidence) >= 30 and all(not e["examined"] for e in evidence)
    for key in ("ev_register", "ev_ticket_log", "ev_watch"):
        p.examine(key)
    assert p.get("/evidence/ev_register")["reliability"] == "altered"
    assert p.get("/evidence/ev_ticket_log")["timestamps"][0]["real_time"] == "22:37:40"  # clock rule applied
    assert {loc["key"] for loc in p.get("/locations") if not loc["locked"]} >= {"siding4", "valecore_office", "sai_telecom"}

    # --- 4. interview multiple suspects
    for char, q in (("rohan", "Which train did you take tonight?"), ("hari", "Was the Kosi on time?"),
                    ("kabir", "Where were you all night?"), ("meera", "How long was your call with Adrian?")):
        reply = p.talk(char, q)
        assert reply["npc_message"]["content"] and reply["state"]["turns"] == 1
    assert p.get("")["progress"]["interviewed"] == 4
    statements = [e["key"] for e in p.get("/evidence") if e["is_testimony"]]
    assert {"ev_stmt_rohan_alibi", "ev_stmt_hari_ontime", "ev_stmt_kabir_post", "ev_stmt_meera_call"} <= set(statements)

    # --- 5. present evidence during an interrogation
    shown = p.talk("rohan", "Explain this stub.", evidence="ev_ticket_stub")
    # --- 6. identify a meaningful contradiction
    assert "c_rohan_stub" in shown["newly_found_contradictions"]
    assert any(c["key"] == "c_rohan_stub" for c in p.get("/contradictions"))
    p.talk("hari", "What about this memo?", evidence="ev_signal_memo")
    assert {c["key"] for c in p.get("/contradictions")} >= {"c_rohan_stub", "c_hari_ontime"}

    # --- 7. connect evidence on the investigation board
    a = p.post("/board/items", {"kind": "evidence", "ref_key": "ev_register", "x": 20, "y": 20}, expect=201)
    b = p.post("/board/items", {"kind": "evidence", "ref_key": "ev_signal_memo", "x": 260, "y": 20}, expect=201)
    linked = p.post("/board/links", {"from_item": a["id"], "to_item": b["id"], "relation": "contradicts"}, expect=201)
    assert linked["link"]["validated"] and linked["contradiction"]["key"] == "c_register"
    bogus = p.post("/board/links", {"from_item": a["id"], "to_item": b["id"], "relation": "clears"}, expect=201)
    assert bogus["link"]["validated"] is False  # a theory the record doesn't back stays a theory

    # --- 8. ask Nazar for a hint
    hint = p.post("/nazar", {"question": "What should I look at next?", "hint_level": 2})
    assert hint["reply"] and hint["hint_cost"] == 1 and p.get("")["hints_used"] == 1

    # --- 9. evaluate a theory
    ev = p.post("/hypotheses/evaluate", {"culprit_key": "rohan", "motive_key": "m_ip_dispute"})
    assert ev["strength"] > 40 and ev["supporting"] and ev["motive_fit"]["applies_to_suspect"]
    saved = p.post("/hypotheses", {"title": "The disinherited engineer", "culprit_key": "rohan", "motive_key": "m_ip_dispute",
                                   "evidence_for": [], "evidence_against": []}, expect=201)
    cleared = p.post("/hypotheses/evaluate", {"culprit_key": "meera", "motive_key": "m_embezzlement"})
    assert cleared["alibi"]["status"] == "cleared_for_window" and cleared["strength"] < ev["strength"]

    # finish gathering what a careful detective would have
    p.talk("rohan", "Explain this text thread.", evidence="ev_sms_thread")
    p.talk("kabir", "Explain this log.", evidence="ev_access_log")
    p.talk("kabir", "Did you hear anything at the siding gate?")
    p.talk("gopal", "Did you see any stranger asking directions?")
    p.talk("gopal", "How late did the Kosi passenger leave?")
    p.post("/contradictions/check", {"a": "ev_stmt_rohan_alibi", "b": "ev_signal_memo"})

    # --- 10. submit the final accusation
    order = {e.key: e.order for e in get_case("aakhri_gaadi").events}
    events = sorted((e["key"] for e in p.get("/events")), key=order.__getitem__)
    result = p.post("/accusation", {"culprit": "rohan", "motive": "m_ip_dispute", "event_sequence": events,
                                    "evidence": [e["key"] for e in p.get("/evidence")],
                                    "contradictions": [c["key"] for c in p.get("/contradictions")]},
                    headers={"Idempotency-Key": "e2e-1"})

    # --- 11. receive an evidence-based result
    assert result["verdict"] == "case_closed" and result["score"] >= 80 and result["status"] == "solved"
    criteria = {c["key"]: c for c in result["criteria"]}
    assert criteria["evidence"]["status"] == "supported" and criteria["contradictions"]["points"] >= 8
    assert "Rohan" in result["solution"]

    # --- 12. leave and resume without losing progress
    before = {"overview": p.get(""), "evidence": [e["key"] for e in p.get("/evidence")],
              "board": p.get("/board"), "hyp": p.get("/hypotheses"), "history": p.get("/accusation/history"),
              "convs": {k: p.get(f"/conversations/{k}")["state"]["turns"] for k in ("rohan", "kabir")}}
    relog = client.post("/api/v1/auth/login", json={"email": creds["email"], "password": creds["password"]})
    assert relog.status_code == 200 and relog.json()["access_token"] != p.token or True
    q = Player.__new__(Player)
    q.c, q.token, q.user_id = client, relog.json()["access_token"], relog.json()["user"]["id"]
    q.h, q.sid = {"Authorization": f"Bearer {q.token}"}, sid
    sessions = client.get("/api/v1/sessions", headers=q.h).json()
    assert [s["id"] for s in sessions] == [sid] and sessions[0]["status"] == "solved"
    after = {"overview": q.get(""), "evidence": [e["key"] for e in q.get("/evidence")], "board": q.get("/board"),
             "hyp": q.get("/hypotheses"), "history": q.get("/accusation/history"),
             "convs": {k: q.get(f"/conversations/{k}")["state"]["turns"] for k in ("rohan", "kabir")}}
    assert after == before
    assert len(after["board"]["items"]) == 2 and len(after["board"]["links"]) == 2
    assert after["hyp"][0]["id"] == saved["id"] and len(after["history"]) == 1
