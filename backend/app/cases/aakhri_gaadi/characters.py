"""The six people of 'Aakhri Gaadi' — five suspects and one witness.

Every Fact separates what the character *really knows* (`text`, server-side only) from what they *say*
while the gate is closed (`public_line`, possibly false) and what they say once it opens (`reveal_line`).
"""

from __future__ import annotations

from ..base import Character, Fact, Gate, Portrait

# --------------------------------------------------------------------------------------------- ROHAN
ROHAN = Character(
    key="rohan", name="Rohan Deshmukh", role="Former CTO, Valecore Systems", age=41, is_suspect=True,
    personality="Soft-spoken, exact, wounded pride. Dry humour. Hates being called emotional. Over-explains when lying.",
    style="Measured full sentences; engineering metaphors ('edge case', 'race condition'); polite to the point of "
          "coldness; calls the player 'Inspector'. Occasional Hindi: 'dekhiye', 'theek hai'.",
    relationship_to_victim="Built Pathfinder with Adrian; dismissed in January. Claims the invention is his.",
    public_facts=(
        "Founding engineer and, until January, CTO of Valecore Systems.",
        "Lives in Lakadganj, 40 km away; a sister lives in Devgarh.",
        "Publicly disputes who invented Valecore's Pathfinder routing engine.",
    ),
    relationships={
        "adrian": "Former friend and boss; now says Adrian 'stole four years of my life'.",
        "meera": "Signed his termination. Thinks she let it happen.",
        "tanvi": "Spoke to her once off the record about Pathfinder.",
    },
    greeting="Inspector. I assume you want to hear that I was on a train. I was.",
    deflections=(
        "I'd rather not speculate about other people's evenings, Inspector.",
        "That's a question for the people who were there. I was gone by then.",
        "With respect, you are asking me to prove a negative.",
    ),
    unknown_lines=("I don't know anything about that.", "Not something I'd have any way of knowing."),
    evidence_reactions={
        "ev_button": "Half the men in Devgarh own an olive raincoat in September. That proves nothing.",
        "ev_gate_thread": "Thread on a gate. It's the monsoon, Inspector. Everything snags on everything.",
        "ev_paperweight": "I haven't seen that object in my life.",
        "ev_watch": "I'm sorry for his death. I don't see what a watch has to do with me.",
        "ev_key": "A key in a drain. I'd say that points at whoever put it there.",
        "ev_cctv_waiting": "Then those two ladies are lucky. Good for them.",
        "ev_dismissal": "Yes, I was fired. It is not a secret and not a motive; it is an employment record.",
    },
    portrait=Portrait("#c79a78", "#1d1a1a", "#4c5a3a", "#9cb36c", glasses=True, hair_style="short", age="mid"),
    base_trust=35, base_stress=14, defensiveness=1.3, sort=3,
    facts=(
        Fact(
            "rf_dismissal",
            "Rohan was dismissed in January with an invention-assignment clause he signed under pressure.",
            ("fired", "dismissed", "terminated", "valecore", "cto", "job", "quit", "let go", "severance", "restructuring", "company"),
            public_line="I was let go in January. 'Restructuring.' I signed what they put in front of me, which I regret. "
                        "I built half of that company and was shown the door with a month's severance.",
            volunteer=True,
        ),
        Fact(
            "rf_pathfinder",
            "Rohan wrote the core of Pathfinder; Adrian filed the patent solely in his own name; Rohan has notebooks.",
            ("pathfinder", "patent", "invention", "algorithm", "code", "stolen", "credit", "notebook", "ip", "northwind", "sale"),
            public_line="Pathfinder is my work. Four years of it. Adrian's name is on the patent, which I consider a "
                        "clerical error that a court will fix. I've spoken to a lawyer — that's the civilised route.",
            reveal_line="Pathfinder was mine, line by line. He filed it in his name three weeks after firing me, and "
                        "in two days he'd have sold it for four hundred crore. Do you know what that feels like?",
            gate=Gate(trust_bypass=60, evidence_any=("ev_patent", "ev_dismissal", "ev_sale_agreement", "ev_t_kabir_voices")),
        ),
        Fact(
            "rf_visit",
            "Rohan came to Devgarh intending to confront Adrian before the Northwind signing.",
            ("why", "here", "devgarh", "visit", "station", "sister", "sunita", "purpose", "came", "weekend"),
            public_line="My sister Sunita lives near the old bazaar. I came to see her for the weekend, and I was at the "
                        "station only to take the Kosi Passenger home to Lakadganj.",
            public_truthful=False,
            leak_markers=("to confront", "to meet adrian"),
        ),
        Fact(
            "rf_alibi",
            "Rohan did NOT take the Kosi Passenger. He bought a platform ticket at 22:25 ST, asked Gopal the way to "
            "Siding 4, and was in the saloon at 22:45 RT.",
            ("where", "when", "train", "kosi", "passenger", "alibi", "time", "left", "leave", "depart", "10:15", "clock", "aboard", "ticket"),
            public_line="I took the 10:15 Kosi Passenger. By the platform clock I was aboard before half past ten and "
                        "away not long after. I never went anywhere near the siding.",
            public_truthful=False,
            grants_statement="ev_stmt_rohan_alibi",
            reveal_line="...All right. I did not take that train. I bought a platform ticket because I needed to get "
                        "past the barrier. I'd been asked to come to the saloon. I should have said so at the start.",
            gate=Gate(evidence_any=("ev_ticket_stub", "ev_ticket_log", "ev_button", "ev_gate_thread", "ev_t_gopal_olive", "ev_t_tanvi_sighting")),
            leak_markers=("platform ticket", "saloon at"),
        ),
        Fact(
            "rf_contact",
            "Rohan texted Adrian from a burner SIM registered to his sister Sunita.",
            ("contact", "phone", "message", "text", "sms", "call", "number", "spoke", "talk", "burner", "sim", "04417", "mobile", "touch", "recently", "messages", "texts"),
            public_line="I haven't had any contact with Adrian since January. Only lawyers, and only in writing.",
            public_truthful=False,
            grants_statement="ev_stmt_rohan_nocontact",
            reveal_line="That number is mine — a prepaid SIM in Sunita's name; I didn't want my own phone anywhere near "
                        "him. I told him I would go to the press. He texted back: Siding 4, a quarter to eleven.",
            gate=Gate(evidence_any=("ev_sms_thread", "ev_sim_record")),
            leak_markers=("burner", "prepaid"),
        ),
        Fact(
            "rf_met",
            "Rohan met Adrian in the saloon around 22:46 RT and left after the killing.",
            ("met", "meet", "saloon", "carriage", "siding", "inside", "argued", "argument", "visited", "adrian", "alive", "last"),
            public_line="I did not meet Adrian tonight. I did not see him.",
            public_truthful=False,
            reveal_line="I met him in the saloon at about a quarter to eleven. We argued — about the patent, about the "
                        "sale. When I walked out he was alive and shouting at his phone. That's the truth.",
            gate=Gate(requires_revealed=("rf_alibi",), evidence_any=("ev_ticket_stub", "ev_ticket_log", "ev_sms_thread", "ev_sim_record", "ev_button", "ev_gate_thread", "ev_t_gopal_olive", "ev_t_tanvi_sighting", "ev_t_kabir_voices")),
            grants_evidence="ev_t_rohan_admission",
            leak_markers=("in the saloon",),
        ),
        Fact(
            "rf_threat",
            "Rohan emailed Adrian in March threatening to go to the press.",
            ("email", "threat", "threatened", "regret", "press", "angry", "march", "journalist"),
            public_line="Angry emails? Yes, I'm human. Everyone says things in March. I never threatened to hurt anyone.",
        ),
        Fact(
            "rf_confession",
            "Rohan struck Adrian once with the brass paperweight, locked the door with Adrian's key, and dropped the "
            "key in the storm drain.",
            ("killed", "kill", "murder", "murdered", "paperweight", "drain", "struck", "blow", "confess", "confession", "lock", "locked", "hit him", "killer"),
            public_line="You are accusing me of murder on the strength of circumstance, Inspector. I will have my lawyer here by morning.",
            public_truthful=False,
            reveal_line="He said the code was his. He said I'd signed it away and could sue, 'if you can afford it.' "
                        "The paperweight was just there. One blow — I never meant... He went down and didn't move. "
                        "I took his key and locked the door, I don't know why; I wanted time. I dropped it by the gate. "
                        "I've been waiting for you to come ever since.",
            gate=Gate(stress_min=45, need_count=3, requires_revealed=("rf_met",),
                      evidence_any=("ev_watch", "ev_key", "ev_button", "ev_gate_thread", "ev_sms_thread", "ev_sim_record",
                                    "ev_paperweight", "ev_patent", "ev_threat_email", "ev_t_kabir_voices", "ev_ticket_log")),
            grants_evidence="ev_t_rohan_confession",
            secret=True,
            leak_markers=("paperweight", "storm drain", "one blow", "i hit him", "i killed"),
        ),
    ),
)

