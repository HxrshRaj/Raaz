from __future__ import annotations

from tests.helpers import Player


def add(p: Player, label, time, clock="RT", actor=None, loc=None, ev=None, expect=201):
    return p.post("/timeline", {"label": label, "time": time, "clock": clock, "actor_key": actor, "location_key": loc,
                                "evidence_keys": [ev] if ev else []}, expect=expect)


def issues(p: Player, kind: str | None = None):
    v = p.get("/timeline")["validation"]
    return [i for i in v["issues"] if kind is None or i["type"] == kind]


# ================================================================== timeline
def test_timeline_entry_validation(player: Player):
    add(player, "x", "25:99", expect=400)
    add(player, "x", "22:45", loc="siding4", expect=403)  # place not visited
    add(player, "x", "22:45", ev="ev_watch", expect=404)  # evidence not held
    add(player, "x", "22:45", actor="nobody", expect=404)
    assert player.get("/timeline")["entries"] == []


def test_source_mismatch_is_flagged_and_matching_entries_are_accepted(player: Player):
    player.inspect("carriage", "h_body")
    player.inspect("carriage", "h_wrist")
    add(player, "Adrian's heart stops", "22:30", ev="ev_watch")
    assert [i["type"] for i in issues(player)] == ["source_mismatch"]
    add(player, "Adrian's heart stops (corrected)", "22:58:41", ev="ev_watch")
    assert len(issues(player, "source_mismatch")) == 1  # only the first, wrong entry is flagged


def test_clock_offset_is_applied_only_once_the_player_knows_it(player: Player):
    player.inspect("security_room", "h_dvr_platform")
    player.inspect("carriage", "h_body")
    player.inspect("carriage", "h_wrist")
    add(player, "Hari flags off the Kosi", "22:45:10", clock="ST", actor="hari", loc="platform", ev="ev_cctv_platform")
    add(player, "Adrian dies", "22:58:41", clock="RT", actor="hari", loc="carriage", ev="ev_watch")
    # without the clock rule, 22:45:10 vs 22:58:41 look 13+ minutes apart: the walk is possible, and mixed clocks are flagged
    assert issues(player, "impossible_travel") == []
    assert issues(player, "clock_unreconciled") or issues(player, "mixed_clocks")
    player.inspect("platform", "h_clock")  # now the offset is known: 22:45:10 ST == 22:57:10 RT, 91 s before the death
    bad = issues(player, "impossible_travel")
    assert len(bad) == 1 and "Hari" in bad[0]["message"] and bad[0]["severity"] == "error"
    assert player.get("/timeline")["entries"][0]["real_time"] == "22:57:10"


def test_same_place_or_enough_time_is_fine(player: Player):
    player.inspect("platform", "h_clock")
    add(player, "Kabir at the stall", "22:58:05", actor="kabir", loc="tea_stall")
    add(player, "Kabir back at the security room", "23:01:10", actor="kabir", loc="security_room")  # 3m05s walk: enough
    assert issues(player, "impossible_travel") == []
    add(player, "Kabir at the saloon", "22:59:00", actor="kabir", loc="carriage")  # 55 s after the stall: impossible
    assert len(issues(player, "impossible_travel")) >= 1


def test_timeline_delete_and_isolation(client, player: Player):
    e = add(player, "Something", "22:00")["entry"]
    other = Player(client, "Eve")
    other.start()
    other.delete(f"/timeline/{e['id']}", expect=404)
    player.delete(f"/timeline/{e['id']}")
    assert player.get("/timeline")["entries"] == []


# ================================================================== board
def pin(p: Player, kind, ref="", text="", expect=201):
    return p.post("/board/items", {"kind": kind, "ref_key": ref, "text": text, "x": 10, "y": 10}, expect=expect)


def test_board_only_accepts_real_accessible_things(player: Player):
    pin(player, "evidence", "ev_watch", expect=404)  # not collected
    pin(player, "person", "nobody", expect=404)
    pin(player, "location", "siding4", expect=404)  # locked
    pin(player, "note", text="   ", expect=400)
    assert pin(player, "person", "rohan")["label"] == "Rohan Deshmukh"
    again = pin(player, "person", "rohan")
    assert again["id"] and len(player.get("/board")["items"]) == 1  # pinning twice is idempotent


