"""Artifact storage + experiment / model-version tracking (DB tables; MLflow mirrored when installed and configured)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..config import get_settings
from ..logging_setup import get_logger
from ..models import MLExperiment, ModelVersion

log = get_logger("raaz.ml")


def artifacts_root() -> Path:
    p = Path(get_settings().artifacts_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def model_dir(name: str, version: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", version)
    return artifacts_root() / name / safe


def active_dir(name: str, db: Session | None = None) -> Path | None:
    """Directory of the most recent artifact for `name` (DB active flag if available, else newest folder)."""
    if db is not None:
        mv = db.scalar(select(ModelVersion).where(ModelVersion.name == name, ModelVersion.is_active.is_(True))
                       .order_by(ModelVersion.id.desc()))
        if mv is not None and Path(mv.artifact_path).exists():
            return Path(mv.artifact_path)
    base = artifacts_root() / name
    if not base.exists():
        return None
    dirs = sorted((d for d in base.iterdir() if d.is_dir()), key=lambda d: d.stat().st_mtime, reverse=True)
    return dirs[0] if dirs else None


def _mlflow_log(name: str, task: str, params: dict[str, Any], metrics: dict[str, float], artifact_dir: Path | None) -> str | None:
    uri = get_settings().mlflow_tracking_uri
    if not uri:
        return None
    try:  # pragma: no cover - optional dependency, not installed in CI
        import mlflow

        mlflow.set_tracking_uri(uri)
        mlflow.set_experiment(f"raaz-{task}")
        with mlflow.start_run(run_name=name) as run:
            mlflow.log_params({k: str(v)[:250] for k, v in params.items()})
            mlflow.log_metrics({k: float(v) for k, v in metrics.items()})
            if artifact_dir and artifact_dir.exists():
                mlflow.log_artifacts(str(artifact_dir))
            return run.info.run_id
    except Exception as e:  # noqa: BLE001
        log.warning("mlflow logging skipped", extra={"error": str(e)})
        return None


def flat_metrics(d: dict[str, Any], prefix: str = "") -> dict[str, float]:
    out: dict[str, float] = {}
    for k, v in d.items():
        if isinstance(v, dict):
            if k in ("per_class",):
                continue
            out.update(flat_metrics(v, f"{prefix}{k}."))
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            out[f"{prefix}{k}"] = float(v)
    return out


def record(db: Session, *, name: str, task: str, framework: str, dataset_version: str, dataset_hash: str,
           params: dict[str, Any], metrics: dict[str, Any], artifact_dir: Path, version: str, activate: bool = True) -> ModelVersion:
    run_id = _mlflow_log(name, task, params, flat_metrics(metrics), artifact_dir)
    exp = MLExperiment(name=name, task=task, dataset_version=dataset_version, dataset_hash=dataset_hash, params=params,
                       metrics=json.loads(json.dumps(metrics, default=float)), mlflow_run_id=run_id)
    db.add(exp)
    db.flush()
    if activate:
        db.execute(update(ModelVersion).where(ModelVersion.name == name).values(is_active=False))
    existing = db.scalar(select(ModelVersion).where(ModelVersion.name == name, ModelVersion.version == version))
    if existing is not None:
        existing.experiment_id, existing.metrics, existing.artifact_path = exp.id, json.loads(json.dumps(metrics, default=float)), str(artifact_dir)
        existing.is_active = activate
        mv = existing
    else:
        mv = ModelVersion(experiment_id=exp.id, name=name, version=version, framework=framework, artifact_path=str(artifact_dir),
                          metrics=json.loads(json.dumps(metrics, default=float)), is_active=activate)
        db.add(mv)
    db.commit()
    return mv
