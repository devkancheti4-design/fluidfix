# Changelog

## 0.6.0 — 2026-08-31

- **The engine law fused into the guard.** The third machine-authored kernel
  (`act = (4 & ntzb(x-7)) + ntzb(x + (x&128))`) is vendored verbatim in
  `fluidfix/engine.py` — pinned by a fingerprint test (sha256 `48bf50bf…`,
  1,555 chars) — and now rules on every non-green pass instead of hard-coded
  policy:
  - **BUILT+AMB → ADD_STATE**: when two *different* candidates both green the
    suite, the guard refuses and asks for one pinning test instead of
    shipping whichever came first. It never guesses between
    suite-indistinguishable repairs.
  - **CAPPED → RAISE_BUDGET**: when a budget truncated the search (packet
    sampling, or more implicated files than the pass tried), the guard
    escalates — packet ×3/×9, candidate files 24/72 — under a wall-clock cap
    (`--escalate-budget`, default 600s). Refusals state the cap was hit.
  - **REFUTED → HARVEST_COUNTEREXAMPLE / UNREAD → ADD_MATERIAL**: honest,
    specific stops (what was tried; what to install) — never silent.
- **Measured: byte-faithful replays of all four v0.5 misses** (same seeded
  sites, columns, tokens; injection asserted against pinned baselines; raw
  logs in `docs/data/scale/`). Three now repair byte-exact:
  `click/_textwrap.py:18` and `click/termui.py:744` at the default budget,
  `click/utils.py:70` at `--escalate-budget 1800`. The fourth
  (`arrow/locales.py:5468`) still refuses — boundedly, tree untouched, with
  the honest hint — at both 600s and 1800s. Full table in `docs/SCALE.md`.
- **Zero-padded literals now decrement width-preserving** (`034`→`033`,
  never `33`). The round-1 termui replay measured the green-only imposter
  this generated; with the fix the byte-exact restore is generated and wins.
  Regression-tested against the exact replay line.
- 55/55 tests. The law's rulings and each fused path (AMB refusal, CAPPED
  escalation, REFUTED stop) have dedicated tests in
  `tests/test_engine_fusion.py`.

## 0.5.0 — 2026-08-31

- **Large-repo localisation, measured then fixed.** A strict seeded benchmark
  (docs/SCALE.md) scored the shipped pipeline 0/6 on click. Three general
  fixes — file ranking by failing-test-name affinity + coverage specificity
  (not file size), spread-sampled packets (no first-N truncation), and
  appliers that emit every-occurrence candidate sets — took the identical
  sites to 14/18 byte-exact across click, arrow, and sortedcontainers, with
  both held-out repos beating the diagnosed one. All misses autopsied and
  named in docs/SCALE.md; out-of-vocabulary safety 3/3 refused.
- Precision wording sharpened after the first-ever green-only repair on a
  weakly-tested line: fluidfix never ships a repair its suite rejects;
  byte-exactness is bounded by suite strength (14/15 accepted repairs exact
  in this benchmark).

## 0.4.0 — 2026-08-31

- **`fluidfix init` — the zero-tests on-ramp.** Scans the repo, probes every
  module in a subprocess, and generates `test_fluidfix_smoke.py` covering the
  ones that import cleanly today — so a repo with NO tests becomes guardable
  in three commands (install, init, guard). Modules that don't import are
  reported and excluded; existing files are never clobbered without --force.
  The generated file carries the paste-trick template for leveling up to
  value-level guarding. End-to-end tested: init -> guard repairs an
  import-breaking operator flip and commits the restoration.

## 0.3.0 — 2026-08-31

- **Repo-searchable value classes.** Taught transforms may now return a
  candidate SET (list of lines) mined from repo context — `Observation`
  carries `file`, `root`, and `all_lines`; the loop tries each candidate in
  order (bounded at 32) and the suite adjudicates every one. Measured before:
  rule-shaped classes generalized 11/11 exact from one example, value-shaped
  0/5 (all refused). With one context-aware registration, the same held-out
  value bugs now repair byte-exact — and when the correct value exists
  nowhere in the repo, every candidate fails and the guard still refuses with
  the tree byte-identical. The no-wrong-repairs contract is unchanged;
  precision is bounded by suite strength.
