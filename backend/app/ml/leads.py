"""Lead prioritisation: which person deserves the player's attention next.

IMPORTANT DESIGN CONSTRAINTS
  * It ranks *leads*, not guilt. Output is labelled "lead priority", never "probability of guilt".
  * Features are computed only from what the player can see (held evidence, voiced statements, established
    contradictions, interviews). Neither the case's culprit field nor any character identity is an input.
  * The training label ("an unestablished contradiction about them could be pursued right now") is derived from the case
    structure by simulation. It is a proxy for "worth following up", and is documented as such: it can't know what is
    actually useful to a human player.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

from ..cases.base import CaseSpec
from ..engine.clock import effective_held

FEATURES = ["motive", "presence", "meeting", "claims_broken", "unchecked_statements", "alibi_cleared", "not_interviewed",
            "connections", "anomaly_flags"]

PHRASES = {
    "motive": "evidence bearing on a motive",
    "presence": "evidence placing them near the scene",
    "meeting": "evidence of a prior arrangement with the victim",
    "claims_broken": "a statement already contradicted",
    "unchecked_statements": "statements not yet tested against records",
    "alibi_cleared": "an established alibi for the time of death",
    "not_interviewed": "you haven't interviewed them yet",
    "connections": "evidence connected to them",
    "anomaly_flags": "anomalies in records tied to them",
}

# Fixed, documented weights for the transparent baseline.
BASELINE_W = {"motive": 1.0, "presence": 1.0, "meeting": 1.0, "claims_broken": -1.0, "unchecked_statements": 2.0,
              "alibi_cleared": -1.0, "not_interviewed": 1.5, "connections": 0.3, "anomaly_flags": 1.5}


def features_for(view, case: CaseSpec, char_key: str, anomaly_people: set[str] | None = None) -> list[float]:
    held = effective_held(case, view.held)
    f = dict.fromkeys(FEATURES, 0.0)
    for k in view.held:
        ev = case.ev(k)
        related = char_key in ev.related_people
        bearing = [b for b in ev.bears_on if b.character == char_key and all(r in held for r in b.requires)]
        if related or bearing:
            f["connections"] += 1
        for b in bearing:
            if b.stance == "points_to":
                if b.aspect == "motive":
                    f["motive"] += 1
                elif b.aspect == "meeting":
                    f["meeting"] += 1
                else:
                    f["presence"] += 1
    f["claims_broken"] = sum(1 for r in case.contradictions if r.about == char_key and r.key in view.contradictions)
    in_found = {e for r in case.contradictions if r.key in view.contradictions for p in r.pairs for e in p}
    f["unchecked_statements"] = sum(1 for k in view.held if k.startswith("ev_stmt_") and char_key in case.ev(k).related_people
                                    and k not in in_found)
    f["alibi_cleared"] = 1.0 if any(char_key in a.characters and all(r in held for r in a.requires) for a in case.alibis) else 0.0
    conv = view.conversations.get(char_key)
    f["not_interviewed"] = 0.0 if (conv is not None and getattr(conv, "turns", 0) > 0) else 1.0
    f["anomaly_flags"] = 1.0 if (anomaly_people and char_key in anomaly_people) else 0.0
    return [f[n] for n in FEATURES]


def baseline_score(x: list[float]) -> float:
    return sum(BASELINE_W[n] * v for n, v in zip(FEATURES, x, strict=True))


def _actionable_discrepancy(case: CaseSpec, held: set[str], found: set[str], interviewed: bool, char_key: str) -> bool:
    """True if a contradiction about this person is still unestablished AND the player could act on it now:
    they hold one side of it (a statement or record) or haven't yet interviewed the person."""
    for r in case.contradictions:
        if r.about != char_key or r.key in found:
            continue
        if not interviewed or any(e in held for p in r.pairs for e in p):
            return True
    return False