def test_links_are_validated_against_the_record(player: Player):
    player.inspect("stationmaster_office", "h_ticket_log")
    player.inspect("carriage", "h_under_desk")
    log, stub = pin(player, "evidence", "ev_ticket_log"), pin(player, "evidence", "ev_ticket_stub")
    rohan, meera = pin(player, "person", "rohan"), pin(player, "person", "meera")
    ok = player.post("/board/links", {"from_item": log["id"], "to_item": rohan["id"], "relation": "implicates"}, expect=201)
    assert ok["link"]["validated"] is True
    no = player.post("/board/links", {"from_item": log["id"], "to_item": meera["id"], "relation": "implicates"}, expect=201)
    assert no["link"]["validated"] is False
    same = player.post("/board/links", {"from_item": log["id"], "to_item": stub["id"], "relation": "related"}, expect=201)
    assert same["link"]["validated"] is True  # share the PT-0412 event
    wrong_kind = player.post("/board/links", {"from_item": log["id"], "to_item": stub["id"], "relation": "clears"}, expect=201)
    assert wrong_kind["link"]["validated"] is False
    player.post("/board/links", {"from_item": log["id"], "to_item": log["id"], "relation": "related"}, expect=400)
    player.post("/board/links", {"from_item": log["id"], "to_item": stub["id"], "relation": "teleports"}, expect=400)


def test_board_contradiction_link_records_a_contradiction_once(player: Player):
    player.inspect("stationmaster_office", "h_register")
    player.inspect("stationmaster_office", "h_in_tray")
    a, b = pin(player, "evidence", "ev_register"), pin(player, "evidence", "ev_signal_memo")
    first = player.post("/board/links", {"from_item": a["id"], "to_item": b["id"], "relation": "contradicts"}, expect=201)
    assert first["newly_found_contradiction"] and first["contradiction"]["key"] == "c_register"
    again = player.post("/board/links", {"from_item": b["id"], "to_item": a["id"], "relation": "contradicts"}, expect=201)
    assert again["link"]["validated"] and not again["newly_found_contradiction"]
    assert [c["key"] for c in player.get("/contradictions")] == ["c_register"]


def test_board_move_persist_delete_cascades_links_and_blocks_foreign_items(client, player: Player):
    a, b = pin(player, "person", "rohan"), pin(player, "person", "meera")
    player.c.patch(player.url(f"/board/items/{a['id']}"), json={"x": 321, "y": 123}, headers=player.h)
    moved = next(i for i in player.get("/board")["items"] if i["id"] == a["id"])
    assert (moved["x"], moved["y"]) == (321, 123)
    link = player.post("/board/links", {"from_item": a["id"], "to_item": b["id"], "relation": "related"}, expect=201)["link"]
    other = Player(client, "Eve")
    other.start()
    assert other.c.patch(other.url(f"/board/items/{a['id']}"), json={"x": 1, "y": 1}, headers=other.h).status_code == 404
    other.post("/board/links", {"from_item": a["id"], "to_item": b["id"], "relation": "related"}, expect=404)
    player.delete(f"/board/items/{a['id']}")
    board = player.get("/board")
    assert [i["id"] for i in board["items"]] == [b["id"]] and board["links"] == [] and link["id"]


def test_board_rejects_out_of_range_positions_and_oversized_notes(player: Player):
    assert player.c.post(player.url("/board/items"), json={"kind": "note", "text": "ok", "x": 10**9, "y": 0}, headers=player.h).status_code == 422
    assert player.c.post(player.url("/board/items"), json={"kind": "note", "text": "x" * 500, "x": 1, "y": 1}, headers=player.h).status_code == 422


# ================================================================== hypotheses
def test_hypothesis_evaluation_tracks_evidence_and_alibis(player: Player):
    empty = player.post("/hypotheses/evaluate", {"culprit_key": "rohan", "motive_key": "m_ip_dispute"})
    assert empty["supporting"] == [] and empty["strength"] <= 40 and any("motive" in q for q in empty["open_questions"])
    player.search_everything()
    full = player.post("/hypotheses/evaluate", {"culprit_key": "rohan", "motive_key": "m_ip_dispute"})
    assert full["strength"] > empty["strength"] and full["motive_fit"]["supporting_evidence"]
    meera = player.post("/hypotheses/evaluate", {"culprit_key": "meera", "motive_key": "m_embezzlement"})
    assert meera["alibi"]["status"] == "cleared_for_window" and meera["opposing"]
    player.post("/hypotheses/evaluate", {"culprit_key": "gopal"}, expect=404)  # a witness is not a suspect
    player.post("/hypotheses/evaluate", {"culprit_key": "rohan", "motive_key": "m_nonsense"}, expect=404)
    saved = player.post("/hypotheses", {"title": "t", "culprit_key": "rohan", "motive_key": "m_ip_dispute", "evidence_for": ["ev_watch"],
                                        "evidence_against": []}, expect=201)
    assert saved["evaluation"]["strength"] == full["strength"]
    player.post("/hypotheses", {"title": "t", "culprit_key": "rohan", "motive_key": None, "evidence_for": ["ev_not_held"],
                                "evidence_against": []}, expect=404)
