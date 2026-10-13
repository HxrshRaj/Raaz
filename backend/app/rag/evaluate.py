"""Retrieval evaluation against a small hand-labelled query set.

Run:  python -m app.rag.evaluate
Labels were written by hand from the case package (each query has the chunk refs a human would accept). The set is
small (n≈24) and was authored alongside the corpus, so treat the numbers as a regression guard, not a benchmark.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..cases.registry import get_case
from .store import retrieve

# (query, accepted source refs)
LABELLED: list[tuple[str, tuple[str, ...]]] = [
    ("why is the station clock wrong", ("ev:ev_clock_slow", "doc:doc_clock_policy", "evx:ev_clock_slow")),
    ("which clock do the cameras use", ("doc:doc_clock_policy", "evx:ev_clock_slow", "ev:ev_clock_slow")),
    ("what is a platform ticket allowed to do", ("doc:doc_ticket_rules", "evx:ev_ticket_stub", "evx:ev_ticket_log")),
    ("can a platform ticket be used to travel", ("doc:doc_ticket_rules",)),
    ("how can the carriage door be locked from outside", ("doc:doc_lock_manual", "ev:ev_door_lock", "evx:ev_door_lock")),
    ("where is the spare key kept", ("ev:ev_key_register", "doc:doc_lock_manual", "evx:ev_key_register")),
    ("when did Adrian's heart stop", ("ev:ev_watch", "evx:ev_watch", "doc:doc_forensics")),
    ("how is time of death determined", ("doc:doc_forensics", "evx:ev_autopsy_prelim", "ev:ev_autopsy_prelim")),
    ("was the Kosi passenger on time", ("ev:ev_register", "ev:ev_signal_memo", "evx:ev_register", "doc:doc_kosi", "ev:ev_cctv_platform")),
    ("signal failure delayed the train", ("ev:ev_signal_memo", "evx:ev_signal_memo", "doc:doc_kosi")),
    ("who bought tea at the stall", ("ev:ev_upi_ledger", "evx:ev_upi_ledger", "ev:ev_tea_cups")),
    ("lipstick on a clay cup", ("ev:ev_tea_cups", "evx:ev_tea_cups")),
    ("camera that was unplugged", ("ev:ev_cam7_cable", "evx:ev_cam7_cable", "ev:ev_maint_log", "evx:ev_maint_log")),
    ("badge records for the siding gate", ("ev:ev_access_log", "evx:ev_access_log")),
    ("text messages on Adrian's phone", ("ev:ev_sms_thread", "evx:ev_sms_thread")),
    ("who was the unsaved number registered to", ("ev:ev_sim_record", "evx:ev_sim_record", "evx:ev_sms_thread")),
    ("patent for the Pathfinder engine", ("ev:ev_patent", "evx:ev_patent", "doc:doc_valecore_press", "ev:ev_sale_agreement")),
    ("threatening email to the founder", ("ev:ev_threat_email", "evx:ev_threat_email")),
    ("money transferred to Kaveri Holdings", ("ev:ev_ledger_kaveri", "evx:ev_ledger_kaveri", "ev:ev_bank_slip", "evx:ev_bank_slip")),
    ("what did the police surgeon conclude", ("ev:ev_autopsy_prelim", "evx:ev_autopsy_prelim")),
    ("olive coloured raincoat button", ("ev:ev_button", "evx:ev_button", "ev:ev_gate_thread", "evx:ev_gate_thread")),
    ("what weapon was used", ("ev:ev_paperweight", "evx:ev_paperweight", "ev:ev_autopsy_prelim")),
    ("how far is the tea stall from the siding gate", ("doc:doc_layout",)),
    ("who is the journalist writing about the sale", ("ev:ev_newspaper", "evx:ev_newspaper", "doc:doc_valecore_press")),
]


@dataclass
class RetrievalReport:
    n: int
    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    mrr: float
    misses: list[str]

    def as_dict(self) -> dict:
        return {"n": self.n, "recall@1": round(self.recall_at_1, 3), "recall@3": round(self.recall_at_3, 3),
                "recall@5": round(self.recall_at_5, 3), "mrr": round(self.mrr, 3), "misses": self.misses}


def evaluate(db: Session, case_id: str = "aakhri_gaadi") -> RetrievalReport:
    case = get_case(case_id)
    held = frozenset(e.key for e in case.evidence)  # evaluation is on the *fully unlocked* corpus
    r1 = r3 = r5 = 0
    rr = 0.0
    misses = []
    for q, accepted in LABELLED:
        hits = retrieve(db, case_id=case_id, query=q, scopes=("case_doc", "evidence"), held=held, examined=held, k=5)
        refs = [h.source_ref.split("#")[0] for h in hits]
        rank = next((i + 1 for i, ref in enumerate(refs) if ref in accepted), None)
        if rank is None:
            misses.append(q)
            continue
        r1 += rank <= 1
        r3 += rank <= 3
        r5 += rank <= 5
        rr += 1 / rank
    n = len(LABELLED)
    return RetrievalReport(n, r1 / n, r3 / n, r5 / n, rr / n, misses)


if __name__ == "__main__":  # pragma: no cover
    import json

    from ..db import SessionLocal
    from ..main import init_database

    init_database()
    with SessionLocal() as s:
        print(json.dumps(evaluate(s).as_dict(), indent=2))
