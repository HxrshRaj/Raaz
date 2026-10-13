"""Contradiction, alibi and accusation rules for 'Aakhri Gaadi'. Server-side only."""

from __future__ import annotations

from ..base import AccusationSpec, AlibiRule, ContradictionRule, EvidenceRequirement

CONTRADICTIONS: tuple[ContradictionRule, ...] = (
    ContradictionRule(
        "c_rohan_stub", "Rohan's 'gone before half past ten' vs a platform ticket sold at 22:25",
        "Rohan claims he was aboard the Kosi Passenger and gone before 22:30. A platform ticket (PT-0412, not a "
        "journey ticket) was sold to a payer named 'ROHAN D***' at 22:25 station time, and its stub was left inside "
        "the saloon.",
        (("ev_stmt_rohan_alibi", "ev_ticket_stub"), ("ev_stmt_rohan_alibi", "ev_ticket_log")), "rohan", 3),
    ContradictionRule(
        "c_rohan_train", "Rohan's train had not left yet",
        "Rohan says the Kosi Passenger left on time and he was away well before 22:30. The signal memo, the Platform 2 "
        "camera and Gopal all agree the Kosi was held until about 22:45 station time (22:57 real time).",
        (("ev_stmt_rohan_alibi", "ev_signal_memo"), ("ev_stmt_rohan_alibi", "ev_cctv_platform"),
         ("ev_stmt_rohan_alibi", "ev_t_gopal_train")), "rohan", 2),
    ContradictionRule(
        "c_rohan_contact", "'No contact since January' vs the 04417 texts",
        "Rohan denies contact with Adrian, but the unsaved number that exchanged texts with Adrian tonight was "
        "activated in his sister's name with Rohan as the alternate contact.",
        (("ev_stmt_rohan_nocontact", "ev_sim_record"), ("ev_stmt_rohan_nocontact", "ev_sms_thread")), "rohan", 3),
    ContradictionRule(
        "c_register", "The register says 22:15; everything else says 22:45",
        "The Working Register records the Kosi Passenger departing 22:15 'On time' (station time). The signal memo, the "
        "Platform 2 camera and Gopal place the departure at about 22:45 station time. The entry was overwritten, so the "
        "register cannot serve as anyone's alibi.",
        (("ev_register", "ev_signal_memo"), ("ev_register", "ev_cctv_platform"), ("ev_register", "ev_t_gopal_train")),
        "hari", 2),
    ContradictionRule(
        "c_hari_ontime", "Hari's 'on time' vs the flag-off footage",
        "Hari insists the Kosi left at 10:15 on time, but his own memo says Signal 4B held it until 22:44 and the camera "
        "shows him flagging it away at 22:45:10 station time.",
        (("ev_stmt_hari_ontime", "ev_cctv_platform"), ("ev_stmt_hari_ontime", "ev_signal_memo")), "hari", 1),
    ContradictionRule(
        "c_meera_call", "Meera's 'under a minute' vs a 4-minute call",
        "Meera says Adrian's call lasted under a minute. The call log shows 22:36:20–22:40:32 (4m12s).",
        (("ev_stmt_meera_call", "ev_call_log"),), "meera", 1),
    ContradictionRule(
        "c_kabir_post", "Kabir's 'in the room all night' vs the gate log",
        "Kabir says he never left the security room. His badge went through the siding gate in and out at 22:41–22:44 "
        "station time.",
        (("ev_stmt_kabir_post", "ev_access_log"),), "kabir", 1),
    ContradictionRule(
        "c_cam7", "'CAM-7 checked, OK' vs the unplugged cable",
        "The maintenance log claims CAM-7 was checked every day, but its cable has been unplugged long enough to "
        "grow cobwebs.",
        (("ev_maint_log", "ev_cam7_cable"),), "kabir", 1),
    ContradictionRule(
        "c_tanvi_cups", "Tanvi's 'never near the carriage' vs two tea cups",
        "Tanvi says she never went near the carriage, but two of Gopal's stamped cups — one with a woman's lipstick — "
        "were inside it.",
        (("ev_stmt_tanvi_tea", "ev_tea_cups"),), "tanvi", 1),
)

