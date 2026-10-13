"""All evidence for 'Aakhri Gaadi' (physical items, documents, logs, statements and testimony)."""

from __future__ import annotations

from ..base import Bears, Evidence, Timestamp

T = Timestamp
B = Bears

_PHYSICAL: tuple[Evidence, ...] = (
    Evidence(
        "ev_clock_slow", "Platform 1 master clock", "timeline",
        "The master clock on Platform 1 reads 11:35 PM. Your wristwatch says 11:47. A brass tag under it reads: "
        "'Lightning surge Sunday 18:10 — clock retarded 12 min. Recalibration pending. — Signal Dept.'",
        "The tag is dated Sunday. Everything that takes its time from this clock — the working register, the DVR "
        "overlay, signal sheets, the access controller and the platform-ticket printers — is therefore twelve minutes "
        "behind real time. Station time (ST) + 12 min = real time (RT). Phones, UPI/bank systems and wearables "
        "use network time and are not affected.",
        "Platform 1, inspected with the Inspector's wristwatch", "platform", "verified", icon="clock",
        events=(), timestamps=(T("Clock reading", "ST", "23:35"),),
    ),
    Evidence(
        "ev_timetable", "Timetable board", "timeline",
        "Painted timetable board: 20:40 Intercity (Pf 1); 22:15 56721 Kosi Passenger (Pf 2); 23:50 Up Express "
        "(cancelled — monsoon).",
        "The Kosi Passenger is the only train that could have taken a passenger away from Devgarh between ten and "
        "eleven tonight. Adrian's Intercity arrived at 20:40.",
        "Platform 1 notice board", "platform", "verified", icon="board", events=("e_arrive",),
    ),
    Evidence(
        "ev_autopsy_prelim", "Police surgeon's preliminary note", "physical",
        "Dr. Iyer: a single blunt-force blow to the left temple from a heavy, rounded object. No defensive wounds. "
        "Time of death by temperature: between 22:30 and 23:30 — a wide window on a wet night.",
        "Dr. Iyer adds: 'If he's wearing a connected watch, read its last heartbeat. That is better than any "
        "thermometer. Ask what clock it keeps.' The victim was struck once, probably mid-argument, by someone "
        "he was talking to.",
        "Police surgeon, at the scene", "carriage", "verified", icon="body", related_people=("adrian",),
    ),
    Evidence(
        "ev_watch", "Adrian's smartwatch", "digital",
        "Smartwatch heart-rate log: pulse climbing from 22:50, then a final beat recorded at 22:58:41. After that, a "
        "flat line.",
        "The watch takes its time from the mobile network — real time (RT), unaffected by the station clock. Time of "
        "death: 22:58 ± 1 minute RT. Whoever killed Adrian was inside the carriage at that moment.",
        "Wearable on the victim's left wrist", "carriage", "verified", icon="watch", events=("e_death",),
        related_people=("adrian",), timestamps=(T("Last heartbeat", "RT", "22:58:41"),),
    ),
    Evidence(
        "ev_sms_thread", "Adrian's text thread with an unsaved number", "digital",
        "A thread with an unsaved number ending 04417. 19:34 (in): 'I know you're in Devgarh for the Northwind signing. "
        "Ten minutes tonight or I go to the press.' 21:58 (out): 'Siding 4. 10:45. Come alone. Last chance to settle "
        "this.'",
        "Phone times are network time (RT). The sender has a grievance the company would prefer kept out of the "
        "newspapers, and agreed to a meeting at the saloon at 22:45. The subscriber behind the number can be found at "
        "the telecom shop that activated it.",
        "Adrian's phone, message app", "carriage", "verified", icon="phone", events=("e_sms",),
        unlocks_locations=("sai_telecom",),
        timestamps=(T("Meeting set", "RT", "21:58"), T("First message", "RT", "19:34")),
    ),
    Evidence(
        "ev_call_log", "Adrian's call log", "digital",
        "20:02 Meera Kapadia (in) 3m02s · 22:36:20 Meera Kapadia (out) 4m12s · 23:08:04 Meera (missed) · 23:21:30 "
        "Meera (missed).",
        "The 22:36 call ended at 22:40:32 RT: Adrian was alive then, and talking to Meera for over four minutes. Two "
        "unanswered calls from Meera follow, after the time of death.",
        "Adrian's phone, call history", "carriage", "verified", icon="phone", events=("e_call",),
        related_people=("meera",), timestamps=(T("Call start", "RT", "22:36:20"), T("Call end", "RT", "22:40:32")),
    ),
    Evidence(
        "ev_ticket_stub", "Torn platform-ticket stub PT-0412", "physical",
        "A torn stub wedged against the desk's iron foot: 'DEVGARH JN — PLATFORM TICKET — Rs 10 — PT-0412 — 22:25 — "
        "valid 2 hrs'.",
        "Platform tickets print the issuing machine's clock — station time. 22:25 ST is 22:37 RT. A platform ticket "
        "admits you to the platform; it is not a ticket for travel. Someone who was inside this carriage had entered "
        "the station on foot minutes before the meeting. The serial PT-0412 will be in the machine's journal.",
        "Under the writing desk", "carriage", "verified", icon="ticket", events=("e_ticket",),
        timestamps=(T("Issued", "ST", "22:25"),),
        bears_on=(B("rohan", "points_to", ("ev_ticket_log",), "Serial PT-0412 was sold to 'ROHAN D***'.", "presence"),),
    ),
    Evidence(
        "ev_button", "Olive horn button with thread", "physical",
        "A 14 mm olive-green horn button with a loop of waxed thread, caught in the seam of the visitor's armchair.",
        "Cheap rubberised raincoat button of the kind sold in the Lakadganj market; the thread was torn, not cut — "
        "the coat was snagged or grabbed. Rough, recent tear.",
        "Visitor's armchair cushion", "carriage", "verified", icon="chair",
    ),
    Evidence(
        "ev_paperweight", "Brass locomotive paperweight", "physical",
        "A 2 kg brass paperweight shaped like a WDM-2 locomotive, rolled against the bulkhead. Wiped, but a rust-red "
        "residue sits in the wheel spokes.",
        "Blood trace in the spokes; shape consistent with the head wound. No usable prints — wiped. The blow was "
        "struck with the nearest heavy object on the desk: not planned in advance.",
        "Against the bulkhead beneath the desk", "carriage", "verified", icon="desk",
    ),
    Evidence(
        "ev_door_lock", "The locked carriage door", "physical",
        "The deadbolt was thrown when the door was found. Adrian's carriage key is not on his body or anywhere in "
        "the coach.",
        "The lock manual says the deadbolt cannot be thrown from outside without a key. Someone locked the door from "
        "the outside after Adrian died, using his key — and took the key away with them. The spare has been in the "
        "stationmaster's cabinet. The yard side of the siding now bears looking at.",
        "Carriage door", "carriage", "verified", icon="lock", events=("e_locked",),
        unlocks_locations=("siding4",),
    ),
    Evidence(
        "ev_tea_cups", "Two clay tea cups", "physical",
        "Two kulhad cups on the side table stamped 'GOPAL CHAI — PF3'. One has a lipstick edge.",
        "The tea has been cold a long while — skin formed. They were drunk well before the end of the evening. "
        "One of them was drunk from by a woman. Gopal's stall is the only one that stamps its cups.",
        "Side table in the saloon", "carriage", "verified", icon="cup", related_people=("tanvi",),
    ),
    Evidence(
        "ev_sale_agreement", "Draft Share Purchase Agreement", "financial",
        "Valecore Systems ↔ Northwind Logistics, Rs 410 crore. Schedule 4, IP: 'Pathfinder routing engine — inventor "
        "and sole assignor: A. Vale'. Signing at Valecore's Devgarh office on Monday.",
        "In Adrian's margin note: 'R.D. — cl. 9 risk. Settle before Mon.' The sale depends on Adrian's clean title "
        "to Pathfinder.",
        "Adrian's briefcase", "carriage", "verified", icon="case", unlocks_locations=("valecore_office",),
    ),
    Evidence(
        "ev_register", "Station Working Register, p. 212", "timeline",
        "Entry: '22:15 — 56721 Kosi Passenger — dep. Pf 2 — On time.' Initialled H.J. (Station time.)",
        "Under the lens the '1' in '22:15' and the words 'On time' sit on a rubbed surface. Pen pressure from an "
        "earlier entry shows through: '22:45'. The entry has been overwritten.",
        "Stationmaster's working register", "stationmaster_office", "unverified", "altered", icon="book",
        events=("e_train",), related_people=("hari",), timestamps=(T("Recorded departure", "ST", "22:15"),),
        bears_on=(B("hari", "undermines_claim", (), "The register was altered by the keeper of the register.", "claim"),),
    ),
    Evidence(
        "ev_key_register", "Key cabinet sign-out sheet", "access",
        "'SC-4471 spare: OUT 20:40 (H. Joshi — walked Mr Vale's aide to the saloon). RETURNED 21:05.'",
        "Both entries are in Hari's hand and initialled by the duty clerk. The spare key was back on its hook from "
        "21:05, so it was not the key that locked the carriage. (Station time.)",
        "Key cabinet", "stationmaster_office", "verified", icon="key", events=("e_arrive",),
        related_people=("hari",),
    ),
    Evidence(
        "ev_siding_receipt", "Unofficial stabling receipt", "financial",
        "Pocket receipt book, carbon copy: 'Siding 4 — saloon stabling — Rs 50,000 cash — rec'd from V. Corp aide, "
        "20:50.' No corresponding entry in the official Siding Occupancy Ledger.",
        "An under-the-table payment: that is why the saloon is not on the official yard plan. It says nothing about "
        "the murder, but it explains why the stationmaster was nervous about every record in this room.",
        "Stationmaster's desk drawer", "stationmaster_office", "verified", icon="drawer",
        events=("e_arrive",), related_people=("hari",),
    ),
    Evidence(
        "ev_ticket_log", "Platform-ticket machine journal", "access",
        "Journal: 22:18:03 PT-0411 UPI 'MEHTA S.' · 22:25:40 PT-0412 UPI 'ROHAN D***' · 22:51:10 PT-0413 cash.",
        "Journal times are station time: 22:25:40 ST = 22:37:40 RT. PT-0412 was sold to a UPI payer 'ROHAN D***' — "
        "the same serial as the stub in the carriage. The ticket counter's list shows no journey ticket issued to "
        "a Deshmukh tonight.",
        "Platform-ticket machine's daily journal", "stationmaster_office", "verified", icon="printer",
        events=("e_ticket",), related_people=("rohan",), timestamps=(T("PT-0412 sold", "ST", "22:25:40"),),
        bears_on=(B("rohan", "points_to", (), "A platform ticket in his name was sold at 22:25 ST.", "presence"),),
    ),
    Evidence(
        "ev_signal_memo", "Signal fault memo", "timeline",
        "H. Joshi's handwritten memo on a signal sheet: 'Sig 4B failed 22:20. Kosi Passenger (56721) held at Pf 2. "
        "Section Controller cleared 22:44.'",
        "Memo times are station time. The Kosi Passenger was held until 22:44 ST — 22:56 RT — at the earliest. It can't "
        "have left at 22:15, and no one aboard it can have been 'gone before half past ten'.",
        "Stationmaster's in-tray", "stationmaster_office", "verified", icon="tray", events=("e_train",),
        related_people=("hari",), timestamps=(T("Fault", "ST", "22:20"), T("Cleared", "ST", "22:44")),
    ),
    Evidence(
        "ev_sightline", "View from the waiting-room window", "physical",
        "From the bench by the window one can see the Siding 4 gate but not the saloon beyond it.",
        "At night, through rain-smeared glass, you see silhouettes and lamp-lit shapes — enough to count people and "
        "judge clothing colour, not faces.",
        "Waiting-room window", "waiting_room", "verified", icon="window",
    ),
    Evidence(
        "ev_bank_slip", "Torn RTGS acknowledgement", "financial",
        "A torn RTGS acknowledgement: Rs 3.1 crore from 'Valecore Ops A/c' to 'Kaveri Holdings', initialled M.K.",
        "Dated last month. Not a legitimate payee on Valecore's vendor list. A pattern of transfers to one company "
        "is suggested.",
        "Waiting-room bin", "waiting_room", "unverified", "verified", icon="bin", related_people=("meera",),
        bears_on=(B("meera", "points_to", (), "Meera has a financial secret that Adrian was close to exposing.", "motive"),),
    ),
    Evidence(
        "ev_newspaper", "Devgarh Dispatch, page three", "digital",
        "'Valecore's quiet sale: who really owns Pathfinder?' by Tanvi Sethi.",
        "The piece hints that 'a former engineer disputes the origin of the code' without naming him. Tanvi had been "
        "circling the story for weeks.",
        "Waiting-room bench", "waiting_room", "verified", icon="news", related_people=("tanvi",),
    ),
    Evidence(
        "ev_cctv_waiting", "Waiting-room camera WR-1 footage", "digital",
        "WR-1 overlay (station time): Meera Kapadia in frame from 21:53; Tanvi Sethi from 21:53:40. Tanvi leaves frame "
        "22:12–22:15. Meera leaves frame 22:56–23:00, phone to ear. Otherwise both seated.",
        "Between 22:40 and 22:55 ST nothing moves but the two women and the rain. At 22:46:41 ST — which, with the "
        "clock offset, is the real time Adrian's heart stopped — both are in frame.",
        "Security room DVR", "security_room", "verified", icon="monitor",
        related_people=("meera", "tanvi"), timestamps=(T("Overlay", "ST", "21:53"),),
        bears_on=(
            B("meera", "clears", ("ev_watch", "ev_clock_slow"), "In frame at the moment of death.", "alibi"),
            B("tanvi", "clears", ("ev_watch", "ev_clock_slow"), "In frame at the moment of death.", "alibi"),
        ),
    ),
    Evidence(
        "ev_cctv_platform", "Platform 2 camera PF2-1 footage", "digital",
        "PF2-1 overlay (station time): 22:44:50 the guard waves a green lamp; 22:45:10 Hari Joshi raises the flag; "
        "22:45:20 the Kosi Passenger moves.",
        "Hari is in frame from 22:41 to 22:47 ST. 22:45:10 ST = 22:57:10 RT. The platform is a six-minute walk from "
        "the saloon, so Hari cannot also have been in the carriage at 22:58:41 RT. And the train left 30 station-"
        "minutes after the register says it did.",
        "Security room DVR", "security_room", "verified", icon="monitor", events=("e_train",),
        related_people=("hari",), timestamps=(T("Flag-off", "ST", "22:45:10"),),
        bears_on=(
            B("hari", "clears", ("ev_watch", "ev_clock_slow"), "On Platform 2 a minute and a half before the death.", "alibi"),
            B("rohan", "undermines_claim", ("ev_stmt_rohan_alibi",), "The train was not away until 22:45 ST.", "claim"),
        ),
    ),
    Evidence(
        "ev_access_log", "Access-controller export", "access",
        "(Station time) 21:58 K.RATHORE — SECURITY ROOM DOOR IN · 22:41:07 K.RATHORE — SIDING GATE IN · 22:44:20 "
        "SIDING GATE OUT · 22:49:12 SECURITY ROOM DOOR IN. 'CAM-7 heartbeat ONLINE' every 60.000 s for six days.",
        "Kabir's badge went through the siding gate at 22:41 ST (22:53 RT) and out at 22:44 ST (22:56 RT) — he was "
        "not in the security room. Also: CAM-7's 'heartbeat' arrives at exactly 60.000 s every time for six days, "
        "unlike every other device (which jitter by a few hundred ms). That precision is machine-generated.",
        "Access-control terminal", "security_room", "verified", icon="pc", events=("e_voices",),
        related_people=("kabir",), timestamps=(T("Gate in", "ST", "22:41:07"), T("Gate out", "ST", "22:44:20")),
        bears_on=(B("kabir", "undermines_claim", ("ev_stmt_kabir_post",), "He was not in the room.", "claim"),),
    ),
    Evidence(
        "ev_maint_log", "Camera maintenance logbook", "access",
        "'CAM-7 siding — checked, OK.' Signed K. Rathore for Mon, Tue, Wed, Thu, Fri.",
        "Five entries in identical ink and hand; the Thursday date is written over. No fault ever reported.",
        "Security room logbook", "security_room", "disputed", icon="book", related_people=("kabir",),
    ),
    Evidence(
        "ev_upi_ledger", "Chai stall UPI ledger", "financial",
        "Bank-synced (real time): 21:24:12 ₹40 T.SETHI (2× chai) · 22:58:05 ₹30 K.RATHORE · others.",
        "Kabir paid for tea at Platform 3 at 22:58:05 RT — 36 seconds before Adrian's heart stopped. The stall is a "
        "minute from the siding gate and three from the saloon. Tanvi bought two teas at 21:24.",
        "Gopal's payment app", "tea_stall", "verified", icon="phone", related_people=("kabir", "tanvi", "gopal"),
        timestamps=(T("Kabir pays", "RT", "22:58:05"), T("Tanvi pays", "RT", "21:24:12")),
        bears_on=(
            B("kabir", "clears", ("ev_watch",), "At the tea stall 36 s before the death, three minutes away.", "alibi"),
        ),
    ),
    Evidence(
        "ev_key", "Adrian's carriage key", "physical",
        "A brass key on a leather tag, stamped 'SC-4471 — A.V.', in the muddy storm drain six metres from the wicket gate.",
        "Adrian's own key — the one that locked the door. Dropped, not placed: mud on the bow. Whoever carried it "
        "left through this gate. Rain has washed away prints.",
        "Storm drain beside Siding 4", "siding4", "verified", icon="key", events=("e_locked",),
    ),
    Evidence(
        "ev_cam7_cable", "CAM-7 cable", "access",
        "CAM-7's data cable is unplugged at the junction box and taped with grey tape. Dust and cobwebs on the tape.",
        "Cobwebs and dust show it has been disconnected for days. CAM-7 recorded nothing tonight — or all week. "
        "The 'heartbeat' in the access log is a lie told by software.",
        "Camera pole, Siding 4", "siding4", "verified", icon="camera", related_people=("kabir",),
    ),
    Evidence(
        "ev_gate_thread", "Olive thread on the gate latch", "physical",
        "A tuft of olive waxed-cotton thread caught on the wicket gate's rusted latch.",
        "Same colour and weave as the button thread in the saloon. The rust under the thread is bright: it was torn "
        "off tonight. An olive raincoat went through this gate.",
        "Wicket gate, Siding 4", "siding4", "verified", icon="gate",
    ),
    Evidence(
        "ev_dismissal", "Rohan Deshmukh's HR file", "financial",
        "Termination letter 12 January ('restructuring'); Invention Assignment cl. 9; and a handwritten objection "
        "signed R. Deshmukh: 'Pathfinder is mine. I will not forget this.'",
        "Rohan was Valecore's CTO. He argued that Pathfinder pre-dated his assignment and that his dismissal was "
        "meant to cut him out of the sale.",
        "Valecore HR cabinet", "valecore_office", "verified", icon="drawer", related_people=("rohan",),
        bears_on=(B("rohan", "points_to", (), "A documented grievance over Pathfinder.", "motive"),),
    ),
    Evidence(
        "ev_patent", "Provisional patent application", "financial",
        "Filed 3 February by Adrian Vale as sole inventor: 'Adaptive route-optimisation engine (Pathfinder)'. "
        "Attached: scans of Rohan's 2021 lab notebooks deriving the core algorithm.",
        "Rohan's notebooks, dated three years before the filing, show he derived the algorithm. Adrian filed it in "
        "his own name weeks after firing him — and Rs 410 crore depends on that title.",
        "Valecore legal tray", "valecore_office", "verified", icon="doc", related_people=("rohan",),
        bears_on=(B("rohan", "points_to", (), "Motive: authorship and profit of Pathfinder.", "motive"),),
    ),
    Evidence(
        "ev_threat_email", "Rohan's email to Adrian", "digital",
        "18 March, R. Deshmukh → A. Vale: 'You filed my work in your name. You'll regret this. If Northwind signs, I "
        "take the notebooks to the press.'",
        "The 'press' threat mirrors the 19:34 text from the unsaved number tonight.",
        "Adrian's mail archive", "valecore_office", "verified", icon="pc", related_people=("rohan",),
        bears_on=(B("rohan", "points_to", (), "A prior threat in his own words.", "motive"),),
    ),
    Evidence(
        "ev_ledger_kaveri", "Audit workpapers: Kaveri Holdings", "financial",
        "Rs 11.2 crore moved from Valecore Ops to Kaveri Holdings over 24 months. Registered director: Meera Kapadia.",
        "A textbook siphon, uncovered by the auditors days ago and put to Adrian on Friday. Meera had a motive "
        "to silence him — but motive is not presence.",
        "Auditors' workpapers", "valecore_office", "verified", icon="folder", related_people=("meera",),
        bears_on=(B("meera", "points_to", (), "A strong financial motive.", "motive"),),
    ),
    Evidence(
        "ev_sim_record", "SIM activation record, number …04417", "access",
        "Activation 9 February: subscriber 'Sunita Deshmukh'; alternate contact: Rohan Deshmukh (brother); cash; "
        "photo-ID copy attached.",
        "The number that texted Adrian was bought in Rohan's sister's name — a burner with a paper trail back to "
        "him. Sunita Deshmukh lives near the old bazaar in Devgarh.",
        "Sai Mobile & SIM Centre register", "sai_telecom", "verified", icon="book", related_people=("rohan",),
        events=("e_sms",),
        bears_on=(B("rohan", "points_to", ("ev_sms_thread",), "The 04417 number belongs to his circle.", "meeting"),),
    ),
)

