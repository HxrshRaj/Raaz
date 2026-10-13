"""Classical clue-category classifiers (scikit-learn): baselines vs a stronger model, with honest evaluation."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC

from .data import CATEGORIES, Sample


def build_models(seed: int = 7) -> dict[str, Pipeline]:
    word = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1, lowercase=True)
    both = FeatureUnion([
        ("w", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, lowercase=True)),
        ("c", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, lowercase=True)),
    ])
    return {
        "majority": Pipeline([("clf", DummyClassifier(strategy="most_frequent"))]),
        "tfidf_nb": Pipeline([("v", TfidfVectorizer(ngram_range=(1, 1), lowercase=True)), ("clf", MultinomialNB(alpha=0.3))]),
        "tfidf_logreg": Pipeline([("v", word), ("clf", LogisticRegression(max_iter=2000, C=6.0, random_state=seed))]),
        "wordchar_svm": Pipeline([("v", both), ("clf", LinearSVC(C=1.0, random_state=seed))]),
    }


def _xy(samples: list[Sample]) -> tuple[list[str], list[str]]:
    return [s.text for s in samples], [s.label for s in samples]


def metrics(y_true: list[str], y_pred: list[str]) -> dict[str, Any]:
    p, r, f, _ = precision_recall_fscore_support(y_true, y_pred, labels=list(CATEGORIES), zero_division=0)
    return {
        "n": len(y_true),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "macro_f1": round(float(f1_score(y_true, y_pred, labels=list(CATEGORIES), average="macro", zero_division=0)), 4),
        "per_class": {c: {"precision": round(float(p[i]), 3), "recall": round(float(r[i]), 3), "f1": round(float(f[i]), 3)}
                      for i, c in enumerate(CATEGORIES)},
        "confusion": confusion_matrix(y_true, y_pred, labels=list(CATEGORIES)).tolist(),
    }


@dataclass
class ClassicalResult:
    models: dict[str, Pipeline]
    table: dict[str, dict[str, Any]]
    best: str


def train_classical(train: list[Sample], val: list[Sample], test: list[Sample], real: list[Sample], seed: int = 7) -> ClassicalResult:
    xt, yt = _xy(train)
    xv, yv = _xy(val)
    xs, ys = _xy(test)
    xr, yr = _xy(real)
    models = build_models(seed)
    table: dict[str, dict[str, Any]] = {}
    for name, m in models.items():
        t0 = time.perf_counter()
        m.fit(xt, yt)
        fit_s = time.perf_counter() - t0
        table[name] = {
            "fit_seconds": round(fit_s, 3),
            "val": metrics(yv, list(m.predict(xv))),
            "test": metrics(ys, list(m.predict(xs))),
            "real_ood": metrics(yr, list(m.predict(xr))),
        }
    # model selection uses ONLY the validation split
    best = max(table, key=lambda k: table[k]["val"]["macro_f1"])
    return ClassicalResult(models, table, best)


def top_features(model: Pipeline, n: int = 8) -> dict[str, list[tuple[str, float]]]:
    """Most influential n-grams per class for linear models with a plain TF-IDF vectoriser."""
    clf = model.named_steps["clf"]
    v = model.named_steps.get("v")
    if not hasattr(clf, "coef_") or not hasattr(v, "get_feature_names_out"):
        return {}
    names = np.asarray(v.get_feature_names_out())
    out = {}
    for i, c in enumerate(clf.classes_):
        idx = np.argsort(-clf.coef_[i])[:n]
        out[str(c)] = [(str(names[j]), round(float(clf.coef_[i][j]), 3)) for j in idx]
    return out
