# Known limitations and future improvements

**Scope honesty.** This is a complete, playable vertical slice with one case. It is not a finished commercial game.

## Not verified in the build environment

PostgreSQL (including the migration), Redis, Docker/Compose, GitHub Actions, MLflow, and any live LLM provider were not
available; those code paths are written and tested with mocks/SQLite only. Expect to fix small issues on first real use.
No load, accessibility-audit or security-penetration testing was done.

## Product

* One case (*Aakhri Gaadi*); the engine and authoring format are generic, but only one case package exists.
* Player free text is mapped to facts by weighted topic matching (plus a RAG fallback). Unusual phrasing may surface the
  wrong fact or a deflection. With an LLM the *wording* is free, but fact *selection* is still this matcher.
* Fallback dialogue is authored per fact, so scripted replies repeat when you repeat a question (by design).
* Hindi/Hinglish is limited to selected phrases; the UI is English only.
* Art is procedural SVG (scenes, portraits) with CSS rain/flicker/pulse. Audio is synthesised ambience, not music.
* Accessibility: keyboard operation, labelled controls, reduced-motion support and live regions are implemented and the
  board is operable with arrow keys. No screen-reader pass was performed; colour contrast was only spot-checked.

## AI / ML

* Dialogue quality with a real LLM is untested here; the leak scan is phrase-based (`leak_markers`), so a paraphrased
  leak could pass. Structural defences (no secrets in prompts) are the primary safeguard.
* RAG uses a hashing embedder (no learned semantics) and no pgvector index; fine at this scale only.
* The PyTorch model underperforms the classical baselines on the available data (documented in ML.md). The lead-ranking
  label is a simulation proxy; anomaly detection is evaluated on synthetic faults only.
* Agent runs are deterministic pipelines (no LLM planning) and don't resume after a process restart.
* Cost tracking is an estimate, and only if prices are configured.

## Engineering

* Background jobs are an in-process pool, not Celery; Redis is only used for rate limiting.
* No streaming (SSE/WebSocket) dialogue; no multiplayer.
* JWT in `localStorage`; no email verification, password reset or MFA.
* "Supports / clears" semantics are authored per evidence item (`bears_on`); a new case needs them authored too.

## Ideas

Second case and a case-select screen · pgvector and a learned embedder · LLM planner for the agent graph using the same
typed tools · SSE streaming of NPC replies · cookie-based auth · voice lines · richer scene art · difficulty modes
(fewer hints, stricter scoring) · shareable replay of a solved case's reasoning board.
