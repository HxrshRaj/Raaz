# API

Base path `/api/v1`. Interactive OpenAPI docs: `GET /api/docs` (disabled when `RAAZ_ENV=prod`); schema at
`/api/openapi.json`. Operational endpoints outside the versioned API: `GET /health` (liveness), `GET /ready`
(DB reachable), `GET /metrics` (Prometheus text; requires `X-Metrics-Token` if `RAAZ_METRICS_TOKEN` is set).

## Conventions

* **Auth:** `Authorization: Bearer <JWT>` from `/auth/register`, `/auth/login` or `/auth/guest`.
* **Ownership:** every `/sessions/{id}/…` route returns **404** unless the session belongs to the caller.
* **Errors** always use one envelope (never a stack trace):
  ```json
  {"error": {"code": "location_locked", "message": "You have no reason to go there yet.", "details": {}, "request_id": "ab12…"}}
  ```
  Status codes: 400 domain rule, 401 unauthenticated, 403 forbidden/locked, 404 not found (or not yours), 409 conflict
  (`case_closed`, `still_answering`, `concurrent_accusation`, `agent_busy`), 422 validation (unknown fields are rejected),
  429 rate limited (`Retry-After`), 503 models not trained.
* **Idempotency:** `POST …/accusation` honours `Idempotency-Key`; replays return the stored response.
* **Request ids:** send `X-Request-ID` or one is generated; it is echoed in the response and error body.
* **Rate limits:** per-user buckets (general, LLM-backed, agents, training) and per-IP for auth endpoints.
* **No solution data:** responses contain only what the player has earned. `tests/test_engine_flow.py::
  test_no_public_endpoint_leaks_the_solution` sweeps every read endpoint after exploring everything.

## Endpoints (57)

| Method | Path | Area |
|---|---|---|
| GET | `/sessions/{session_id}/investigations` | assistant |
| POST | `/sessions/{session_id}/investigations` | assistant |
| GET | `/sessions/{session_id}/investigations/{run_id}` | assistant |
| POST | `/sessions/{session_id}/investigations/{run_id}/cancel` | assistant |
| GET | `/sessions/{session_id}/nazar` | assistant |
| POST | `/sessions/{session_id}/nazar` | assistant |
| POST | `/auth/guest` | auth |
| POST | `/auth/login` | auth |
| GET | `/auth/me` | auth |
| POST | `/auth/register` | auth |
| GET | `/cases` | game |
| GET | `/progress` | game |
| GET | `/sessions` | game |
| POST | `/sessions` | game |
| GET | `/sessions/{session_id}` | game |
| POST | `/sessions/{session_id}/accusation` | game |
| GET | `/sessions/{session_id}/accusation/history` | game |
| GET | `/sessions/{session_id}/accusation/options` | game |
| GET | `/sessions/{session_id}/board` | game |
| POST | `/sessions/{session_id}/board/items` | game |
| DELETE | `/sessions/{session_id}/board/items/{item_id}` | game |
| PATCH | `/sessions/{session_id}/board/items/{item_id}` | game |
| POST | `/sessions/{session_id}/board/links` | game |
| DELETE | `/sessions/{session_id}/board/links/{link_id}` | game |
| GET | `/sessions/{session_id}/contradictions` | game |
| POST | `/sessions/{session_id}/contradictions/check` | game |
| GET | `/sessions/{session_id}/dossiers` | game |
| GET | `/sessions/{session_id}/dossiers/{char_key}` | game |
| GET | `/sessions/{session_id}/events` | game |
| GET | `/sessions/{session_id}/evidence` | game |
| GET | `/sessions/{session_id}/evidence/timestamps` | game |
| GET | `/sessions/{session_id}/evidence/{ev_key}` | game |
| POST | `/sessions/{session_id}/evidence/{ev_key}/examine` | game |
| GET | `/sessions/{session_id}/hypotheses` | game |
| POST | `/sessions/{session_id}/hypotheses` | game |
| POST | `/sessions/{session_id}/hypotheses/evaluate` | game |
| DELETE | `/sessions/{session_id}/hypotheses/{hid}` | game |
| PUT | `/sessions/{session_id}/hypotheses/{hid}` | game |
| GET | `/sessions/{session_id}/locations` | game |
| GET | `/sessions/{session_id}/locations/{loc_key}` | game |
| POST | `/sessions/{session_id}/locations/{loc_key}/hotspots/{hotspot_key}/inspect` | game |
| POST | `/sessions/{session_id}/reopen` | game |
| GET | `/sessions/{session_id}/reports` | game |
| GET | `/sessions/{session_id}/timeline` | game |
| POST | `/sessions/{session_id}/timeline` | game |
| DELETE | `/sessions/{session_id}/timeline/{entry_id}` | game |
| GET | `/ml/workbench` | ml |
| GET | `/ml/workbench/jobs/{job_id}` | ml |
| POST | `/ml/workbench/predict` | ml |
| POST | `/ml/workbench/train` | ml |
| GET | `/sessions/{session_id}/ml/anomalies` | ml |
| POST | `/sessions/{session_id}/ml/classify` | ml |
| GET | `/sessions/{session_id}/ml/leads` | ml |
| GET | `/sessions/{session_id}/conversations` | npc |
| GET | `/sessions/{session_id}/conversations/{char_key}` | npc |
| POST | `/sessions/{session_id}/conversations/{char_key}/messages` | npc |
| GET | `/system/info` | npc |

`GET /system/info` reports whether an LLM provider is configured. The `/ml/workbench*` endpoints are a developer
tool: enabled by default in `dev`/`test`, **disabled in `prod`** unless `RAAZ_ML_WORKBENCH_ENABLED=true`.

## Notable payloads

| Call | Request | Response highlights |
|---|---|---|
| `POST /sessions` | `{case_id, mode: standard|demo}` | overview: progress, locations (locked ones show only a hint), briefing |
| `POST …/hotspots/{h}/inspect` | – | `narration`, `new_evidence[]`, `already_found[]`, `unlocked_locations[]` |
| `POST …/conversations/{c}/messages` | `{text, evidence_key?}` | `npc_message`, `state{mood,trust band,turns}`, `generation{mode: llm|fallback, reason, label}`, `new_evidence`, `contradictions`, `unlocked_locations` |
| `POST …/contradictions/check` | `{a, b}` | `established`, `newly_found`, `contradiction` |
| `POST …/board/links` | `{from_item, to_item, relation, note}` | `link.validated`, optional `contradiction` |
| `POST …/accusation` | `{culprit, motive, event_sequence[], evidence[], contradictions[]}` | `verdict`, `score`, `criteria[]` (rubric rows), `evidence_annotations`, `next_steps`, `solution` *only when the case is closed* |
| `POST …/nazar` | `{question, hint_level: 1|2|3}` | `reply`, `structured{observed, interpretations, speculation, suggested_questions}`, `sources[]`, `hint_cost`, `mode` |
| `POST …/investigations` | `{question}` → `202 {id}` | poll `GET …/investigations/{id}` for `status`, `steps[]`, `result` |
