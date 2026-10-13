from __future__ import annotations

import json
import random
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import Field
from sqlalchemy import select

from ...deps import DB, CurrentUser, View, rate_limit, require_workbench
from ...errors import DomainError
from ...jobs import submit
from ...ml import registry, service
from ...ml.data import (
    CATEGORIES,
    DATASET_VERSION,
    dataset_hash,
    group_split,
    make_clue_dataset,
    real_clue_eval_set,
)
from ...models import Job, MLExperiment, ModelVersion
from ...schemas.requests import Strict

router = APIRouter(tags=["ml"], dependencies=[Depends(rate_limit("api"))])


class ClassifyIn(Strict):
    text: str = Field(min_length=3, max_length=600)


class TrainIn(Strict):
    seed: int = Field(default=7, ge=0, le=10_000)
    include_torch: bool = True


# ---------------------------------------------------------------------------- gameplay-facing
@router.post("/sessions/{session_id}/ml/classify")
def classify(body: ClassifyIn, view: View):
    r = service.classify(body.text)
    if r is None:
        raise DomainError("models_not_trained", "The clue classifier has not been trained on this server "
                          "(run `python -m app.ml.train_all`).", status=503)
    return r


@router.get("/sessions/{session_id}/ml/leads")
def leads(view: View):
    return service.rank_leads(view)


@router.get("/sessions/{session_id}/ml/anomalies")
def anomalies(view: View):
    return service.scan_anomalies(view)


# ---------------------------------------------------------------------------- developer workbench (separate from gameplay)
def _summary() -> dict | None:
    p = Path(registry.artifacts_root()) / "latest_summary.json"
    return json.loads(p.read_text()) if p.exists() else None


@router.get("/ml/workbench", dependencies=[Depends(require_workbench)])
def workbench(db: DB, user: CurrentUser):
    samples = make_clue_dataset(7)
    train, val, test = group_split(samples, 7)
    counts: dict[str, int] = {c: 0 for c in CATEGORIES}
    for s in samples:
        counts[s.label] += 1
    summary = _summary()
    exps = db.scalars(select(MLExperiment).order_by(MLExperiment.id.desc()).limit(30))
    models = db.scalars(select(ModelVersion).order_by(ModelVersion.id.desc()).limit(30))
    examples = []
    rng = random.Random(1)
    for s in rng.sample(test, min(8, len(test))):
        c = service.classify(s.text)
        examples.append({"text": s.text, "truth": s.label, "predictions": c["predictions"] if c else []})
    return {
        "available": service.models_available(),
        "dataset": {"version": DATASET_VERSION, "hash": dataset_hash(samples), "total": len(samples), "train": len(train),
                    "val": len(val), "test": len(test), "real_ood": len(real_clue_eval_set()), "class_counts": counts,
                    "warning": "Synthetic template data; in-distribution scores are optimistic. Real-OOD is the case's own "
                               "evidence (small, hand-labelled)."},
        "latest_summary": summary,
        "experiments": [{"id": e.id, "name": e.name, "task": e.task, "dataset_version": e.dataset_version,
                         "created_at": e.created_at.isoformat(), "metrics": _headline(e.metrics), "mlflow_run_id": e.mlflow_run_id}
                        for e in exps],
        "models": [{"id": m.id, "name": m.name, "version": m.version, "framework": m.framework, "active": m.is_active,
                    "created_at": m.created_at.isoformat()} for m in models],
        "prediction_examples": examples,
        "measured_vs_estimated": "All metrics here are measured on the stated splits by this code; none are estimates.",
    }


def _headline(m: dict) -> dict:
    out = {}
    for k in ("macro_f1", "accuracy", "test_auc_model", "test_auc_heuristic_baseline"):
        if k in m:
            out[k] = m[k]
    for split in ("val", "test", "real_ood"):
        if isinstance(m.get(split), dict) and "macro_f1" in m[split]:
            out[f"{split}_macro_f1"] = m[split]["macro_f1"]
    return out


@router.post("/ml/workbench/train", status_code=202,
             dependencies=[Depends(require_workbench), Depends(rate_limit("train", 3))])
def train(body: TrainIn, user: CurrentUser):
    from ...ml.train_all import train_everything

    def job():
        s = train_everything(body.seed, include_torch=body.include_torch)
        service.clear_cache()
        return {"total_seconds": s["total_seconds"], "models": list(s["models"])}

    return {"job_id": submit("ml_train", job, max_attempts=1)}


@router.get("/ml/workbench/jobs/{job_id}", dependencies=[Depends(require_workbench)])
def job_status(job_id: str, db: DB, user: CurrentUser):
    j = db.get(Job, job_id)
    if j is None or j.kind != "ml_train":
        raise DomainError("not_found", "job not found", status=404)
    return {"id": j.id, "status": j.status, "attempts": j.attempts, "result": j.result, "error": j.error}


@router.post("/ml/workbench/predict", dependencies=[Depends(require_workbench)])
def workbench_predict(body: ClassifyIn, user: CurrentUser):
    r = service.classify(body.text)
    if r is None:
        raise DomainError("models_not_trained", "Train the models first.", status=503)
    return r
