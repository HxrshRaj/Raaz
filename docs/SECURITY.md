# Security notes

## Threat model in one paragraph

Players are untrusted: they can craft requests, try to read other people's investigations, try to extract the solution
from NPCs/Nazar/agents, and try to inject instructions through chat text. The server is trusted; the LLM is
**semi-trusted** (it can hallucinate or be steered), so it is given no secrets and its output is validated.

## Controls and where they are tested

| Risk | Control | Test |
|---|---|---|
| Solution exposure | Case package is server memory only; catalog tables hold names/categories; responses are projections; OpenAPI contains no case content; event & character lists don't leak order/identity | `test_no_public_endpoint_leaks_the_solution`, `test_openapi_exposes_no_case_content`, `test_event_list_does_not_leak_chronology`, `test_lead_ranking_is_independent_of_the_true_culprit` |
| Cross-player access (IDOR) | One dependency resolves sessions by `(id, user_id)`; 404 for missing and foreign alike; every child lookup (board item, run, entry) re-checks `session_id` | `test_player_cannot_touch_another_players_state_through_any_route`, board/agent/timeline isolation tests |
| Hidden evidence via direct calls | Evidence endpoints/examine/present/board/accusation require the item to be in the player's discoveries; unknown vs not-yours indistinguishable | `test_cannot_examine_or_read_undiscovered_evidence`, `test_cannot_present_evidence_you_do_not_hold` |
| Forged case truth | Request models forbid unknown fields; no endpoint accepts verdicts/scores | `test_cannot_forge_case_truth_via_request_bodies` |
| Auth | bcrypt (cost 12; >72-byte passwords rejected, not truncated), HS256 JWT with expiry, strong secret enforced in prod (`>= 32` chars, no placeholder), generic registration/login errors | `test_register_login_me_flow`, `test_passwords_are_hashed…`, `test_protected_routes_need_a_valid_token` |
| Brute force / abuse | Per-IP limits on auth, per-user limits on API/LLM/agents/training; 429 with `Retry-After` | `test_rate_limit_returns_429…`, `test_login_is_ip_rate_limited` |
| Injection (SQL) | SQLAlchemy parameterised access only; LLM output is never executed or used in queries; agents have no SQL/shell tool | `test_tools_enforce_permissions` |
| Prompt injection | Player text sanitised + pattern scan → deflection without calling the model; prompts delimit untrusted text and contain no secrets; retrieved text stripped of imperative lines; Nazar/NPC outputs scanned | `test_prompt_injection_is_deflected…`, `test_nazar_injection_deflected` |
| Output leakage | Leak-marker scan of every unrevealed fact across *all* characters, schema validation, meta-language & markup rejection → labelled fallback | `test_llm_reply_that_leaks_is_rejected…` |
| Agent abuse | Typed args (`extra=forbid`), per-tool permission checks, bounded iterations/time, one active run/session, no write tools, cancel | `test_tools_enforce_permissions`, iteration/timeout/cancel tests |
| Races (double-spend a clue/attempt) | Atomic upserts, conditional updates, optimistic versions, idempotency keys | parallel inspect/examine/accuse/message tests |
| CORS / headers | Explicit origin allow-list, no credentials, allowed headers limited; `nosniff`, `no-referrer`, `no-store`; nginx adds `X-Frame-Options` | `test_cors_is_restricted`, `test_security_headers…` |
| Error leakage | One envelope, no stack traces, request ids | `test_security_headers_request_id_and_error_envelope` |
| Secrets | Environment only (`RAAZ_*`), `.env` git-ignored, `.env.example` has placeholders; log formatter redacts keys named password/token/secret/api_key | – |
| Auditability | `audit_events` for register/login/failed login/guest/session create/reopen/accusation/agent start | `test_audit_log_records_sensitive_actions` |
| Resource exhaustion | request-size limits via field bounds (600-char chat, 400-char agent question, 80 evidence max), board/timeline/hypothesis caps, per-conversation token budget, training endpoint rate-limited & off in prod | validation tests |

## Known gaps / choices (be aware)

* The SPA stores the JWT in `localStorage` (simple, XSS-exposed). An `HttpOnly` cookie + CSRF protection would be
  stronger; the CSP is not set by the API (add one at your reverse proxy).
* Guest accounts are anonymous (creation is limited to 20/min per IP); disable them with `RAAZ_ALLOW_GUEST=false`.
* Per-IP limits use the client address uvicorn reports. Behind a reverse proxy, run uvicorn with `--proxy-headers` and
  `--forwarded-allow-ips` set to your proxy (the provided Dockerfile trusts `*` because the API port is not published).
* No email verification, password reset, or MFA.
* `/metrics` is open unless `RAAZ_METRICS_TOKEN` is set — set it or keep the port internal.
* Pickle is used to load our own ML artifacts (`lead_ranker`, `anomaly_detector`); never place untrusted files in
  `RAAZ_ARTIFACTS_DIR`.
* The injection detector is pattern-based and can be evaded; the real defences are structural (no secrets in prompts,
  validated outputs, engine-owned truth).
* Not penetration-tested; dependency vulnerability scanning is not wired into CI.
