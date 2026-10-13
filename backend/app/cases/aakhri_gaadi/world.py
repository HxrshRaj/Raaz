"""Locations, hotspots, events, motives, reference documents for 'Aakhri Gaadi'."""

from __future__ import annotations

from ..base import ClockSpec, Doc, Event, Hotspot, Location, Motive

BRIEFING = (
    "Devgarh Junction, 11:47 PM. The monsoon has been hammering the city for three days and the last "
    "Up Express left an hour ago. In a private saloon carriage on Siding 4 — a coach that was supposed to "
    "stay locked all night — Adrian Vale, 46, founder of Valecore Systems, lies dead. One blow to the "
    "temple. The door was locked from the outside, and the key is not on him.\n\n"
    "Five people had reasons to be at the station tonight: his business partner, the stationmaster, a "
    "journalist, a former Valecore engineer, and the security contractor. A tea-stall owner saw most of "
    "it and understood none of it. Their stories do not agree with the logs, and the logs do not agree "
    "with each other. The station clock has been wrong for days.\n\n"
    "Valecore's sale to Northwind Logistics closes on Monday and every one of them will be gone by "
    "morning. You have tonight."
)

LOCATIONS: tuple[Location, ...] = (
    Location(
        key="platform",
        name="Devgarh Junction — Platforms 1 & 2",
        description="Wet iron, sodium lamps, a clock everyone has stopped trusting. The Kosi Passenger "
        "stands on Platform 2 and the rain drums on the zinc roof.",
        scene="platform",
        sort=1,
        hotspots=(
            Hotspot(
                "h_clock", "Platform clock", "The big Seiko-faced station clock reads 11:35. Your own "
                "wristwatch says 11:47. A brass maintenance tag hangs under it.",
                ("ev_clock_slow",), 46, 10, 9, 14, icon="clock",
            ),
            Hotspot(
                "h_timetable", "Timetable board", "The painted timetable board, rain-streaked but legible.",
                ("ev_timetable",), 10, 34, 16, 22, icon="board",
            ),
        ),
    ),
    Location(
        key="carriage",
        name="Private Saloon SC-4471",
        description="A restored 1930s saloon coach: teak panelling, brass lamps, a writing desk bolted to "
        "the floor. Rain ticks on the roof. The light is still on.",
        scene="carriage",
        sort=2,
        hotspots=(
            Hotspot(
                "h_body", "Adrian Vale", "He lies beside the desk. One wound at the left temple. The police "
                "surgeon, kneeling in the lamplight, gives you a preliminary opinion.",
                ("ev_autopsy_prelim",), 38, 62, 16, 16, icon="body",
            ),
            Hotspot(
                "h_wrist", "Smartwatch on the wrist", "A smartwatch, still on his left wrist, screen dark.",
                ("ev_watch",), 44, 58, 7, 8, requires=("ev_autopsy_prelim",), icon="watch",
            ),
            Hotspot(
                "h_phone", "Mobile phone on the desk", "His phone lies face-up beside the lamp, "
                "unlocked — the surgeon had the thumb-print applied under protocol.",
                ("ev_sms_thread", "ev_call_log"), 66, 52, 8, 9, icon="phone",
            ),
            Hotspot(
                "h_desk", "Writing desk", "Papers, a blotter, an empty place where something heavy stood.",
                ("ev_paperweight",), 56, 44, 14, 12, requires=("ev_autopsy_prelim",), icon="desk",
            ),
            Hotspot(
                "h_under_desk", "Under the desk", "Something pale is wedged against the desk's iron foot.",
                ("ev_ticket_stub",), 52, 82, 9, 8, icon="ticket",
            ),
            Hotspot(
                "h_seat", "Visitor's armchair", "A leather armchair, pulled out for a guest. Something "
                "small glints in the seam of the cushion.",
                ("ev_button",), 20, 66, 12, 14, icon="chair",
            ),
            Hotspot(
                "h_tea", "Two clay cups", "Two kulhad cups sit on a side table, one with a faint "
                "lipstick edge.",
                ("ev_tea_cups",), 80, 62, 8, 8, icon="cup",
            ),
            Hotspot(
                "h_briefcase", "Open briefcase", "A leather briefcase, half-packed, a bound document "
                "on top.",
                ("ev_sale_agreement",), 74, 78, 12, 9, icon="case",
            ),
            Hotspot(
                "h_door", "Carriage door and lock", "The door's brass deadbolt is thrown. From inside "
                "it turns with a thumb-latch; from outside it can only be locked with a key.",
                ("ev_door_lock",), 90, 40, 8, 30, icon="lock",
            ),
        ),
    ),
    Location(
        key="stationmaster_office",
        name="Stationmaster's Office",
        description="Brass bells, teak almirahs, forty years of registers and a smell of damp paper. "
        "The door was unlocked when you arrived.",
        scene="office",
        sort=3,
        hotspots=(
            Hotspot(
                "h_register", "Station Working Register", "The great ledger of the day's movements, "
                "open at tonight's page.",
                ("ev_register",), 14, 48, 16, 14, icon="book",
            ),
            Hotspot(
                "h_key_cabinet", "Key cabinet", "A glass-fronted cabinet of numbered hooks with a "
                "sign-out register hanging beside it.",
                ("ev_key_register",), 64, 30, 14, 26, icon="key",
            ),
            Hotspot(
                "h_drawer", "Desk drawer", "The stationmaster's top drawer, half-open.",
                ("ev_siding_receipt",), 38, 64, 12, 8, icon="drawer",
            ),
            Hotspot(
                "h_ticket_log", "Ticket machine journal", "The daily printout from the platform-ticket "
                "machine, folded under a paperweight.",
                ("ev_ticket_log",), 30, 50, 9, 8, icon="printer",
            ),
            Hotspot(
                "h_in_tray", "In-tray", "An in-tray with a handwritten memo clipped to a signal sheet.",
                ("ev_signal_memo",), 52, 56, 9, 8, icon="tray",
            ),
        ),
    ),
    Location(
        key="waiting_room",
        name="Waiting Room (1st Class)",
        description="Cane benches, a dead ceiling fan, a window facing the siding side of the yard.",
        scene="waiting",
        sort=4,
        hotspots=(
            Hotspot(
                "h_window", "Window onto the yard", "From the bench by this window you can see the "
                "Siding 4 gate, but not the carriage beyond it.",
                ("ev_sightline",), 62, 28, 18, 30, icon="window",
            ),
            Hotspot(
                "h_bin", "Waste bin", "A steel bin beside the bench. Paper at the top is torn but "
                "pale and crisp.",
                ("ev_bank_slip",), 14, 72, 9, 12, icon="bin",
            ),
            Hotspot(
                "h_newspaper", "Folded newspaper", "Yesterday's Devgarh Dispatch, folded to page three.",
                ("ev_newspaper",), 40, 64, 12, 8, icon="news",
            ),
        ),
    ),
    Location(
        key="security_room",
        name="Security Room (Rathore Securitas)",
        description="Six flickering monitors, a thermos, an access-control PC and a logbook with a "
        "ballpoint on a string.",
        scene="security",
        sort=5,
        hotspots=(
            Hotspot(
                "h_dvr_waiting", "Monitor 2 — waiting room camera", "The DVR keeps 48 hours. You queue "
                "the waiting-room camera.",
                ("ev_cctv_waiting",), 18, 36, 16, 18, icon="monitor",
            ),
            Hotspot(
                "h_dvr_platform", "Monitor 4 — Platform 2 camera", "You queue Platform 2 for the "
                "relevant stretch.",
                ("ev_cctv_platform",), 38, 36, 16, 18, icon="monitor",
            ),
            Hotspot(
                "h_access_pc", "Access-control terminal", "Every badge and gate sensor in the yard "
                "reports here.",
                ("ev_access_log",), 64, 48, 14, 14, icon="pc",
            ),
            Hotspot(
                "h_maint_log", "Maintenance logbook", "The camera maintenance logbook, signed daily.",
                ("ev_maint_log",), 80, 70, 12, 8, icon="book",
            ),
        ),
    ),
    Location(
        key="tea_stall",
        name="Gopal's Chai Stall (Platform 3)",
        description="A tin-roofed stall, a hissing kerosene stove, the only warm light on the "
        "platform. Gopal knows everyone.",
        scene="tea",
        sort=6,
        hotspots=(
            Hotspot(
                "h_upi_ledger", "UPI payment ledger", "Gopal taps his phone's payment app. The "
                "bank-synced timestamps are on the real clock.",
                ("ev_upi_ledger",), 62, 52, 12, 12, icon="phone",
            ),
        ),
    ),
    Location(
        key="siding4",
        name="Siding 4 & Storm Drain",
        description="A muddy spur behind the yard gate. Rails shine under a single lamp; a storm "
        "drain runs along the fence.",
        scene="siding",
        initially_unlocked=False,
        sort=7,
        unlock_hint="Something about the carriage door suggests the killer used the yard side.",
        hotspots=(
            Hotspot(
                "h_drain", "Storm drain", "Brown water chuckles down the drain. Something brass "
                "catches the torch.",
                ("ev_key",), 30, 78, 14, 9, icon="drain",
            ),
            Hotspot(
                "h_cam7", "Camera pole (CAM-7)", "CAM-7 should be watching this gate.",
                ("ev_cam7_cable",), 70, 20, 8, 26, icon="camera",
            ),
            Hotspot(
                "h_gate", "Yard gate latch", "The wicket gate onto Station Road, its latch rusted.",
                ("ev_gate_thread",), 50, 46, 10, 20, icon="gate",
            ),
        ),
    ),
    Location(
        key="valecore_office",
        name="Valecore Systems — Devgarh Office",
        description="Glass partitions, dead monitors, a half-packed whiteboard. The office manager "
        "lets you in with a landlord's keys.",
        scene="corp",
        off_site=True,
        initially_unlocked=False,
        sort=8,
        unlock_hint="The sale agreement names Valecore's Devgarh office.",
        hotspots=(
            Hotspot(
                "h_hr", "HR file cabinet", "Personnel files, alphabetised, a few pulled.",
                ("ev_dismissal",), 16, 50, 14, 24, icon="drawer",
            ),
            Hotspot(
                "h_patent", "Legal tray", "A tray of IP filings awaiting the Northwind lawyers.",
                ("ev_patent",), 44, 56, 12, 10, icon="doc",
            ),
            Hotspot(
                "h_mail", "Adrian's mail archive", "Adrian's office PC, unlocked under the warrant.",
                ("ev_threat_email",), 66, 50, 14, 14, icon="pc",
            ),
            Hotspot(
                "h_audit", "Audit workpapers", "The auditors' workpapers on the conference table.",
                ("ev_ledger_kaveri",), 78, 74, 14, 10, icon="folder",
            ),
        ),
    ),
    Location(
        key="sai_telecom",
        name="Sai Mobile & SIM Centre, Lakadganj Road",
        description="A narrow shopfront of phone covers and recharge coupons. The shutter was half "
        "down; a call to the owner's son got it rolled up.",
        scene="shop",
        off_site=True,
        initially_unlocked=False,
        sort=9,
        unlock_hint="The text thread shows a number that isn't saved in Adrian's phone.",
        hotspots=(
            Hotspot(
                "h_sim", "SIM activation register", "A spiral-bound register of activations with "
                "photo-copied IDs.",
                ("ev_sim_record",), 36, 54, 16, 12, icon="book",
            ),
        ),
    ),
)

