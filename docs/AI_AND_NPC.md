# AI & NPC architecture

## Four kinds of "intelligence", kept apart

| Kind | Where | May decide | May not decide |
|---|---|---|---|
| **Canonical game logic** | `cases/`, `engine/` | everything about truth, access, rules, scoring | – |
| **AI-generated dialogue** | `npc/` (+ optional LLM) | wording and tone of a reply | which facts exist, which may be said, trust/stress, evidence granted, contradictions |
| **ML recommendations** | `ml/` | advisory rankings/tags/anomalies | culprit, scoring |
| **Agent analysis** | `agents/`, `nazar/` | summaries/proposals over the player's own evidence | canonical truth; consequential actions |

## The NPC model

Each `Character` has a persona, speech style, relationships, base trust/stress/defensiveness and a list of **Facts**.
A fact separates three things:

```text
text          what the character actually knows/believes          (server only; never sent to a client or put in a prompt unless voiced)
public_line   what they say while the gate is closed (may be a lie; public_truthful says whether)
reveal_line   what they say once the gate opens
gate          trust_min · stress_min · evidence_any (need_count) · evidence_all · requires_revealed · min_turns · trust_bypass
```

So deception, incompleteness, honest mistakes and hearsay (`kind`: firsthand/hearsay/belief) are *data*. Not everyone
lies: Gopal and Meera's purpose are honest; Hari lies to protect his career, not to hide a killing; Kabir lies to hide
negligence; Tanvi to protect a source; one person lies because he is guilty.

### Knowledge boundary

Prompts are assembled **per character** from: persona, current mood/trust band, *only the lines that character has
already said to the player*, and the *beats allowed this turn*. Secrets that have not been voiced are never in the
prompt, so there is nothing for a model to leak. `tests/test_npc.py::test_prompt_contains_only_what_the_character_may_know`
and `…::test_unrevealed_secret_text_never_enters_rohans_prompt` assert this on the actual prompt text.

### One turn

1. **Validate** — presented evidence must be in the player's inventory (404 otherwise, same as a nonexistent key).
2. **Sanitise & scan** player text for injection patterns (`ignore previous instructions`, fake tags, "reveal the
   solution", …). Flagged turns get an in-character deflection and **no LLM call**.
3. **Plan (deterministic)**
   * tone → trust/stress deltas (polite helps; accusations raise stress, scaled by the character's defensiveness);
   * fact selection: weighted topic match (generic words like "adrian" count 0.4, specific ones 1.0, threshold 1.0),
     boosted by evidence that appears in a fact's gate; RAG similarity only as a last resort; open-ended prompts
     ("tell me what happened") surface `volunteer` facts;
   * for each fact: gate open → *reveal*; closed → *public* line (statement evidence is recorded, e.g. "Rohan: 'I took
     the 10:15 Kosi'") or a deflection; **staging:** a fact whose prerequisite was revealed *this* turn waits for the next;
   * contradictions triggered by presenting evidence to the person they are about; evidence/testimony to grant.
4. **Generate** — LLM (if configured, within budget, not an injection) phrases the beats as JSON
   `{reply, mood, used_beats}`; otherwise the same beats are voiced by scripted lines. `prompt_version`
   (`npc-2026.10.1`) is stored with every reply.
5. **Validate output** — JSON schema; reject markup and meta-language ("as an AI…"); reject any phrase from the
   `leak_markers` of *any fact that has not been revealed* (except words the player themself used or that appear in
   the evidence just shown). One stricter retry, then fallback. The engine's mood is authoritative.
6. **Commit** in one short transaction guarded by `conversation.version`.

### Memory (three layers)

1. **Canonical** — immutable case package + `disclosures`; summaries can never overwrite it.
2. **Character** — `character_memories` (evidence seen, things said, extractive summaries every 8 turns) and the
   disclosure set.
3. **Conversational** — `messages` plus per-session `rag_chunks` (`dialogue`, `memory`) retrieved with a session +
   character ACL; excerpts are treated as untrusted data in prompts.

### Quality controls

Structured response schema · prompt versioning · context limits (6 recent messages, 2 retrieved excerpts, 600-char
inputs) · provider timeouts and bounded retries with exponential backoff (`LLMError.retryable`: timeout, rate limit,
unavailable; **not** auth/bad-request) · per-conversation token budget (`RAAZ_CONVERSATION_TOKEN_BUDGET`) · per-user
LLM rate limit · metrics: `raaz_llm_calls_total`, `raaz_llm_tokens_total`, `raaz_llm_latency_seconds`,
`raaz_npc_output_rejected_total`, `raaz_npc_fallback_total`. `raaz_llm_estimated_cost_usd_total` exists only if you
configure per-1k-token prices and is an **estimate**.

### Fallback mode — never disguised

Without a provider (or after any failure) the response carries `generation.mode = "fallback"` with a `reason`
(`no_llm_configured`, `provider_timeout`, `output_rejected`, `token_budget_exhausted`, `injection_deflected`) and a
label the UI displays; replies are tagged `scripted`. The deterministic engine is unaffected.

### Providers

`npc/providers.py`: `AnthropicProvider`, `OpenAICompatProvider` (any OpenAI-compatible endpoint), and a test-only
`ScriptedProvider`. Model names are environment variables. Note: `temperature` is intentionally *not* sent to the
Anthropic SDK (current models manage sampling themselves). **Neither real provider was called during this build** —
the integration is covered by mocked-provider tests only.

## Nazar

Deterministic analysis of the player's verified state (`nazar/service.py`): unchecked statements, unchecked
contradiction pairs among *held* items, unreconciled clocks, unsearched places, uninterviewed people, per-suspect
weight of evidence. Hint levels 1/2/3 escalate specificity (nudge → names items you hold → full breakdown, −0/−1/−2
points). Output separates **observed / interpretation / speculation**, cites RAG sources the player may access, and
never names a culprit. If an LLM is configured it may *rephrase* the structured analysis; the reply is rejected if it
mentions any evidence the player has not collected.
