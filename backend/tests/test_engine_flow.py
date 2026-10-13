from __future__ import annotations

import json

from tests.helpers import Player


def test_new_session_starts_clean(player: Player):
    ov = player.get("")
    assert ov["case_title"].startswith("Aakhri Gaadi")
    assert ov["progress"]["evidence"] == 0
    locs = {loc["key"]: loc for loc in player.get("/locations")}
    assert not locs["platform"]["locked"]
    assert locs["siding4"]["locked"] and locs["valecore_office"]["locked"] and locs["sai_telecom"]["locked"]
    assert player.get("/evidence") == []


def test_locked_location_cannot_be_entered(player: Player):
    player.get("/locations/siding4", expect=403)
    player.post("/locations/siding4/hotspots/h_drain/inspect", expect=403)


def test_discovery_and_unlock_chain(player: Player):
    r = player.inspect("carriage", "h_door")
    assert [e["key"] for e in r["new_evidence"]] == ["ev_door_lock"]
    assert [u["key"] for u in r["unlocked_locations"]] == ["siding4"]
    r2 = player.inspect("siding4", "h_drain")
    assert r2["new_evidence"][0]["key"] == "ev_key"
    # the second look finds nothing new
    again = player.inspect("siding4", "h_drain")
    assert again["new_evidence"] == [] and again["already_found"] == ["ev_key"]


def test_gated_hotspot_is_invisible_until_prerequisite(player: Player):
    keys = {h["key"] for h in player.get("/locations/carriage")["hotspots"]}
    assert "h_wrist" not in keys and "h_desk" not in keys
    player.post("/locations/carriage/hotspots/h_wrist/inspect", expect=404)
    player.inspect("carriage", "h_body")
    keys = {h["key"] for h in player.get("/locations/carriage")["hotspots"]}
    assert {"h_wrist", "h_desk"} <= keys


def test_examine_reveals_detail_once(player: Player):
    player.inspect("stationmaster_office", "h_register")
    ev = player.get("/evidence/ev_register")
    assert ev["examined_detail"] is None and ev["reliability"] == "unverified"
    first = player.examine("ev_register")
    assert first["first_examination"] and "overwritten" in first["evidence"]["examined_detail"]
    assert first["evidence"]["reliability"] == "altered"
    assert player.examine("ev_register")["first_examination"] is False


def test_cannot_examine_or_read_undiscovered_evidence(player: Player):
    player.post("/evidence/ev_watch/examine", expect=404)
    player.get("/evidence/ev_watch", expect=404)
    player.post("/evidence/ev_nonexistent/examine", expect=404)


def test_clock_conversion_is_hidden_until_clock_is_known(player: Player):
    player.inspect("stationmaster_office", "h_ticket_log")
    ev = player.get("/evidence/ev_ticket_log")
    assert all("real_time" not in t for t in ev["timestamps"])
    player.inspect("platform", "h_clock")
    ev = player.get("/evidence/ev_ticket_log")
    assert ev["timestamps"][0]["real_time"] == "22:37:40"


def test_contradiction_requires_real_conflict(player: Player):
    player.inspect("stationmaster_office", "h_register")
    player.inspect("stationmaster_office", "h_in_tray")
    player.inspect("platform", "h_timetable")
    bad = player.post("/contradictions/check", {"a": "ev_register", "b": "ev_timetable"})
    assert bad["established"] is False
    good = player.post("/contradictions/check", {"a": "ev_register", "b": "ev_signal_memo"})
    assert good["established"] and good["newly_found"]
    assert good["contradiction"]["key"] == "c_register"
    again = player.post("/contradictions/check", {"a": "ev_signal_memo", "b": "ev_register"})
    assert again["established"] and not again["newly_found"]
    assert [c["key"] for c in player.get("/contradictions")] == ["c_register"]


def test_save_and_resume_preserves_state(client, player: Player):
    player.inspect("carriage", "h_body")
    player.inspect("carriage", "h_phone")
    before = player.get("/evidence")
    # "leave and come back": a brand-new HTTP client with the same token sees the same investigation
    sessions = client.get("/api/v1/sessions", headers=player.h).json()
    assert sessions and sessions[0]["id"] == player.sid
    after = player.get("/evidence")
    assert [e["key"] for e in before] == [e["key"] for e in after]
    assert player.get("")["progress"]["evidence"] == len(after)


def test_no_public_endpoint_leaks_the_solution(player: Player):
    """Sweep the whole map and every read endpoint; none may contain solution-only strings."""
    player.search_everything()
    blobs = [json.dumps(player.get(p)) for p in ("", "/locations", "/evidence", "/dossiers", "/events", "/contradictions",
                                                 "/board", "/timeline", "/hypotheses", "/accusation/options")]
    for ch in ("rohan", "meera", "hari", "tanvi", "kabir", "gopal"):
        blobs.append(json.dumps(player.get(f"/dossiers/{ch}")))
    text = "\n".join(blobs).lower()
    for forbidden in ("solution_culprit", "solution_narrative", "struck adrian once", "canonical", "leak_markers",
                      "reveal_line", "public_truthful", "rf_confession", "dropped the key in the storm drain by the wicket"):
        assert forbidden not in text, forbidden
    # dossier of the true culprit must look like every other dossier
    d = player.get("/dossiers/rohan")
    assert set(d) == set(player.get("/dossiers/meera"))
    assert "culprit" not in json.dumps(d).lower()