ALIBIS: tuple[AlibiRule, ...] = (
    AlibiRule(
        "al_waiting", ("meera", "tanvi"), ("ev_cctv_waiting", "ev_watch", "ev_clock_slow"),
        "At the moment Adrian's heart stopped (22:58:41 RT = 22:46:41 station time) both Meera Kapadia and Tanvi Sethi "
        "are in frame on the waiting-room camera, six minutes from the saloon.",
        "22:58:41 RT"),
    AlibiRule(
        "al_hari", ("hari",), ("ev_cctv_platform", "ev_watch", "ev_clock_slow"),
        "Hari Joshi flagged off the Kosi Passenger on Platform 2 at 22:57:10 RT — 91 seconds before the death, six "
        "minutes from the saloon.", "22:58:41 RT"),
    AlibiRule(
        "al_kabir", ("kabir",), ("ev_upi_ledger", "ev_watch"),
        "Kabir Rathore paid for tea at Platform 3 at 22:58:05 RT — 36 seconds before the death, three minutes from the "
        "saloon.", "22:58:41 RT"),
)

ACCUSATION = AccusationSpec(
    culprit="rohan",
    motive="m_ip_dispute",
    motive_partial=("m_dismissal_revenge",),
    canonical_sequence=("e_sms", "e_call", "e_ticket", "e_directions", "e_voices", "e_train", "e_death", "e_locked"),
    min_sequence=4,
    requirements=(
        EvidenceRequirement(
            "r_placement", "Places the accused at the saloon or siding",
            ("ev_ticket_stub", "ev_ticket_log", "ev_button", "ev_gate_thread", "ev_t_gopal_olive", "ev_t_tanvi_sighting", "ev_key"), 5),
        EvidenceRequirement(
            "r_meeting", "Shows a pre-arranged meeting with the victim",
            ("ev_sms_thread", "ev_sim_record", "ev_t_rohan_admission"), 5),
        EvidenceRequirement(
            "r_alibi", "Breaks the accused's alibi",
            ("ev_signal_memo", "ev_cctv_platform", "ev_t_gopal_train", "ev_t_hari_admission"), 5),
        EvidenceRequirement(
            "r_motive", "Establishes the motive",
            ("ev_patent", "ev_dismissal", "ev_threat_email", "ev_t_kabir_voices", "ev_sale_agreement"), 4),
        EvidenceRequirement("r_time", "Fixes the time of death", ("ev_watch",), 3),
        EvidenceRequirement(
            "r_elimination", "Eliminates the other suspects",
            ("ev_cctv_waiting", "ev_cctv_platform", "ev_upi_ledger"), 3, need=2),
    ),
    key_contradictions=("c_rohan_stub", "c_rohan_train", "c_rohan_contact", "c_register"),
    closing_threshold=4,
    must_have_any_of=("r_placement", "r_meeting"),
    max_attempts=3,
)

SOLUTION_NARRATIVE = (
    "Rohan Deshmukh, fired as CTO after Adrian patented Pathfinder in his own name, learned of the Rs 410 crore Northwind "
    "sale. From a burner SIM in his sister's name he texted Adrian that he would go to the press; Adrian replied at 21:58 "
    "with a meeting at Siding 4 at 22:45. Rohan bought a platform ticket at 22:25 station time (22:37 real), asked Gopal the "
    "way, and reached the saloon. They argued; Kabir overheard it at about 22:53. At 22:58:41 Rohan struck Adrian once with a "
    "brass paperweight, took Adrian's key, locked the door from outside, dropped the key in the storm drain by the wicket gate "
    "and left, snagging his olive raincoat on the gate. His 'I took the 10:15 Kosi Passenger' alibi leaned on a register "
    "that Hari had altered for unrelated reasons; the Kosi in fact left at 22:57 real time."
)