EVENTS: tuple[Event, ...] = (
    Event("e_arrive", 1, "20:40", "Adrian's saloon is stabled on Siding 4",
          "Adrian Vale arrives on the Intercity; his private coach is parked on Siding 4 under an informal arrangement.",
          ("ev_timetable", "ev_key_register", "ev_siding_receipt")),
    Event("e_sms", 2, "21:58", "Adrian texts an unsaved number",
          "At 21:58 Adrian texts a mobile number: 'Siding 4. 10:45. Come alone. Last chance to settle this.'",
          ("ev_sms_thread",)),
    Event("e_call", 3, "22:36", "Adrian and Meera argue by phone",
          "From 22:36 to 22:40 Adrian is on a four-minute call with Meera Kapadia.",
          ("ev_call_log", "ev_t_meera_admission")),
    Event("e_ticket", 4, "22:37", "A platform ticket is bought for the Siding 4 visitor",
          "A platform ticket (not a journey ticket) is bought by 'ROHAN D***' and the holder enters the station.",
          ("ev_ticket_log", "ev_ticket_stub")),
    Event("e_directions", 5, "22:42", "A stranger in an olive raincoat asks the way to Siding 4",
          "A tall man in an olive raincoat asks Gopal for the Siding 4 gate.",
          ("ev_t_gopal_olive", "ev_t_tanvi_sighting")),
    Event("e_voices", 6, "22:53", "Angry voices heard from the carriage",
          "Kabir, passing the gate, hears Adrian arguing with a younger man about who wrote 'the code'.",
          ("ev_t_kabir_voices",)),
    Event("e_train", 7, "22:57", "The Kosi Passenger leaves — long after its schedule",
          "Held by a signal failure, the Kosi Passenger is flagged off at 22:45 station time (22:57 real) — not at 22:15.",
          ("ev_signal_memo", "ev_cctv_platform", "ev_t_gopal_train", "ev_t_hari_admission")),
    Event("e_death", 8, "22:58", "Adrian's heart stops",
          "The smartwatch records the last heartbeat at 22:58:41.",
          ("ev_watch",)),
    Event("e_locked", 9, "23:02", "The carriage is locked from outside",
          "After the death someone locked the carriage door from outside using Adrian's own key.",
          ("ev_door_lock", "ev_key")),
    Event("e_found", 10, "23:47", "The body is discovered",
          "Kabir and Meera, worried by the unanswered calls, have the carriage opened with the spare key.",
          ()),
)

MOTIVES: tuple[Motive, ...] = (
    Motive("m_ip_dispute", "A dispute over who created — and who profits from — the Pathfinder engine",
           "Authorship and sale of a valuable invention.", ("rohan",),
           ("ev_patent", "ev_threat_email", "ev_sale_agreement", "ev_t_kabir_voices")),
    Motive("m_dismissal_revenge", "Revenge for being dismissed from the company",
           "A personal grudge over a firing.", ("rohan",), ("ev_dismissal",)),
    Motive("m_embezzlement", "Stopping the discovery of siphoned company funds",
           "Preventing exposure of financial misconduct.", ("meera",),
           ("ev_ledger_kaveri", "ev_bank_slip", "ev_t_meera_kaveri")),
    Motive("m_exposure", "Silencing a story before it was published",
           "Preventing or controlling press coverage.", ("tanvi",), ("ev_newspaper", "ev_t_tanvi_pendrive")),
    Motive("m_bribe_cover", "Hiding an under-the-table payment from the Railways",
           "Protecting a career from an official inquiry.", ("hari",), ("ev_siding_receipt", "ev_t_hari_bribe")),
    Motive("m_contract", "A dispute over a security contract",
           "Money owed or contract penalties.", ("kabir",), ("ev_maint_log", "ev_cam7_cable")),
    Motive("m_robbery", "Robbery", "A theft that went wrong.", (), ()),
)

