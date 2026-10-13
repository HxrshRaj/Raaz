# Case authoring guide

A case is a Python package under `backend/app/cases/<case_id>/` that builds a `CaseSpec` (`cases/base.py`) and is
registered in `cases/registry.py`. It is the **only** place truth lives. Nothing in it is serialised to clients;
`engine/game.py` projects the safe subset a player has earned.

```
cases/aakhri_gaadi/
  world.py       briefing · locations + hotspots · events · motives · reference docs · clock rule · travel times
  evidence.py    every Evidence (physical, documents, logs, statements, testimony)
  characters.py  Characters and their Facts (what they know / say / when they reveal)
  rules.py       contradictions · alibis · accusation spec (rubric) · private solution narrative
  logs.py        structured machine-log data used by the anomaly detector
  __init__.py    build() -> CaseSpec
```

## Steps

1. **Fix the truth first.** Write the true timeline in *real time* and decide which devices use which clock. Encode
   clock offsets in `ClockSpec`; never leave "what time was it really?" to a model.
2. **Locations & hotspots.** Each `Hotspot` yields evidence; `requires` hides it until prerequisite evidence is held
   (e.g. the watch is only noticeable after the body). Evidence can `unlocks_locations`.
3. **Evidence.** Give each item `description` (seen on pickup) and `examined_detail` (revealed by examining). Put the
   clue-critical nuance (e.g. "pen pressure shows the earlier figure") in `examined_detail` so examination matters.
   `timestamps` carry the clock (`RT` real / `ST` station); `bears_on` states how it bears on each suspect and
   under what prerequisites (e.g. an alibi only holds once the clock rule is known); `aspect` is one of
   motive/presence/meeting/alibi/claim.
4. **Characters & facts.** For each fact decide: what do they *really* know (`text`), what do they say first
   (`public_line`, `public_truthful`), what makes them say the truth (`gate`), what that grants
   (`grants_statement` for a stated claim, `grants_evidence` for revealed testimony), and `leak_markers` — short
   lowercase phrases that must never appear in generated text until the fact is revealed. Add `topics` (retrieval
   vocabulary; use specific words, generic ones are down-weighted) and `evidence_reactions` for items they have no
   gated fact about.
5. **Contradictions.** `ContradictionRule(pairs=…)` lists (statement-or-record, record) pairs; any held pair makes
   the rule establishable via presentation, an explicit check, or a board link.
6. **Alibis.** `AlibiRule.requires` lists *all* evidence needed to establish "X cannot have been there" — include the
   clock evidence when conversion is needed (`ev_clock_slow` stands for "the player knows the offset").
7. **Accusation spec.** Canonical event order, motive (+ acceptable partials), rubric requirements
   (`any_of`, `need`, weights summing to 25), key contradictions, closing threshold and a `must_have_any_of` gate.
8. **Validate.**
   ```bash
   python -m app.cli validate-case        # static integrity: unknown keys, unobtainable evidence, bad gates…
   pytest tests/test_accusation.py        # scripted playthrough must still close the case
   ```
9. **Solvability review** (manual, important): can every deduction be reached from inspectable evidence, timelines,
   conversations or verifiable contradictions *without guessing* or a magic phrase? The test
   `test_case_is_solvable_end_to_end` plays the case using only public API actions.

## Rules of thumb

* Don't make everyone a liar. Mix honest, mistaken, evasive and deceptive-for-unrelated-reasons characters.
* A red herring needs its own *resolving* evidence (e.g. Meera's embezzlement is real but she is on camera at the
  moment of death — if the player has the clock rule).
* Never reveal sequence through list order: the API lists events alphabetically and characters in dossier order
  (`Character.sort`), and tests assert this.
* Keep `public_line`s in the character's voice; they are what players read in fallback mode.
* Bump `CaseSpec.version` when content changes; the RAG corpus rebuilds when the content hash changes.

## Aakhri Gaadi at a glance (spoiler-free)

6 people · 9 locations (3 unlock through evidence) · 55 evidence items (33 physical/documentary + 6 stated claims +
16 testimonies) · 9 contradiction rules · 3 alibi rules · 10 events · 7 motive options · a 12-minute clock error that
matters. A full solution walkthrough intentionally lives only in the test suite (`tests/test_accusation.py`) and the
server-side `solution_narrative`.