_STATEMENTS: tuple[Evidence, ...] = tuple(
    Evidence(k, name, "testimony", text, detail, f"Interview: {who}", None, "testimony",
             related_people=(who_key,), is_testimony=True, icon="speech", events=evs)
    for (k, name, text, detail, who, who_key, evs) in (
        ("ev_stmt_rohan_alibi", "Rohan: 'I took the 10:15 Kosi'",
         "'I took the 10:15 Kosi Passenger. By the platform clock I was aboard before half past ten and away not "
         "long after. I never went near the siding.'",
         "A statement of alibi: left on the scheduled Kosi Passenger and gone before 22:30.", "Rohan Deshmukh", "rohan", ()),
        ("ev_stmt_rohan_nocontact", "Rohan: 'No contact since January'",
         "'I haven't had any contact with Adrian since January. Only lawyers.'",
         "A claim of no contact. Mobile contact tonight would contradict it.", "Rohan Deshmukh", "rohan", ()),
        ("ev_stmt_meera_call", "Meera: 'Under a minute'",
         "'Adrian rang me around half past ten. Under a minute. He said he'd see me at eleven.'",
         "A description of the call. The phone's call log has its own opinion.", "Meera Kapadia", "meera", ()),
        ("ev_stmt_hari_ontime", "Hari: 'On time, as the register says'",
         "'Every departure is entered as it happens. The Kosi Passenger left at 10:15, on time, exactly as the "
         "register says.'", "A claim that the register is accurate.", "Hari Joshi", "hari", ()),
        ("ev_stmt_tanvi_tea", "Tanvi: 'Only at the tea stall'",
         "'I spoke to him at the tea stall around nine-fifteen. No comment. That was all. I never went near his "
         "carriage.'", "A claim that she never entered the saloon.", "Tanvi Sethi", "tanvi", ()),
        ("ev_stmt_kabir_post", "Kabir: 'In the room all night'",
         "'I was in the security room all night. Nothing happened on my watch.'",
         "A claim of continuous presence at his post.", "Kabir Rathore", "kabir", ()),
    )
)