- `apply()` retained as the single-candidate back-compat API.

## 0.2.1 — 2026-08-31

- Guard refusals now diagnose themselves: when no candidate file is found and
  `pytest-cov` is missing from the target interpreter, the refusal (and
  `.fluidfix/last_refusal.json`) says exactly that and gives the install
  command. Found live: on pallets/click (1,990 tests) an assert-only failure
  names no source file, so without pytest-cov the guard refused; with it, the
  guard localised and repaired the fault unaided in 71s. Verified again on
  sortedcontainers. Docs now list pytest-cov as a prerequisite.

## 0.2.0 — 2026-08-30

- `--dictionary FILE` on `guard` and `repair`, and `load_dictionary()`: ship a
  versioned per-repo fault-class dictionary (a Python file of `register()`
  calls). One hard example teaches a class; the guard loads it at startup and
  every member of the class is repaired autonomously from then on.
- `commit_repair()` now returns "committed" / "clean" / "failed" so a
  restoration that already matches HEAD is not reported as a failure.
- `docs/media/`: five sub-30s terminal recordings from real runs (live PyPI
  install, guard commit-and-forget, real-library repair, teach-a-class,
  one-hard-example -> whole-class across three files).

## 0.1.0 — 2026-08-30 (r3)

- `fluidfix guard`: commit-and-forget maintenance. Mechanical fault-file
  discovery (traceback frames, else failing-test coverage ranking), one-shot
  CI mode (exit 2 on refusal) or `--interval` watch mode, opt-in `--commit`
  of each restoration, and a machine-readable `.fluidfix/last_refusal.json`
  teach-me signal on refusal. Library API: `guard_once`,
  `find_candidate_files`, `commit_repair`, `write_refusal`.

## 0.1.0 — 2026-08-30 (r2, pre-release review applied)

- `register()`: teach a new fault class from one registration — observation
  contract + transform; the router infers the act code from the same worked
  example. Mechanical observer now covers registered kinds generically.
- Review fixes (all reproduced before fixing): site-local zero simplification
  in `_reduce_literal` (was able to eat an unrelated `-0.5` elsewhere on the
  line); byte-preserving file handling (CRLF/FF-safe, no write on refusal);
  path-boundary coverage matching (same-suffix sibling packages can no longer
  shadow the defect file); root-level modules get a correct default `--cov`
  target; CLI timeout flags (`--suite-timeout`, `--test-timeout`,
  `--candidate-timeout`, defaulting consistently); observer errors are
  diagnosable (truncation, missing text, wrong echoed ids raise instead of
  masquerading as refusals); injected observer clients work without the SDK;
  `acts_tried` counts only real candidates.

## 0.1.0 — 2026-08-30

Initial release.

- Vendored routing kernel (fluid-router, verbatim, `minimal in D∩I`) and
  EMIT/ADVANCE/HALT loop discipline (fluid-router2, verbatim).
- Mechanical localisation: traceback frames ∪ failing-test coverage
  (pytest-cov `--lf`, no `-x`) ∪ AST statement-span expansion. 33/33 true
  lines captured on the benchmark corpus at 0 tokens.
- Observers: `MechanicalObserver` (zero-token) and `ClaudeObserver`
  (Claude Opus 5, batched, schema-forced, with server-side refusal fallbacks).
- Clear-data applier pointers: `literal_value`/`literal_occurrence` (17/27 →
  26/27 in-vocabulary byte-exact on the corpus) and `op_occurrence` (closes
  the last measured miss).
- Safety: green-suite refusal, out-of-vocabulary refusal, byte-exact rollback,
  candidate timeouts, defended oracle (five encoded harness-defect classes).
- `fluidfix` CLI: `repair`, `packet`, `selfcheck`.
