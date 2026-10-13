# RAAZ (राज़): The AI Detective

> *Har raaz ke peeche ek kahaani hai.* — Every secret has a story behind it.

RAAZ is an Indian-noir detective game. You investigate a death in a locked private carriage at **Devgarh
Junction** on a monsoon night: search locations, examine evidence, interrogate six people in your own words,
catch contradictions, pin clues on a board, reason about a clock that runs twelve minutes slow, and finally
make an accusation that is scored by a transparent, evidence-based rubric.

The first (and currently only) case is **Aakhri Gaadi — The Last Train**.

**The central design rule:** the *truth* of a case is fixed and lives only on the server. An LLM may *word* what
a character says, but it never decides what is true, never sees the solution, and never scores your
accusation. See [Who decides what](#who-decides-what).

| Layer | Status |
|---|---|
| Deterministic game engine, case, evidence, contradictions, timeline, board, accusation | ✅ implemented & tested |
| NPC dialogue: engine-planned, leak-checked, **scripted fallback when no LLM is configured** | ✅ implemented & tested with mocked providers; 🟡 not exercised against a live provider in this build |
| Nazar (assistant), hybrid RAG with access control, retrieval eval | ✅ |
| Agent investigations (explicit state graph, typed permissioned tools) | ✅ |
| ML: clue classifiers, lead ranking, anomaly detection; PyTorch TextCNN | ✅ trained & evaluated (results are modest — see [docs/ML.md](docs/ML.md)) |
| React/TypeScript frontend | ✅ type-checked, built, 16 tests, driven manually in a browser |
| PostgreSQL, Redis, Docker Compose, GitHub Actions | ⛔ **authored but not executed here** (no Postgres/Redis/Docker engine available) — see [Status & verification](#status--verification) |

## Quick start (no services needed)

Requirements: Python 3.11+, Node 20+. Everything below runs on a laptop; the database defaults to SQLite.

```bash
# 1) backend
cd backend
python -m venv .venv && source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pip install torch --index-url https://download.pytorch.org/whl/cpu   # optional: only for the PyTorch model
python -m uvicorn app.main:app --reload --port 8000        # OpenAPI docs at http://localhost:8000/api/docs

# 2) frontend (second terminal)
cd frontend
npm install
npm run dev                                                 # http://localhost:5173  (proxies /api to :8000)
```

Open <http://localhost:5173>, choose **New Case → Play as guest**.

Optional extras:

```bash
python -m app.cli train-ml        # train & evaluate the ML models (≈25 s on CPU); powers "Where to look next" + board note tags
cp .env.example .env              # then edit: add an LLM key for generated NPC dialogue (see below)
```

### NPC dialogue: with and without an LLM

* **No key (default):** suspects answer with *authored* lines selected by the game engine. The UI says so on the
  interrogation screen ("Scripted fallback — … not generated text") and tags each reply `scripted`. The whole
  game is playable and solvable this way.
* **With a key:** set `RAAZ_LLM_PROVIDER=anthropic` + `RAAZ_ANTHROPIC_API_KEY=…`, or `RAAZ_LLM_PROVIDER=openai`
  + `RAAZ_OPENAI_API_KEY=…` (optionally `RAAZ_OPENAI_BASE_URL` for any OpenAI-compatible server). Replies are then
  generated *inside the engine's plan*, schema-checked and scanned for leaks; any rejected/failed generation
  falls back to scripted lines and is labelled as such. Keys are read from the environment only.

### Docker (authored, not yet run by the author)

```bash
cp .env.example .env     # set POSTGRES_PASSWORD and RAAZ_JWT_SECRET (>= 32 random chars)
docker compose up --build
# web: http://localhost:8080   api: internal (proxied under /api)
```

## How to play (spoiler-free)

1. **Office** — read the briefing, see progress, leads, and run an *Investigation desk* analysis.
2. **Explore** — click glowing markers in each location. Examine items in the **Evidence** inventory; details hide in
   the examination notes. Some places unlock only because of what you find.
3. **Suspects → Interrogate** — type questions freely, or **Present** an item and watch the reaction. Characters
   remember what you showed them and what they told you. Trust and stress shift with your manner.
4. **Contradictions** — mark two items that conflict (Evidence tab), present them in an interrogation, or draw a
   *contradicts* link on the **Board**. The server only accepts conflicts the record actually supports.
5. **Timeline** — place events. Station systems and phones keep different clocks; once you learn how they relate,
   times convert and impossible journeys are flagged.
6. **Nazar** (top bar) — three hint levels (nudge → evidence hint → analysis); it labels what is observed vs.
   interpreted vs. speculation and never names the culprit.
7. **Accuse** — choose suspect, motive, order the night's events, cite evidence and contradictions. You get
   three attempts; a wrong accusation costs reputation and the accused stops trusting you. A closed case reveals
   what happened.

## Who decides what

| Concern | Decided by | Never by |
|---|---|---|
| Culprit, motive, timeline, evidence, who knows what, contradictions, unlocks, scoring | **Case package + deterministic engine** (server-side) | LLM, ML, agents, client |
| *How a suspect words an answer* | LLM (when configured) inside a per-turn plan; otherwise authored lines | — |
| *Where to look next* (lead priority), clue-category tags, log anomalies | ML models — advisory, labelled as leads | the accusation |
| Multi-step analysis ("does X's alibi hold?") | Agent graph with typed read-only tools — it *proposes*; you confirm | canonical truth |

Details: [docs/AI_AND_NPC.md](docs/AI_AND_NPC.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Repository map

```
backend/
  app/
    cases/        private case packages (aakhri_gaadi: world, evidence, characters, rules, logs) + validator
    engine/       deterministic game: state, clock rules, discovery, contradictions, timeline, board, accusation
    npc/          dialogue planner, LLM providers, safety (injection/leak checks), scripted fallback
    nazar/        assistant          rag/   embeddings, BM25, ACL retrieval, ingestion, evaluation
    agents/       explicit state graph + typed tools    ml/   datasets, sklearn, PyTorch, leads, anomaly, registry
    api/v1/       FastAPI routers   models.py  SQLAlchemy 2.x   jobs.py  persisted background jobs
  alembic/        migrations        tests/   117 tests
frontend/         React + TS + Vite + Tailwind SPA (src/pages, src/components, src/lib, src/test)
docs/             architecture, schema, API, AI/NPC, case authoring, ML, RAG & agents, testing, deployment, security …
```

## Documentation

[Implementation plan & checklist](IMPLEMENTATION_PLAN.md) · [Architecture](docs/ARCHITECTURE.md) ·
[Database](docs/DATABASE.md) · [API](docs/API.md) · [AI & NPC](docs/AI_AND_NPC.md) ·
[Case authoring](docs/CASE_AUTHORING.md) · [ML & deep learning](docs/ML.md) · [RAG & agents](docs/RAG_AND_AGENTS.md) ·
[Testing](docs/TESTING.md) · [Deployment](docs/DEPLOYMENT.md) · [Security](docs/SECURITY.md) ·
[Troubleshooting](docs/TROUBLESHOOTING.md) · [Known limitations](docs/LIMITATIONS.md)

## Status & verification

Commands actually executed during the build and their results are recorded in
[docs/TESTING.md](docs/TESTING.md#verification-log). In short: backend `pytest` (117 tests), `ruff`, `mypy`; frontend
`tsc`, `vitest` (16 tests) and a production `vite build`; the ML training/evaluation CLI; a manual browser
walk-through of title → guest login → new case → exploration → interrogation (with evidence presentation and a
contradiction) → board linking. **Not executed:** PostgreSQL, Redis, Docker/Compose, the GitHub Actions workflow,
any live LLM provider. They are written to be correct and are called out as unverified wherever relevant.

## License & authorship

All code, content and artwork in this repository are original to this project and owned by its author. No
third-party game assets are used; audio is synthesised at runtime. Third-party libraries retain their own licenses.
