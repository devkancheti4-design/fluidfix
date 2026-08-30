# fluidfix measured results — 2026-08-30

All headline numbers in the README come from this run. Raw per-bug data ships
in [data/](data/); the corpus, injector, and recorded baselines are in
[fluid-router](https://github.com/devkancheti4-design/fluid-router)
`benchmark/` (note: fluid-router's own `BENCHMARK.md` measures the *original*
blind-search pipeline — a different configuration; its numbers appear below
only in the rows labelled "recorded").

## Corpus

The 33 valid recorded bugs from fluid-router `benchmark/bugs.json`: injected
single-token mutations in humanize 4.16.0, inflection 0.5.1, natsort 8.4.0,
parse 1.22.1, wcwidth 0.8.2, each verified live to fail its library's own
suite. 27 inside the four-act vocabulary, 6 outside (and/or, True/False, */÷).

## Results

| pipeline | observer | applier | in-vocab byte-exact | green-only | oov refused | tokens |
|---|---|---|---|---|---|---|
| fluidfix | Claude Opus 5, one batched call | pointer (v2) | **26/27** | 0 | 6/6 | 125,402 total¹ |
| fluidfix | Claude Opus 5, one batched call | first-match (v1) | 17/27 | 0 | 6/6 | same call |
| recorded blind kernel² | none (whole-file search) | first-match | 17/27 | 2 | 6/6 refused | 0 |
| recorded full Opus 5² | — | — | 22/27 (+5 green-only) | 5 | 5/6 exact, 1 green | 1,322,802 |

¹ Fleet-level figure from the orchestration harness (`subagent_tokens`, all
agent context included) — provenance in `data/lean_arm_tokens.json`. The
recorded full-Opus token column uses fluid-router's own accounting
(`benchmark/tok.json`); the two support the ~10× ratio, not a precise one.

² From fluid-router's committed `benchmark/final.json` / `tok.json`,
independently revalidated on 10 of 33 bugs the same day (live Opus 5 agents:
10/10 green, 10/10 byte-exact, 44.9k tokens/bug).

- Localisation: the batched observer named the correct defective line
  **33/33**. The mechanical localiser alone (frames ∪ failing-test coverage ∪
  AST statement spans) put the true line in the packet **33/33** at 0 tokens.
- Renumbering: with the 27 live in-vocab observations fixed, the kernel's
  decisions were correct under all 16 act-vocabulary translations,
  **432/432**; a lookup table frozen at one numbering scores 27/432.
- Every v1→v2 gap and the single v2 miss (bug 11: a line carrying both a `+`
  and the faulty `-`) trace to the applier's first-match heuristics — the
  router chose the correct act on all 27 observations. The `op_occurrence`
  pointer shipped in this package closes bug 11's class (covered by
  `tests/test_acts.py`).
- Decision speed: fluid-router2's C verifier measures 1.55 ns/decision for
  the authored kernels; this package's pure-Python reference is roughly
  0.6 µs/decision. Either way the marginal decision costs no tokens.

## What was NOT measured

- The fully mechanical fluidfix pipeline (mechanical observer + SBFL
  localisation) was validated end-to-end on individual bugs and the test
  suite, not scored across the full 33-bug corpus. The 17/27 "no model"
  figure above is the recorded blind-kernel result, which searches whole
  files without localisation — a strictly harder configuration.
- Real-bug distributions: this corpus is injected single-token mutations.
  fluid-router's `benchmark/domain/` study measures single-token
  substitutions at ~16% of real one-line fixes, and its per-repository
  dictionary result (+21 points, 62% vs 41%) is a **candidate-containment
  ceiling** with the buggy line supplied — not a realized repair rate.
