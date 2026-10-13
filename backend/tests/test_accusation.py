from __future__ import annotations

import threading

import pytest

from app.cases.registry import get_case
from tests.helpers import Player

CORRECT = {"culprit": "rohan", "motive": "m_ip_dispute"}


def investigate_fully(p: Player) -> None:
    """A scripted but *player-realistic* solve: only uses public API actions."""
    p.search_everything()
    for char, q in (("rohan", "Which train did you take tonight?"), ("rohan", "Have you been in touch with Adrian, any messages?"),
                    ("kabir", "Where were you all night?"), ("hari", "Was the Kosi on time?"),
                    ("meera", "How long was your call with Adrian?"), ("tanvi", "Did you go into his carriage?")):
        p.talk(char, q)
    p.talk("rohan", "Explain this.", evidence="ev_ticket_stub")
    p.talk("rohan", "And this text thread?", evidence="ev_sms_thread")
    p.talk("kabir", "Explain this log.", evidence="ev_access_log")
    p.talk("kabir", "Did you hear anything at the siding gate?")
    p.talk("hari", "What about this memo?", evidence="ev_signal_memo")
    p.talk("gopal", "Did you see any stranger asking directions?")
    p.talk("gopal", "How late did the Kosi passenger leave?")
    for a, b in (("ev_stmt_rohan_alibi", "ev_signal_memo"), ("ev_register", "ev_cctv_platform")):
        p.post("/contradictions/check", {"a": a, "b": b})


def chronological(keys: list[str]) -> list[str]:
    order = {e.key: e.order for e in get_case("aakhri_gaadi").events}
    return sorted(keys, key=lambda k: order[k])


def solution_payload(p: Player) -> dict:
    events = chronological([e["key"] for e in p.get("/events")])
    return {**CORRECT, "event_sequence": events,
            "evidence": [e["key"] for e in p.get("/evidence")],
            "contradictions": [c["key"] for c in p.get("/contradictions")]}


def test_case_is_solvable_end_to_end(player: Player):
    investigate_fully(player)
    keys = {c["key"] for c in player.get("/contradictions")}
    assert {"c_rohan_stub", "c_rohan_contact", "c_rohan_train", "c_register"} <= keys
    res = player.post("/accusation", solution_payload(player))
    assert res["verdict"] == "case_closed", res
    assert res["score"] >= 80
    assert res["status"] == "solved" and "Rohan" in res["solution"]
    assert player.get("")["status"] == "solved" and player.get("")["score"] == res["score"]
    # a closed case stays closed
    player.post("/accusation", solution_payload(player), expect=409)
    player.talk("rohan", "Anything else?", expect=409)


def test_empty_handed_accusation_is_not_enough(player: Player):
    res = player.post("/accusation", {**CORRECT, "event_sequence": [], "evidence": [], "contradictions": []})
    assert res["verdict"] == "insufficient_evidence" and res["score"] < 60
    assert res["next_steps"] and res["status"] == "active"
    assert "solution" not in res
    # the report names *rubric categories*, never evidence the player has not found
    assert "ev_" not in str(res["next_steps"])


def test_wrong_suspect_has_consequences_and_evidence_based_report(player: Player):
    investigate_fully(player)
    res = player.post("/accusation", {"culprit": "meera", "motive": "m_embezzlement", "event_sequence": [],
                                      "evidence": ["ev_ledger_kaveri", "ev_bank_slip"], "contradictions": []})
    assert res["verdict"] == "wrong_suspect" and res["reputation_delta"] < 0 and "solution" not in res
    assert res["criteria"][0]["status"] == "contradicted"  # her alibi is established by the evidence held
    assert "waiting-room camera" in res["criteria"][0]["message"]
    assert player.get("")["reputation"] < 100 and player.get("")["attempts"] == 1
    # the accused is now hostile
    assert player.get("/conversations/meera")["state"]["mood"] == "hostile"
    assert "consequence" in res


def test_three_wrong_accusations_close_the_case_then_it_can_be_reopened(player: Player):
    player.search_everything()
    for _i in range(3):
        res = player.post("/accusation", {"culprit": "tanvi", "motive": "m_exposure", "event_sequence": [], "evidence": [],
                                          "contradictions": []})
        assert res["verdict"] == "wrong_suspect"
    assert res["status"] == "closed_unsolved" and res["attempts_left"] == 0
    player.post("/accusation", {"culprit": "rohan", "motive": "m_ip_dispute", "event_sequence": [], "evidence": [],
                                "contradictions": []}, expect=409)
    ov = player.post("/reopen")
    assert ov["status"] == "active" and ov["attempts"] == 0 and ov["reputation"] < 100


def test_cannot_cite_evidence_or_contradictions_you_do_not_have(player: Player):
    player.post("/accusation", {**CORRECT, "event_sequence": [], "evidence": ["ev_watch"], "contradictions": []}, expect=404)
    player.post("/accusation", {**CORRECT, "event_sequence": [], "evidence": [], "contradictions": ["c_rohan_stub"]}, expect=400)
    player.post("/accusation", {**CORRECT, "event_sequence": ["e_death"], "evidence": [], "contradictions": []}, expect=400)
    player.post("/accusation", {"culprit": "gopal", "motive": "m_ip_dispute", "event_sequence": [], "evidence": [],
                                "contradictions": []}, expect=404)  # the witness is not an accusable suspect


def test_idempotency_key_prevents_double_charge(player: Player):
    body = {"culprit": "tanvi", "motive": "m_exposure", "event_sequence": [], "evidence": [], "contradictions": []}
    a = player.post("/accusation", body, headers={"Idempotency-Key": "k1"})
    b = player.post("/accusation", body, headers={"Idempotency-Key": "k1"})
    assert a == b and player.get("")["attempts"] == 1


def test_concurrent_accusations_consume_one_attempt_each(player: Player):
    body = {"culprit": "tanvi", "motive": "m_exposure", "event_sequence": [], "evidence": [], "contradictions": []}
    codes: list[int] = []

    def go():
        r = player.c.post(player.url("/accusation"), json=body, headers=player.h)
        codes.append(r.status_code)

    ts = [threading.Thread(target=go) for _ in range(8)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    ov = player.get("")
    assert codes.count(200) == ov["attempts"]  # no attempt is lost or double counted
    assert ov["attempts"] <= 3 and set(codes) <= {200, 409}
    assert len(player.get("/accusation/history")) == ov["attempts"]


@pytest.mark.parametrize("path", ["/accusation/options", "/timeline", "/board", "/hypotheses", "/reports"])
def test_read_endpoints_work_on_fresh_session(player: Player, path: str):
    assert player.get(path) is not None


def test_sequence_scoring_rewards_correct_order(player: Player):
    investigate_fully(player)
    events = chronological([e["key"] for e in player.get("/events")])
    good = player.post("/accusation", {**CORRECT, "event_sequence": events, "evidence": [e["key"] for e in player.get("/evidence")],
                                       "contradictions": [c["key"] for c in player.get("/contradictions")]})
    p2 = Player(player.c, "Second")
    p2.start()
    investigate_fully(p2)
    shuffled = list(reversed(chronological([e["key"] for e in p2.get("/events")])))
    bad = p2.post("/accusation", {**CORRECT, "event_sequence": shuffled, "evidence": [e["key"] for e in p2.get("/evidence")],
                                  "contradictions": [c["key"] for c in p2.get("/contradictions")]})
    seq = lambda r: next(c for c in r["criteria"] if c["key"] == "sequence")["points"]  # noqa: E731
    assert seq(good) > seq(bad)


def test_event_list_does_not_leak_chronology(player: Player):
    investigate_fully(player)
    listed = [e["key"] for e in player.get("/events")]
    assert len(listed) >= 6
    assert listed != chronological(listed)  # the API order is not the true order
