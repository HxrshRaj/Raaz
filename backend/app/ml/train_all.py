"""Train every ML component, evaluate, save artifacts, record experiments.

    python -m app.ml.train_all [--seed 7]

Artifacts go to RAAZ_ARTIFACTS_DIR (default backend/artifacts, git-ignored). Nothing is downloaded.
"""

from __future__ import annotations

import argparse
import json
import pickle
import time
from typing import Any

import joblib

from ..cases.registry import get_case
from ..db import SessionLocal
from . import anomaly as anomaly_mod
from . import leads as leads_mod
from . import registry
from .data import DATASET_VERSION, dataset_hash, group_split, make_clue_dataset, real_clue_eval_set
from .text_clf import top_features, train_classical


def train_everything(seed: int = 7, persist_db: bool = True, include_torch: bool = True) -> dict[str, Any]:
    t0 = time.perf_counter()
    samples = make_clue_dataset(seed)
    train, val, test = group_split(samples, seed)
    real = real_clue_eval_set()
    dhash = dataset_hash(samples)
    version = f"{DATASET_VERSION}-{dhash[:8]}-s{seed}"
    summary: dict[str, Any] = {
        "dataset": {"version": DATASET_VERSION, "hash": dhash, "synthetic_samples": len(samples), "train": len(train),
                    "val": len(val), "test": len(test), "real_ood": len(real),
                    "classes": sorted({s.label for s in samples}),
                    "warning": "Synthetic template data: in-distribution scores are optimistic. 'real_ood' is the case's own "
                               "authored evidence (small, hand-labelled) and is the honest generalisation check."},
        "models": {},
    }
    db = SessionLocal() if persist_db else None
    try:
        # ---- classical text classifiers
        cres = train_classical(train, val, test, real, seed)
        d = registry.model_dir("clue_classifier_sklearn", version)
        d.mkdir(parents=True, exist_ok=True)
        joblib.dump(cres.models[cres.best], d / "model.joblib")
        (d / "metrics.json").write_text(json.dumps(cres.table))
        summary["models"]["clue_classifier_sklearn"] = {"selected_on_validation": cres.best, "comparison": cres.table,
                                                        "top_features": top_features(cres.models["tfidf_logreg"])}
        if db:
            registry.record(db, name="clue_classifier_sklearn", task="text_classification", framework="sklearn",
                            dataset_version=DATASET_VERSION, dataset_hash=dhash,
                            params={"selected": cres.best, "seed": seed}, metrics=cres.table[cres.best], artifact_dir=d,
                            version=version)

        # ---- PyTorch
        if include_torch:
            from .torch_clf import TorchConfig, save_artifacts, train_torch

            cfg = TorchConfig(seed=seed)
            tres = train_torch(train, val, test, real, cfg)
            td = registry.model_dir("clue_classifier_torch", version)
            save_artifacts(tres, td)
            summary["models"]["clue_classifier_torch"] = {
                "architecture": "TextCNN (embedding 64, conv k=2/3/4 x64, max-pool, dropout 0.4)", "params": tres.n_params,
                "best_epoch": tres.best_epoch, "epochs_run": len(tres.history), "train_seconds": round(tres.train_seconds, 2),
                "history": tres.history, **tres.metrics}
            if db:
                registry.record(db, name="clue_classifier_torch", task="text_classification", framework="pytorch",
                                dataset_version=DATASET_VERSION, dataset_hash=dhash,
                                params={**{k: (list(v) if isinstance(v, tuple) else v) for k, v in cfg.__dict__.items()}},
                                metrics={**tres.metrics, "best_epoch": tres.best_epoch}, artifact_dir=td, version=version)

        # ---- lead prioritisation
        case = get_case("aakhri_gaadi")
        lmodel, lmetrics = leads_mod.train(case)
        ld = registry.model_dir("lead_ranker", version)
        ld.mkdir(parents=True, exist_ok=True)
        with open(ld / "model.pkl", "wb") as fh:
            pickle.dump(lmodel, fh)
        (ld / "metrics.json").write_text(json.dumps(lmetrics))
        summary["models"]["lead_ranker"] = lmetrics
        if db:
            registry.record(db, name="lead_ranker", task="lead_prioritisation", framework="sklearn", dataset_version="simulated-v1",
                            dataset_hash=dhash, params={"model": "logistic_regression"}, metrics=lmetrics, artifact_dir=ld,
                            version=version)

        # ---- anomaly detection
        det, ametrics = anomaly_mod.fit()
        ad = registry.model_dir("anomaly_detector", version)
        ad.mkdir(parents=True, exist_ok=True)
        with open(ad / "model.pkl", "wb") as fh:
            pickle.dump(det, fh)
        (ad / "metrics.json").write_text(json.dumps(ametrics))
        summary["models"]["anomaly_detector"] = ametrics
        if db:
            registry.record(db, name="anomaly_detector", task="anomaly_detection", framework="sklearn",
                            dataset_version="simulated-logs-v1", dataset_hash=dhash,
                            params={"model": "isolation_forest"}, metrics=ametrics, artifact_dir=ad, version=version)
    finally:
        if db:
            db.close()
    summary["total_seconds"] = round(time.perf_counter() - t0, 2)
    (registry.artifacts_root() / "latest_summary.json").write_text(json.dumps(summary, default=float))
    return summary


def _print(summary: dict[str, Any]) -> None:
    print(f"dataset {summary['dataset']['version']}  train/val/test = {summary['dataset']['train']}/"
          f"{summary['dataset']['val']}/{summary['dataset']['test']}  real OOD = {summary['dataset']['real_ood']}")
    cmp_ = summary["models"]["clue_classifier_sklearn"]["comparison"]
    print(f"\n{'model':<16}{'val F1':>8}{'test F1':>9}{'real-OOD F1':>13}")
    for k, v in cmp_.items():
        print(f"{k:<16}{v['val']['macro_f1']:>8}{v['test']['macro_f1']:>9}{v['real_ood']['macro_f1']:>13}")
    t = summary["models"].get("clue_classifier_torch")
    if t:
        print(f"{'torch_textcnn':<16}{t['val']['macro_f1']:>8}{t['test']['macro_f1']:>9}{t['real_ood']['macro_f1']:>13}"
              f"   (best epoch {t['best_epoch']}, {t['params']} params)")
    print("\nlead ranker:", {k: v for k, v in summary["models"]["lead_ranker"].items() if k.startswith("test_auc")})
    print("anomaly:", {k: v for k, v in summary["models"]["anomaly_detector"].items() if k != "note"})
    print(f"\nselected sklearn model (validation): {summary['models']['clue_classifier_sklearn']['selected_on_validation']}")
    print(f"total {summary['total_seconds']}s")


if __name__ == "__main__":  # pragma: no cover
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--no-torch", action="store_true")
    a = ap.parse_args()
    from ..main import init_database

    init_database()
    _print(train_everything(a.seed, include_torch=not a.no_torch))