# --------------------------------------------------------------------------------------------- MEERA
MEERA = Character(
    key="meera", name="Meera Kapadia", role="Co-founder & CFO, Valecore Systems", age=44, is_suspect=True,
    personality="Controlled, intelligent, impatient with sloppiness. Fear shows as precision. Protects her reputation first.",
    style="Crisp, clipped, formal. Finance vocabulary ('exposure', 'reconcile', 'materiality'). Corrects the player's "
          "wording. Never raises her voice; goes colder instead.",
    relationship_to_victim="Co-founder and oldest business partner; due ~22% of the sale proceeds.",
    public_facts=(
        "Co-founder and CFO of Valecore; Adrian's partner for 14 years.",
        "Stands to receive roughly a fifth of the Northwind proceeds.",
        "Waited in the first-class waiting room for Adrian to join her.",
    ),
    relationships={
        "adrian": "Fourteen years; recent months strained over 'governance'.",
        "rohan": "Let him go in January on Adrian's instruction. Remembers his email.",
        "tanvi": "Treats her as a hazard.",
        "kabir": "Valecore's security vendor; she approved his invoices.",
    },
    greeting="Inspector. Let's be precise, shall we? Ask your questions.",
    deflections=(
        "That is speculation, Inspector. I deal in reconciled facts.",
        "I'd prefer not to characterise colleagues. Ask me something I can document.",
        "I don't see the materiality of that question.",
    ),
    unknown_lines=("I wasn't there. I can't say.", "I have no information on that."),
    evidence_reactions={
        "ev_cctv_waiting": "As I said — the camera will confirm it. I'd appreciate that being on the record.",
        "ev_sale_agreement": "Yes. The Northwind agreement. All three of us would have been rich by Tuesday.",
        "ev_watch": "Twenty to eleven... no. Whatever time that says, I was in the waiting room.",
        "ev_ticket_log": "I don't know that name. Is it relevant to me?",
    },
    portrait=Portrait("#d2a384", "#26201e", "#5a2d3b", "#c9a45a", hair_style="bun", age="mid"),
    base_trust=30, base_stress=16, defensiveness=1.0, sort=1,
    facts=(
        Fact(
            "mk_purpose",
            "Adrian called Meera at 20:02 to come to the station; they were to review closing papers.",
            ("why", "here", "station", "came", "purpose", "waiting", "adrian", "meeting", "review"),
            public_line="Adrian asked me to be at the station by ten to review the closing papers. He liked drama in his "
                        "venues. I waited in the first-class waiting room, as the camera will show.",
            volunteer=True,
        ),
        Fact(
            "mk_call",
            "The 22:36 call lasted 4m12s and was an argument about the Kaveri Holdings transfers.",
            ("call", "phone", "rang", "spoke", "talk", "conversation", "last", "contact", "heard", "22:36", "minute"),
            public_line="He rang me around half past ten. Under a minute. He said he would see me at eleven and hung up.",
            public_truthful=False,
            grants_statement="ev_stmt_meera_call",
            reveal_line="Four minutes. It became an argument; he had the auditors' file in front of him. I walked out of "
                        "the call, not out of the station. And since you will ask: he was very much alive when it ended.",
            gate=Gate(evidence_any=("ev_call_log",)),
            grants_evidence="ev_t_meera_admission",
            leak_markers=("argument", "auditors"),
        ),
        Fact(
            "mk_kaveri",
            "Meera siphoned Rs 11.2 crore into Kaveri Holdings, which she owns.",
            ("money", "funds", "kaveri", "audit", "books", "accounts", "transfer", "embezzle", "financial", "ledger", "finance", "company"),
            public_line="Valecore's books are in order. We are about to undergo Northwind's due diligence — they would be "
                        "very much more interested than you in anything irregular.",
            public_truthful=False,
            reveal_line="Kaveri Holdings is mine. Rs 11.2 crore over two years — a loan to myself, I called it. Adrian "
                        "found it and gave me until Monday to restore it. It is theft; I won't dress it up. But I did not "
                        "kill him. I could not have — I was in that room with half the station watching.",
            gate=Gate(evidence_any=("ev_ledger_kaveri", "ev_bank_slip", "ev_t_tanvi_pendrive")),
            grants_evidence="ev_t_meera_kaveri",
            secret=True,
            leak_markers=("kaveri holdings is mine", "11.2", "siphon"),
        ),
        Fact(
            "mk_rohan",
            "Meera knows Rohan emailed Adrian in March ('you'll regret this') and has a sister in Devgarh.",
            ("rohan", "deshmukh", "engineer", "former", "enemies", "grudge", "threat", "who", "suspect", "anyone", "pathfinder"),
            public_line="Rohan Deshmukh. Our former CTO. He emailed Adrian in March — 'you'll regret this' — over Pathfinder. "
                        "He has a sister in Devgarh. I'd talk to him, Inspector, if I were you. Not that I'm steering you.",
            gate=Gate(trust_min=25),
        ),
        Fact(
            "mk_camera",
            "Adrian told Meera the siding security was sloppy and the camera there did not record.",
            ("camera", "security", "cctv", "kabir", "siding", "guard", "rathore", "recording"),
            public_line="Adrian complained last week that the camera covering the siding wasn't recording. He told Mr Rathore. "
                        "I approved Mr Rathore's invoices; I did not audit his cameras.",
            kind="hearsay",
        ),
        Fact(
            "mk_tanvi",
            "Meera saw Tanvi in the waiting room and suspects she was there for Adrian.",
            ("tanvi", "sethi", "journalist", "reporter", "press", "newspaper", "dispatch"),
            public_line="Miss Sethi has been circling Valecore for weeks. She sat opposite me for an hour and said nothing; "
                        "I assumed she was waiting for him.",
        ),
        Fact(
            "mk_where",
            "Meera sat in the waiting room except for a short phone call outside at about 23:08 RT.",
            ("where", "waiting", "alibi", "room", "stayed", "left", "leave", "stepped", "outside"),
            public_line="In the waiting room, the entire time. I stepped out once to try Adrian's phone when he did not "
                        "come. Perhaps four minutes. The camera will confirm it.",
        ),
    ),
)

