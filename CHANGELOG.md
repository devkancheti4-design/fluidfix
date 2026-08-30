# Changelog

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
