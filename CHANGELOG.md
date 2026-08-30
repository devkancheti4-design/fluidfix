# Changelog

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
