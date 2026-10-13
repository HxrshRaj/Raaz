"""Datasets for the ML components.

* `make_clue_dataset` — SYNTHETIC clue descriptions generated from hand-written templates (6 categories). It exists so a
  classifier can be trained reproducibly offline; it is NOT real investigative data and in-distribution scores on it are
  optimistic. Splits are made **by template group**, so no template (and no near-duplicate sentence frame) appears in more
  than one split.
* `real_clue_eval_set` — the case's own authored evidence descriptions with their authored categories. Small (≈48) and
  out-of-distribution relative to the templates: the honest generalisation check.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass

from ..cases.registry import get_case

DATASET_VERSION = "clues-v1"
CATEGORIES = ("timeline", "financial", "access", "testimony", "physical", "digital")

_PEOPLE = ["the stationmaster", "the security contractor", "a former employee", "the journalist", "the business partner",
           "a porter", "the tea vendor", "the night clerk", "a guard", "the caretaker", "the driver", "an auditor"]
_TIMES = ["22:10", "22:45", "23:05", "21:30", "22:58", "23:20", "20:55", "22:31", "21:47", "23:40"]
_PLACES = ["platform 2", "the siding gate", "the waiting room", "the security room", "the ticket office", "the goods shed",
           "the yard office", "the tea stall", "the footbridge", "the signal cabin"]
_AMOUNTS = ["Rs 50,000", "Rs 3.1 crore", "Rs 11 lakh", "Rs 2,400", "Rs 75 lakh", "Rs 18 crore", "Rs 9,500"]
_OBJECTS = ["a brass key", "a torn button", "a coil of thread", "muddy boot prints", "a cracked mug", "a wet raincoat",
            "a heavy paperweight", "a cigarette end", "a lipstick-stained cup", "a bent latch", "a smear of grease"]
_DEVICES = ["a mobile phone", "the DVR", "a laptop", "a smartwatch", "the access controller", "a tablet", "the CCTV server"]

TEMPLATES: dict[str, list[str]] = {
    "timeline": [
        "The register records the train departing at {t} but another note puts it at {t2}.",
        "A clock in {p} shows {t} while the wristwatch says {t2}, a gap of twelve minutes.",
        "According to the schedule the service was due at {t}; it actually left after {t2}.",
        "Sequence of events places the argument at {t} and the discovery at {t2}.",
        "The time on the sheet was written over; the earlier figure reads {t}.",
        "Arrival noted at {t}, departure noted at {t2}, with no entry in between.",
        "The duty roster shows a shift change at {t}, forty minutes before the incident.",
        "Elapsed time between the call and the alarm was roughly {t} to {t2}.",
        "The delayed train held at {p} until {t2}, long past its scheduled {t}.",
        "A time discrepancy exists between the station clock and network time at {t}.",
        "Timeline entry: left {p} at {t}, reached the yard at {t2}.",
        "The memo is dated {t} but refers to events that happened at {t2}.",
        "Chronology: the lights went out at {t}, the bell rang at {t2}.",
        "The timetable board lists {t}; the signal log lists {t2} for the same movement.",
    ],
    "financial": [
        "A payment of {a} was moved to an account controlled by {pp}.",
        "The receipt shows {a} paid in cash with no matching ledger entry.",
        "An audit extract lists transfers totalling {a} over two years.",
        "The invoice from {pp} for {a} was approved without a purchase order.",
        "Bank slip: {a} credited to a holding company on {t}.",
        "The sale price of {a} depends on clean ownership of the technology.",
        "A loan of {a} was never repaid and the interest has been waived.",
        "The ledger carries an unexplained withdrawal of {a}.",
        "Cash book entry: {a} received for stabling the coach, not entered in the official register.",
        "Share agreement values the firm at {a} and names a sole inventor.",
        "The contractor claims {a} in unpaid fees under the security agreement.",
        "Payroll shows {a} paid as severance after the dismissal.",
        "An RTGS acknowledgement for {a} is torn in half.",
        "Accounts show {a} diverted from operations into a shell company.",
    ],
    "access": [
        "The badge reader logged {pp} entering {p} at {t} with no exit recorded.",
        "Gate sensor shows the door opened at {t} and closed at {t2}.",
        "The key register shows the spare key signed out at {t} and returned at {t2}.",
        "Access controller export: card 0471 used at {p} at {t}.",
        "The lock can only be thrown from outside with the carriage key.",
        "Entry through {p} requires a swipe, yet none is recorded at {t}.",
        "The camera heartbeat arrives every 60.000 seconds with no variation at all.",
        "Maintenance log says the camera was checked but its cable is unplugged.",
        "The cabinet of keys was unlocked and nobody signed for the hook at {t}.",
        "Visitor pass issued at {t} for {p}, never surrendered at exit.",
        "The turnstile counted one more entry than exit between {t} and {t2}.",
        "A SIM activation form lists a relative as subscriber and {pp} as alternate contact.",
        "Door held open at {p} for eleven minutes according to the controller.",
        "Authorisation to use the siding was never issued, but the gate record shows entry at {t}.",
    ],
    "testimony": [
        "{pp} said they heard raised voices near {p} at {t}.",
        "In a statement, {pp} claims to have been at {p} all evening.",
        "The witness told officers a tall man asked the way to {p}.",
        "{pp} denied any contact with the victim since January.",
        "According to {pp}, the call lasted under a minute.",
        "{pp} admitted leaving the post for about eight minutes.",
        "A bystander recalls seeing someone in an olive coat go through the gate.",
        "{pp} insists the entry in the register is accurate.",
        "The interview record notes that {pp} changed their account when questioned about {t}.",
        "{pp} swore they never entered the carriage, then later conceded a short visit.",
        "Statement of {pp}: I did not see anything unusual at {p}.",
        "{pp} told the inspector that the argument was about who wrote the code.",
        "Gopal remembers the train leaving after the thunder, not before.",
        "{pp} could not explain the discrepancy and asked for a lawyer.",
    ],
    "physical": [
        "{o} was found beneath the desk in the carriage.",
        "Forensic note: residue on {o} is consistent with the head wound.",
        "{o} lay near {p}, recently disturbed.",
        "A tuft of olive thread was caught on the rusted latch of the gate.",
        "{o} had been wiped, but traces remain in the grooves.",
        "The surgeon notes a single blunt injury to the left temple.",
        "{o} was recovered from the storm drain six metres from the gate.",
        "Mud on {o} suggests it was dropped rather than placed.",
        "Fibres matching {o} were recovered from the armchair.",
        "The cushion seam held {o}, torn off with force.",
        "{o} showed fresh scratches and a smear of dried blood.",
        "Beside the body lay {o}, still faintly warm.",
        "A boot print in the mud near {p} points towards the gate.",
        "The cups on the side table were cold, one marked with lipstick.",
    ],
    "digital": [
        "The text thread on {d} shows a message sent at {t}: come alone.",
        "{d} recorded the last heartbeat at {t} before the signal went flat.",
        "CCTV footage from {p} shows {pp} sitting still at {t}.",
        "The call log on {d} lists an outgoing call at {t} lasting four minutes.",
        "Video overlay on {d} runs twelve minutes behind real time.",
        "An email archive on {d} holds a message sent in March threatening to go to the press.",
        "Payment app history on {d} timestamps a purchase at {t}.",
        "The DVR export for {p} covers {t} to {t2} without gaps.",
        "{d} backup contains scanned notebooks dated three years earlier.",
        "A deleted chat on {d} was recovered, last edited at {t}.",
        "Metadata on the file in {d} shows it was created at {t}.",
        "The wearable synced to the network clock and logged a pulse spike at {t}.",
        "Messages between the burner number and the victim are stored on {d}.",
        "Server logs on {d} confirm the camera feed dropped at {t}.",
    ],
}


@dataclass
class Sample:
    text: str
    label: str
    group: str  # category:template-index


def _fill(rng: random.Random, tpl: str) -> str:
    return tpl.format(
        t=rng.choice(_TIMES), t2=rng.choice(_TIMES), p=rng.choice(_PLACES), pp=rng.choice(_PEOPLE),
        a=rng.choice(_AMOUNTS), o=rng.choice(_OBJECTS).capitalize() if tpl.startswith("{o}") else rng.choice(_OBJECTS),
        d=rng.choice(_DEVICES),
    )


def make_clue_dataset(seed: int = 7, per_template: int = 9) -> list[Sample]:
    rng = random.Random(seed)
    out: list[Sample] = []
    for cat, tpls in TEMPLATES.items():
        for i, tpl in enumerate(tpls):
            seen: set[str] = set()
            tries = 0
            while len(seen) < per_template and tries < 200:
                tries += 1
                txt = _fill(rng, tpl)
                if rng.random() < 0.25:  # light surface noise
                    txt = rng.choice(["Noted: ", "Report - ", "Inspector's note: ", ""]) + txt
                if txt not in seen:
                    seen.add(txt)
                    out.append(Sample(txt, cat, f"{cat}:{i}"))
    return out


def group_split(samples: list[Sample], seed: int = 7, val_frac: float = 0.15, test_frac: float = 0.2):
    """Split by template group (stratified per category) so no template spans splits."""
    rng = random.Random(seed)
    by_cat: dict[str, list[str]] = {}
    for s in samples:
        by_cat.setdefault(s.label, [])
        if s.group not in by_cat[s.label]:
            by_cat[s.label].append(s.group)
    train_g: set[str] = set()
    val_g: set[str] = set()
    test_g: set[str] = set()
    for groups in by_cat.values():
        gs = groups[:]
        rng.shuffle(gs)
        n = len(gs)
        n_test, n_val = max(1, round(n * test_frac)), max(1, round(n * val_frac))
        test_g |= set(gs[:n_test])
        val_g |= set(gs[n_test:n_test + n_val])
        train_g |= set(gs[n_test + n_val:])
    pick = lambda gs: [s for s in samples if s.group in gs]  # noqa: E731
    return pick(train_g), pick(val_g), pick(test_g)


def dataset_hash(samples: list[Sample]) -> str:
    h = hashlib.sha256()
    for s in sorted(samples, key=lambda x: (x.group, x.text)):
        h.update(f"{s.group}|{s.label}|{s.text}\n".encode())
    return h.hexdigest()


def real_clue_eval_set() -> list[Sample]:
    case = get_case("aakhri_gaadi")
    return [Sample(f"{e.name}. {e.description}", e.category, f"real:{e.key}") for e in case.evidence]
