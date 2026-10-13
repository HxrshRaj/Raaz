"""Anomaly detection over simulated access logs / device heartbeats / badge sessions.

Findings are LEADS: an anomaly says "this record behaves unlike normal records", never "this person is guilty".
IsolationForest (unsupervised) is compared with a simple statistical baseline on labelled *synthetic* streams with
injected faults. Real-world performance is unknown; the case log is a single hand-built example.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import f1_score, precision_score, recall_score

# --------------------------------------------------------------------------- heartbeat streams
STREAM_FEATURES = ["log_std", "cv", "frac_exact", "max_gap_ratio", "mean_dev"]


def stream_features(intervals: list[float], nominal: float = 60.0) -> list[float]:
    a = np.asarray(intervals, dtype=float)
    std = float(a.std())
    mean = float(a.mean())
    frac_exact = float(np.mean(np.abs(a - nominal) < 1e-9))
    return [math.log10(std + 1e-6), std / mean if mean else 0.0, frac_exact, float(a.max() / nominal), abs(mean - nominal)]


def synth_streams(n: int = 400, anomaly_rate: float = 0.1, seed: int = 3) -> tuple[list[list[float]], list[int], list[str]]:
    rng = random.Random(seed)
    xs, ys, kinds = [], [], []
    for _ in range(n):
        length = rng.randint(300, 900)
        sigma = rng.uniform(0.15, 0.6)
        base = [max(58.0, 60.0 + rng.gauss(0, sigma)) for _ in range(length)]
        if rng.random() < anomaly_rate:
            kind = rng.choice(["too_perfect", "gap", "drift"])
            if kind == "too_perfect":
                base = [60.0] * length
            elif kind == "gap":
                i = rng.randint(50, length - 50)
                base[i] = rng.uniform(300, 1200)
            else:
                base = [x + rng.uniform(2.5, 6.0) for x in base]
            xs.append(stream_features(base))
            ys.append(1)
            kinds.append(kind)
        else:
            xs.append(stream_features(base))
            ys.append(0)
            kinds.append("normal")
    return xs, ys, kinds


# --------------------------------------------------------------------------- badge sessions
SESSION_FEATURES = ["dwell_log", "unpaired", "overlap_later"]


def session_features(sessions: list[dict]) -> list[list[float]]:
    out = []
    for s in sessions:
        later = any(o["person"] == s["person"] and o["t_in"] > s["t_in"] and o["door"] != s["door"] for o in sessions)
        unpaired = s["t_out"] is None
        dwell = (s["t_out"] - s["t_in"]) if not unpaired else 0
        out.append([math.log10(max(dwell, 1)), 1.0 if unpaired else 0.0, 1.0 if (unpaired and later) else 0.0])
    return out


def synth_sessions(n: int = 600, anomaly_rate: float = 0.08, seed: int = 4) -> tuple[list[dict], list[int]]:
    rng = random.Random(seed)
    sessions, ys = [], []
    for _i in range(n):
        who = f"p{rng.randint(1, 40)}"
        door = rng.choice(["A", "B", "C"])
        t_in = rng.randint(0, 80000)
        if rng.random() < anomaly_rate:
            kind = rng.choice(["no_exit_overlap", "marathon"])
            if kind == "no_exit_overlap":
                sessions.append({"person": who, "door": door, "t_in": t_in, "t_out": None})
                sessions.append({"person": who, "door": "Z", "t_in": t_in + rng.randint(600, 3000), "t_out": None})
                ys += [1, 0]
            else:
                sessions.append({"person": who, "door": door, "t_in": t_in, "t_out": t_in + rng.randint(30000, 70000)})
                ys.append(1)
        else:
            sessions.append({"person": who, "door": door, "t_in": t_in, "t_out": t_in + int(rng.lognormvariate(5.7, 0.5))})
            ys.append(0)
    return sessions, ys


# --------------------------------------------------------------------------- detectors
@dataclass
class Detectors:
    stream_if: IsolationForest
    session_if: IsolationForest
    stream_mu: np.ndarray
    stream_sd: np.ndarray


def fit(seed: int = 3) -> tuple[Detectors, dict[str, Any]]:
    xs, ys, _kinds = synth_streams(seed=seed)
    xs_arr = np.asarray(xs)
    split = int(0.6 * len(xs))
    normal_train = xs_arr[:split][np.asarray(ys[:split]) == 0]  # train on (assumed) clean data only
    sif = IsolationForest(n_estimators=200, contamination=0.03, random_state=seed).fit(normal_train)
    mu, sd = normal_train.mean(0), normal_train.std(0) + 1e-9
    sessions, sy = synth_sessions(seed=seed + 1)
    sfx = np.asarray(session_features(sessions))
    # session labels align to sessions; train only on those labelled normal (the synthetic generator knows)
    kif = IsolationForest(n_estimators=200, contamination=0.03, random_state=seed).fit(sfx[np.asarray(sy) == 0])
    det = Detectors(sif, kif, mu, sd)

    # ---- evaluation on held-out synthetic data (a different seed than training)
    ex, ey, _ = synth_streams(seed=seed + 100)
    ey_arr = np.asarray(ey)
    ex_arr = np.asarray(ex)
    pred_if = (sif.predict(ex_arr) == -1).astype(int)
    z = np.abs((ex_arr - mu) / sd).max(1)
    pred_z = (z > 4.0).astype(int)
    s2, y2 = synth_sessions(seed=seed + 101)
    sfx2 = np.asarray(session_features(s2))
    pred_s = (kif.predict(sfx2) == -1).astype(int)

    def rep(y, p):
        return {"precision": round(float(precision_score(y, p, zero_division=0)), 3),
                "recall": round(float(recall_score(y, p, zero_division=0)), 3),
                "f1": round(float(f1_score(y, p, zero_division=0)), 3), "n": int(len(y)), "positives": int(sum(y))}

    metrics = {"streams_isolation_forest": rep(ey_arr, pred_if), "streams_zscore_baseline": rep(ey_arr, pred_z),
               "sessions_isolation_forest": rep(np.asarray(y2), pred_s),
               "note": "Evaluated on synthetic data with injected faults; says nothing about real-world accuracy."}
    return det, metrics


def scan_case(det: Detectors, streams: dict[str, list[float]], sessions: list[dict]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for dev, vals in streams.items():
        f = np.asarray([stream_features(vals)])
        flagged_if = det.stream_if.predict(f)[0] == -1
        z = float(np.abs((f - det.stream_mu) / det.stream_sd).max())
        if flagged_if or z > 4.0:
            std = float(np.std(vals))
            reasons = []
            if std < 1e-6:
                reasons.append("interval jitter is exactly zero — unlike every other device, whose pings vary by a few hundred ms")
            if max(vals) > 90:
                reasons.append("contains a long gap in pings")
            findings.append({"kind": "device_heartbeat", "subject": dev, "score": round(z, 2), "isolation_forest": bool(flagged_if),
                             "reasons": reasons or ["statistically unlike the other devices"]})
    sf = np.asarray(session_features(sessions))
    pred = det.session_if.predict(sf)
    for s, f, p in zip(sessions, sf, pred, strict=True):
        if p == -1 or f[2] == 1.0:
            why = []
            if f[1] == 1.0:
                why.append("no exit logged for this entry")
            if f[2] == 1.0:
                why.append("the same badge appears at another door afterwards while this entry is still open")
            if f[0] > 4.2:
                why.append("unusually long dwell time")
            if why:
                findings.append({"kind": "badge_session", "subject": f"{s['person']} @ {s['door']}", "score": float(f[1] + f[2]),
                                 "isolation_forest": bool(p == -1), "reasons": why,
                                 "t_in": s["t_in"], "t_out": s["t_out"]})
    findings.sort(key=lambda x: -x["score"])
    return findings
