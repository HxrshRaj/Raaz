# Testing guide

```bash
# backend (≈ 85 s)  — SQLite in a throwaway temp dir; LLM providers are mocked; no network
cd backend && pip install -r requirements-dev.txt && pip install torch --index-url https://download.pytorch.org/whl/cpu
pytest                      # all 117 tests
ruff check app tests && mypy app --ignore-missing-imports
python -m app.cli validate-case

# frontend
cd frontend && npm ci && npm run typecheck && npm test && npm run build
```

Run against PostgreSQL: `RAAZ_TEST_DATABASE_URL=postgresql+psycopg://… pytest` (the CI `backend-postgres` job does this;
**not executed by the author**).

## What is covered

| File | Focus |
|---|---|
| `test_engine_flow.py` | case initialisation, locked places, discovery + unlock chain, gated hotspots, examine once, clock conversion hidden until known, contradiction rules, **save/resume**, **no endpoint leaks the solution** |
| `test_npc.py` (20) | scripted-fallback honesty, evidence-presentation validation, lie → statement → contradiction, secrets stay shut without evidence, knowledge boundary, trust gate, staged confession, **prompt contains only permitted knowledge**, leak rejection → fallback, invalid JSON, meta-language, provider timeout/auth handling, **prompt-injection deflection with no model call**, memory in next prompt, token budget, cross-player authorization, concurrent messages |
| `test_accusation.py` | **case solvable end-to-end via public API**, insufficient-evidence verdict, wrong-suspect consequences & evidence-based report, 3 strikes → cold → reopen, can't cite evidence you don't hold, idempotency, concurrent accusations, event order doesn't leak chronology, sequence scoring |
| `test_board_timeline.py` | timeline validation (source mismatch, mixed clocks, impossible travel with clock offset), board validation against the record, contradiction via board link (once), move/delete/cascade/isolation, hypothesis evaluation |
| `test_assistant.py` | Nazar (knows nothing it wasn't given, hint escalation, never names culprit, observed/interpretation/speculation, source ACL, injection, LLM rejection), **RAG ACL** (evidence, character, session scoping), retrieval-quality guard, **agents** (trace, only-held content, tool authorization, iteration limit, timeout, cancellation, node failure, isolation) |
| `test_ml.py` | label integrity, reproducible data, **no template/text leakage across splits**, preprocessing, classical vs majority baseline, selection on validation only, PyTorch early-stopping/checkpoint/round-trip/**seeded reproducibility**, model registry, inference API, **lead features never reference the solution / ranking independent of culprit**, anomaly detection |
| `test_security_ops.py` | register/login/token tampering/expiry, bcrypt hashing, validation, **other players can't touch any route**, no forged truth via bodies, rate limits (429 + `Retry-After`), CORS, headers & error envelope, OpenAPI has no case content, audit log, metrics, **DB constraints**, **parallel inspections discover once**, background-job failure/retry/give-up, **Alembic migration matches models** |
| `test_e2e_acceptance.py` | the 12-step journey: new investigation → enter station → clues → interviews → present evidence → contradiction → board → Nazar → theory → accusation → result → **leave & resume** with identical state |
| frontend `game.test.tsx` (16) | navigation, loading/error/retry, signed-out redirect, inventory filter + examine, contradiction test, hotspot search, locked place, interrogation (free text, present evidence + contradiction toast, 409 handling, loading skeleton), board pin/connect, resume from title and archive, API client error handling |

## Verification log

Commands actually executed in the build environment (Windows 11, Python 3.11.9, Node 24) and their outcome:

| Command | Result |
|---|---|
| `pytest` (backend) | **117 passed** |
| `ruff check app tests` | clean |
| `mypy app --ignore-missing-imports` | no issues (64 files) |
| `python -m app.cli validate-case` | `aakhri_gaadi@1.0.0: OK` |
| `alembic upgrade head` + `alembic check` (SQLite, inside a test) | passes, no drift |
| `python -m app.cli train-ml` | models trained; metrics in [ML.md](ML.md) |
| `python -m app.cli rag-eval` | recall@3 0.958, MRR 0.896 |
| `npm run typecheck` / `npm test` / `vite build` | clean / **16 passed** / built |
| Manual browser run (dev servers) | title → guest → new case → office → saloon search (evidence found, new hotspots appear) → interrogation (statement recorded; evidence presented → "Contradiction exposed!") → inventory → board pin + validated link; mobile layout checked |
| `docker compose config` | parses |

**Not executed (be sceptical of these):** PostgreSQL (incl. the Alembic migration on PG), Redis, `docker compose up`,
image builds, the GitHub Actions workflow, any live Anthropic/OpenAI call, MLflow, load/performance testing, screen
reader testing.