# --------------------------------------------------------------------------------------------- HARI
HARI = Character(
    key="hari", name="Hariprasad Joshi", role="Stationmaster, Devgarh Junction", age=58, is_suspect=True,
    personality="Dutiful, proud of the station's history, terrified of inquiries. Bureaucratic evasions, then a rush of "
                "humiliated honesty.",
    style="Formal, courteous, rule-bound: 'as per rules', 'Sir/Madam', 'arrey'. Cites regulation numbers. Speech gets "
          "halting when cornered.",
    relationship_to_victim="Took a cash payment from Adrian's aide to stable the saloon off the books.",
    public_facts=(
        "Stationmaster of Devgarh Junction for eleven years; thirty-one years in the Railways.",
        "Keeper of the Station Working Register and the key cabinet.",
        "On Platform 2 when the Kosi Passenger left.",
    ),
    relationships={
        "adrian": "A VIP guest; he 'did not wish to offend'.",
        "kabir": "Thinks the contractor's men sleep on duty.",
        "gopal": "Has known him thirty years; they trade gossip.",
    },
    greeting="Good evening, sir. Everything is as per rules, I assure you. How may I assist?",
    deflections=(
        "As per rules, that would be a matter for the Divisional Office, sir.",
        "I would not like to say without the file in front of me.",
        "Arrey, sir, I am only a stationmaster. Ask me about trains.",
    ),
    unknown_lines=("I did not see this, sir.", "That is not in my knowledge."),
    evidence_reactions={
        "ev_key_register": "Yes, yes. The spare key. Signed out, signed back. I am very particular.",
        "ev_cctv_platform": "That is me. I was flagging off the Kosi Passenger, sir. It is my duty.",
        "ev_ticket_log": "The platform ticket journal. It is a machine. It prints, I file.",
    },
    portrait=Portrait("#b78763", "#8a8a85", "#37424f", "#b08d57", glasses=True, beard=False, hair_style="cap", age="old"),
    base_trust=45, base_stress=20, defensiveness=1.2, sort=2,
    facts=(
        Fact(
            "hj_clock",
            "The Platform 1 master clock has run 12 minutes slow since Sunday's lightning; all station systems follow it.",
            ("clock", "time", "slow", "late", "wrong", "twelve", "sync", "offset", "register", "dvr", "cctv"),
            public_line="Since Sunday's lightning the master clock lags, sir. Twelve minutes. Everything on the station network "
                        "follows it — the register, the signal sheets, the cameras — until the electrician comes. "
                        "I have raised a complaint.",
            grants_evidence="ev_t_hari_clock",
        ),
        Fact(
            "hj_spare_key",
            "Hari signed out the spare saloon key at 20:40 and returned it at 21:05.",
            ("key", "spare", "cabinet", "saloon", "lock", "locked", "open", "opened", "unlock"),
            public_line="The spare key to SC-4471 is in my cabinet. I walked Mr Vale's aide to the saloon at 20:40, signed "
                        "the key out, and returned it by 21:05. The register will tell you. Tonight I opened the door with it.",
        ),
        Fact(
            "hj_register",
            "Hari altered the Kosi Passenger entry from 22:45 to 22:15 'On time' to avoid a delay inquiry.",
            ("register", "kosi", "passenger", "departure", "depart", "time", "late", "delay", "on time", "entry", "altered", "22:15", "overwrite", "signal"),
            public_line="Every departure is entered as it happens, sir. The Kosi Passenger left at 10:15, on time, exactly as "
                        "the register says. I take pride in my register.",
            public_truthful=False,
            grants_statement="ev_stmt_hari_ontime",
            reveal_line="...Signal 4B failed at twenty past ten, sir. The Kosi was held until 22:44 — I flagged her away at "
                        "22:45. A delay of that kind is an incident report, a Divisional inquiry, my pension. I altered "
                        "the entry. Fifteen for forty-five. 'On time.' I swear I changed nothing else, sir.",
            gate=Gate(evidence_any=("ev_signal_memo", "ev_cctv_platform", "ev_t_gopal_train", "ev_register")),
            grants_evidence="ev_t_hari_admission",
            leak_markers=("altered the entry", "inquiry"),
        ),
        Fact(
            "hj_receipt",
            "Hari took Rs 50,000 cash from Adrian's aide to stable the saloon; unofficial.",
            ("saloon", "siding", "permit", "permission", "payment", "paid", "money", "cash", "fee", "bribe", "aide", "berth", "stabled", "parked"),
            public_line="The saloon was stabled on Siding 4 as per Railway Board permission. All papers are in order, sir.",
            public_truthful=False,
            reveal_line="...Rs 50,000, sir, from Mr Vale's aide. Siding rent, he said. There is no such rule. I will lose my "
                        "pension, I know. But I never touched Mr Vale — I was on Platform 2 with a delayed train.",
            gate=Gate(evidence_any=("ev_siding_receipt",)),
            grants_evidence="ev_t_hari_bribe",
            secret=True,
            leak_markers=("50,000", "rs 50", "fifty thousand"),
        ),
        Fact(
            "hj_flag",
            "Hari flagged off the Kosi Passenger himself on Platform 2 at about 22:45 ST.",
            ("flag", "platform", "kosi", "where", "alibi", "doing", "dispatch", "guard", "whistle", "thunder"),
            public_line="I was on Platform 2 to flag off the Kosi Passenger myself, sir. Signal fault, thunder — a very "
                        "difficult evening. The guard will confirm.",
        ),
        Fact(
            "hj_office",
            "Hari left his office unlocked from about 22:20 ST while attending the signal fault.",
            ("office", "unlocked", "door", "access", "anyone", "entered", "keys", "who"),
            public_line="My office is not locked when I am on duty, sir. It is a railway office. Tonight I was at the signal "
                        "cabin and on the platform for half an hour.",
        ),
        Fact(
            "hj_kabir",
            "Hari believes Kabir's guards neglect duty.",
            ("kabir", "security", "guard", "rathore", "camera", "cctv"),
            public_line="Mr Rathore's men? Well, sir, I would not say... the cameras on the yard side have been a nuisance for "
                        "months. I have written to the Divisional Office twice.",
            kind="belief",
        ),
    ),
)