def simulate(case: CaseSpec, n_states: int = 1500, seed: int = 21):
    """Random plausible investigation states -> (X, y, state_id). Label: an unestablished, actionable discrepancy exists for the person."""
    rng = random.Random(seed)
    keys = [e.key for e in case.evidence]
    X: list[list[float]] = []
    y: list[int] = []
    g: list[int] = []
    suspects = [c.key for c in case.characters]
    for s in range(n_states):
        order = keys[:]
        rng.shuffle(order)
        held = set(order[: rng.randint(0, len(order))])
        found = {r.key for r in case.contradictions if any(p[0] in held and p[1] in held for p in r.pairs) and rng.random() < 0.5}
        convs = {c: SimpleNamespace(turns=rng.randint(0, 6)) for c in suspects if rng.random() < 0.6}
        view = SimpleNamespace(held=held, contradictions={k: True for k in found}, conversations=convs)
        for c in suspects:
            X.append(features_for(view, case, c))
            y.append(1 if _actionable_discrepancy(case, held, found, c in convs and convs[c].turns > 0, c) else 0)
            g.append(s)
    return np.asarray(X), np.asarray(y), np.asarray(g)


@dataclass
class LeadModel:
    scaler: StandardScaler
    clf: LogisticRegression

    def proba(self, X: np.ndarray) -> np.ndarray:
        return self.clf.predict_proba(self.scaler.transform(X))[:, 1]

    def contributions(self, x: list[float]) -> list[tuple[str, float]]:
        z = self.scaler.transform(np.asarray([x]))[0]
        return sorted(((n, float(c * v)) for n, c, v in zip(FEATURES, self.clf.coef_[0], z, strict=True)), key=lambda t: -abs(t[1]))


def train(case: CaseSpec, seed: int = 21) -> tuple[LeadModel, dict[str, Any]]:
    X, y, g = simulate(case, 1500, seed)
    states = np.unique(g)
    rng = np.random.default_rng(seed)
    rng.shuffle(states)
    cut = int(0.75 * len(states))
    tr = np.isin(g, states[:cut])
    te = ~tr
    scaler = StandardScaler().fit(X[tr])
    clf = LogisticRegression(max_iter=1000, C=1.0, random_state=seed).fit(scaler.transform(X[tr]), y[tr])
    model = LeadModel(scaler, clf)
    p = model.proba(X[te])
    base = np.asarray([baseline_score(list(r)) for r in X[te]])
    metrics = {
        "n_states": int(len(states)), "rows": int(len(y)), "positive_rate": round(float(y.mean()), 3),
        "test_auc_model": round(float(roc_auc_score(y[te], p)), 4),
        "test_auc_heuristic_baseline": round(float(roc_auc_score(y[te], base)), 4),
        "coefficients": {n: round(float(c), 3) for n, c in zip(FEATURES, clf.coef_[0], strict=True)},
        "note": "Labels come from a simulation over the case structure (see module docstring); AUC measures agreement with "
                "that proxy label, not usefulness to real players.",
    }
    return model, metrics


def rank(view, case: CaseSpec, model: LeadModel | None, anomaly_people: set[str] | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for c in case.characters:
        x = features_for(view, case, c.key, anomaly_people)
        if model is not None:
            score = float(model.proba(np.asarray([x]))[0])
            contrib = model.contributions(x)
        else:
            score = float(1 / (1 + np.exp(-baseline_score(x) / 3)))
            contrib = sorted(((n, BASELINE_W[n] * v) for n, v in zip(FEATURES, x, strict=True)), key=lambda t: -abs(t[1]))
        why = [f"{'+' if w > 0 else '−'} {PHRASES[n]}" for n, w in contrib if abs(w) > 0.05][:3]
        rows.append({"character": c.key, "name": c.name, "priority": round(score, 3),
                     "baseline": round(float(1 / (1 + np.exp(-baseline_score(x) / 3))), 3), "reasons": why,
                     "features": dict(zip(FEATURES, x, strict=True))})
    salt = getattr(getattr(view, "session", None), "id", "")
    # ties are broken by a per-session hash so that list/author order can never hint at anything
    rows.sort(key=lambda r: (-r["priority"], hashlib.md5(f"{salt}:{r['character']}".encode()).hexdigest()))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows
