"""Inference layer for the ML components (lazy, cached, safe to call when nothing has been trained yet)."""

from __future__ import annotations

import pickle
import threading
from typing import Any

import joblib
import numpy as np

from ..cases.aakhri_gaadi import logs as case_logs
from ..cases.registry import get_case
from ..engine.state import SessionView
from . import anomaly as anomaly_mod
from . import leads as leads_mod
from . import registry

_lock = threading.Lock()
_cache: dict[tuple[str, str], Any] = {}

DISCLAIMER_LEADS = ("Lead priority suggests where to look next. It is not a measure of guilt and it never decides the case; "
                    "only your evidence-backed accusation does.")
DISCLAIMER_ANOM = "Anomalies are leads that need an explanation, not proof of wrongdoing."


def _load(name: str) -> Any | None:
    d = registry.active_dir(name)
    if d is None:
        return None
    key = (name, str(d))
    with _lock:
        if key in _cache:
            return _cache[key]
        try:
            if name == "clue_classifier_sklearn":
                obj = joblib.load(d / "model.joblib")
            elif name == "clue_classifier_torch":
                from .torch_clf import load_artifacts

                obj = load_artifacts(d)
            else:
                with open(d / "model.pkl", "rb") as fh:
                    obj = pickle.load(fh)  # noqa: S301 - our own artifacts from our own training run, not user input
        except Exception:  # noqa: BLE001 - corrupt/missing artifacts must never break gameplay
            return None
        _cache[key] = obj
        return obj


def clear_cache() -> None:
    with _lock:
        _cache.clear()


def models_available() -> dict[str, bool]:
    return {n: registry.active_dir(n) is not None for n in
            ("clue_classifier_sklearn", "clue_classifier_torch", "lead_ranker", "anomaly_detector")}


def classify(text: str) -> dict[str, Any] | None:
    text = text.strip()[:600]
    if not text:
        return None
    sk = _load("clue_classifier_sklearn")
    out: dict[str, Any] = {"predictions": []}
    if sk is not None:
        label = str(sk.predict([text])[0])
        conf = None
        clf = sk.named_steps["clf"]
        if hasattr(clf, "predict_proba"):
            pr = sk.predict_proba([text])[0]
            conf = float(pr.max())
        elif hasattr(clf, "decision_function"):
            d = np.asarray(sk.decision_function([text])[0])
            e = np.exp(d - d.max())
            conf = float((e / e.sum()).max())
        out["predictions"].append({"model": "sklearn", "category": label, "confidence": None if conf is None else round(conf, 3)})
    tm = _load("clue_classifier_torch")
    if tm is not None:
        lab, p = tm.predict([text])[0]
        out["predictions"].append({"model": "pytorch_textcnn", "category": lab, "confidence": round(p, 3)})
    if not out["predictions"]:
        return None
    out["category"] = out["predictions"][0]["category"]
    return out


def predict_category(text: str) -> str | None:
    r = classify(text)
    return r["category"] if r else None


# ------------------------------------------------------------------------------ anomalies
def _robust_fallback(streams: dict[str, list[float]]) -> list[dict[str, Any]]:
    """Used when no trained detector exists: robust z-score on log-std across devices."""
    feats = {d: anomaly_mod.stream_features(v) for d, v in streams.items()}
    col = np.asarray([f[0] for f in feats.values()])
    med, mad = float(np.median(col)), float(np.median(np.abs(col - np.median(col)))) + 1e-9
    out = []
    for d, f in feats.items():
        z = abs(f[0] - med) / (1.4826 * mad)
        if z > 4:
            out.append({"kind": "device_heartbeat", "subject": d, "score": round(float(z), 2), "isolation_forest": False,
                        "reasons": ["interval jitter differs sharply from the other devices"]})
    return out


def scan_anomalies(view: SessionView) -> dict[str, Any]:
    if "ev_access_log" not in view.held:
        return {"available": False, "findings": [], "disclaimer": DISCLAIMER_ANOM,
                "message": "Nothing to scan yet — you haven't collected the machine logs."}
    streams = case_logs.heartbeat_intervals()
    sessions = case_logs.badge_sessions()
    det = _load("anomaly_detector")
    findings = anomaly_mod.scan_case(det, streams, sessions) if det is not None else _robust_fallback(streams)
    # present only what the player's evidence supports: device findings need the log; ownership needs the maintenance log
    out = []
    for f in findings:
        item = dict(f)
        item["person"] = None
        if f["kind"] == "badge_session" and "K.RATHORE" in f["subject"]:
            item["person"] = "kabir"
        elif f["subject"] == "CAM-7" and "ev_maint_log" in view.held:
            item["person"] = "kabir"
        if f["kind"] == "badge_session":
            h = int(f["t_in"]) // 3600
            m = (int(f["t_in"]) % 3600) // 60
            item["detail"] = f"entry at {h:02d}:{m:02d} (station clock)"
        out.append(item)
    return {"available": True, "model": "isolation_forest+zscore" if det is not None else "robust_zscore_fallback",
            "findings": out, "disclaimer": DISCLAIMER_ANOM}


# ------------------------------------------------------------------------------ leads
def rank_leads(view: SessionView) -> dict[str, Any]:
    case = get_case(view.case.id)
    model = _load("lead_ranker")
    anomaly_people = {f["person"] for f in scan_anomalies(view)["findings"] if f.get("person")}
    rows = leads_mod.rank(view, case, model, anomaly_people)
    return {"model": "lead_ranker (logistic regression)" if model is not None else "transparent heuristic baseline",
            "ranking": rows, "disclaimer": DISCLAIMER_LEADS}