# --------------------------------------------------------------------------------------------- TANVI
TANVI = Character(
    key="tanvi", name="Tanvi Sethi", role="Investigative reporter, Devgarh Dispatch", age=29, is_suspect=True,
    personality="Sharp, funny, restless; hides fear with sarcasm; fiercely protective of sources.",
    style="Quick, ironic Hinglish: 'arre', 'yaar', 'Inspector sahab'. Deflects with questions. Gets quiet and exact when "
          "it matters.",
    relationship_to_victim="Wrote about Valecore's sale; Adrian secretly became her source tonight.",
    public_facts=(
        "Investigative reporter at the Devgarh Dispatch, writing on Valecore's Northwind sale.",
        "Sat in the first-class waiting room for much of the evening.",
    ),
    relationships={
        "adrian": "Had been refused interviews for weeks; he called her over tonight.",
        "meera": "Treats her as the story's villain.",
        "rohan": "Spoke to him once; he would not go on record.",
    },
    greeting="Arre, Inspector sahab! Is this on or off the record? Never mind — it's always on.",
    deflections=(
        "Source protection, Inspector. Ask me something I can answer without ending my career.",
        "Yaar, that's not a question, that's a trap.",
        "I report what I can print. That bit I can't.",
    ),
    unknown_lines=("No idea, honestly.", "I wasn't there for that bit."),
    evidence_reactions={
        "ev_tea_cups": "Okay — those are from Gopal's stall. Fine. Fine.",
        "ev_newspaper": "That's my byline. Congratulations, you can read.",
        "ev_cctv_waiting": "Great, I'm famous. Look at that bench!",
    },
    portrait=Portrait("#c28e6e", "#1b1517", "#8a3b2d", "#e0b05a", hair_style="long", age="young"),
    base_trust=40, base_stress=12, defensiveness=0.8, sort=4,
    facts=(
        Fact(
            "ts_why",
            "Tanvi came for a quote and ended up meeting Adrian privately.",
            ("why", "here", "story", "valecore", "sale", "northwind", "interview", "quote", "reporter", "came"),
            public_line="Chasing a quote. Valecore's sale is the biggest story in this city in a decade. Adrian had refused to "
                        "talk to me for weeks, so I doorstepped him at the station.",
            volunteer=True,
        ),
        Fact(
            "ts_contact",
            "Tanvi was inside the saloon from about 21:30 to 21:52 RT; Adrian gave her a pen drive.",
            ("adrian", "spoke", "talk", "saw", "met", "carriage", "saloon", "inside", "contact", "tea", "stall", "last", "9:15", "interview"),
            public_line="I spoke to him at the tea stall around nine-fifteen. 'No comment.' That was all. I never went near "
                        "his carriage — I'm a reporter, not a burglar.",
            public_truthful=False,
            grants_statement="ev_stmt_tanvi_tea",
            reveal_line="Okay. Okay! He waved me over after nine-thirty and I sat in that armchair for twenty minutes. Tea. "
                        "He'd changed his mind about talking. I was out of there by about ten to ten — via the yard side, "
                        "because the stationmaster's lot watch the front. I didn't see why I should say so.",
            gate=Gate(trust_bypass=75, evidence_any=("ev_tea_cups", "ev_upi_ledger")),
            grants_evidence="ev_t_tanvi_admission",
            leak_markers=("armchair", "pen drive", "pendrive"),
        ),
        Fact(
            "ts_pendrive",
            "Adrian gave Tanvi a pen drive of documents about Kaveri Holdings.",
            ("pendrive", "pen drive", "documents", "papers", "gave", "usb", "kaveri", "files", "leak", "source"),
            public_line="Sources are sources, Inspector. I protect them even from you.",
            reveal_line="Fine. A pen drive. Documents on a company called Kaveri Holdings and who owns it. He wanted me to "
                        "publish if the board stalled. I haven't opened half of it, and I won't pretend it didn't look "
                        "like a man protecting himself.",
            gate=Gate(trust_min=45, requires_revealed=("ts_contact",)),
            grants_evidence="ev_t_tanvi_pendrive",
            secret=True,
            leak_markers=("kaveri",),
        ),
        Fact(
            "ts_sighting",
            "At about 22:44 RT (phone clock) Tanvi saw a tall man in an olive raincoat go through the Siding 4 gate from the waiting-room window; no face.",
            ("saw", "see", "seen", "window", "gate", "siding", "man", "someone", "anyone", "suspicious", "raincoat", "coat", "olive", "noticed", "who", "wearing"),
            public_line="I was watching the yard from the waiting-room window, I'll admit. Can't tell you much — rain, dark, "
                        "everyone's a shape.",
            reveal_line="Around 10:44 on my phone, a tall man in an olive raincoat went through the Siding 4 gate. Alone. "
                        "I never saw a face. I only remember because I texted my editor 'he's gone quiet' a minute later.",
            gate=Gate(trust_min=45),
            grants_evidence="ev_t_tanvi_sighting",
            kind="firsthand",
            leak_markers=("olive raincoat",),
        ),
        Fact(
            "ts_waiting",
            "Tanvi sat in the waiting room opposite Meera, leaving only briefly.",
            ("where", "waiting", "alibi", "room", "meera", "bench", "stayed", "washroom"),
            public_line="Waiting room, opposite Madam Kapadia — we sat like two cats. I went to the washroom once, three minutes. "
                        "Camera will have it.",
        ),
        Fact(
            "ts_rohan",
            "Tanvi interviewed Rohan once off the record; he hinted Pathfinder was his.",
            ("rohan", "deshmukh", "engineer", "pathfinder", "former", "cto", "source", "disputes"),
            public_line="A former engineer told me off the record that Pathfinder wasn't Adrian's. I won't say who. "
                        "But anyone who reads page three can work it out.",
            kind="hearsay",
        ),
    ),
)