_TESTIMONY: tuple[Evidence, ...] = tuple(
    Evidence(k, name, "testimony", text, detail, f"Interview: {who}", None, "testimony",
             related_people=(who_key,), is_testimony=True, icon="speech", events=evs, timestamps=ts,
             bears_on=bears)
    for (k, name, text, detail, who, who_key, evs, ts, bears) in (
        ("ev_t_gopal_train", "Gopal: the Kosi left very late",
         "Gopal says the Kosi Passenger sat on Platform 2 'until the big thunder' and left when the station clock "
         "showed about quarter to eleven, flagged off by Hari-babu himself.",
         "Gopal reads time off the station clock — so 'quarter to eleven' is station time (22:45 ST = 22:57 RT).",
         "Gopal Yadav", "gopal", ("e_train",), (T("Departure (his estimate)", "ST", "22:45"),), ()),
        ("ev_t_gopal_olive", "Gopal: stranger asked the way to Siding 4",
         "Gopal remembers a tall man in an olive raincoat and spectacles who asked the way to the Siding 4 gate at "
         "'about half past ten by the clock'.",
         "Half past ten by the station clock is about 22:42 RT — minutes after PT-0412 was sold. The stranger did "
         "not ask for the Kosi Passenger.", "Gopal Yadav", "gopal", ("e_directions",),
         (T("Directions asked", "ST", "22:30"),), ()),
        ("ev_t_gopal_clock", "Gopal: the clock is slow",
         "Gopal: 'The station clock is twelve minutes slow since Sunday, sahab. Everybody on this platform knows. "
         "My phone is the right one.'", "Confirms the clock offset independently of the maintenance tag.",
         "Gopal Yadav", "gopal", (), (), ()),
        ("ev_t_hari_clock", "Hari: the master clock lags by 12 minutes",
         "Hari admits the Platform 1 clock has lagged twelve minutes since Sunday's lightning, and that every "
         "station system follows it.", "Corroborates the maintenance tag.", "Hari Joshi", "hari", (), (), ()),
        ("ev_t_hari_admission", "Hari admits altering the register",
         "Hari admits the Kosi was held until 22:44 ST by a signal failure. Fearing an inquiry, he rewrote '22:45' "
         "as '22:15' and 'On time'. He says he changed nothing else.",
         "An admission that the departure was recorded wrongly — the register is no longer an alibi for anybody.",
         "Hari Joshi", "hari", ("e_train",), (T("Actual departure", "ST", "22:45"),),
         (B("hari", "undermines_claim", (), "Admitted tampering.", "claim"),)),
        ("ev_t_hari_bribe", "Hari admits the off-book payment",
         "Hari admits taking Rs 50,000 cash from Adrian's aide for the siding berth, off the books.",
         "A career-ending secret, unrelated to the murder.", "Hari Joshi", "hari", ("e_arrive",), (), ()),
        ("ev_t_kabir_admission", "Kabir admits leaving his post",
         "Kabir admits he went to the siding gate at 22:41 ST to check the dead camera and was out of the room "
         "about eight minutes in all.", "Confirms the gate log.", "Kabir Rathore", "kabir", ("e_voices",),
         (T("Gate", "ST", "22:41"),), ()),
        ("ev_t_kabir_cam", "Kabir admits CAM-7 was dead",
         "Kabir: CAM-7 has been dead since Tuesday after electricians cut the cable; he told no one to avoid "
         "contract penalties and kept the heartbeat server pinging.", "Explains the logbook and the perfect "
         "heartbeat.", "Kabir Rathore", "kabir", (), (), ()),
        ("ev_t_kabir_voices", "Kabir heard an argument in the saloon",
         "Kabir heard two men in the saloon: Adrian, and a younger voice shouting, 'Mera kaam hai woh — tumne chura "
         "liya!' ('That's my work — you stole it!'). He heard no blows and walked on.",
         "At about 22:53 RT Adrian was alive and arguing with a younger man about stolen work.", "Kabir Rathore",
         "kabir", ("e_voices",), (T("Voices heard", "ST", "22:41"),), ()),
        ("ev_t_tanvi_admission", "Tanvi admits she was inside the saloon",
         "Tanvi admits Adrian invited her in at 21:30 and she stayed until about 21:50, drinking tea; she left "
         "through the yard side.", "Confirms she lied about 'never going near the carriage' but was gone an hour "
         "before the death.", "Tanvi Sethi", "tanvi", (), (T("Left saloon", "RT", "21:52"),), ()),
        ("ev_t_tanvi_pendrive", "Tanvi received a pen drive from Adrian",
         "Tanvi says Adrian gave her a pen drive of documents on 'Kaveri Holdings' — he wanted them published if the "
         "board stalled.", "Explains Adrian's motive for calling in the press, and Meera's exposure.",
         "Tanvi Sethi", "tanvi", (), (), ()),
        ("ev_t_tanvi_sighting", "Tanvi saw a man in an olive raincoat at the siding gate",
         "From the waiting-room window at about 22:44 (her phone clock), Tanvi saw a tall man in an olive raincoat "
         "go through the Siding 4 gate. She saw no face.",
         "Her phone shows network time (RT). It matches the stranger Gopal described.", "Tanvi Sethi", "tanvi",
         ("e_directions",), (T("Sighting", "RT", "22:44"),), ()),
        ("ev_t_meera_admission", "Meera admits the call was an argument",
         "Meera admits the 22:36 call lasted over four minutes and became an argument. She says she stayed in the "
         "waiting room afterwards.", "Confirms the call log and her alibi.", "Meera Kapadia", "meera",
         ("e_call",), (), ()),
        ("ev_t_meera_kaveri", "Meera admits Kaveri Holdings is hers",
         "Meera admits she owns Kaveri Holdings and took Rs 11.2 crore; she says Adrian had given her until Monday.",
         "A confession of fraud, not of murder.", "Meera Kapadia", "meera", (), (), ()),
        ("ev_t_rohan_admission", "Rohan admits meeting Adrian",
         "Rohan admits the 04417 number is his, that he did not take the Kosi Passenger, and that he met Adrian in "
         "the saloon at about quarter to eleven. He claims Adrian was alive when he left.",
         "An admission placing him in the saloon at the critical hour — and a claim, not a proof.",
         "Rohan Deshmukh", "rohan", ("e_ticket",), (), (B("rohan", "points_to", (), "Admitted presence.", "presence"),)),
        ("ev_t_rohan_confession", "Rohan's confession",
         "Rohan says that after Adrian called the code his own and told him to sue, he picked up the paperweight. "
         "One blow. He locked the door with Adrian's key and dropped it in the drain.",
         "A confession, voluntarily given after being confronted with the evidence.", "Rohan Deshmukh", "rohan",
         ("e_death", "e_locked"), (), (B("rohan", "points_to", (), "Confession.", "presence"),)),
    )
)

EVIDENCE: tuple[Evidence, ...] = _PHYSICAL + _STATEMENTS + _TESTIMONY
