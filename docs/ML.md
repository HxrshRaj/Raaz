# Machine learning & deep learning

Reproduce everything below with:

```bash
cd backend && python -m app.cli train-ml            # ≈ 25 s on CPU (add --no-torch to skip PyTorch)
```

Artifacts go to `RAAZ_ARTIFACTS_DIR` (git-ignored), experiments to the `ml_experiments`/`model_versions` tables (and
MLflow if `RAAZ_MLFLOW_TRACKING_URI` is set and `mlflow` is installed — that mirror was **not** exercised here).
Dev workbench UI: `/workbench` (enabled by default in dev, disabled in prod).

**Read this first:** the numbers are small-data results on a *synthetic* dataset plus a tiny hand-labelled real set.
They show the pipeline works and how models compare; they do **not** show real-world accuracy. ML never decides the
culprit.

## A. Clue classification (6 categories)

*Task:* classify an evidence description as timeline / financial / access / testimony / physical / digital. *Used for:*
suggested category tags on the player's own board notes (`ML guess: …`) and in the workbench.

*Data (`clues-v1`)*: 6 × 14 hand-written sentence templates filled with random slot values → 716 samples
(hash recorded). **Splits are by template group** (train 466 / val 103 / test 147): no template or sentence appears in
more than one split (asserted in `tests/test_ml.py`). A separate **real OOD set** = the case's own 55 authored
evidence items with their authored categories.

*Measured results (macro-F1, seed 7):*

| Model | Validation | Test (synthetic, unseen templates) | Real OOD (n=55) |
|---|---|---|---|
| majority baseline | 0.050 | 0.052 | 0.038 |
| TF-IDF + Multinomial NB | 0.602 | 0.717 | 0.684 |
| TF-IDF + Logistic Regression | 0.559 | 0.745 | 0.657 |
| word+char TF-IDF + Linear SVM | **0.716** | **0.758** | **0.708** |
| **PyTorch TextCNN** | 0.682 | 0.611 | 0.454 |

The classical model is **selected on validation only** (`wordchar_svm`); test/OOD are never used for selection.

*Honest reading:* the deep model did **not** beat the classical baselines here — with ~470 training sentences a
61k-parameter CNN overfits template surface forms and generalises worst to the real items. This is the expected
outcome on such a small dataset and is reported as measured. Label noise is also real: several templates are
legitimately ambiguous (a "log" can be digital or access; testimony often mentions times).

### PyTorch component (`ml/torch_clf.py`)

TextCNN: Embedding(64) → Conv1d (kernels 2/3/4 × 64 filters) → global max-pool → dropout 0.4 → Linear(6). Number/time
normalisation tokens, vocabulary from the training split, `<unk>` for unseen words. Adam (lr 3e-3, wd 1e-4), batch 32,
early stopping on validation loss (patience 6), best-epoch checkpoint restored, single-thread seeded training
(same seed ⇒ identical loss curve — tested), artifacts: `model.pt` (state dict), `vocab.json`, `config.json`,
`metrics.json`; inference through `TorchPredictor.predict_proba` (round-trip tested). CPU only. This is a separate
model from the dialogue LLM; **no language model is trained**.

## B. Lead prioritisation ("Where to look next")

*Purpose:* rank people by how actionable the next step with them is. It is labelled **lead priority**, never guilt, and
the UI says so.

*Features* (only what the player can see; no character identity, no culprit, no solution): motive / presence / meeting
evidence counts, contradicted claims, statements not yet tested, alibi established, not yet interviewed, connected
evidence, record anomalies. A test (`test_lead_features_never_reference_the_solution`) inspects the module's AST and
`test_lead_ranking_is_independent_of_the_true_culprit` swaps the case's culprit and requires an identical ranking.
Ties are broken by a per-session hash so list order can't hint at anything.

*Training:* logistic regression on 1,500 simulated investigation states × 6 people. *Label (proxy):* "an
unestablished contradiction about this person exists and the player could act on it now (holds one side, or hasn't
interviewed them)". The label is derived from case structure — a limitation: it measures agreement with that proxy,
not usefulness to players.

*Measured (held-out simulated states, AUC):* model **0.849** vs transparent hand-weighted heuristic **0.807**.

## C. Anomaly detection over logs

*Data:* case-specific machine logs (`cases/aakhri_gaadi/logs.py`): heartbeat intervals for seven cameras (CAM-7 is
exactly 60.000 s — a software keep-alive) and badge sessions. *Detectors:* IsolationForest (trained on clean
synthetic streams/sessions, contamination 0.03) vs a z-score baseline; reasons are generated per finding.

*Measured on held-out **synthetic** faults (injected "too perfect", gap, drift, open-session-overlap):*

| Detector | Precision | Recall | F1 |
|---|---|---|---|
| Streams — IsolationForest | 0.83 | 1.00 | 0.91 |
| Streams — z-score baseline | 0.93 | 1.00 | **0.96** |
| Badge sessions — IsolationForest | 0.78 | 0.49 | 0.60 |

The simple baseline beats IsolationForest on streams; both are shown. Findings are presented as *leads that need an
explanation*, e.g. "interval jitter is exactly zero — unlike every other device". Only visible once the access log is
collected, and person attribution requires the maintenance log.

## MLOps

Dataset hash + version recorded per run · experiments/model versions in SQL · deterministic seeds · artifacts
outside Git · `/metrics` has request latency histograms, LLM/NPC/agent/job counters (measured, in-process, reset on
restart) · estimated LLM cost only if you configure prices (labelled estimate).