# --------------------------------------------------------------------------------------------- KABIR
KABIR = Character(
    key="kabir", name="Kabir Rathore", role="Owner, Rathore Securitas (station security contractor)", age=36, is_suspect=True,
    personality="Ex-army, proud, defensive about his firm's reputation; takes shortcuts and hates being caught at them.",
    style="Short sentences, barked. 'Dekhiye sir', 'Sir, with respect'. Sweats and gets formal when confronted; "
          "becomes surprisingly candid once he stops lying.",
    relationship_to_victim="Valecore's security vendor for the event; had the Siding 4 camera under contract.",
    public_facts=(
        "Runs Rathore Securitas, the station's contracted security firm.",
        "Controls the security room and the yard access system.",
    ),
    relationships={
        "meera": "She signs his invoices and once asked which cameras covered the siding.",
        "hari": "Thinks Hari fusses over paperwork and forgets the yard.",
        "gopal": "Buys his chai every night.",
    },
    greeting="Sir. Rathore. I've got the logs, the footage, the lot. Ask.",
    deflections=(
        "Dekhiye sir, that's not my department.",
        "Sir, with respect, I run a security room, not a detective agency.",
        "I'd have to check the register on that.",
    ),
    unknown_lines=("Didn't see it, sir.", "Not on my watch, sir."),
    evidence_reactions={
        "ev_cctv_waiting": "That's WR-1. Works fine. Always has.",
        "ev_upi_ledger": "Yes, that's me. Chai. I'm allowed chai.",
    },
    portrait=Portrait("#a97c5a", "#111111", "#2c3441", "#7d8a99", beard=True, hair_style="short", age="mid"),
    base_trust=35, base_stress=18, defensiveness=1.4, sort=5,
    facts=(
        Fact(
            "kr_post",
            "Kabir left the security room at about 22:41 ST (22:53 RT) and visited the siding gate for about three minutes.",
            ("where", "room", "post", "monitor", "watch", "security", "all night", "leave", "left", "gate", "siding", "alibi", "doing"),
            public_line="I was in the security room all night, sir. Screens, logbook, thermos. Nothing happened on my watch.",
            public_truthful=False,
            grants_statement="ev_stmt_kabir_post",
            reveal_line="...Fine. I badged out to the siding gate at 22:41 by the clock. A rumour of an inspector from the "
                        "Divisional Office — I wanted to see CAM-7 myself. I was gone three minutes. Then I went for chai.",
            gate=Gate(evidence_any=("ev_access_log",)),
            grants_evidence="ev_t_kabir_admission",
            leak_markers=("badged out", "left the room"),
        ),
        Fact(
            "kr_camera",
            "CAM-7 has been dead since Tuesday; Kabir signed the log anyway and kept the heartbeat ping.",
            ("camera", "cameras", "cam-7", "cam7", "cctv", "recording", "footage", "maintenance log", "logbook", "operational", "heartbeat"),
            public_line="All cameras are operational, sir. The maintenance log is signed daily. CAM-7 covers the siding gate.",
            public_truthful=False,
            reveal_line="CAM-7 has been dead since Tuesday. Electricians cut the cable. I didn't report it — contract penalty "
                        "clause — and I signed the log and left the heartbeat server pinging. Stupid. I know.",
            gate=Gate(evidence_any=("ev_cam7_cable", "ev_maint_log", "ev_access_log"), need_count=2),
            grants_evidence="ev_t_kabir_cam",
            secret=True,
            leak_markers=("cable was cut", "dead since", "signed the log"),
        ),
        Fact(
            "kr_voices",
            "At about 22:53 RT Kabir heard Adrian arguing with a younger man: 'Mera kaam hai woh — tumne chura liya.'",
            ("heard", "hear", "voice", "voices", "shout", "shouting", "argument", "argue", "saloon", "carriage", "noise", "anything", "siding", "gate"),
            public_line="Nothing, sir. It was raining. I heard rain.",
            public_truthful=False,
            reveal_line="Voices. From the saloon, as I passed. Mr Vale — and a younger man. The younger one was shouting: "
                        "'Mera kaam hai woh — tumne chura liya!' It's my work, you stole it. I didn't recognise him. I "
                        "thought: rich men's quarrel, none of mine. I walked on. Four minutes later he was dead and I was "
                        "drinking tea.",
            gate=Gate(trust_min=30, requires_revealed=("kr_post",)),
            grants_evidence="ev_t_kabir_voices",
            leak_markers=("chura liya", "you stole it"),
        ),
        Fact(
            "kr_tea",
            "Kabir paid Gopal for chai by UPI at 22:58:05 RT.",
            ("tea", "chai", "gopal", "stall", "paid", "payment", "upi", "22:58"),
            public_line="After the gate I went for chai at Gopal's. Paid on the phone. Ask Gopal.",
        ),
        Fact(
            "kr_meera",
            "Meera asked Kabir the day before which cameras covered the siding.",
            ("meera", "kapadia", "madam", "cameras", "asked", "siding", "recording"),
            public_line="Madam Kapadia asked me, the day before, which cameras cover the siding. I told her honestly: CAM-7... "
                        "and I told her it was fine. Don't read anything into that, sir.",
            gate=Gate(trust_min=45),
            kind="hearsay",
        ),
    ),
)

