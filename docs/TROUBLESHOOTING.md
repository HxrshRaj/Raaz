# Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Frontend shows "Can't reach the server" | Backend not running on :8000, or `VITE_API_PROXY` points elsewhere. Start `uvicorn app.main:app --port 8000`. |
| `401` everywhere after restarting the backend | Token expired or `RAAZ_JWT_SECRET` changed → sign in again. Keep the secret stable. |
| API exits at start with "RAAZ_JWT_SECRET must be a strong random secret" | `RAAZ_ENV=prod` requires a 32+ char, non-placeholder secret. |
| Suspects always answer with authored lines and a "Scripted fallback" label | No LLM provider configured (expected). Set `RAAZ_LLM_PROVIDER` + key. If configured, check the reply's `generation.reason` (`provider_auth`, `provider_timeout`, `output_rejected`, `token_budget_exhausted`). |
| "Where to look next" says *transparent heuristic baseline*, or board notes have no "ML guess" | ML models aren't trained yet: `python -m app.cli train-ml`. |
| `models_not_trained` (503) from `/ml/classify` | Same as above. |
| PyTorch model missing / `ModuleNotFoundError: torch` | `pip install torch --index-url https://download.pytorch.org/whl/cpu`, or train with `--no-torch`. |
| `database is locked` on SQLite | Heavy parallel writes in dev; use PostgreSQL for concurrent play (WAL + 30 s busy timeout are already set). |
| `409 still_answering` when chatting | Two messages to the same suspect overlapped (for example a double-click). Wait for the reply. |
| `409 agent_busy` | One investigation per session at a time; wait or cancel it. |
| `429 rate_limited` | Slow down, or raise `RAAZ_RATE_LIMIT_PER_MIN` / `RAAZ_LLM_RATE_LIMIT_PER_MIN` for load tests. |
| Can't enter a place | It is locked until evidence points there; the Office "Places" panel shows which are locked. |
| Times don't line up on the Timeline | Station systems keep the (slow) platform clock; phones and banks keep real time. Find how the clocks relate and conversions appear. |
| Alembic: "Target database is not up to date" | `alembic upgrade head` (the container does this automatically). |
| `vite build` warns about chunk size | The charting library lives in the lazily loaded ML workbench chunk; the warning is informational. |
| Port 5173/8000 in use | Change `server.port` in `vite.config.ts` or uvicorn `--port`, and update `VITE_API_PROXY`. |
| Fonts look plain | Fonts load from Google Fonts; offline you get serif/system fallbacks (layout is unaffected). |
| No sound | Sound is off by default and browsers need a user gesture: toggle it on the title screen or in Settings. |