DOCS: tuple[Doc, ...] = (
    Doc("doc_briefing", "Police briefing — 23:52", BRIEFING),
    Doc("doc_layout", "Station layout (yard map)",
        "Devgarh Junction has four platforms and a yard behind them. Platform 1 is the main platform with the station "
        "clock and the stationmaster's office. Platform 2 serves local trains such as the Kosi Passenger. The tea stall "
        "stands on Platform 3. The first-class waiting room faces the yard. The security room sits behind Platform 1. "
        "Siding 4 runs behind the yard fence and is reached from the platforms by the yard gate (the 'siding gate') or "
        "from Station Road by a wicket gate. Walking times in the rain: tea stall to siding gate 2 minutes; siding gate "
        "to saloon 2 minutes; waiting room to saloon 6 minutes; Platform 2 to saloon 6 minutes."),
    Doc("doc_ticket_rules", "Railway rules — platform tickets",
        "A platform ticket admits a person to the platform for two hours and is NOT a ticket for travel. Passengers "
        "boarding a train must hold a journey ticket or reservation. Platform ticket machines print an issue time and a "
        "serial; the journal is kept by the stationmaster."),
    Doc("doc_clock_policy", "Station network clocks",
        "All station systems — the register, DVR overlay, signal sheets, access controller and platform-ticket "
        "printers — take their time from the Platform 1 master clock. Mobile phones, bank/UPI systems and wearables "
        "use network time.", "ev_clock_slow"),
    Doc("doc_lock_manual", "Saloon SC-4471 lock manual",
        "The saloon door has a spring deadbolt. From inside it is thrown with the thumb-latch. From outside it can only "
        "be thrown with the carriage key (one with the owner, one spare in the stationmaster's cabinet). The deadbolt "
        "cannot be thrown from outside without a key."),
    Doc("doc_valecore_press", "Valecore press note",
        "Valecore Systems, Devgarh-founded logistics-software firm, will sign a Rs 410 crore sale of its routing "
        "technology ('Pathfinder') to Northwind Logistics on Monday. Founder Adrian Vale called Pathfinder 'the best "
        "thing I ever built'."),
    Doc("doc_kosi", "Kosi Passenger service card",
        "Train 56721 Kosi Passenger: scheduled departure Platform 2, 22:15. Monsoon speed restrictions apply. Late "
        "running is reported to the Section Controller; delays over 15 minutes trigger a stationmaster's incident note."),
    Doc("doc_forensics", "How the police surgeon dates a death",
        "Rigor and temperature give wide windows on a wet night. A wearable heart-rate trace, where available, fixes "
        "the time of death far more tightly, provided you know which clock it uses.", "ev_autopsy_prelim"),
)

CLOCK = ClockSpec(
    st_to_rt_minutes=12,
    discovered_by=("ev_clock_slow", "ev_t_hari_clock", "ev_t_gopal_clock"),
    sources_on_st=(
        "ev_register", "ev_signal_memo", "ev_cctv_waiting", "ev_cctv_platform", "ev_access_log",
        "ev_ticket_log", "ev_ticket_stub", "ev_t_gopal_train", "ev_t_gopal_olive", "ev_t_kabir_admission",
    ),
)

TRAVEL: dict[tuple[str, str], int] = {
    ("tea_stall", "siding4"): 1,
    ("siding4", "carriage"): 2,
    ("tea_stall", "carriage"): 3,
    ("waiting_room", "carriage"): 6,
    ("platform", "carriage"): 6,
    ("security_room", "carriage"): 5,
    ("stationmaster_office", "carriage"): 6,
    ("waiting_room", "siding4"): 4,
    ("platform", "siding4"): 4,
    ("security_room", "siding4"): 3,
    ("security_room", "tea_stall"): 3,
    ("stationmaster_office", "platform"): 1,
}