# --------------------------------------------------------------------------------------------- GOPAL
GOPAL = Character(
    key="gopal", name="Gopal Yadav", role="Tea-stall owner, Platform 3 (witness)", age=52, is_suspect=False,
    personality="Warm, talkative, observant, honest; remembers events not clocks; afraid of getting anyone in trouble.",
    style="Folksy Hinglish, rambling, 'sahab', 'madam', 'arrey baba'. Times things by trains and thunder, and reads "
          "the platform clock.",
    relationship_to_victim="Sold Adrian's visitors tea; barely spoke to him.",
    public_facts=(
        "Has run the Platform 3 chai stall for twenty-two years.",
        "Sees nearly everyone who crosses the station after dark.",
    ),
    relationships={
        "hari": "Old friend; calls him Hari-babu.",
        "kabir": "A nightly customer.",
        "tanvi": "Sold her two teas around 21:24.",
    },
    greeting="Arrey, sahab, chai? Sit, sit. Rain's been terrible, no?",
    deflections=(
        "Arrey baba, I only sell chai, sahab.",
        "I don't remember that, sahab — so many people tonight.",
    ),
    unknown_lines=("Didn't see, sahab.", "Don't know, sahab, God's honest."),
    evidence_reactions={
        "ev_tea_cups": "Those are mine, sahab — see the stamp, GOPAL CHAI. I only stamp my own kulhads.",
        "ev_clock_slow": "Everyone knows the clock is slow, sahab!",
        "ev_ticket_stub": "Platform ticket? Half the world buys one to see off relatives.",
    },
    portrait=Portrait("#a37452", "#555555", "#8c6b3f", "#cf8a3a", beard=True, hair_style="cap", age="old"),
    base_trust=60, base_stress=6, defensiveness=0.5, sort=6,
    facts=(
        Fact(
            "gy_train",
            "The Kosi Passenger left very late — about 22:45 by the station clock — after a signal failure and thunder.",
            ("kosi", "train", "passenger", "late", "delay", "left", "depart", "platform 2", "flag", "hari", "thunder", "what time", "time", "when"),
            public_line="The Kosi Passenger? Very late, sahab! She sat there with her signal red until after the big thunder. "
                        "Hari-babu flagged her away himself — the station clock said quarter to eleven, near enough.",
            grants_evidence="ev_t_gopal_train",
            volunteer=True,
        ),
        Fact(
            "gy_clock",
            "Gopal knows the station clock is 12 minutes slow; his phone is right.",
            ("clock", "time", "slow", "phone", "watch", "wrong", "twelve"),
            public_line="The station clock is twelve minutes slow since Sunday, sahab. Everybody here knows. My phone is "
                        "the right one — but I still look up at the clock, old habit.",
            grants_evidence="ev_t_gopal_clock",
        ),
        Fact(
            "gy_olive",
            "Gopal saw a tall man in an olive raincoat and spectacles ask the way to the Siding 4 gate at about 22:30 ST.",
            ("man", "stranger", "tall", "raincoat", "coat", "olive", "spectacles", "asked", "directions", "way", "siding", "gate", "who", "saw", "strange", "anyone", "suspicious", "new"),
            public_line="Tall man, spectacles, olive raincoat. Asked me the way to the Siding 4 gate. Half past ten by the clock, "
                        "perhaps. I pointed. He didn't buy chai, sahab — and I remember because he looked like a man "
                        "who needed one.",
            grants_evidence="ev_t_gopal_olive",
            gate=Gate(trust_min=30),
        ),
        Fact(
            "gy_cups",
            "A young woman bought two teas at 21:24 RT and took them toward the siding.",
            ("cups", "kulhad", "clay", "tea", "woman", "madam", "two", "bought", "stamp", "tanvi", "siding"),
            public_line="My kulhads? A young madam bought two at nine twenty-four by my phone, took them toward the yard side. "
                        "Pretty, with a notebook. I don't know her name, sahab.",
            gate=Gate(evidence_any=("ev_tea_cups", "ev_upi_ledger")),
        ),
        Fact(
            "gy_kabir",
            "Kabir came for tea shortly before 23:00 RT and paid on his phone — unusual.",
            ("kabir", "guard", "security", "rathore", "chai", "paid", "upi", "tea"),
            public_line="Kabir-sahab came for chai a little before eleven by my phone. He never pays on the phone — always cash. "
                        "That night he paid on the phone, quick quick.",
        ),
    ),
)

# Order is deliberately NOT chronological-by-guilt: it matches the dossier display order (see Character.sort).
CHARACTERS: tuple[Character, ...] = (MEERA, HARI, ROHAN, TANVI, KABIR, GOPAL)
