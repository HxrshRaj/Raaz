from __future__ import annotations

import dataclasses
import inspect

import numpy as np
import pytest

from app import db as dbmod
from app.cases.aakhri_gaadi import logs as case_logs
from app.cases.registry import get_case
from app.engine.state import get_owned_session, load_view
from app.ml import anomaly, leads, registry, service
from app.ml.data import CATEGORIES, dataset_hash, group_split, make_clue_dataset, real_clue_eval_set
from app.ml.text_clf import train_classical
from app.ml.torch_clf import TorchConfig, Vocab, load_artifacts, normalize, save_artifacts, train_torch
from app.models import ModelVersion
from tests.helpers import Player


# ============================================================================ data integrity & leakage
def test_labels_and_vocabulary_are_clean():
    samples = make_clue_dataset(7)
    assert {s.label for s in samples} == set(CATEGORIES)
    assert all(s.text.strip() and "{" not in s.text for s in samples)  # no unfilled template slots
    counts = {c: sum(s.label == c for s in samples) for c in CATEGORIES}
    assert max(counts.values()) / min(counts.values()) < 1.6  # roughly balanced


def test_dataset_is_reproducible():
    assert dataset_hash(make_clue_dataset(7)) == dataset_hash(make_clue_dataset(7))
    assert dataset_hash(make_clue_dataset(7)) != dataset_hash(make_clue_dataset(8))


def test_no_template_or_text_leaks_across_splits():
    train, val, test = group_split(make_clue_dataset(7), 7)
    g = lambda ss: {s.group for s in ss}  # noqa: E731
    t = lambda ss: {s.text for s in ss}  # noqa: E731
    assert not (g(train) & g(val)) and not (g(train) & g(test)) and not (g(val) & g(test))
    assert not (t(train) & t(test)) and not (t(train) & t(val))
    for split in (train, val, test):
        assert {s.label for s in split} == set(CATEGORIES)  # every class present in every split


def test_preprocessing_normalises_times_and_numbers():
    assert normalize("Left at 22:45 and paid Rs 50,000.") == ["left", "at", "<time>", "and", "paid", "rs", "<num>"]
    v = Vocab.build(["alpha beta", "beta gamma"])
    assert v.encode("beta zzz", 4) == [v.stoi["beta"], 1, 0, 0]


def test_real_eval_set_uses_case_categories():
    real = real_clue_eval_set()
    assert len(real) == len(get_case("aakhri_gaadi").evidence)
    assert {s.label for s in real} <= set(CATEGORIES)


# ============================================================================ classical + torch
@pytest.fixture(scope="module")
def trained(client):
    from app.ml.train_all import train_everything

    return train_everything(seed=7, persist_db=True, include_torch=True)


def test_classical_models_beat_majority_and_selection_uses_validation(trained):
    t = trained["models"]["clue_classifier_sklearn"]
    cmp_ = t["comparison"]
    assert cmp_["majority"]["test"]["macro_f1"] < 0.15
    for name in ("tfidf_nb", "tfidf_logreg", "wordchar_svm"):
        assert cmp_[name]["test"]["macro_f1"] > 0.5, (name, cmp_[name]["test"])
    best_by_val = max(cmp_, key=lambda k: cmp_[k]["val"]["macro_f1"])
    assert t["selected_on_validation"] == best_by_val
    assert len(cmp_["wordchar_svm"]["test"]["confusion"]) == len(CATEGORIES)


def test_torch_trains_with_early_stopping_and_checkpoint(trained):
    t = trained["models"]["clue_classifier_torch"]
    assert t["epochs_run"] <= 40 and 1 <= t["best_epoch"] <= t["epochs_run"]
    losses = [h["train_loss"] for h in t["history"]]
    assert losses[-1] < losses[0]  # it learned something
    assert t["test"]["macro_f1"] > 0.35  # clearly above chance (1/6); the honest comparison is in docs
    assert t["params"] > 10_000


def test_torch_artifacts_roundtrip_and_reproducibility(tmp_path):
    samples = make_clue_dataset(7, per_template=5)
    train, val, test = group_split(samples, 7)
    real = real_clue_eval_set()
    cfg = TorchConfig(seed=3, max_epochs=6, patience=3)
    a = train_torch(train, val, test, real, cfg)
    b = train_torch(train, val, test, real, cfg)
    assert [h["val_loss"] for h in a.history] == [h["val_loss"] for h in b.history]  # same seed -> same run
    save_artifacts(a, tmp_path)
    pred = load_artifacts(tmp_path)
    texts = [s.text for s in test[:12]]
    from app.ml.torch_clf import TorchPredictor

    fresh = TorchPredictor(a.net, a.vocab, a.cfg)
    assert np.allclose(pred.predict_proba(texts), fresh.predict_proba(texts), atol=1e-6)
    p = pred.predict_proba(texts)
    assert p.shape == (12, len(CATEGORIES)) and np.allclose(p.sum(1), 1.0, atol=1e-5)
    assert pred.predict_proba([]).shape[0] == 0


def test_models_registered_in_db(trained):
    with dbmod.SessionLocal() as db:
        names = {m.name for m in db.query(ModelVersion).filter(ModelVersion.is_active.is_(True))}
    assert {"clue_classifier_sklearn", "clue_classifier_torch", "lead_ranker", "anomaly_detector"} <= names
    assert registry.active_dir("clue_classifier_torch") is not None


def test_inference_api_and_graceful_failures(client, player: Player, trained):
    service.clear_cache()
    r = player.post("/ml/classify", {"text": "The badge reader logged a swipe at the siding gate at 22:41."})
    assert {p["model"] for p in r["predictions"]} == {"sklearn", "pytorch_textcnn"}
    assert r["category"] in CATEGORIES
    player.post("/ml/classify", {"text": "x"}, expect=422)  # validation
    player.post("/ml/classify", {"text": "a" * 700}, expect=422)


def test_board_notes_get_a_predicted_category(player: Player, trained):
    service.clear_cache()
    item = player.post("/board/items", {"kind": "note", "text": "Bank slip shows a transfer of Rs 3.1 crore", "x": 10, "y": 10},
                       expect=201)
    assert item["predicted_category"] in CATEGORIES


# ============================================================================ leads (no culprit leakage)
def test_lead_features_never_reference_the_solution():
    import ast

    tree = ast.parse(inspect.getsource(leads))
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert not (names & {"accusation", "solution_culprit", "solution_motive", "solution_narrative", "culprit"}), names


def test_lead_ranking_is_independent_of_the_true_culprit(player: Player, trained):
    player.search_everything()
    with dbmod.SessionLocal() as db:
        view = load_view(db, get_owned_session(db, player.user_id, player.sid))
        case = view.case
        model = service._load("lead_ranker")
        base = leads.rank(view, case, model)
        # a case whose "true culprit" is somebody else must produce an identical ranking
        for other in ("meera", "kabir"):
            alt = dataclasses.replace(case, accusation=dataclasses.replace(case.accusation, culprit=other),
                                      solution_culprit=other)
            assert [r["character"] for r in leads.rank(view, alt, model)] == [r["character"] for r in base]
    # presenting scores as guilt is explicitly disclaimed
    out = player.get("/ml/leads")
    assert "never decides the case" in out["disclaimer"]
    assert len(out["ranking"]) == 6 and sorted(r["rank"] for r in out["ranking"]) == [1, 2, 3, 4, 5, 6]
    assert all(0 <= r["priority"] <= 1 for r in out["ranking"])


def test_lead_ranking_moves_with_the_investigation(player: Player, trained):
    before = {r["character"]: r for r in player.get("/ml/leads")["ranking"]}
    assert all(r["features"]["not_interviewed"] == 1 for r in before.values())
    player.talk("kabir", "Where were you all night?")
    after = {r["character"]: r for r in player.get("/ml/leads")["ranking"]}
    assert after["kabir"]["features"]["not_interviewed"] == 0 and after["kabir"]["features"]["unchecked_statements"] == 1


def test_lead_model_beats_or_matches_documented_baseline(trained):
    m = trained["models"]["lead_ranker"]
    assert m["test_auc_model"] >= 0.7
    assert "proxy" in m["note"].lower()


# ============================================================================ anomalies
def test_anomaly_detector_flags_the_synthetic_heartbeat_and_open_session(trained):
    det = service._load("anomaly_detector")
    findings = anomaly.scan_case(det, case_logs.heartbeat_intervals(), case_logs.badge_sessions())
    subjects = [f["subject"] for f in findings]
    assert "CAM-7" in subjects
    assert not any(s.startswith("CAM-") and s != "CAM-7" for s in subjects)  # healthy cameras are not flagged
    assert any("K.RATHORE" in s for s in subjects)
    cam = next(f for f in findings if f["subject"] == "CAM-7")
    assert "exactly zero" in " ".join(cam["reasons"])


def test_anomaly_endpoint_requires_the_log_and_is_framed_as_leads(player: Player, trained):
    assert player.get("/ml/anomalies")["available"] is False
    player.inspect("security_room", "h_access_pc")
    out = player.get("/ml/anomalies")
    assert out["available"] and any(f["subject"] == "CAM-7" for f in out["findings"])
    assert "not proof" in out["disclaimer"]
    assert next(f for f in out["findings"] if f["subject"] == "CAM-7")["person"] is None  # maintenance log not held yet


def test_anomaly_metrics_reported_honestly(trained):
    m = trained["models"]["anomaly_detector"]
    assert m["streams_zscore_baseline"]["recall"] >= 0.9
    assert "synthetic" in m["note"].lower()


def test_stream_features_shape_and_zero_jitter():
    f = anomaly.stream_features([60.0] * 100)
    assert len(f) == len(anomaly.STREAM_FEATURES) and f[2] == 1.0
    g = anomaly.stream_features([60 + 0.4 * ((-1) ** i) for i in range(100)])
    assert g[0] > f[0]


def test_classical_pipeline_serialisable(trained):
    import joblib

    d = registry.active_dir("clue_classifier_sklearn")
    m = joblib.load(d / "model.joblib")
    assert m.predict(["Cash book entry: Rs 50,000 received for stabling the coach."])[0] in CATEGORIES


def test_train_classical_is_seeded():
    s = make_clue_dataset(7, per_template=5)
    tr, va, te = group_split(s, 7)
    a = train_classical(tr, va, te, real_clue_eval_set(), 7)
    b = train_classical(tr, va, te, real_clue_eval_set(), 7)
    assert a.table["tfidf_logreg"]["test"]["macro_f1"] == b.table["tfidf_logreg"]["test"]["macro_f1"]
